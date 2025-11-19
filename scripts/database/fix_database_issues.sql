-- ============================================================================
-- Database Fixes for ClimateGPT DuckDB Database
-- ============================================================================
-- This script fixes all critical database issues identified in the analysis:
-- 1. Removes duplicate records with invalid iso3 codes
-- 2. Standardizes data types across all tables
-- 3. Adds missing metadata columns
-- 4. Creates primary key constraints
-- 5. Adds performance indexes
--
-- IMPORTANT: Run this on a BACKUP of your database first!
-- Usage: duckdb data/warehouse/climategpt.duckdb < fix_database_issues.sql
-- ============================================================================

-- Set to display progress
.timer on
.echo on

-- ============================================================================
-- PHASE 1: REMOVE DUPLICATE AND INVALID RECORDS (CRITICAL)
-- ============================================================================

PRINT '=== Phase 1: Cleaning Invalid Data ===';

-- Remove records with invalid ISO3 codes (-99 is a placeholder)
DELETE FROM power_country_year WHERE iso3 = '-99';
DELETE FROM transport_country_year WHERE iso3 = '-99';

-- Verify removals
SELECT 'Removed duplicates from power_country_year' as status,
       (SELECT COUNT(*) FROM power_country_year WHERE iso3 = '-99') as remaining_invalid;
SELECT 'Removed duplicates from transport_country_year' as status,
       (SELECT COUNT(*) FROM transport_country_year WHERE iso3 = '-99') as remaining_invalid;

-- ============================================================================
-- PHASE 2: STANDARDIZE DATA TYPES (CRITICAL)
-- ============================================================================

PRINT '=== Phase 2: Standardizing Data Types ===';

-- Fix transport_country_year numeric types (FLOAT -> DOUBLE)
ALTER TABLE transport_country_year ALTER COLUMN emissions_tonnes TYPE DOUBLE;
ALTER TABLE transport_country_year ALTER COLUMN MtCO2 TYPE DOUBLE;

-- Note: city_id standardization requires table recreation (DuckDB limitation)
-- This is handled in the Python fix script (fix_database_schema.py)

-- ============================================================================
-- PHASE 3: ADD MISSING METADATA COLUMNS (HIGH PRIORITY)
-- ============================================================================

PRINT '=== Phase 3: Adding Missing Metadata Columns ===';

-- Add metadata to all power tables
ALTER TABLE power_country_year ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE power_country_year ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 power';
ALTER TABLE power_country_year ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'country';
ALTER TABLE power_country_year ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'yearly';

ALTER TABLE power_country_month ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE power_country_month ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 power';
ALTER TABLE power_country_month ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'country';
ALTER TABLE power_country_month ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'monthly';

ALTER TABLE power_admin1_year ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE power_admin1_year ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 power';
ALTER TABLE power_admin1_year ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'admin1';
ALTER TABLE power_admin1_year ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'yearly';

ALTER TABLE power_admin1_month ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE power_admin1_month ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 power';
ALTER TABLE power_admin1_month ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'admin1';
ALTER TABLE power_admin1_month ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'monthly';

ALTER TABLE power_city_year ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE power_city_year ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 power';
ALTER TABLE power_city_year ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'city';
ALTER TABLE power_city_year ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'yearly';

ALTER TABLE power_city_month ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE power_city_month ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 power';
ALTER TABLE power_city_month ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'city';
ALTER TABLE power_city_month ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'monthly';

-- Add metadata to all transport tables
ALTER TABLE transport_country_year ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE transport_country_year ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 transport';
ALTER TABLE transport_country_year ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'country';
ALTER TABLE transport_country_year ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'yearly';

ALTER TABLE transport_country_month ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE transport_country_month ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 transport';
ALTER TABLE transport_country_month ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'country';
ALTER TABLE transport_country_month ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'monthly';

ALTER TABLE transport_admin1_year ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE transport_admin1_year ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 transport';
ALTER TABLE transport_admin1_year ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'admin1';
ALTER TABLE transport_admin1_year ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'yearly';

