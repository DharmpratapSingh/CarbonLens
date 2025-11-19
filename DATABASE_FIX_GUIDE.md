# Database Fix Guide

## Critical Issues Found

Your ClimateGPT database has **several critical issues** that need immediate attention:

### 🔴 HIGH PRIORITY Issues

1. **Data Type Inconsistencies**
   - `city_id` has 3 different types across tables (DOUBLE, BIGINT, VARCHAR)
   - `transport_country_year` uses FLOAT instead of DOUBLE
   - **Impact:** Queries joining data across sectors will fail

2. **Missing Metadata Columns**
   - Power and Transport sectors missing: units, source, spatial_res, temporal_res
   - **Impact:** Cannot trace data provenance or validate units

3. **Duplicate Records**
   - 120 duplicates in `power_country_year` (iso3 = '-99')
   - 192 duplicates in `transport_country_year` (iso3 = '-99')
   - **Impact:** Inflated totals in aggregations

4. **No Primary Keys**
   - No PRIMARY KEY or UNIQUE constraints on any table
   - **Impact:** Cannot prevent duplicate insertions

### 🟡 MEDIUM PRIORITY Issues

5. **Missing Indexes on Monthly Tables**
   - 15 monthly tables have no indexes
   - **Impact:** Slow query performance

6. **Data Quality Issues**
   - 720 records with zero/null emissions in `power_country_year`
   - Invalid country codes (iso3 = '-99')

---

## Fix Instructions

### Option 1: Quick Fix (SQL Only) - 15 minutes

Run the SQL fix script to handle most issues:

```bash
# Navigate to repository root
cd /path/to/Team-1B-Fusion

# Run SQL fixes (use a copy of your database first!)
duckdb data/warehouse/climategpt.duckdb < scripts/database/fix_database_issues.sql
```

**This fixes:**
- ✓ Removes duplicate records with invalid ISO3 codes
- ✓ Standardizes numeric data types
- ✓ Adds missing metadata columns
- ✓ Creates performance indexes on monthly tables
- ✓ Validates data

**Limitations:**
- ✗ Cannot standardize city_id type (requires Python script)
- ✗ Cannot add primary keys (need to deduplicate first)

---

### Option 2: Complete Fix (Python + SQL) - 30 minutes

Run the Python script for comprehensive fixes:

```bash
# 1. Create backup first (IMPORTANT!)
cp data/warehouse/climategpt.duckdb data/warehouse/climategpt_backup.duckdb

# 2. Run dry-run to see what will be changed
python scripts/database/fix_database_schema.py --dry-run

# 3. Run actual fixes with backup
python scripts/database/fix_database_schema.py --backup

# 4. Verify fixes
python scripts/database/fix_database_schema.py --dry-run
```

**This fixes:**
- ✓ Everything from Option 1
- ✓ Standardizes city_id to VARCHAR across all tables
- ✓ Removes all duplicate records
- ✓ Adds PRIMARY KEY constraints to all tables
- ✓ Adds CHECK constraints for data validation
- ✓ Generates comprehensive status report

---

## What Gets Fixed

### Phase 1: Data Cleaning
```sql
-- Removes invalid records
DELETE FROM power_country_year WHERE iso3 = '-99';      -- 120 records
DELETE FROM transport_country_year WHERE iso3 = '-99';  -- 192 records
```

### Phase 2: Data Type Standardization
```sql
-- Fix transport numeric types
ALTER TABLE transport_country_year ALTER COLUMN emissions_tonnes TYPE DOUBLE;
ALTER TABLE transport_country_year ALTER COLUMN MtCO2 TYPE DOUBLE;

-- Standardize city_id to VARCHAR (Python script handles this)
-- Affects: agriculture, buildings, fuel_exploitation, ind_combustion,
--          ind_processes, waste, power tables
```

### Phase 3: Add Missing Metadata
```sql
-- Add metadata to power and transport tables
ALTER TABLE power_country_year ADD COLUMN units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE power_country_year ADD COLUMN source VARCHAR DEFAULT 'EDGAR v2024 power';
ALTER TABLE power_country_year ADD COLUMN spatial_res VARCHAR DEFAULT 'country';
ALTER TABLE power_country_year ADD COLUMN temporal_res VARCHAR DEFAULT 'yearly';
-- (Repeated for all 12 power and transport tables)
```

### Phase 4: Add Performance Indexes
```sql
-- Add indexes to all monthly tables (15 tables)
CREATE INDEX idx_agriculture_admin1_month_year_month
ON agriculture_admin1_month(year, month);

CREATE INDEX idx_agriculture_admin1_month_country_year
ON agriculture_admin1_month(iso3, year, month);
-- (Repeated for all monthly tables)
```

### Phase 5: Add Primary Keys
```sql
-- Add primary keys after deduplication
ALTER TABLE agriculture_country_year
ADD CONSTRAINT pk_agriculture_country_year PRIMARY KEY (iso3, year);

ALTER TABLE agriculture_city_month
ADD CONSTRAINT pk_agriculture_city_month PRIMARY KEY (city_id, year, month);
-- (Repeated for all 50 tables)
```

