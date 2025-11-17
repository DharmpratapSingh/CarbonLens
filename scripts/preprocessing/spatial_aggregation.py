"""
Spatial aggregation module for EDGAR emissions data.

Implements hybrid spatial join algorithm to aggregate gridded emissions
to administrative boundaries (countries, states, cities).
"""

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from typing import Dict, List, Tuple, Optional
import logging
from tqdm import tqdm

from sector_config import SPATIAL_CONFIG

logger = logging.getLogger(__name__)


class SpatialAggregator:
    """Aggregate gridded emissions to administrative boundaries."""

    def __init__(
        self,
        geometries: Dict[str, gpd.GeoDataFrame],
        fallback_radius_km: float = SPATIAL_CONFIG["fallback_radius_km"]
    ):
        """
        Initialize spatial aggregator.

        Args:
            geometries: Dictionary of GeoDataFrames for each admin level
            fallback_radius_km: Radius for nearest centroid fallback
        """
        self.geometries = geometries
        self.fallback_radius_km = fallback_radius_km
        self._prepared_geometries = {}

    def aggregate(
        self,
        emissions_grid: pd.DataFrame,
        admin_level: str,
        time_col: str = "time",
        lat_col: str = "lat",
        lon_col: str = "lon",
        value_col: str = "emissions"
    ) -> pd.DataFrame:
        """
        Aggregate emissions grid to administrative boundaries.

        Args:
            emissions_grid: DataFrame with lat, lon, time, emissions columns
            admin_level: Target admin level (admin0, admin1, cities)
            time_col: Name of time column
            lat_col: Name of latitude column
            lon_col: Name of longitude column
            value_col: Name of emissions value column

        Returns:
            Aggregated DataFrame with admin boundaries and emissions
        """
        logger.info(f"Aggregating to {admin_level} level...")

        # Get target geometries
        if admin_level not in self.geometries:
            raise ValueError(f"Unknown admin level: {admin_level}")

        target_gdf = self.geometries[admin_level].copy()

        # Convert emissions grid to GeoDataFrame
        logger.info("Converting grid to points...")
        grid_gdf = self._grid_to_geodataframe(
            emissions_grid, lat_col, lon_col, time_col, value_col
        )

        # Perform spatial join
        logger.info("Performing spatial join...")
        matched = self._spatial_join(grid_gdf, target_gdf, admin_level)

        # Aggregate by admin unit and time
        logger.info("Aggregating emissions...")
        result = self._aggregate_emissions(matched, admin_level, time_col, value_col)

        logger.info(f"Aggregated {len(result)} records for {admin_level}")
        return result

    def _grid_to_geodataframe(
        self,
        df: pd.DataFrame,
        lat_col: str,
        lon_col: str,
        time_col: str,
        value_col: str
    ) -> gpd.GeoDataFrame:
        """Convert emissions grid DataFrame to GeoDataFrame."""
        # Create point geometries
        geometry = [Point(lon, lat) for lon, lat in zip(df[lon_col], df[lat_col])]

        gdf = gpd.GeoDataFrame(
            df[[time_col, value_col]],
            geometry=geometry,
            crs="EPSG:4326"
        )

        return gdf

    def _spatial_join(
        self,
        grid_gdf: gpd.GeoDataFrame,
        target_gdf: gpd.GeoDataFrame,
        admin_level: str
    ) -> gpd.GeoDataFrame:
        """
        Perform hybrid spatial join: polygon intersect + nearest centroid fallback.
        """
        # Phase 1: Polygon intersection
        logger.info("Phase 1: Polygon intersection...")
        matched = gpd.sjoin(
            grid_gdf,
            target_gdf,
            how="inner",
            predicate="intersects"
        )

        n_matched = len(matched)
        n_total = len(grid_gdf)
        coverage_pct = (n_matched / n_total) * 100

        logger.info(f"Matched {n_matched:,}/{n_total:,} points ({coverage_pct:.1f}%)")

        # Phase 2: Nearest centroid fallback for unmatched points
        if coverage_pct < 95:
            logger.info("Phase 2: Nearest centroid fallback...")
            matched_indices = matched.index
            unmatched = grid_gdf[~grid_gdf.index.isin(matched_indices)].copy()

            if len(unmatched) > 0:
                fallback = self._nearest_centroid_match(unmatched, target_gdf, admin_level)
                matched = pd.concat([matched, fallback], ignore_index=True)

                new_coverage = (len(matched) / n_total) * 100
                logger.info(f"After fallback: {len(matched):,}/{n_total:,} ({new_coverage:.1f}%)")

        return matched

    def _nearest_centroid_match(
        self,
        unmatched_gdf: gpd.GeoDataFrame,
        target_gdf: gpd.GeoDataFrame,
        admin_level: str
    ) -> gpd.GeoDataFrame:
        """Match unmatched points to nearest admin unit centroid."""
        # Calculate centroids of target geometries
        target_centroids = target_gdf.copy()
        target_centroids['geometry'] = target_centroids.geometry.centroid

        # Find nearest centroid for each unmatched point
        matched_indices = []

        for idx, point in tqdm(unmatched_gdf.iterrows(), total=len(unmatched_gdf), desc="Nearest matching"):
            distances = target_centroids.geometry.distance(point.geometry)
            nearest_idx = distances.idxmin()

            # Only match if within fallback radius
            min_distance_km = distances[nearest_idx] * 111  # approx km per degree

            if min_distance_km <= self.fallback_radius_km:
                matched_indices.append((idx, nearest_idx))

        # Create matched GeoDataFrame
        if matched_indices:
            matched_rows = []
            for grid_idx, target_idx in matched_indices:
                row = unmatched_gdf.loc[grid_idx].to_dict()
                # Add target admin attributes
                for col in target_gdf.columns:
                    if col != 'geometry':
                        row[col] = target_gdf.loc[target_idx, col]
                matched_rows.append(row)

            return gpd.GeoDataFrame(matched_rows, crs="EPSG:4326")
        else:
            return gpd.GeoDataFrame(columns=unmatched_gdf.columns, crs="EPSG:4326")

    def _aggregate_emissions(
        self,
        matched_gdf: gpd.GeoDataFrame,
        admin_level: str,
        time_col: str,
        value_col: str
    ) -> pd.DataFrame:
        """Aggregate emissions by admin unit and time."""
        # Determine grouping columns based on admin level
        group_cols = [time_col]

        if admin_level == "admin0":
            group_cols.append("name")  # country name
        elif admin_level == "admin1":
            group_cols.extend(["name", "country"])  # state name, country
        elif admin_level == "cities":
            group_cols.extend(["name", "country", "state"])  # city, country, state

        # Aggregate
        result = matched_gdf.groupby(group_cols, as_index=False)[value_col].sum()

        # Sort by time and name
        result = result.sort_values([time_col] + group_cols[1:])

        return result


def aggregate_sector_emissions(
    emissions_df: pd.DataFrame,
    sector: str,
    geometries: Dict[str, gpd.GeoDataFrame],
    admin_levels: Optional[List[str]] = None
) -> Dict[str, pd.DataFrame]:
    """
    Aggregate emissions for a sector across multiple admin levels.

    Args:
        emissions_df: Emissions grid DataFrame
        sector: Sector name
        geometries: Geographic boundaries
        admin_levels: List of admin levels to aggregate to

    Returns:
        Dictionary mapping admin level to aggregated DataFrame
    """
    if admin_levels is None:
        admin_levels = SPATIAL_CONFIG["admin_levels"]

    aggregator = SpatialAggregator(geometries)
    results = {}

    for level in admin_levels:
        logger.info(f"\n=== Aggregating {sector} to {level} ===")
        results[level] = aggregator.aggregate(emissions_df, level)

    return results


if __name__ == "__main__":
    # Test aggregation with sample data
    logging.basicConfig(level=logging.INFO)

    print("Spatial aggregation module loaded successfully")
    print(f"Fallback radius: {SPATIAL_CONFIG['fallback_radius_km']} km")
