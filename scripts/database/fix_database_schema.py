#!/usr/bin/env python3
"""
Advanced Database Schema Fixes for ClimateGPT

This script handles complex schema changes that can't be done in pure SQL:
1. Standardizes city_id to VARCHAR across all tables
2. Adds primary key constraints
3. Deduplicates data before adding constraints
4. Creates backup tables before modifications

Usage:
    python fix_database_schema.py [--backup] [--dry-run]

Options:
    --backup    Create backup of database before modifications
    --dry-run   Show what would be done without making changes
"""

import duckdb
import argparse
import logging
from pathlib import Path
from datetime import datetime
import shutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseSchemaFixer:
    """Fix complex schema issues in ClimateGPT database."""

    def __init__(self, db_path: Path, dry_run: bool = False):
        self.db_path = db_path
        self.dry_run = dry_run
        self.con = None

    def connect(self):
        """Connect to database."""
        logger.info(f"Connecting to {self.db_path}")
        self.con = duckdb.connect(str(self.db_path), read_only=self.dry_run)

    def close(self):
        """Close database connection."""
        if self.con:
            self.con.close()

    def backup_database(self):
        """Create backup of database."""
        backup_path = self.db_path.parent / f"{self.db_path.stem}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.duckdb"
        logger.info(f"Creating backup at {backup_path}")

        if not self.dry_run:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"✓ Backup created: {backup_path}")
        else:
            logger.info(f"[DRY RUN] Would create backup at {backup_path}")

        return backup_path

    def standardize_city_id_type(self):
        """Standardize city_id column to VARCHAR across all tables."""
        logger.info("\n" + "="*80)
        logger.info("STANDARDIZING city_id DATA TYPE")
        logger.info("="*80)

        # Get all tables with city_id column
        tables_query = """
        SELECT table_name, column_name, data_type
        FROM information_schema.columns
        WHERE column_name = 'city_id'
        AND table_schema = 'main'
        ORDER BY table_name
        """

        tables_with_city_id = self.con.execute(tables_query).fetchall()

        logger.info(f"Found {len(tables_with_city_id)} tables with city_id column")

        for table_name, col_name, data_type in tables_with_city_id:
            if data_type != 'VARCHAR':
                logger.info(f"\nConverting {table_name}.city_id from {data_type} to VARCHAR")

                if not self.dry_run:
                    # DuckDB requires table recreation for type changes
                    # 1. Create temp table with correct type
                    create_temp = f"""
                    CREATE TABLE {table_name}_temp AS
                    SELECT
                        CAST(city_id AS VARCHAR) as city_id,
                        * EXCLUDE (city_id)
                    FROM {table_name}
                    """

                    self.con.execute(create_temp)

                    # 2. Drop original table
                    self.con.execute(f"DROP TABLE {table_name}")

                    # 3. Rename temp to original
                    self.con.execute(f"ALTER TABLE {table_name}_temp RENAME TO {table_name}")

                    logger.info(f"  ✓ Converted {table_name}.city_id to VARCHAR")
                else:
                    logger.info(f"  [DRY RUN] Would convert {table_name}.city_id to VARCHAR")

    def remove_duplicates(self, table_name: str, key_columns: list):
        """Remove duplicate records from a table."""
        logger.info(f"Checking for duplicates in {table_name}")

        # Count duplicates
        key_cols_str = ', '.join(key_columns)
        dup_query = f"""
        SELECT {key_cols_str}, COUNT(*) as count
        FROM {table_name}
        GROUP BY {key_cols_str}
        HAVING COUNT(*) > 1
        """

        duplicates = self.con.execute(dup_query).fetchall()

        if duplicates:
            logger.warning(f"  Found {len(duplicates)} sets of duplicate records")

            if not self.dry_run:
                # Keep only the first occurrence of each duplicate
                dedup_query = f"""
                CREATE TABLE {table_name}_temp AS
                SELECT DISTINCT ON ({key_cols_str}) *
                FROM {table_name}
                ORDER BY {key_cols_str}
                """

                self.con.execute(dedup_query)
                self.con.execute(f"DROP TABLE {table_name}")
                self.con.execute(f"ALTER TABLE {table_name}_temp RENAME TO {table_name}")

                logger.info(f"  ✓ Removed duplicates from {table_name}")
            else:
                logger.info(f"  [DRY RUN] Would remove duplicates from {table_name}")
        else:
            logger.info(f"  ✓ No duplicates found in {table_name}")

    def add_primary_keys(self):
        """Add primary key constraints to all tables."""
        logger.info("\n" + "="*80)
        logger.info("ADDING PRIMARY KEY CONSTRAINTS")
        logger.info("="*80)

        # Define primary keys for each table pattern
        pk_definitions = {
            '_country_year': ['iso3', 'year'],
            '_country_month': ['iso3', 'year', 'month'],
            '_admin1_year': ['admin1_geoid', 'year'],
            '_admin1_month': ['admin1_geoid', 'year', 'month'],
            '_city_year': ['city_id', 'year'],
            '_city_month': ['city_id', 'year', 'month'],
        }

        # Get all tables
        tables = self.con.execute("SHOW TABLES").fetchall()

        for (table_name,) in tables:
            # Skip materialized views
            if table_name.startswith('mv_'):
                continue

            # Determine primary key columns
            pk_cols = None
            for pattern, cols in pk_definitions.items():
                if pattern in table_name:
                    pk_cols = cols
                    break

            if pk_cols:
                # First, remove duplicates
                self.remove_duplicates(table_name, pk_cols)

                # Then add primary key
                pk_name = f"pk_{table_name}"
                pk_cols_str = ', '.join(pk_cols)

                logger.info(f"Adding primary key to {table_name}: {pk_cols_str}")

                if not self.dry_run:
                    try:
                        # DuckDB syntax for adding primary key
                        # Note: This might fail if duplicates still exist
                        alter_query = f"""
                        ALTER TABLE {table_name}
                        ADD CONSTRAINT {pk_name} PRIMARY KEY ({pk_cols_str})
                        """
                        self.con.execute(alter_query)
                        logger.info(f"  ✓ Added primary key to {table_name}")
                    except Exception as e:
                        logger.error(f"  ✗ Failed to add primary key to {table_name}: {e}")
                else:
                    logger.info(f"  [DRY RUN] Would add primary key to {table_name}")

    def add_check_constraints(self):
        """Add check constraints for data validation."""
        logger.info("\n" + "="*80)
        logger.info("ADDING CHECK CONSTRAINTS")
        logger.info("="*80)

        constraints = [
            # Year must be between 2000 and 2024
            ("year >= 2000 AND year <= 2024", "year_range"),
            # Month must be between 1 and 12 (for monthly tables)
            ("month >= 1 AND month <= 12", "month_range"),
            # Emissions must be non-negative
            ("emissions_tonnes >= 0", "emissions_positive"),
        ]

        tables = self.con.execute("SHOW TABLES").fetchall()

        for (table_name,) in tables:
            if table_name.startswith('mv_'):
                continue

            # Check which columns exist
            columns = self.con.execute(f"DESCRIBE {table_name}").fetchall()
            col_names = [col[0] for col in columns]

            for constraint_expr, constraint_suffix in constraints:
                # Only add month constraint to monthly tables
                if 'month' in constraint_expr and '_month' not in table_name:
                    continue

                # Check if relevant columns exist
                if 'year' in constraint_expr and 'year' not in col_names:
                    continue
                if 'month' in constraint_expr and 'month' not in col_names:
                    continue
                if 'emissions_tonnes' in constraint_expr and 'emissions_tonnes' not in col_names:
                    continue

                constraint_name = f"chk_{table_name}_{constraint_suffix}"

                logger.info(f"Adding constraint to {table_name}: {constraint_expr}")

                if not self.dry_run:
                    try:
                        alter_query = f"""
                        ALTER TABLE {table_name}
                        ADD CONSTRAINT {constraint_name} CHECK ({constraint_expr})
                        """
                        self.con.execute(alter_query)
                        logger.info(f"  ✓ Added constraint to {table_name}")
                    except Exception as e:
                        logger.warning(f"  ⚠ Could not add constraint to {table_name}: {e}")
                else:
                    logger.info(f"  [DRY RUN] Would add constraint to {table_name}")

    def generate_report(self):
        """Generate final status report."""
        logger.info("\n" + "="*80)
        logger.info("DATABASE STATUS REPORT")
        logger.info("="*80)

        # Table count
        tables = self.con.execute("SHOW TABLES").fetchall()
        logger.info(f"\nTotal tables: {len(tables)}")

        # Total row count
        total_rows = 0
        for (table_name,) in tables:
            count = self.con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            total_rows += count

        logger.info(f"Total rows: {total_rows:,}")

        # Check for remaining issues
        logger.info("\nData Quality Checks:")

        # Invalid ISO3 codes
        invalid_iso3 = 0
        for (table_name,) in tables:
            if 'country' in table_name and not table_name.startswith('mv_'):
                columns = self.con.execute(f"DESCRIBE {table_name}").fetchall()
                col_names = [col[0] for col in columns]
                if 'iso3' in col_names:
                    count = self.con.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE iso3 = '-99'"
                    ).fetchone()[0]
                    invalid_iso3 += count

        if invalid_iso3 == 0:
            logger.info("  ✓ No invalid ISO3 codes found")
        else:
            logger.warning(f"  ✗ Found {invalid_iso3} records with invalid ISO3 codes")

        # Zero emissions
        zero_emissions = 0
        for (table_name,) in tables:
            if not table_name.startswith('mv_'):
                columns = self.con.execute(f"DESCRIBE {table_name}").fetchall()
                col_names = [col[0] for col in columns]
                if 'emissions_tonnes' in col_names:
                    count = self.con.execute(
                        f"SELECT COUNT(*) FROM {table_name} WHERE emissions_tonnes = 0 OR emissions_tonnes IS NULL"
                    ).fetchone()[0]
                    zero_emissions += count

        logger.info(f"  Records with zero/null emissions: {zero_emissions:,}")

        logger.info("\n" + "="*80)

    def run(self, create_backup: bool = True):
        """Run all fixes."""
        logger.info("="*80)
        logger.info("DATABASE SCHEMA FIXER")
        logger.info("="*80)

        if self.dry_run:
            logger.info("*** DRY RUN MODE - NO CHANGES WILL BE MADE ***\n")

        try:
            self.connect()

            if create_backup and not self.dry_run:
                self.backup_database()

            # Run fixes in order
            self.standardize_city_id_type()
            self.add_primary_keys()
            self.add_check_constraints()

            # Generate report
            self.generate_report()

            logger.info("\n✓ All fixes completed successfully!")

        except Exception as e:
            logger.error(f"Error during fix process: {e}", exc_info=True)
            raise
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description="Fix ClimateGPT database schema issues")
    parser.add_argument(
        '--db-path',
        type=Path,
        default=Path('data/warehouse/climategpt.duckdb'),
        help='Path to DuckDB database'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create backup before making changes'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )

    args = parser.parse_args()

    if not args.db_path.exists():
        logger.error(f"Database not found: {args.db_path}")
        return 1

    fixer = DatabaseSchemaFixer(args.db_path, dry_run=args.dry_run)
    fixer.run(create_backup=args.backup)

    return 0


if __name__ == "__main__":
    exit(main())
