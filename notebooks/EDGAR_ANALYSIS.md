# EDGAR_Transport.ipynb - Comprehensive Analysis

## 1. Overview & Purpose

The notebook implements a complete **emissions data processing pipeline** for the **EDGAR Transport sector** (2000-2024). It combines monthly gridded emissions data from the Copernicus Climate Data Store, applies spatial joins to map grid cells to geographic boundaries (cities, states/provinces, countries), and outputs aggregated datasets at multiple temporal and spatial scales.

**Key Workflow:**
- Combine raw EDGAR Transport NetCDF files (2000-2024) → single uncompressed dataset
- Create reference lookups (grid cells → lat/lon, time provenance)
- Map grid cells to cities, admin-1 regions, and countries via spatial joins
- Aggregate emissions by city, admin-1, and country at monthly/yearly scales
- Export to Parquet (analysis format) and CSV (MCP ingestion format)
- Generate manifest JSON and expanded variants with different spatial coverage

---

## 2. Sectors Processed

**ONLY TRANSPORT SECTOR** - This notebook is specifically for transport emissions:
- Aviation, maritime, and road transport
- All covered under EDGAR v2024 Transport sector codes
- Global 0.1° resolution (~11 km at equator)

**Data Characteristics:**
- **Time Coverage:** January 2000 - December 2023 (288 monthly timesteps)
- **Spatial Resolution:** 0.1° x 0.1° grid cells
- **Variable:** "emissions" (CO₂ equivalent in tonnes)
- **Data Format:** NetCDF4 (xarray-readable)

---

## 3. Key Data Processing Steps

### **Phase 1A: Raw Data Combination**
- **Input:** 24 individual yearly NetCDF files in `bkl_TRANSPORT_emi_nc/`
- **Process:**
  - Open each year's file with xarray
  - Concatenate along time dimension
  - NO normalization, NO time decoding, NO compression (for speed)
  - Preserve raw dimensions: (time=288, lat=1800, lon=3600)

- **Outputs:**
  - `edgar_transport_2000_2024_rawcombined.nc` - uncompressed NetCDF
  - `grid_cells.parquet` - lookup: (lat, lon) → cell_id
  - `provenance.parquet` - lookup: concat_index → raw time value

**Key Config:**
```
RAW_DIR = Path("bkl_TRANSPORT_emi_nc")
OUT_NC = Path("data/curated/edgar_transport_2000_2024_rawcombined.nc")
```

### **Phase 1B: Time Coordinate Repair**
- **Input:** Combined uncompressed NetCDF with raw time values
- **Process:**
  - Verify 288 steps (24 years × 12 months)
  - Convert to CF-compliant numeric time: "days since 2000-01-01"
  - Ensure datetime index is properly encoded for downstream xarray operations

- **Output:**
  - `edgar_transport_2000_2024_rawcombined_fixedtime.nc` - CF-compliant NetCDF

### **Phase 2A: City Aggregation (Hybrid Spatial Join)**
- **Input:**
  - Fixed-time NetCDF
  - UCDB (Global Human Settlement Layer) city polygons (GeoPackage)
  - Natural Earth Admin-0 countries (shapefile)
  - Natural Earth Admin-1 states/provinces (shapefile)

- **Process:**
  1. **Polygon buffering:** Add 30 km buffer around UCDB city polygons to capture adjacent urban sprawl
  2. **ISO3 attachment:** Spatially join UCDB centroids → Admin-0 to attach country codes
  3. **Hybrid mapping strategy:**
     - **Primary:** Polygon intersects - find grid cells within buffered city polygons
     - **Fallback:** Nearest centroid with adaptive radii (0-600 km depending on country density)
     - **Optional:** Country-bounded Voronoi fill (force-assign remaining cells to nearest city within country)
  
  4. **Time aggregation:**
     - Monthly: sum emissions by (city_id, year, month)
     - Yearly: sum emissions by (city_id, year)

- **Config:**
  ```
  BUFFER_KM = 30
  MAX_RADIUS_M = 600_000  # ~600 km fallback
  BATCH_SIZE = 400_000
  CRS_WGS84 = "EPSG:4326"
  CRS_METRIC = "EPSG:6933"  # Equal-area projection for distance
  ```

- **Outputs:**
  - `city-month/transport_city_month.parquet` (primary)
  - `city-month/transport_city_month_expanded.parquet` (wider coverage variant)
  - `city-year/transport_city_year.parquet` (primary)
  - `city-year/transport_city_year_expanded.parquet`