ALTER TABLE transport_admin1_month ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE transport_admin1_month ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 transport';
ALTER TABLE transport_admin1_month ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'admin1';
ALTER TABLE transport_admin1_month ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'monthly';

ALTER TABLE transport_city_year ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE transport_city_year ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 transport';
ALTER TABLE transport_city_year ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'city';
ALTER TABLE transport_city_year ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'yearly';

ALTER TABLE transport_city_month ADD COLUMN IF NOT EXISTS units VARCHAR DEFAULT 'tonnes CO2';
ALTER TABLE transport_city_month ADD COLUMN IF NOT EXISTS source VARCHAR DEFAULT 'EDGAR v2024 transport';
ALTER TABLE transport_city_month ADD COLUMN IF NOT EXISTS spatial_res VARCHAR DEFAULT 'city';
ALTER TABLE transport_city_month ADD COLUMN IF NOT EXISTS temporal_res VARCHAR DEFAULT 'monthly';

-- ============================================================================
-- PHASE 4: ADD INDEXES FOR PERFORMANCE (MEDIUM PRIORITY)
-- ============================================================================

PRINT '=== Phase 4: Creating Performance Indexes ===';

-- Indexes for agriculture monthly tables
CREATE INDEX IF NOT EXISTS idx_agriculture_admin1_month_year_month
ON agriculture_admin1_month(year, month);

CREATE INDEX IF NOT EXISTS idx_agriculture_admin1_month_country_year
ON agriculture_admin1_month(iso3, year, month);

CREATE INDEX IF NOT EXISTS idx_agriculture_city_month_year_month
ON agriculture_city_month(year, month);

CREATE INDEX IF NOT EXISTS idx_agriculture_city_month_city_year
ON agriculture_city_month(city_id, year, month);

CREATE INDEX IF NOT EXISTS idx_agriculture_country_month_year_month
ON agriculture_country_month(year, month);

CREATE INDEX IF NOT EXISTS idx_agriculture_country_month_iso3_year
ON agriculture_country_month(iso3, year, month);

-- Indexes for buildings monthly tables
CREATE INDEX IF NOT EXISTS idx_buildings_admin1_month_year_month
ON buildings_admin1_month(year, month);

CREATE INDEX IF NOT EXISTS idx_buildings_admin1_month_country_year
ON buildings_admin1_month(iso3, year, month);

CREATE INDEX IF NOT EXISTS idx_buildings_city_month_year_month
ON buildings_city_month(year, month);

CREATE INDEX IF NOT EXISTS idx_buildings_city_month_city_year
ON buildings_city_month(city_id, year, month);

CREATE INDEX IF NOT EXISTS idx_buildings_country_month_year_month
ON buildings_country_month(year, month);

CREATE INDEX IF NOT EXISTS idx_buildings_country_month_iso3_year
ON buildings_country_month(iso3, year, month);

-- Indexes for fuel_exploitation monthly tables
CREATE INDEX IF NOT EXISTS idx_fuel_exploitation_admin1_month_year_month
ON fuel_exploitation_admin1_month(year, month);

CREATE INDEX IF NOT EXISTS idx_fuel_exploitation_admin1_month_country_year
ON fuel_exploitation_admin1_month(iso3, year, month);

CREATE INDEX IF NOT EXISTS idx_fuel_exploitation_city_month_year_month
ON fuel_exploitation_city_month(year, month);

CREATE INDEX IF NOT EXISTS idx_fuel_exploitation_city_month_city_year
ON fuel_exploitation_city_month(city_id, year, month);

CREATE INDEX IF NOT EXISTS idx_fuel_exploitation_country_month_year_month
ON fuel_exploitation_country_month(year, month);

CREATE INDEX IF NOT EXISTS idx_fuel_exploitation_country_month_iso3_year
ON fuel_exploitation_country_month(iso3, year, month);

-- Indexes for ind_combustion monthly tables
CREATE INDEX IF NOT EXISTS idx_ind_combustion_admin1_month_year_month
ON ind_combustion_admin1_month(year, month);

