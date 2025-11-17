"""
Centralized configuration for EDGAR sector preprocessing.

This module contains all paths, parameters, and constants used across
the preprocessing pipeline for different sectors.
"""

from pathlib import Path
from typing import Dict, Any

# Base paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "curated-2"
GEO_DATA_DIR = DATA_DIR / "geo"
WAREHOUSE_DIR = DATA_DIR / "warehouse"

# Sector configurations
SECTORS = {
    "transport": {
        "name": "Transport",
        "edgar_code": "TRO",
        "description": "Aviation, maritime, and road transport emissions",
        "raw_pattern": "v2024_FT2023_*.0.1x0.1.nc",
        "time_range": (2000, 2023),
        "subsectors": ["aviation", "maritime", "road"]
    },
    "power-industry": {
        "name": "Power Industry",
        "edgar_code": "ENE",
        "description": "Power generation and industrial energy emissions",
        "raw_pattern": "v2024_ENE_*.0.1x0.1.nc",
        "time_range": (2000, 2023),
        "subsectors": ["coal", "gas", "oil"]
    },
    "waste": {
        "name": "Waste",
        "edgar_code": "WAS",
        "description": "Waste treatment and disposal emissions",
        "raw_pattern": "v2024_WAS_*.0.1x0.1.nc",
        "time_range": (2000, 2023),
        "subsectors": []
    },
    "agriculture": {
        "name": "Agriculture",
        "edgar_code": "AGR",
        "description": "Agricultural emissions",
        "raw_pattern": "v2024_AGR_*.0.1x0.1.nc",
        "time_range": (2000, 2023),
        "subsectors": []
    }
}

# Geographic data files
GEO_FILES = {
    "cities": GEO_DATA_DIR / "cities.geojson",
    "admin1": GEO_DATA_DIR / "admin1.geojson",
    "admin0": GEO_DATA_DIR / "countries.geojson"
}

# Spatial aggregation parameters
SPATIAL_CONFIG = {
    "grid_resolution": 0.1,  # degrees
    "admin_levels": ["admin0", "admin1", "cities"],
    "fallback_radius_km": 50,  # for nearest centroid matching
    "min_coverage_threshold": 0.01,  # minimum emission value to include
}

# Processing parameters
PROCESSING_CONFIG = {
    "chunk_size": 12,  # months to process at once
    "batch_years": 3,  # years per batch for memory efficiency
    "parallel_workers": 4,
    "output_formats": ["parquet", "csv"]
}

# Quality assurance thresholds
QA_CONFIG = {
    "min_coverage_pct": 85,  # minimum % of grid cells captured
    "max_null_pct": 5,  # maximum % of null values allowed
    "outlier_std_threshold": 6,  # standard deviations for outlier detection
}

# Database configuration
DB_CONFIG = {
    "db_path": WAREHOUSE_DIR / "climategpt.duckdb",
    "schema_version": "v2024",
    "compression": "snappy"
}


def get_sector_config(sector: str) -> Dict[str, Any]:
    """Get configuration for a specific sector."""
    if sector not in SECTORS:
        raise ValueError(f"Unknown sector: {sector}. Available: {list(SECTORS.keys())}")
    return SECTORS[sector]


def get_output_path(sector: str, admin_level: str, temporal: str) -> Path:
    """Get output path for processed data."""
    return PROCESSED_DATA_DIR / f"{sector}_{admin_level}_{temporal}.parquet"


def get_raw_data_path(sector: str) -> Path:
    """Get path to raw NetCDF files for a sector."""
    return RAW_DATA_DIR / sector


# Export commonly used paths
__all__ = [
    "SECTORS",
    "GEO_FILES",
    "SPATIAL_CONFIG",
    "PROCESSING_CONFIG",
    "QA_CONFIG",
    "DB_CONFIG",
    "get_sector_config",
    "get_output_path",
    "get_raw_data_path",
]
