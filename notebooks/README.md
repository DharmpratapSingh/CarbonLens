# Notebooks Directory

This directory contains Jupyter notebooks for data exploration and analysis.

## Contents

### EDGAR_Transport.ipynb

**Large preprocessing notebook (694 KB)** - Original EDGAR Transport sector processing pipeline.

**What it does:**
- Combines 24 yearly NetCDF files (2000-2023) for Transport sector
- Repairs time coordinates to CF-compliant format
- Performs spatial aggregation to cities, states, and countries
- Implements hybrid spatial join algorithm
- Exports to Parquet/CSV for MCP server

**Status:** This notebook has been **refactored into modular scripts** in `scripts/preprocessing/`:
- `sector_config.py` - Configuration
- `geometry_loader.py` - Geographic data loading
- `spatial_aggregation.py` - Spatial join engine
- `process_transport_sector.py` - Transport pipeline
- `process_power_sector.py` - Power pipeline
- `process_all_sectors.py` - Batch processor

**Use this notebook for:**
- Understanding the original processing logic
- Prototyping new analysis approaches
- Debugging spatial aggregation issues

**For production processing:** Use the modular scripts in `scripts/preprocessing/` instead.

## Analysis Documentation

### EDGAR_ANALYSIS_SUMMARY.txt

Executive summary of the EDGAR Transport notebook analysis:
- What the notebook does (5-minute read)
- Sectors, phases, and libraries
- Extractable components overview
- Quick reference tables

### EDGAR_ANALYSIS.md

Technical deep dive into the notebook:
- Complete phase-by-phase breakdown
- 7 modular components with function signatures
- Proposed directory structure
- Code examples for refactoring

### EDGAR_PIPELINE_ARCHITECTURE.txt

Visual reference documentation:
- Data flow diagrams
- Module dependency graphs
- Spatial join algorithms (with ASCII art)
- Output schemas and config parameters

### README_ANALYSIS.md

Navigation guide to all analysis documentation with implementation roadmap and ROI estimates.

## Development Workflow

### For Exploration

1. **Start Jupyter:**
```bash
uv run jupyter notebook
```

2. **Open notebook:**
Navigate to `notebooks/EDGAR_Transport.ipynb`

3. **Explore:**
- Review processing steps
- Test modifications
- Prototype new features

### For Production

**Don't use notebooks for production processing!** Instead:

1. **Use modular scripts:**
```bash
cd scripts/preprocessing
uv run python process_transport_sector.py --raw-data ../../data/raw/transport
```

2. **Benefits of scripts:**
- Reproducible and testable
- Version controlled
- Easier to debug
- Can be automated
- Modular and reusable

## Adding New Notebooks

When creating new notebooks for exploration:

1. **Save in this directory:** `notebooks/your_analysis.ipynb`
2. **Add to .gitignore if large:** Notebooks with large outputs shouldn't be committed
3. **Extract to scripts when ready:** Move production code to `scripts/`
4. **Document in this README:** Add a section describing the notebook

## Best Practices

- **Keep notebooks for exploration only**
- **Extract production code to scripts**
- **Clear outputs before committing** (to reduce file size)
- **Use meaningful cell markdown** for documentation
- **Don't hardcode paths** - use config files

## Notebook Checklist

Before committing a notebook:

- [ ] All outputs cleared (Kernel → Restart & Clear Output)
- [ ] File size < 1 MB (check with `ls -lh`)
- [ ] No sensitive data (API keys, passwords)
- [ ] Markdown cells document the analysis
- [ ] Notebook is in `notebooks/` directory

## Questions?

- See `scripts/README.md` for information on modular preprocessing scripts
- See main `README.md` for overall project documentation
- Check `docs/` for detailed technical documentation