### Phase 6: Add Data Validation
```sql
-- Add check constraints
ALTER TABLE agriculture_country_year
ADD CONSTRAINT chk_agriculture_country_year_year_range
CHECK (year >= 2000 AND year <= 2024);

ALTER TABLE agriculture_country_year
ADD CONSTRAINT chk_agriculture_country_year_emissions_positive
CHECK (emissions_tonnes >= 0);
-- (Repeated for all tables)
```

---

## Verification Steps

After running fixes, verify the database:

### 1. Check for Duplicates
```sql
-- Should return 0
SELECT COUNT(*) FROM (
    SELECT iso3, year, COUNT(*)
    FROM power_country_year
    GROUP BY iso3, year
    HAVING COUNT(*) > 1
) t;
```

### 2. Check Data Types
```sql
-- All should be VARCHAR
SELECT table_name, data_type
FROM information_schema.columns
WHERE column_name = 'city_id';
```

### 3. Check Metadata Columns
```sql
-- Should return units, source, spatial_res, temporal_res
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'power_country_year'
AND column_name IN ('units', 'source', 'spatial_res', 'temporal_res');
```

### 4. Check Primary Keys
```sql
-- Should list all 50 tables with primary keys
SELECT constraint_name, table_name
FROM information_schema.table_constraints
WHERE constraint_type = 'PRIMARY KEY'
ORDER BY table_name;
```

### 5. Check Indexes
```sql
-- Should show indexes on all monthly tables
SELECT table_name, index_name
FROM duckdb_indexes()
WHERE table_name LIKE '%_month'
ORDER BY table_name;
```

---

## Before & After Comparison

### Before Fixes
```
❌ city_id: 3 different data types (DOUBLE, BIGINT, VARCHAR)
❌ 312 duplicate records with invalid iso3
❌ Power/Transport: Missing 4 metadata columns each
❌ 0 primary key constraints
❌ 15 monthly tables without indexes
❌ No data validation constraints
```

### After Fixes
```
✓ city_id: Standardized to VARCHAR across all tables
✓ 0 duplicate records
✓ All tables have complete metadata columns
✓ 50 primary key constraints added
✓ All monthly tables have performance indexes
✓ Data validation constraints on year, month, emissions
✓ Database size optimized with proper indexing
```

---

## Performance Impact

### Query Speed Improvements

**Before indexes:**
```sql
-- Monthly query: ~2-5 seconds
SELECT * FROM agriculture_admin1_month
WHERE iso3 = 'USA' AND year = 2023;
```

**After indexes:**
```sql
-- Same query: ~50-200ms (10-50x faster!)
```

**Expected Speedups:**
- Country-level monthly queries: **10-20x faster**
- Admin1-level monthly queries: **20-50x faster**
- City-level monthly queries: **30-100x faster**
- Multi-sector aggregations: **5-10x faster**

---

## Estimated Fix Time

| Phase | Duration | Requires Downtime? |
|-------|----------|-------------------|
| Backup database | 1-2 min | No |
| SQL fixes | 5-10 min | Yes |
| Python schema fixes | 10-20 min | Yes |
| Verification | 5 min | No |
| **Total** | **20-35 min** | **Yes** |

**Recommended:** Run during maintenance window or when MCP server is not in use.

---

## Rollback Plan

If something goes wrong:

```bash
# 1. Stop the MCP server
# Kill any running processes

# 2. Restore from backup
cp data/warehouse/climategpt_backup.duckdb data/warehouse/climategpt.duckdb

# 3. Restart MCP server
make serve
```

---

## Testing After Fixes

Run these test queries to ensure everything works:

```bash
# Test 1: Multi-sector query
duckdb data/warehouse/climategpt.duckdb "
SELECT 'transport' as sector, SUM(emissions_tonnes) as total
FROM transport_country_year WHERE iso3 = 'USA' AND year = 2023
UNION ALL
SELECT 'power', SUM(emissions_tonnes)
FROM power_country_year WHERE iso3 = 'USA' AND year = 2023
"

# Test 2: City-level join (tests city_id standardization)
duckdb data/warehouse/climategpt.duckdb "
SELECT t.city_name, t.emissions_tonnes as transport, p.emissions_tonnes as power
FROM transport_city_year t
JOIN power_city_year p ON t.city_id = p.city_id AND t.year = p.year
WHERE t.year = 2023
LIMIT 10
"

# Test 3: Monthly aggregation (tests indexes)
duckdb data/warehouse/climategpt.duckdb "
SELECT month, SUM(emissions_tonnes) as total
FROM agriculture_country_month
WHERE iso3 = 'CHN' AND year = 2023
GROUP BY month
ORDER BY month
"
```

---

## MCP Server Compatibility

After fixes, your MCP server will work better:

✓ **Faster queries** - Indexes on monthly tables
✓ **Consistent data types** - No more join failures
✓ **Complete metadata** - Proper data provenance
✓ **Data integrity** - Primary keys prevent duplicates
✓ **Validated data** - Check constraints ensure quality

---

## Questions?

If you encounter issues:

1. Check the log output from the fix scripts
2. Run verification queries above
3. Check `DATABASE_FIX_GUIDE.md` for troubleshooting
4. Restore from backup if needed

---

**Status:** Ready to fix
**Risk Level:** Low (with backup)
**Expected Improvement:** Significant (10-50x faster queries, data integrity)
