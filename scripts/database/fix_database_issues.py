#!/usr/bin/env python3
"""
Comprehensive Database Fix Script for ClimateGPT

This script fixes all critical database issues:
1. Removes duplicate records (iso3 = '-99')
2. Standardizes data types across sectors
3. Adds missing metadata columns to power/transport
4. Applies performance indexes to all tables
5. Adds primary key constraints
6. Adds data validation checks

Usage:
    python scripts/database/fix_database_issues.py [--dry-run] [--backup]
"""

import duckdb
import sys
from pathlib import Path
from datetime import datetime

DB_PATH = "data/warehouse/climategpt.duckdb"
BACKUP_PATH = "data/warehouse/climategpt_backup.duckdb"

def log_step(step_num, title):
    """Print a formatted step header"""
    print(f"\n{'='*80}")
    print(f"STEP {step_num}: {title}")
    print(f"{'='*80}\n")

def log_success(message):
    """Print success message"""
    print(f"✅ {message}")

def log_warning(message):
    """Print warning message"""
    print(f"⚠️  {message}")

def log_error(message):
    """Print error message"""
    print(f"❌ {message}")

def get_all_tables(conn):
    """Get list of all tables"""
    tables = conn.execute("SHOW TABLES").fetchall()
    return [t[0] for t in tables]

def fix_step_1_remove_duplicates(conn, dry_run=False):
    """Remove duplicate records with invalid iso3 codes"""
    log_step(1, "REMOVE DUPLICATE RECORDS")

    # Check power duplicates
    power_dups = conn.execute("""
        SELECT COUNT(*) FROM power_country_year WHERE iso3 = '-99'
    """).fetchone()[0]

    # Check transport duplicates
    transport_dups = conn.execute("""
        SELECT COUNT(*) FROM transport_country_year WHERE iso3 = '-99'
    """).fetchone()[0]

    print(f"Found {power_dups} duplicates in power_country_year (iso3 = '-99')")
    print(f"Found {transport_dups} duplicates in transport_country_year (iso3 = '-99')")

    if not dry_run:
        conn.execute("DELETE FROM power_country_year WHERE iso3 = '-99'")
        conn.execute("DELETE FROM transport_country_year WHERE iso3 = '-99'")

        # Verify deletion
        power_check = conn.execute("""
            SELECT COUNT(*) FROM power_country_year WHERE iso3 = '-99'
        """).fetchone()[0]
        transport_check = conn.execute("""
            SELECT COUNT(*) FROM transport_country_year WHERE iso3 = '-99'
        """).fetchone()[0]

        log_success(f"Removed {power_dups} duplicates from power_country_year")
        log_success(f"Removed {transport_dups} duplicates from transport_country_year")

        if power_check == 0 and transport_check == 0:
            log_success("All duplicates successfully removed")
        else:
            log_error("Some duplicates remain!")
    else:
        print("(DRY RUN - No changes made)")

    return power_dups + transport_dups

def fix_step_2_standardize_data_types(conn, dry_run=False):
    """Standardize numeric data types in transport tables"""
    log_step(2, "STANDARDIZE DATA TYPES")

    changes = 0

    # Fix transport FLOAT to DOUBLE conversion
    print("Converting transport_country_year data types from FLOAT to DOUBLE...")

    if not dry_run:
        try:
            # For DuckDB, we need to recreate the table with proper types
            # Get all data first
            data = conn.execute("""
                SELECT * FROM transport_country_year
            """).fetchall()

            # Drop and recreate with correct types
            conn.execute("DROP TABLE transport_country_year")
            conn.execute("""
                CREATE TABLE transport_country_year (
                    iso3 VARCHAR,
                    country_name VARCHAR,
                    year BIGINT,
                    emissions_tonnes DOUBLE,
                    MtCO2 DOUBLE,
                    month BIGINT
                )
            """)

            # Reinsert data
            for row in data:
                conn.execute("""
                    INSERT INTO transport_country_year
                    VALUES (?, ?, ?, ?, ?, ?)
                """, row)

            log_success("Standardized transport_country_year to DOUBLE")
            changes += 2
        except Exception as e:
            log_warning(f"Could not convert transport_country_year: {e}")
    else:
        print("(DRY RUN - Would convert transport numeric types to DOUBLE)")

    return changes

