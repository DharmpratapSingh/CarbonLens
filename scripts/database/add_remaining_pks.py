#!/usr/bin/env python3
"""
Add primary keys to remaining year-level tables.
These tables were blocked during initial implementation due to materialized view dependencies.
"""

import duckdb
import sys
from pathlib import Path

# Database path
DB_PATH = Path("data/warehouse/climategpt.duckdb")

# Sector-level mappings
SECTORS = [
    "agriculture",
    "buildings",
    "fuel_exploitation",
    "ind_combustion",
    "ind_processes",
    "power",
    "waste",
]

# Granularity levels and their PK columns
GRANULARITY_PK = {
    "country": ("iso3", "year"),
    "admin1": ("admin1_geoid", "year"),
    "city": ("city_id", "year"),
}

def check_pk_exists(conn, table_name):
    """Check if primary key already exists on table."""
    try:
        result = conn.execute(f"""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = '{table_name}'
            AND constraint_type = 'PRIMARY KEY'
        """).fetchall()
        return len(result) > 0
    except Exception as e:
        return False

def add_primary_key(conn, table_name, pk_columns):
    """Add primary key to table."""
    try:
        # Check if PK already exists
        if check_pk_exists(conn, table_name):
            print(f"✓ {table_name}: Primary key already exists")
            return True

        # Try to add PK
        pk_cols_str = ", ".join(pk_columns)
        conn.execute(f"ALTER TABLE {table_name} ADD PRIMARY KEY ({pk_cols_str})")
        print(f"✓ {table_name}: Added primary key ({pk_cols_str})")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"✗ {table_name}: {error_msg[:100]}")
        return False

def main():
    """Main execution."""
    print("=" * 80)
    print("ADDING PRIMARY KEYS TO REMAINING YEAR TABLES")
    print("=" * 80)

    # Connect to database
    try:
        conn = duckdb.connect(str(DB_PATH), read_only=False)
        print(f"✅ Connected to {DB_PATH}\n")
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        sys.exit(1)

    # Track results
    total = 0
    succeeded = 0
    failed = 0
    skipped = 0

    print("YEAR TABLES")
    print("-" * 80)

    # Country-level tables (transport already has PK from previous run)
    for sector in SECTORS:
        table_name = f"{sector}_country_year"
        pk_cols = GRANULARITY_PK["country"]

        total += 1
        if add_primary_key(conn, table_name, pk_cols):
            succeeded += 1
        else:
            failed += 1

    print("\nADMIN1 TABLES")
    print("-" * 80)

    # Admin1 level tables
    for sector in SECTORS:
        table_name = f"{sector}_admin1_year"
        pk_cols = GRANULARITY_PK["admin1"]

        total += 1
        if add_primary_key(conn, table_name, pk_cols):
            succeeded += 1
        else:
            failed += 1

    print("\nCITY TABLES")
    print("-" * 80)

    # City level tables
    for sector in SECTORS:
        table_name = f"{sector}_city_year"
        pk_cols = GRANULARITY_PK["city"]

        total += 1
        if add_primary_key(conn, table_name, pk_cols):
            succeeded += 1
        else:
            failed += 1

    # Verify results
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total tables processed: {total}")
    print(f"Successfully added PKs: {succeeded}")
    print(f"Failed: {failed}")

    if failed > 0:
        print(f"\n⚠️  {failed} tables still have PK dependency issues.")
        print("These may need manual intervention or re-running after")
        print("additional cleanup of views/dependencies.")
    else:
        print("\n✅ All year tables now have primary keys!")

    conn.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main()
