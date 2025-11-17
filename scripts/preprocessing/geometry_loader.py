"""
Geometry loader for EDGAR preprocessing.

Handles loading and standardizing geographic boundary files
for spatial aggregation.
"""

import geopandas as gpd
from pathlib import Path
from typing import Dict, Optional
import logging

from sector_config import GEO_FILES

logger = logging.getLogger(__name__)


class GeometryLoader:
    """Load and manage geographic boundary datasets."""

    def __init__(self):
        self.geometries: Dict[str, gpd.GeoDataFrame] = {}
        self._loaded = False

    def load_all(self) -> None:
        """Load all geographic datasets."""
        logger.info("Loading geographic boundary files...")

        for level, path in GEO_FILES.items():
            self.geometries[level] = self._load_geometry_file(path, level)

        self._loaded = True
        logger.info(f"Loaded {len(self.geometries)} geographic datasets")

    def _load_geometry_file(self, path: Path, level: str) -> gpd.GeoDataFrame:
        """Load and standardize a single geometry file."""
        if not path.exists():
            raise FileNotFoundError(f"Geometry file not found: {path}")

        logger.info(f"Loading {level} from {path}")
        gdf = gpd.read_file(path)

        # Standardize column names
        gdf = self._standardize_columns(gdf, level)

        # Ensure valid geometries
        gdf = gdf[gdf.geometry.is_valid].copy()

        # Reproject to WGS84 if needed
        if gdf.crs != "EPSG:4326":
            logger.info(f"Reprojecting {level} to EPSG:4326")
            gdf = gdf.to_crs("EPSG:4326")

        logger.info(f"Loaded {len(gdf)} {level} features")
        return gdf

    def _standardize_columns(self, gdf: gpd.GeoDataFrame, level: str) -> gpd.GeoDataFrame:
        """Standardize column names based on admin level."""
        column_mapping = {
            "admin0": {
                "name": "country",
                "iso3": "iso3",
                "iso2": "iso2"
            },
            "admin1": {
                "name": "state",
                "country": "country",
                "iso3": "iso3"
            },
            "cities": {
                "name": "city",
                "country": "country",
                "admin1": "state",
                "population": "population"
            }
        }

        if level in column_mapping:
            # Rename columns if they exist
            rename_dict = {}
            for old_col, new_col in column_mapping[level].items():
                if old_col in gdf.columns:
                    rename_dict[old_col] = new_col

            if rename_dict:
                gdf = gdf.rename(columns=rename_dict)

        # Ensure 'name' column exists
        if 'name' not in gdf.columns:
            if 'NAME' in gdf.columns:
                gdf['name'] = gdf['NAME']
            elif 'City' in gdf.columns:
                gdf['name'] = gdf['City']
            elif 'Country' in gdf.columns:
                gdf['name'] = gdf['Country']

        return gdf

    def get(self, level: str) -> gpd.GeoDataFrame:
        """Get geometry for a specific admin level."""
        if not self._loaded:
            self.load_all()

        if level not in self.geometries:
            raise ValueError(f"Unknown admin level: {level}")

        return self.geometries[level].copy()

    def get_all(self) -> Dict[str, gpd.GeoDataFrame]:
        """Get all loaded geometries."""
        if not self._loaded:
            self.load_all()

        return {k: v.copy() for k, v in self.geometries.items()}


# Convenience function
def load_geometries() -> Dict[str, gpd.GeoDataFrame]:
    """Load all geometries and return as dictionary."""
    loader = GeometryLoader()
    return loader.get_all()


if __name__ == "__main__":
    # Test loading
    logging.basicConfig(level=logging.INFO)
    loader = GeometryLoader()
    geometries = loader.get_all()

    print("\nLoaded geometries:")
    for level, gdf in geometries.items():
        print(f"  {level}: {len(gdf)} features, columns: {list(gdf.columns)}")
