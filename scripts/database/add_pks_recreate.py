#!/usr/bin/env python3
"""
Add primary keys to year-level tables by recreating them.
Alternative approach to bypass DuckDB dependency locking.
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

def get_table_columns(conn, table_name):
    """Get list of columns for a table."""
    result = conn.execute(f"""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = '{table_name}'
        ORDER BY ordinal_position
    """).fetchall()
    return [row[0] for row in result]

def recreate_table_with_pk(conn, table_name, pk_columns):
    """
    Recreate table with primary key by:
    1. Creating temp table with PK
    2. Copying data
    3. Dropping original
    4. Renaming temp to original
    """
    try:
        # Check if PK already exists
        pk_check = conn.execute(f"""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = '{table_name}'
            AND constraint_type = 'PRIMARY KEY'
        """).fetchall()

        if pk_check:
            print(f"✓ {table_name}: Primary key already exists")
            return True

        # Get columns
        columns = get_table_columns(conn, table_name)
        if not columns:
            print(f"✗ {table_name}: Could not retrieve columns")
            return False

        # Create temp table with PK
        col_list = ", ".join(columns)
        pk_cols = ", ".join(pk_columns)

        temp_name = f"tmp_{table_name}_pk"

        # Create table with PK constraint
        create_sql = f"""
            CREATE TABLE {temp_name} AS
            SELECT {col_list}
            FROM {table_name}
            ORDER BY {pk_cols}
        """

        conn.execute(create_sql)

        # Now add the PK constraint to temp table
        conn.execute(f"ALTER TABLE {temp_name} ADD PRIMARY KEY ({pk_cols})")

        # Drop original table
        conn.execute(f"DROP TABLE {table_name}")

        # Rename temp to original
        conn.execute(f"ALTER TABLE {temp_name} RENAME TO {table_name}")

        print(f"✓ {table_name}: Recreated with primary key ({pk_cols})")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"✗ {table_name}: {error_msg[:100]}")
        return False

def main():
    """Main execution."""
    print("=" * 80)
    print("ADDING PRIMARY KEYS TO YEAR TABLES (via recreation)")
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

    print("COUNTRY TABLES")
    print("-" * 80)

    # Country-level tables
    for sector in SECTORS:
        table_name = f"{sector}_country_year"
        pk_cols = ("iso3", "year")

        total += 1
        if recreate_table_with_pk(conn, table_name, pk_cols):
            succeeded += 1
        else:
            failed += 1

    print("\nADMIN1 TABLES")
    print("-" * 80)

    # Admin1 level tables
    for sector in SECTORS:
        table_name = f"{sector}_admin1_year"
        pk_cols = ("admin1_geoid", "year")

        total += 1
        if recreate_table_with_pk(conn, table_name, pk_cols):
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

    if succeeded == total:
        print("\n✅ All year tables now have primary keys!")
    else:
        print(f"\n⚠️  {failed} tables could not be updated.")

    conn.close()
    print("\n✅ Database connection closed")

if __name__ == "__main__":
    main()