### **Phase 2B: Admin-1 (State/Province) Aggregation**
- **Input:** Same NetCDF, Admin-1 shapefile, Admin-0 for ISO3 attachment
- **Process:**
  1. **Primary join:** Polygon intersects (cell centroid within Admin-1 boundary)
  2. **Fallback:** Nearest polygon with 250 km cap (EPSG:6933 projected)
  3. **Provenance tracking:** Record join_type (intersects|nearest) and distance_m for lineage
  4. **Time aggregation:** Monthly/yearly groupby

- **Config:**
  ```
  MAX_RADIUS_M = 250_000  # 250 km fallback
  CRS_METRIC = "EPSG:6933"
  ```

- **Outputs:**
  - `admin1-month/transport_admin1_month.parquet` (primary & expanded variants)
  - `admin1-year/transport_admin1_year.parquet`

### **Phase 2C: Country (Admin-0) Aggregation**
- **Input:** NetCDF + Admin-0 countries shapefile
- **Process:**
  1. **Intersects join:** Cell centroid within country boundary
  2. **Ocean handling:** Skip nearest fallback for non-land cells (avoids large nearest join over oceans)
  3. **Provenance tracking:** Record join method
  4. **Time aggregation:** Monthly/yearly

- **Config:**
  ```
  MAX_RADIUS_M = 250_000
  # Note: nearest fallback skipped for countries to avoid ocean bloat
  ```

- **Outputs:**
  - `country-month/transport_country_month.parquet` (primary & expanded)
  - `country-year/transport_country_year.parquet`

### **Phase 3: Metadata & Quality Assurance**
- **Stamp metadata columns:** units, source, spatial_res on all Parquet tables
- **Coverage analysis:** Compare city/admin1/country aggregates vs global totals (should be ~85-95% depending on coverage)
- **STL decomposition:** Trend + seasonal + residual for global emissions time series
- **COVID-19 analysis:** 2019-2020 percent change by grid cell (highlight transport collapse)

### **Phase 4: Export & MCP Preparation**
- **Parquet → CSV:** Convert all curated Parquet tables to CSV
- **Consolidated yearly CSV:** Stack all tables (city, admin1, country) into single denormalized CSV for easy LLM ingestion
- **Expanded variants:** Maintain two versions (standard + wider coverage) side-by-side
- **Manifest JSON:** List all CSVs with metadata (geometry type, time aggregation, source)
- **Folder structure:** Organize into `data/csv_datasets/` for MCP ingestion pipeline

---

## 4. Libraries & Dependencies

### Core Data Science Stack
- **xarray** - NetCDF4 reading/writing, multi-dimensional array operations
- **pandas** - Dataframe groupby, aggregation, CSV I/O
- **numpy** - Numerical operations, masking, indexing

### Geospatial Processing
- **geopandas** - Spatial dataframes, polygon/centroid operations
- **shapely** - Geometry (Polygon, Point) construction
- **pyogrio** - Reading GeoPackage/Shapefile layers (improved I/O)

### Analysis & Visualization
- **statsmodels** - STL decomposition for time series
- **matplotlib** - Plotting (STL, 2019-2020 change map, etc.)

### File I/O
- **pyarrow** - Parquet read/write (via pandas)
- **pathlib** - Path operations
- **json** - Manifest serialization
- **gzip, shutil** - Compression utilities

**Version Notes:**
- xarray with h5netcdf engine (recommended over scipy for large NetCDF)
- geopandas 0.13+ recommended (better spatial_join performance)
- pyogrio replaces fiona for GeoPackage/Shapefile reads

---

## 5. What Can Be Extracted Into Separate Modular Scripts

### **Recommended Modularization Strategy**

The notebook contains several highly repetitive patterns that can be extracted into reusable Python modules:

#### **5.1 Spatial Aggregation Module** (`spatial_aggregation.py`)
**Purpose:** Reusable spatial join and aggregation logic

**Functions to extract:**
```python
def ensure_wgs84(gdf, label) -> GeoDataFrame
    """Convert GeoDataFrame to WGS84 (EPSG:4326)"""

def pick_col(gdf, candidates, label, required=True) -> str
    """Auto-detect column name from list of candidates"""

def create_cell_points(grid_nc, crs="EPSG:4326") -> GeoDataFrame
    """Convert grid lat/lon to Point geometries"""

def hybrid_spatial_join(
    points: GeoDataFrame,
    target_geom: GeoDataFrame,
    primary_col: str,
    max_distance_m: float = 250_000,
    metric_crs: str = "EPSG:6933"
) -> DataFrame
    """
    Two-step spatial join:
    1. Primary: polygon/point intersects
    2. Fallback: nearest neighbor with distance cap
    Returns DataFrame with cell→target mapping + provenance
    """

def aggregate_emissions_by_geom(
    grid_nc: str,
    cell_to_geom_map: np.ndarray,
    geom_ids: np.ndarray,
    by_time: str = "monthly"  # or "yearly"
) -> DataFrame
    """
    Chunk-wise aggregation of emissions from NetCDF
    Returns (geom_id, time, emissions_tonnes)
    """
```