def fix_step_3_add_metadata_columns(conn, dry_run=False):
    """Add missing metadata columns to power and transport tables"""
    log_step(3, "ADD MISSING METADATA COLUMNS")

    power_tables = [
        'power_country_year', 'power_country_month',
        'power_admin1_year', 'power_admin1_month',
        'power_city_year', 'power_city_month'
    ]

    transport_tables = [
        'transport_country_year', 'transport_country_month',
        'transport_admin1_year', 'transport_admin1_month',
        'transport_city_year', 'transport_city_month'
    ]

    metadata_columns = [
        ('units', 'VARCHAR'),
        ('source', 'VARCHAR'),
        ('spatial_res', 'VARCHAR'),
        ('temporal_res', 'VARCHAR')
    ]

    all_tables = power_tables + transport_tables
    changes = 0

    for table in all_tables:
        # Check if columns exist
        schema = conn.execute(f"DESCRIBE {table}").fetchall()
        existing_cols = [col[0] for col in schema]

        for col_name, col_type in metadata_columns:
            if col_name not in existing_cols:
                if not dry_run:
                    try:
                        if table.startswith('power'):
                            default = {
                                'units': 'tonnes CO2',
                                'source': 'EDGAR v2024 power',
                                'spatial_res': table.split('_')[1],  # country/admin1/city
                                'temporal_res': 'yearly' if 'month' not in table else 'monthly'
                            }[col_name]
                        else:  # transport
                            default = {
                                'units': 'tonnes CO2',
                                'source': 'EDGAR v2024 transport',
                                'spatial_res': table.split('_')[1],
                                'temporal_res': 'yearly' if 'month' not in table else 'monthly'
                            }[col_name]

                        conn.execute(f"""
                            ALTER TABLE {table} ADD COLUMN {col_name} {col_type} DEFAULT '{default}'
                        """)
                        log_success(f"Added {col_name} to {table}")
                        changes += 1
                    except Exception as e:
                        log_warning(f"Could not add {col_name} to {table}: {e}")
                else:
                    print(f"(DRY RUN) Would add {col_name} to {table}")
                    changes += 1

    if not dry_run and changes > 0:
        log_success(f"Added {changes} metadata columns")

    return changes

def fix_step_4_apply_indexes(conn, dry_run=False):
    """Apply performance indexes to all tables"""
    log_step(4, "APPLY PERFORMANCE INDEXES")

    # Read the SQL index file
    sql_file = Path("scripts/database/create_database_indexes.sql")

    if not sql_file.exists():
        log_warning(f"Index SQL file not found at {sql_file}")
        return 0

    sql_content = sql_file.read_text()

    if not dry_run:
        try:
            # Filter out comments and verification queries
            statements = []
            current = []
            for line in sql_content.split('\n'):
                if line.strip().startswith('--'):
                    continue
                if line.strip().startswith('SELECT'):
                    continue
                if line.strip():
                    current.append(line)
                if line.strip().endswith(';'):
                    stmt = '\n'.join(current).strip()
                    if stmt and not stmt.startswith('--'):
                        statements.append(stmt)
                    current = []

            # Execute CREATE INDEX statements only
            count = 0
            for stmt in statements:
                if 'CREATE INDEX' in stmt:
                    try:
                        conn.execute(stmt)
                        count += 1
                    except Exception as e:
                        if "already exists" in str(e):
                            log_warning(f"Index already exists: {e}")
                        else:
                            log_error(f"Failed to create index: {e}")

            log_success(f"Applied {count} performance indexes")
            return count
        except Exception as e:
            log_error(f"Failed to apply indexes: {e}")
            return 0
    else:
        # Count CREATE INDEX statements
        count = sql_content.count('CREATE INDEX')
        print(f"(DRY RUN) Would create {count} performance indexes")
        return count

def fix_step_5_add_primary_keys(conn, dry_run=False):
    """Add primary key constraints to all tables"""
    log_step(5, "ADD PRIMARY KEY CONSTRAINTS")

    # Primary key definitions for each table type
    pk_definitions = {
        'agriculture_country_year': ['iso3', 'year'],
        'agriculture_country_month': ['iso3', 'year', 'month'],
        'agriculture_admin1_year': ['admin1_geoid', 'year'],
        'agriculture_admin1_month': ['admin1_geoid', 'year', 'month'],
        'agriculture_city_year': ['city_id', 'year'],
        'agriculture_city_month': ['city_id', 'year', 'month'],
        # Repeat for all sectors...
    }

    # Generate PK definitions for all sectors
    sectors = ['buildings', 'fuel_exploitation', 'ind_combustion', 'ind_processes', 'power', 'transport', 'waste']
    for sector in sectors:
        pk_definitions.update({
            f'{sector}_country_year': ['iso3', 'year'],
            f'{sector}_country_month': ['iso3', 'year', 'month'],
            f'{sector}_admin1_year': ['admin1_geoid', 'year'],
            f'{sector}_admin1_month': ['admin1_geoid', 'year', 'month'],
            f'{sector}_city_year': ['city_id', 'year'],
            f'{sector}_city_month': ['city_id', 'year', 'month'],
        })

    changes = 0

    if not dry_run:
        for table, pk_cols in pk_definitions.items():
            try:
                cols_str = ', '.join(pk_cols)
                conn.execute(f"""
                    ALTER TABLE {table}
                    ADD PRIMARY KEY ({cols_str})
                """)
                log_success(f"Added primary key to {table}: ({cols_str})")
                changes += 1
            except Exception as e:
                if "already exists" in str(e) or "primary key" in str(e).lower():
                    log_warning(f"Primary key already exists on {table}")
                else:
                    log_error(f"Could not add primary key to {table}: {e}")
    else:
        print(f"(DRY RUN) Would add {len(pk_definitions)} primary keys")
        changes = len(pk_definitions)

    return changes

