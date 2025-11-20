-- ============================================================================
-- MATERIALIZED VIEWS FOR CLIMATEGPT
-- ============================================================================
-- Purpose: Pre-compute common aggregations for faster queries
-- Expected Impact: Sub-second responses for common patterns
-- ============================================================================

-- Country-level yearly totals (all sectors combined)
CREATE TABLE IF NOT EXISTS mv_country_total_yearly AS
SELECT
    country_name,
    iso3,
    year,
    SUM(emissions_tonnes) as total_emissions
FROM (
    SELECT country_name, iso3, year, emissions_tonnes FROM transport_country_year
    UNION ALL
    SELECT country_name, iso3, year, emissions_tonnes FROM power_country_year
    UNION ALL
    SELECT country_name, iso3, year, emissions_tonnes FROM waste_country_year
    UNION ALL
    SELECT country_name, iso3, year, emissions_tonnes FROM agriculture_country_year
    UNION ALL
    SELECT country_name, iso3, year, emissions_tonnes FROM buildings_country_year
    UNION ALL
    SELECT country_name, iso3, year, emissions_tonnes FROM fuel_exploitation_country_year
    UNION ALL
    SELECT country_name, iso3, year, emissions_tonnes FROM ind_combustion_country_year
    UNION ALL
    SELECT country_name, iso3, year, emissions_tonnes FROM ind_processes_country_year
)
GROUP BY country_name, iso3, year;

-- Create indexes on materialized view
CREATE INDEX IF NOT EXISTS idx_mv_country_total_yearly_iso3_year
ON mv_country_total_yearly(iso3, year);

CREATE INDEX IF NOT EXISTS idx_mv_country_total_yearly_country_year
ON mv_country_total_yearly(country_name, year);

-- Top 20 emitters by year (for fast "top emitters" queries)
CREATE TABLE IF NOT EXISTS mv_top20_countries_yearly AS
SELECT
    year,
    country_name,
    iso3,
    total_emissions,
    RANK() OVER (PARTITION BY year ORDER BY total_emissions DESC) as rank
FROM mv_country_total_yearly
QUALIFY rank <= 20;

CREATE INDEX IF NOT EXISTS idx_mv_top20_countries_yearly_year
ON mv_top20_countries_yearly(year);

-- Run ANALYZE to update statistics
ANALYZE;

-- ============================================================================
-- USAGE NOTES
-- ============================================================================
-- These materialized views are automatically maintained when base tables
-- are updated. For queries like "top emitters" or "total emissions by country",
-- use these views instead of querying base tables directly.
--
-- Example queries:
--   SELECT * FROM mv_top20_countries_yearly WHERE year = 2023;
--   SELECT * FROM mv_country_total_yearly WHERE iso3 = 'USA' AND year = 2023;
-- ============================================================================