**Reusable across all three sectors (Transport, Power, Agriculture):**
- Same grid structure
- Same spatial join logic (only geometry files change)
- Same time aggregation

---

#### **5.2 Time Processing Module** (`time_processing.py`)
**Purpose:** NetCDF time coordinate handling

**Functions to extract:**
```python
def validate_time_steps(ds: xr.Dataset, expected_count: int) -> bool
    """Guard against malformed time coordinates"""

def repair_time_coordinate(
    ds: xr.Dataset,
    start_date: str = "2000-01-01",
    freq: str = "MS"  # Month Start
) -> xr.Dataset
    """Convert raw/malformed time to CF-compliant datetime64"""

def parse_datetime_from_time_var(time_values) -> pd.DatetimeIndex
    """Handle various EDGAR time encodings"""
```

---

#### **5.3 Aggregation & Export Module** (`aggregation_export.py`)
**Purpose:** Standard aggregation patterns and output formats

**Functions to extract:**
```python
def aggregate_to_month_year(
    gdf: DataFrame,
    emissions_col: str = "emissions_tonnes",
    geom_cols: list = ["city_id", "city_name", "country_name", "iso3"],
    include_provenance: bool = True
) -> tuple[DataFrame, DataFrame]
    """
    Returns (monthly_df, yearly_df) with proper column ordering
    Adds MtCO2 conversion, coverage_share, etc.
    """

def stamp_metadata(
    df: DataFrame,
    units: str = "tonnes CO2",
    source: str = "EDGAR v2024",
    sector: str = "transport",
    spatial_res: str = "0.1°"
) -> DataFrame
    """Add standard metadata columns to all curated tables"""

def export_parquet_csv_pairs(
    tables: dict[str, DataFrame],
    output_dir: Path
) -> None
    """
    Save all tables as both Parquet (analysis) and CSV (MCP)
    """

def consolidate_yearly_csv(
    city_year: DataFrame,
    admin1_year: DataFrame,
    country_year: DataFrame,
    output_path: Path
) -> None
    """
    Stack all levels into denormalized CSV for LLM ingestion
    Adds 'admin_level' column: 'city' | 'admin1' | 'country'
    """
```

---

#### **5.4 Geometry Loading Module** (`geometry_loader.py`)
**Purpose:** Reusable geometry file loading with auto-detection

**Functions to extract:**
```python
def load_cities_gdf(
    gpkg_path: str,
    layer_name: str = None,
    buffer_km: float = 30
) -> GeoDataFrame
    """
    Load UCDB or similar urban polygon layer
    Auto-detects geometry/name/id columns
    Applies buffer and returns cleaned GeoDataFrame
    """

def load_admin_boundaries(
    admin_path: str,
    admin_level: int = 1  # 0=countries, 1=states/provinces
) -> GeoDataFrame
    """
    Load Natural Earth or similar admin boundary
    Auto-detects ISO3, name, id columns
    Returns cleaned GeoDataFrame with standard column names
    """

def standardize_gdf_columns(gdf: GeoDataFrame, admin_level: int) -> GeoDataFrame
    """
    Rename columns to standard names:
    - admin0: (country_name, iso3, geometry)
    - admin1: (admin1_name, admin1_geoid, iso3, geometry)
    """
```

---

#### **5.5 Batch Processing Module** (`batch_processor.py`)
**Purpose:** Memory-efficient batched spatial operations

**Functions to extract:**
```python
def batch_spatial_join(
    points: GeoDataFrame,
    target_geom: GeoDataFrame,
    batch_size: int = 400_000,
    predicate: str = "intersects"
) -> DataFrame
    """
    Chunk point GeoDataFrame to avoid memory errors
    Yields results in batches
    """

def batch_aggregate_from_netcdf(
    grid_nc: str,
    variable: str = "emissions",
    time_subset: slice = None,
    batch_size: int = 1_000_000
) -> Iterator[np.ndarray]
    """
    Lazily read and yield chunks from NetCDF
    """
```

---

#### **5.6 QA/Reporting Module** (`quality_assurance.py`)
**Purpose:** Coverage analysis, decomposition, impact analysis

**Functions to extract:**
```python
def compute_coverage_ratio(
    agg_df: DataFrame,
    grid_nc: str,
    by_year: bool = True
) -> Series
    """
    Compare aggregated totals vs global EDGAR total
    Returns coverage_ratio (should be ~0.85-0.95)
    """

def stl_decompose_emissions(
    ds: xr.Dataset,
    period: int = 12
) -> tuple[Series, Series, Series]
    """Returns (trend, seasonal, residual)"""

def covid_impact_analysis(
    ds: xr.Dataset,
    year1: int = 2019,
    year2: int = 2020
) -> xr.DataArray
    """Calculate (year2 - year1) / year1 by grid cell"""

def build_manifest_json(
    csv_dir: Path,
    output_path: Path
) -> None
    """
    Auto-scan CSV files, infer metadata, write manifest
    Includes geometry_type, time_agg, row_count, columns
    """
```

