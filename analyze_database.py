#!/usr/bin/env python3
"""
Comprehensive Database Analysis Script for ClimateGPT
Analyzes the DuckDB database and outputs detailed statistics
"""

import duckdb
import json
from pathlib import Path
from collections import defaultdict
import sys

# Configuration
DB_PATH = "data/warehouse/climategpt.duckdb"

def analyze_database(db_path: str):
    """Comprehensive database analysis"""

    print("=" * 80)
    print("CLIMATEGPT DATABASE ANALYSIS REPORT")
    print("=" * 80)
    print()

    conn = duckdb.connect(db_path, read_only=True)

    # ========================================================================
    # 1. GENERAL DATABASE INFO
    # ========================================================================
    print("1. DATABASE OVERVIEW")
    print("-" * 80)

    # Get database size
    db_size = Path(db_path).stat().st_size
    print(f"Database File Size: {db_size / (1024**3):.2f} GB ({db_size:,} bytes)")
    print()

    # Get all tables
    tables = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'main'
        ORDER BY table_name
    """).fetchall()

    table_names = [t[0] for t in tables]
    print(f"Total Tables: {len(table_names)}")
    print(f"Table Names: {', '.join(table_names)}")
    print()

    # ========================================================================
    # 2. TABLE-BY-TABLE ANALYSIS
    # ========================================================================
    print("\n2. DETAILED TABLE ANALYSIS")
    print("-" * 80)

    table_stats = {}

    for table_name in table_names:
        print(f"\n📊 TABLE: {table_name}")
        print("  " + "-" * 76)

        stats = {}

        # Row count
        row_count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        stats['row_count'] = row_count
        print(f"  Rows: {row_count:,}")

        # Column information
        columns = conn.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """).fetchall()

        stats['columns'] = [
            {'name': c[0], 'type': c[1], 'nullable': c[2]}
            for c in columns
        ]

        print(f"  Columns ({len(columns)}):")
        for col in columns:
            print(f"    - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")

        # Sample data (first 3 rows)
        print(f"\n  Sample Data (first 3 rows):")
        sample = conn.execute(f"SELECT * FROM {table_name} LIMIT 3").fetchall()
        col_names = [c[0] for c in columns]

        if sample:
            for i, row in enumerate(sample, 1):
                print(f"    Row {i}:")
                for col_name, value in zip(col_names, row):
                    # Truncate long values
                    val_str = str(value)
                    if len(val_str) > 50:
                        val_str = val_str[:47] + "..."
                    print(f"      {col_name}: {val_str}")

        # NULL analysis
        print(f"\n  NULL Value Analysis:")
        null_counts = {}
        for col_name, col_type, _ in columns:
            null_count = conn.execute(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE {col_name} IS NULL
            """).fetchone()[0]

            if null_count > 0:
                pct = (null_count / row_count * 100) if row_count > 0 else 0
                null_counts[col_name] = {'count': null_count, 'percentage': pct}
                print(f"    - {col_name}: {null_count:,} ({pct:.2f}%)")

        if not null_counts:
            print(f"    ✓ No NULL values found")

        stats['null_counts'] = null_counts

        # Data distribution for key columns
        if 'year' in col_names:
            year_dist = conn.execute(f"""
                SELECT
                    MIN(year) as min_year,
                    MAX(year) as max_year,
                    COUNT(DISTINCT year) as distinct_years
                FROM {table_name}
            """).fetchone()

            stats['year_range'] = {
                'min': year_dist[0],
                'max': year_dist[1],
                'distinct': year_dist[2]
            }
            print(f"\n  Year Coverage:")
            print(f"    Range: {year_dist[0]} - {year_dist[1]}")
            print(f"    Distinct Years: {year_dist[2]}")

        if 'month' in col_names:
            month_dist = conn.execute(f"""
                SELECT COUNT(DISTINCT month) as distinct_months
                FROM {table_name}
            """).fetchone()

            stats['month_coverage'] = month_dist[0]
            print(f"    Distinct Months: {month_dist[0]}")

        # Geographic coverage
        geo_cols = ['country_name', 'admin1_name', 'city_name']
        for geo_col in geo_cols:
            if geo_col in col_names:
                geo_stats = conn.execute(f"""
                    SELECT
                        COUNT(DISTINCT {geo_col}) as distinct_count,
                        COUNT(*) - COUNT({geo_col}) as null_count
                    FROM {table_name}
                """).fetchone()

                print(f"\n  {geo_col.replace('_', ' ').title()} Coverage:")
                print(f"    Distinct Values: {geo_stats[0]:,}")
                print(f"    NULL Values: {geo_stats[1]:,}")

                # Top 10 by count
                top_10 = conn.execute(f"""
                    SELECT {geo_col}, COUNT(*) as cnt
                    FROM {table_name}
                    WHERE {geo_col} IS NOT NULL
                    GROUP BY {geo_col}
                    ORDER BY cnt DESC
                    LIMIT 10
                """).fetchall()

                if top_10:
                    print(f"    Top 10 (by row count):")
                    for name, cnt in top_10:
                        print(f"      {name}: {cnt:,} rows")

        # Emissions statistics
        if 'emissions_tonnes' in col_names:
            emissions_stats = conn.execute(f"""
                SELECT
                    MIN(emissions_tonnes) as min_val,
                    MAX(emissions_tonnes) as max_val,
                    AVG(emissions_tonnes) as avg_val,
                    MEDIAN(emissions_tonnes) as median_val,
                    STDDEV(emissions_tonnes) as stddev_val,
                    COUNT(*) - COUNT(emissions_tonnes) as null_count
                FROM {table_name}
            """).fetchone()

            stats['emissions_stats'] = {
                'min': float(emissions_stats[0]) if emissions_stats[0] else None,
                'max': float(emissions_stats[1]) if emissions_stats[1] else None,
                'avg': float(emissions_stats[2]) if emissions_stats[2] else None,
                'median': float(emissions_stats[3]) if emissions_stats[3] else None,
                'stddev': float(emissions_stats[4]) if emissions_stats[4] else None,
                'null_count': emissions_stats[5]
            }

            print(f"\n  Emissions Statistics (tonnes CO₂):")
            print(f"    Min: {emissions_stats[0]:,.2f}" if emissions_stats[0] else "    Min: NULL")
            print(f"    Max: {emissions_stats[1]:,.2f}" if emissions_stats[1] else "    Max: NULL")
            print(f"    Average: {emissions_stats[2]:,.2f}" if emissions_stats[2] else "    Average: NULL")
            print(f"    Median: {emissions_stats[3]:,.2f}" if emissions_stats[3] else "    Median: NULL")
            print(f"    Std Dev: {emissions_stats[4]:,.2f}" if emissions_stats[4] else "    Std Dev: NULL")
            print(f"    NULL Count: {emissions_stats[5]:,}")

        table_stats[table_name] = stats
        print()

    # ========================================================================
    # 3. CROSS-TABLE ANALYSIS
    # ========================================================================
    print("\n3. CROSS-TABLE ANALYSIS")
    print("-" * 80)

    # Total rows across all tables
    total_rows = sum(stats['row_count'] for stats in table_stats.values())
    print(f"Total Rows Across All Tables: {total_rows:,}")

    # Identify table patterns
    sectors = set()
    resolutions = set()
    temporal_res = set()

    for table_name in table_names:
        parts = table_name.split('_')
        if len(parts) >= 3:
            sectors.add(parts[0])
            resolutions.add(parts[1])
            temporal_res.add(parts[2])

    print(f"\nSectors: {', '.join(sorted(sectors))}")
    print(f"Geographic Resolutions: {', '.join(sorted(resolutions))}")
    print(f"Temporal Resolutions: {', '.join(sorted(temporal_res))}")

    # ========================================================================
    # 4. UNIQUE VALUES FOR ENTITY RESOLUTION
    # ========================================================================
    print("\n\n4. UNIQUE VALUES (for Entity Resolution)")
    print("-" * 80)

    # Get all unique countries across all tables
    print("\nUnique Countries (sample from first table with country_name):")
    for table_name in table_names:
        if conn.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table_name}' AND column_name = 'country_name'
        """).fetchall():
            countries = conn.execute(f"""
                SELECT DISTINCT country_name
                FROM {table_name}
                WHERE country_name IS NOT NULL
                ORDER BY country_name
                LIMIT 50
            """).fetchall()

            print(f"  From {table_name} (showing first 50):")
            for country in countries:
                print(f"    - {country[0]}")
            break

    # Get all unique admin1 names (sample)
    print("\nUnique Admin1 Names (sample from first admin1 table):")
    for table_name in table_names:
        if 'admin1' in table_name:
            admin1s = conn.execute(f"""
                SELECT DISTINCT admin1_name, country_name
                FROM {table_name}
                WHERE admin1_name IS NOT NULL
                ORDER BY admin1_name
                LIMIT 30
            """).fetchall()

            print(f"  From {table_name} (showing first 30):")
            for admin1, country in admin1s:
                print(f"    - {admin1} ({country})")
            break

    # Get all unique cities (sample)
    print("\nUnique City Names (sample from first city table):")
    for table_name in table_names:
        if 'city' in table_name:
            cities = conn.execute(f"""
                SELECT DISTINCT city_name, admin1_name, country_name
                FROM {table_name}
                WHERE city_name IS NOT NULL
                ORDER BY city_name
                LIMIT 30
            """).fetchall()

            print(f"  From {table_name} (showing first 30):")
            for city, admin1, country in cities:
                print(f"    - {city}, {admin1}, {country}")
            break

    # ========================================================================
    # 5. INDEX ANALYSIS
    # ========================================================================
    print("\n\n5. INDEX ANALYSIS")
    print("-" * 80)

    for table_name in table_names:
        indexes = conn.execute(f"""
            SELECT
                index_name,
                is_unique,
                sql
            FROM duckdb_indexes()
            WHERE table_name = '{table_name}'
        """).fetchall()

        if indexes:
            print(f"\n{table_name}:")
            for idx in indexes:
                print(f"  - {idx[0]} (Unique: {idx[1]})")
                print(f"    SQL: {idx[2]}")
        else:
            print(f"\n{table_name}: No indexes found")

    # ========================================================================
    # 6. DATA QUALITY ISSUES
    # ========================================================================
    print("\n\n6. DATA QUALITY CHECKS")
    print("-" * 80)

    issues_found = []

    for table_name in table_names:
        # Check for negative emissions
        if conn.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table_name}' AND column_name = 'emissions_tonnes'
        """).fetchall():

            negative_count = conn.execute(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE emissions_tonnes < 0
            """).fetchone()[0]

            if negative_count > 0:
                issues_found.append(f"{table_name}: {negative_count:,} rows with negative emissions")

            # Check for extreme outliers (>3 std dev from mean)
            outliers = conn.execute(f"""
                WITH stats AS (
                    SELECT
                        AVG(emissions_tonnes) as avg_val,
                        STDDEV(emissions_tonnes) as stddev_val
                    FROM {table_name}
                )
                SELECT COUNT(*)
                FROM {table_name}, stats
                WHERE ABS(emissions_tonnes - avg_val) > 3 * stddev_val
            """).fetchone()[0]

            if outliers > 0:
                issues_found.append(f"{table_name}: {outliers:,} statistical outliers (>3σ)")

    if issues_found:
        print("\n⚠️  Issues Found:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("\n✓ No data quality issues detected")

    # ========================================================================
    # 7. SUMMARY STATISTICS
    # ========================================================================
    print("\n\n7. SUMMARY STATISTICS")
    print("-" * 80)

    summary = {
        'total_tables': len(table_names),
        'total_rows': total_rows,
        'database_size_gb': db_size / (1024**3),
        'sectors': list(sorted(sectors)),
        'geographic_resolutions': list(sorted(resolutions)),
        'temporal_resolutions': list(sorted(temporal_res))
    }

    print(json.dumps(summary, indent=2))

    conn.close()

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    if not Path(DB_PATH).exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        print("Please update DB_PATH in the script to point to your database file.")
        sys.exit(1)

    try:
        analyze_database(DB_PATH)
    except Exception as e:
        print(f"ERROR during analysis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
