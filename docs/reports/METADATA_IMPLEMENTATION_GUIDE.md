# Metadata Implementation Guide - Step by Step

## What We Just Created

### 1. **add_metadata_columns.py** ✅
**Location**: `scripts/database/add_metadata_columns.py`
**Purpose**: Adds 7 new columns to all 56 tables

**What it does**:
```
Adds these columns to every table:
├─ data_type VARCHAR
├─ data_origin VARCHAR  
├─ quality_flag VARCHAR
├─ estimation_method VARCHAR
├─ confidence_score DOUBLE
├─ synthetic_probability DOUBLE
└─ estimation_notes VARCHAR

Default values:
├─ data_type: 'real'
├─ data_origin: 'EDGAR v2024'
├─ quality_flag: 'HIGH'
├─ confidence_score: 0.95
├─ synthetic_probability: 0.0
└─ estimation_notes: 'EDGAR verified data'
```

**Usage**:
```bash
python scripts/database/add_metadata_columns.py data/warehouse/climategpt.duckdb
```

**Output**: 
- Log file: `metadata_migration.log`
- Result: 7 new columns added to all 56 tables

---

### 2. **populate_estimated_data.py** ✅
**Location**: `scripts/database/populate_estimated_data.py`
**Purpose**: Marks which records are estimated/synthesized

**What it does**:
```
Identifies regions with estimated/synthesized data:

Africa (2000 cities):
├─ data_type: 'estimated'
├─ quality_flag: 'MEDIUM'
├─ confidence_score: 0.60
├─ synthetic_probability: 0.30
└─ estimation_method: 'regional_scaling'

Middle East/Central Asia (1500 cities):
├─ data_type: 'estimated'
├─ quality_flag: 'MEDIUM'
├─ confidence_score: 0.65
└─ estimation_method: 'statistical_model'

Small Islands (30+ nations):
├─ data_type: 'synthesized'
├─ quality_flag: 'LOW'
├─ confidence_score: 0.40
├─ synthetic_probability: 0.90
└─ estimation_method: 'random_generation'
```

**Usage**:
```bash
python scripts/database/populate_estimated_data.py data/warehouse/climategpt.duckdb
```

**Output**:
- Log file: `estimated_data_marking.log`
- Statistics by sector and data type
- Result: Estimated/synthesized records marked

---

## How to Run (EXECUTION STEPS)

### Step 1: Add Metadata Columns
```bash
cd /Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT
python scripts/database/add_metadata_columns.py
```

**Expected output**:
```
[2025-XX-XX HH:MM:SS] INFO: METADATA COLUMN MIGRATION - START
[2025-XX-XX HH:MM:SS] INFO: Found 56 climate data tables to update

[1/56] Processing: transport_country_year
  ✓ Added column 'data_type' to transport_country_year
  ✓ Added column 'data_origin' to transport_country_year
  ...
[56/56] Processing: industrial_processes_city_month

[2025-XX-XX HH:MM:SS] INFO: MIGRATION COMPLETE
Tables modified: 56
Columns added: 392
Duration: XX.X seconds
```

**Time**: ~30 seconds to 2 minutes

---

### Step 2: Populate Estimated Data Markers
```bash
python scripts/database/populate_estimated_data.py
```

**Expected output**:
```
[2025-XX-XX HH:MM:SS] INFO: ESTIMATED DATA POPULATION - START

Processing transport sector...
  ✓ transport_country_year: 2000 records marked as estimated
  ✓ transport_admin1_year: 15000 records marked as estimated
  ...

DATA TYPE STATISTICS

TRANSPORT SECTOR:
  real: 15000 records (70%)
  estimated: 5000 records (25%)
  synthesized: 500 records (5%)

Confidence scores:
  real: 0.95
  estimated: 0.60
  synthesized: 0.40
```

**Time**: ~1-5 minutes depending on database size

---

## What Changed in Database

### Before:
```
Table: transport_country_year
Columns:
├─ country_name
├─ year
├─ emissions_tonnes
├─ MtCO2
├─ units
├─ source
├─ spatial_res
└─ temporal_res
```

### After:
```
Table: transport_country_year
Columns:
├─ country_name
├─ year
├─ emissions_tonnes
├─ MtCO2
├─ units
├─ source
├─ spatial_res
├─ temporal_res
├─ data_type ← NEW: 'real', 'estimated', or 'synthesized'
├─ data_origin ← NEW: 'EDGAR', 'Statistical', 'Synthetic'
├─ quality_flag ← NEW: 'HIGH', 'MEDIUM', 'LOW'
├─ estimation_method ← NEW: Explains how estimated
├─ confidence_score ← NEW: 0.0-1.0 confidence level
├─ synthetic_probability ← NEW: 0.0-1.0 probability it's synthetic
└─ estimation_notes ← NEW: Details about estimation
```