---

#### **5.7 Config Module** (`sector_config.py`)
**Purpose:** Centralized configuration for all three sectors

**Content:**
```python
SECTORS = {
    "transport": {
        "raw_dir": "bkl_TRANSPORT_emi_nc",
        "output_prefix": "transport",
        "time_range": (2000, 2024),
        "frequencies": ["monthly", "yearly"],
    },
    "power": {
        "raw_dir": "bkl_POWER_emi_nc",
        "output_prefix": "power",
        # ... similar structure
    },
    # ...
}

# Standard parameters (same across all sectors)
BATCH_SIZE = 400_000
MAX_RADIUS_M = {"admin0": 250_000, "admin1": 250_000, "city": 600_000}
CRS_WGS84 = "EPSG:4326"
CRS_METRIC = "EPSG:6933"
BUFFER_KM = 30  # City polygon buffer
```

---

### **5.8 Recommended New Module Structure**

```
preprocessing/
├── __init__.py
├── sector_config.py          # ← Centralized config for all sectors
├── geometry_loader.py        # ← GeoDataFrame loading/standardization
├── spatial_aggregation.py    # ← Two-step spatial join logic
├── batch_processor.py        # ← Memory-efficient chunking
├── time_processing.py        # ← NetCDF time handling
├── aggregation_export.py     # ← Standard agg + export patterns
├── quality_assurance.py      # ← Coverage, STL, impact analysis
│
└── pipelines/
    ├── __init__.py
    ├── transport_pipeline.py  # Main entry point for Transport
    ├── power_pipeline.py      # (future) Power sector
    └── agriculture_pipeline.py # (future) Agriculture sector
```

---

### **5.9 Refactored Transport Pipeline**

**New `transport_pipeline.py` would become:**
```python
from preprocessing import (
    load_cities_gdf, load_admin_boundaries,
    create_cell_points, hybrid_spatial_join,
    aggregate_emissions_by_geom, aggregate_to_month_year,
    export_parquet_csv_pairs, compute_coverage_ratio
)
from sector_config import SECTORS, BATCH_SIZE, MAX_RADIUS_M

def run_transport_pipeline(input_dir: str, output_dir: str):
    """Main orchestration function"""
    
    # Phase 1: Combine NetCDF
    combine_edgar_netcdf(
        input_dir / "bkl_TRANSPORT_emi_nc",
        output_dir / "edgar_transport_rawcombined.nc"
    )
    
    # Phase 2A: Cities
    cities = load_cities_gdf("data/geo/GHS_UCDB/*.gpkg", buffer_km=30)
    countries = load_admin_boundaries("data/geo/ne_10m_admin_0", admin_level=0)
    
    city_map = hybrid_spatial_join(
        create_cell_points(grid_nc),
        cities, "ID_UC_G0",
        max_distance_m=MAX_RADIUS_M["city"]
    )
    
    city_month, city_year = aggregate_to_month_year(
        city_map, include_provenance=True
    )
    export_parquet_csv_pairs({"city_month": city_month, ...}, output_dir)
    
    # ... similar for admin1, admin0
    
    # Phase 3: QA
    compute_coverage_ratio(city_year, grid_nc)
    stl_decompose_emissions(grid_nc)
```

This would reduce the notebook to just orchestration logic, making it much more maintainable.

---

## 6. Implementation Priority for Modularization

**Tier 1 (High ROI - reusable across all sectors):**
1. `spatial_aggregation.py` - 80% of the cell processing code
2. `geometry_loader.py` - Used in every sector
3. `sector_config.py` - Eliminates hardcoded paths

**Tier 2 (Medium ROI):**
4. `aggregation_export.py` - Standard aggregation patterns
5. `time_processing.py` - Handles EDGAR quirks

**Tier 3 (Nice to have):**
6. `quality_assurance.py` - Optional reporting
7. `batch_processor.py` - Helps with very large grids

---

## 7. Data Quality Notes

- **Coverage:** Aggregated sectors typically cover 85-95% of global EDGAR totals (rest is ocean/gaps)
- **Time steps:** Exactly 288 months (2000-01 to 2023-12)
- **Provenance tracking:** join_type (intersects|nearest) + distance_m recorded for lineage
- **Expanded variants:** Wider buffer (40 km) + wider nearest radius (350 km) provide higher coverage but lower accuracy
- **Missing data:** Ocean cells remain unmapped (by design) for country-level data