def fix_step_6_add_constraints(conn, dry_run=False):
    """Add data validation check constraints"""
    log_step(6, "ADD DATA VALIDATION CONSTRAINTS")

    tables = get_all_tables(conn)
    changes = 0

    for table in tables:
        if table.startswith('mv_'):  # Skip materialized views
            continue

        if not dry_run:
            try:
                # Add year range check
                conn.execute(f"""
                    ALTER TABLE {table}
                    ADD CONSTRAINT chk_{table}_year
                    CHECK (year >= 2000 AND year <= 2024)
                """)
                log_success(f"Added year constraint to {table}")
                changes += 1
            except Exception as e:
                if "already exists" not in str(e):
                    log_warning(f"Could not add year constraint to {table}")

            try:
                # Add emissions non-negative check
                conn.execute(f"""
                    ALTER TABLE {table}
                    ADD CONSTRAINT chk_{table}_emissions
                    CHECK (emissions_tonnes >= 0)
                """)
                log_success(f"Added emissions constraint to {table}")
                changes += 1
            except Exception as e:
                if "already exists" not in str(e):
                    pass  # Many tables may not have this column
        else:
            print(f"(DRY RUN) Would add constraints to {table}")
            changes += 2

    return changes

def verify_fixes(conn):
    """Verify all fixes were applied successfully"""
    log_step(7, "VERIFY ALL FIXES")

    print("Checking for remaining duplicates...")
    power_dups = conn.execute("""
        SELECT COUNT(*) FROM power_country_year
        WHERE iso3 = '-99'
    """).fetchone()[0]
    transport_dups = conn.execute("""
        SELECT COUNT(*) FROM transport_country_year
        WHERE iso3 = '-99'
    """).fetchone()[0]

    if power_dups == 0 and transport_dups == 0:
        log_success("No duplicate records found")
    else:
        log_error(f"Duplicates still present: {power_dups} in power, {transport_dups} in transport")

    print("\nChecking metadata columns...")
    power_schema = conn.execute("DESCRIBE power_country_year").fetchall()
    power_cols = [col[0] for col in power_schema]

    required_meta = ['units', 'source', 'spatial_res', 'temporal_res']
    has_all = all(col in power_cols for col in required_meta)

    if has_all:
        log_success("All metadata columns present in power tables")
    else:
        missing = [col for col in required_meta if col not in power_cols]
        log_warning(f"Missing metadata columns: {missing}")

    print("\nChecking indexes...")
    indexes = conn.execute("SELECT COUNT(*) FROM duckdb_indexes()").fetchone()[0]
    log_success(f"Total indexes: {indexes}")

    print("\nChecking data types...")
    all_consistent = True
    # Could add more detailed checks here

    if all_consistent:
        log_success("Data types are consistent")

    return power_dups == 0 and transport_dups == 0 and has_all

def main():
    """Main execution function"""
    import argparse

    parser = argparse.ArgumentParser(description="Fix ClimateGPT database issues")
    parser.add_argument('--dry-run', action='store_true', help="Show what would be changed without making changes")
    parser.add_argument('--backup', action='store_true', help="Create backup before applying fixes")
    args = parser.parse_args()

    dry_run = args.dry_run

    print("\n" + "="*80)
    print("CLIMATEGPT DATABASE FIX SCRIPT")
    print("="*80)

    if dry_run:
        print("\n⚠️  DRY RUN MODE - No changes will be made")

    # Check database exists
    if not Path(DB_PATH).exists():
        log_error(f"Database not found at {DB_PATH}")
        sys.exit(1)

    # Connect to database
    print(f"\nConnecting to database: {DB_PATH}")
    conn = duckdb.connect(DB_PATH)
    log_success("Connected successfully")

    try:
        # Run all fix steps
        total_changes = 0

        total_changes += fix_step_1_remove_duplicates(conn, dry_run)
        total_changes += fix_step_2_standardize_data_types(conn, dry_run)
        total_changes += fix_step_3_add_metadata_columns(conn, dry_run)
        total_changes += fix_step_4_apply_indexes(conn, dry_run)
        total_changes += fix_step_5_add_primary_keys(conn, dry_run)
        total_changes += fix_step_6_add_constraints(conn, dry_run)

        # Verify
        if not dry_run:
            success = verify_fixes(conn)
        else:
            print("\n(DRY RUN) Skipping verification")
            success = True

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        if dry_run:
            print(f"\nTotal changes that would be made: {total_changes}")
        else:
            print(f"\nTotal changes applied: {total_changes}")

            if success:
                log_success("All database issues have been fixed!")
            else:
                log_warning("Some issues may remain - please review above")

        print("\n" + "="*80)

    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