---

## Next Steps (Still to Do)

### Step 3: Update MCP Server
**File**: `src/mcp_server_stdio.py`
**What to do**: Return metadata in query responses
**Timeline**: Tomorrow (1-2 hours)

### Step 4: Update run_llm.py  
**File**: `src/run_llm.py`
**What to do**: Extract and display data type flags
**Timeline**: Tomorrow (1-2 hours)

### Step 5: Test
**What to do**: Run test queries and verify output
**Timeline**: Tomorrow (1-2 hours)

---

## Verification Queries

After running the scripts, verify the data:

```sql
-- Check columns were added
SELECT * FROM transport_country_year LIMIT 1;

-- Count records by data type
SELECT 
    data_type,
    COUNT(*) as count,
    ROUND(AVG(confidence_score), 2) as avg_confidence
FROM transport_country_year
GROUP BY data_type;

-- Check specific country
SELECT 
    country_name,
    year,
    emissions_tonnes,
    data_type,
    quality_flag,
    confidence_score
FROM transport_country_year
WHERE country_name IN ('Germany', 'Kenya', 'Fiji')
LIMIT 10;
```

---

## Sample Output After Implementation

### Current (Before):
```
Query: Germany Transport 2023
Response:
[Source: Transport Sector | EDGAR v2024 Enhanced]
[Quality: 85.0% | Confidence: HIGH (100%) | Uncertainty: ±12%]
Data validated with: IEA Transport Statistics, WHO urban mobility, Copernicus traffic

Germany's transport emissions in 2023 were 164.43 MtCO₂...
```

### Future (After):
```
Query: Germany Transport 2023
Response:
[Source: Transport Sector | EDGAR v2024 Enhanced]
[Quality: 85.0% | Confidence: HIGH (100%) | Uncertainty: ±12%]
[Data Type: REAL DATA | Confidence Score: 0.95]
Data validated with: IEA Transport Statistics, WHO urban mobility, Copernicus traffic

Germany's transport emissions in 2023 were 164.43 MtCO₂...

---

Query: Kenya Transport 2023
Response:
[Source: Transport Sector | Estimated]
[Quality: MEDIUM | Uncertainty: ±25%]
[Data Type: ESTIMATED | Confidence Score: 0.60]
[Estimation Method: Regional scaling from global averages]

Kenya's transport emissions in 2023 were approximately 12.5 MtCO₂...
(Note: This is an estimated value based on regional statistics)

---

Query: Fiji Transport 2023
Response:
[Source: Transport Sector | Synthesized]
[Quality: LOW | Uncertainty: ±40%]
[Data Type: SYNTHESIZED | Confidence Score: 0.40]
[Synthesis Method: Generated from global patterns]

Fiji's transport emissions in 2023 were approximately 0.8 MtCO₂...
(Note: This is synthetic data generated from global patterns - use with caution)
```

---

## Architecture Summary

```
User Query
    ↓
run_llm.py
    ↓
MCP Server (returns metadata + data)
    ↓
Database Query (WITH new metadata columns)
    ├─ data_type: 'real' | 'estimated' | 'synthesized'
    ├─ confidence_score: 0.95 | 0.60 | 0.40
    └─ estimation_method: if not real
    ↓
run_llm.py (extracts metadata)
    ├─ Checks data_type
    ├─ Gets confidence_score
    └─ Applies appropriate display format
    ↓
Final Answer (with data type indicated)
```

---

## Files Changed Summary

### Created:
- ✅ `scripts/database/add_metadata_columns.py` (190 lines)
- ✅ `scripts/database/populate_estimated_data.py` (280 lines)
- ✅ `METADATA_IMPLEMENTATION_GUIDE.md` (this file)

### To Be Modified:
- ⏳ `src/mcp_server_stdio.py` (add metadata to response)
- ⏳ `src/run_llm.py` (extract and display metadata)
- ⏳ `data/curated-2/manifest_mcp_duckdb.json` (document new columns)

### Timeline:
- ✅ Step 1-3: COMPLETE (today)
- ⏳ Step 4-5: Tomorrow (4-6 hours)
- ⏳ Step 6-7: Day 3 (testing)

---

## Rollback (If Needed)

If something goes wrong, the database backup is automatically created:
```
Location: data/warehouse/climategpt_<timestamp>.duckdb
```

You can restore from backup by copying it back to `climategpt.duckdb`.

---

## Questions?

When running the scripts:
1. Check the log files for errors
2. Verify the database is not locked
3. Ensure you have write permissions
4. Run verification queries to confirm data

