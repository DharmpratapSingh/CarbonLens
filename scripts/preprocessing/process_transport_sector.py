#!/usr/bin/env python3
"""
Transport Sector Preprocessing Pipeline

Processes EDGAR v2024 Transport sector emissions data:
- Reads NetCDF files (2000-2023)
- Repairs time coordinates
- Aggregates to admin0, admin1, and city levels
- Exports to Parquet and CSV
"""

import logging
import sys
from pathlib import Path
import xarray as xr
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

from sector_config import get_sector_config, get_output_path, PROCESSING_CONFIG
from geometry_loader import load_geometries
from spatial_aggregation import aggregate_sector_emissions

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransportProcessor:
    """Process Transport sector emissions data."""

    def __init__(self, sector="transport"):
        self.sector = sector
        self.config = get_sector_config(sector)
        self.geometries = None

    def load_raw_data(self, raw_data_path: Path) -> xr.Dataset:
        """Load and combine NetCDF files."""
        logger.info(f"Loading raw data from {raw_data_path}")

        # Find all NetCDF files matching pattern
        pattern = self.config["raw_pattern"]
        nc_files = sorted(raw_data_path.glob(pattern))

        if not nc_files:
            raise FileNotFoundError(f"No NetCDF files found matching {pattern}")

        logger.info(f"Found {len(nc_files)} NetCDF files")

        # Open and combine all files
        ds = xr.open_mfdataset(
            nc_files,
            combine='by_coords',
            parallel=True
        )

        return ds

    def repair_time_coordinates(self, ds: xr.Dataset) -> xr.Dataset:
        """Repair time coordinates to CF-compliant format."""
        logger.info("Repairing time coordinates...")

        # Convert time to datetime if needed
        if 'time' in ds.coords:
            # Ensure proper datetime64 format
            times = pd.to_datetime(ds.time.values)
            ds = ds.assign_coords(time=times)

            # Set time attributes
            ds.time.attrs['long_name'] = 'time'
            ds.time.attrs['standard_name'] = 'time'
            ds.time.attrs['calendar'] = 'gregorian'

        return ds

    def grid_to_dataframe(self, ds: xr.Dataset, variable_name: str = "emissions") -> pd.DataFrame:
        """Convert gridded Dataset to DataFrame."""
        logger.info("Converting grid to DataFrame...")

        # Get the main emissions variable
        if variable_name not in ds:
            # Try to find emissions variable
            for var in ds.data_vars:
                if 'emission' in var.lower() or 'co2' in var.lower():
                    variable_name = var
                    break

        # Convert to DataFrame
        df = ds[variable_name].to_dataframe().reset_index()

        # Rename columns if needed
        if 'latitude' in df.columns:
            df = df.rename(columns={'latitude': 'lat'})
        if 'longitude' in df.columns:
            df = df.rename(columns={'longitude': 'lon'})

        # Remove zero/null emissions
        df = df[df[variable_name] > 0].copy()

        logger.info(f"Grid DataFrame: {len(df):,} non-zero emission points")
        return df

    def process(self, raw_data_path: Path, output_dir: Path) -> Dict[str, Path]:
        """
        Complete processing pipeline for transport sector.

        Args:
            raw_data_path: Path to raw NetCDF files
            output_dir: Directory for output files

        Returns:
            Dictionary mapping admin level to output file path
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {self.config['name']} Sector")
        logger.info(f"{'='*60}\n")

        # Step 1: Load raw data
        ds = self.load_raw_data(raw_data_path)

        # Step 2: Repair time coordinates
        ds = self.repair_time_coordinates(ds)

        # Step 3: Convert to DataFrame
        emissions_df = self.grid_to_dataframe(ds)

        # Step 4: Load geometries
        logger.info("Loading geographic boundaries...")
        self.geometries = load_geometries()

        # Step 5: Spatial aggregation
        admin_levels = ["admin0", "admin1", "cities"]
        results = aggregate_sector_emissions(
            emissions_df,
            self.sector,
            self.geometries,
            admin_levels
        )

        # Step 6: Export results
        output_files = {}
        for level, df in results.items():
            for temporal in ["monthly", "yearly"]:
                # Aggregate to yearly if needed
                if temporal == "yearly":
                    if 'time' in df.columns:
                        df_export = df.copy()
                        df_export['year'] = pd.to_datetime(df_export['time']).dt.year
                        group_cols = [col for col in df_export.columns
                                      if col not in ['time', 'emissions', 'year']]
                        df_export = df_export.groupby(group_cols + ['year'],
                                                       as_index=False)['emissions'].sum()
                    else:
                        continue
                else:
                    df_export = df.copy()

                # Export to Parquet
                output_path = get_output_path(self.sector, level, temporal)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                logger.info(f"Exporting {level}/{temporal} to {output_path}")
                df_export.to_parquet(output_path, compression='snappy', index=False)

                # Also export CSV for smaller datasets
                if len(df_export) < 100000:
                    csv_path = output_path.with_suffix('.csv')
                    df_export.to_csv(csv_path, index=False)

                output_files[f"{level}_{temporal}"] = output_path

        logger.info(f"\n{'='*60}")
        logger.info(f"Processing complete! Generated {len(output_files)} files")
        logger.info(f"{'='*60}\n")

        return output_files


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Process Transport sector emissions")
    parser.add_argument(
        '--raw-data',
        type=Path,
        required=True,
        help='Path to raw NetCDF files'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path('data/curated-2'),
        help='Output directory for processed files'
    )

    args = parser.parse_args()

    processor = TransportProcessor()
    output_files = processor.process(args.raw_data, args.output)

    print("\nOutput files:")
    for key, path in output_files.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