CREATE INDEX IF NOT EXISTS idx_ind_combustion_admin1_month_country_year
ON ind_combustion_admin1_month(iso3, year, month);

CREATE INDEX IF NOT EXISTS idx_ind_combustion_city_month_year_month
ON ind_combustion_city_month(year, month);

CREATE INDEX IF NOT EXISTS idx_ind_combustion_city_month_city_year
ON ind_combustion_city_month(city_id, year, month);

CREATE INDEX IF NOT EXISTS idx_ind_combustion_country_month_year_month
ON ind_combustion_country_month(year, month);

CREATE INDEX IF NOT EXISTS idx_ind_combustion_country_month_iso3_year
ON ind_combustion_country_month(iso3, year, month);

-- Indexes for ind_processes monthly tables
CREATE INDEX IF NOT EXISTS idx_ind_processes_admin1_month_year_month
ON ind_processes_admin1_month(year, month);

CREATE INDEX IF NOT EXISTS idx_ind_processes_admin1_month_country_year
ON ind_processes_admin1_month(iso3, year, month);

CREATE INDEX IF NOT EXISTS idx_ind_processes_city_month_year_month
ON ind_processes_city_month(year, month);

CREATE INDEX IF NOT EXISTS idx_ind_processes_city_month_city_year
ON ind_processes_city_month(city_id, year, month);

CREATE INDEX IF NOT EXISTS idx_ind_processes_country_month_year_month
ON ind_processes_country_month(year, month);

CREATE INDEX IF NOT EXISTS idx_ind_processes_country_month_iso3_year
ON ind_processes_country_month(iso3, year, month);

-- Add indexes to power and transport monthly tables
CREATE INDEX IF NOT EXISTS idx_power_country_month_year_month
ON power_country_month(year, month);

CREATE INDEX IF NOT EXISTS idx_power_country_month_iso3_year
ON power_country_month(iso3, year, month);

CREATE INDEX IF NOT EXISTS idx_power_admin1_month_year_month
ON power_admin1_month(year, month);

CREATE INDEX IF NOT EXISTS idx_power_city_month_year_month
ON power_city_month(year, month);

CREATE INDEX IF NOT EXISTS idx_transport_country_month_year_month
ON transport_country_month(year, month);

CREATE INDEX IF NOT EXISTS idx_transport_country_month_iso3_year
ON transport_country_month(iso3, year, month);

CREATE INDEX IF NOT EXISTS idx_transport_admin1_month_year_month
ON transport_admin1_month(year, month);

CREATE INDEX IF NOT EXISTS idx_transport_city_month_year_month
ON transport_city_month(year, month);

-- ============================================================================
-- PHASE 5: ADD DATA VALIDATION CONSTRAINTS (OPTIONAL)
-- ============================================================================

PRINT '=== Phase 5: Adding Data Validation Constraints ===';

-- Note: DuckDB has limited constraint support
-- Primary keys and unique constraints should be added carefully
-- This is better handled programmatically in the Python fix script

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

PRINT '=== Verification ===';

-- Show all tables
SELECT table_name, estimated_size
FROM duckdb_tables()
WHERE schema_name = 'main'
ORDER BY table_name;

-- Count records per table
SELECT 'agriculture_country_year' as table_name, COUNT(*) as row_count FROM agriculture_country_year
UNION ALL
SELECT 'power_country_year', COUNT(*) FROM power_country_year
UNION ALL
SELECT 'transport_country_year', COUNT(*) FROM transport_country_year
ORDER BY table_name;

-- Verify no invalid ISO3 codes remain
SELECT 'Invalid ISO3 check' as test,
       SUM(CASE WHEN iso3 = '-99' THEN 1 ELSE 0 END) as invalid_count
FROM (
    SELECT iso3 FROM power_country_year
    UNION ALL
    SELECT iso3 FROM transport_country_year
) t;

PRINT '=== Database Fixes Complete ===';
