# Scripts Directory

This directory contains all utility scripts for data processing, database management, and analysis.

## Directory Structure

```
scripts/
├── preprocessing/          # Data preprocessing scripts for EDGAR sectors
│   ├── sector_config.py    # Centralized configuration for all sectors
│   ├── geometry_loader.py  # Geographic boundary file loader
│   ├── spatial_aggregation.py  # Spatial join and aggregation logic
│   ├── process_transport_sector.py  # Transport sector pipeline
│   ├── process_power_sector.py      # Power industry sector pipeline
│   ├── process_all_sectors.py       # Batch process all sectors
│   └── (legacy scripts...)
├── database/               # Database management and optimization
│   ├── analyze_database.py
│   ├── apply_database_indexes.py
│   ├── create_database_indexes.sql
│   ├── create_materialized_views.py
│   └── create_materialized_views.sql
└── analysis/               # Analysis and validation scripts
    ├── audit_dependencies.py
    ├── validate_phase5.py
    └── database_analysis_report.txt
```

## Preprocessing Scripts

### Modular Processing Pipeline

The preprocessing pipeline has been refactored into modular, reusable components:

#### Core Modules

**`sector_config.py`** - Central configuration
- Defines all sector metadata (transport, power, waste, agriculture)
- Configures paths, parameters, and thresholds
- Provides helper functions for path resolution

**`geometry_loader.py`** - Geographic data loader
- Loads and standardizes boundary files (countries, states, cities)
- Auto-detects and normalizes column names
- Ensures valid geometries and proper CRS

**`spatial_aggregation.py`** - Spatial join engine
- Implements hybrid spatial join algorithm:
  1. Polygon intersection (primary method)
  2. Nearest centroid fallback (for unmatched points)
- Aggregates gridded emissions to administrative boundaries
- Tracks provenance and coverage metrics

#### Sector Processors

**`process_transport_sector.py`** - Transport sector pipeline
```bash
python scripts/preprocessing/process_transport_sector.py \
  --raw-data data/raw/transport \
  --output data/curated-2
```

Processes:
- Aviation, maritime, and road transport emissions
- 0.1° resolution NetCDF files (2000-2023)
- Outputs: admin0, admin1, city levels (monthly + yearly)

**`process_power_sector.py`** - Power industry pipeline
```bash
python scripts/preprocessing/process_power_sector.py \
  --raw-data data/raw/power-industry \
  --output data/curated-2
```

Processes power generation and industrial energy emissions using the same pipeline.

**`process_all_sectors.py`** - Batch processor
```bash
# Process all configured sectors
python scripts/preprocessing/process_all_sectors.py \
  --raw-data-dir data/raw \
  --output-dir data/curated-2

# Process specific sectors
python scripts/preprocessing/process_all_sectors.py \
  --sectors transport power-industry
```

### Pipeline Workflow

1. **Load raw NetCDF files** - Combines yearly files, repairs time coordinates
2. **Convert to DataFrame** - Filters non-zero emissions
3. **Load geometries** - Standardizes boundary files
4. **Spatial aggregation** - Hybrid join to admin boundaries
5. **Export results** - Parquet + CSV for monthly and yearly data

### Adding New Sectors

To add a new sector (e.g., agriculture):

1. **Update `sector_config.py`**:
```python
SECTORS["agriculture"] = {
    "name": "Agriculture",
    "edgar_code": "AGR",
    "raw_pattern": "v2024_AGR_*.0.1x0.1.nc",
    "time_range": (2000, 2023),
    "subsectors": []
}
```

2. **Create processor** (or reuse `TransportProcessor`):
```python
# scripts/preprocessing/process_agriculture_sector.py
from process_transport_sector import TransportProcessor

class AgricultureProcessor(TransportProcessor):
    def __init__(self):
        super().__init__(sector="agriculture")
```

3. **Register in `process_all_sectors.py`**:
```python
PROCESSORS["agriculture"] = AgricultureProcessor
```

4. **Run**:
```bash
python scripts/preprocessing/process_all_sectors.py --sectors agriculture
```

## Database Scripts

Located in `scripts/database/`:

- **`analyze_database.py`** - Generate database statistics and analysis
- **`apply_database_indexes.py`** - Apply performance indexes to tables
- **`create_database_indexes.sql`** - SQL index definitions
- **`create_materialized_views.py`** - Create optimized views
- **`create_materialized_views.sql`** - Materialized view definitions

Usage:
```bash
# Analyze database
python scripts/database/analyze_database.py

# Apply indexes
python scripts/database/apply_database_indexes.py
```

## Analysis Scripts

Located in `scripts/analysis/`:

- **`audit_dependencies.py`** - Check dependency versions and security
- **`validate_phase5.py`** - Validate Phase 5 implementation
- **`database_analysis_report.txt`** - Generated analysis report

## Legacy Scripts

The following scripts are kept for backward compatibility but may be deprecated:

- `scripts/preprocessing/expand_cities_dataset.py`
- `scripts/preprocessing/add_expanded_datasets.py`
- `scripts/preprocessing/create_power_monthly.py`
- `scripts/preprocessing/add_monthly_to_manifest.py`

These will be phased out as the modular pipeline matures.

## Dependencies

All scripts use the dependencies defined in `pyproject.toml` and managed by UV:

```bash
# Install dependencies
uv sync

# Run a script
uv run python scripts/preprocessing/process_transport_sector.py --help
```

## Development

### Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to all public functions
- Keep functions focused and modular

### Testing

Test scripts before committing:

```bash
# Test configuration loading
python -c "from scripts.preprocessing.sector_config import *; print(SECTORS)"

# Test geometry loading
python scripts/preprocessing/geometry_loader.py

# Dry run processing
python scripts/preprocessing/process_transport_sector.py --help
```

## Contributing

When adding new scripts:

1. Place in appropriate subdirectory (`preprocessing/`, `database/`, `analysis/`)
2. Add to this README with usage examples
3. Update `sector_config.py` if adding new sectors
4. Ensure compatibility with UV package manager
5. Add type hints and docstrings

## Questions?

See the main README.md or check documentation in `docs/` directory.
