#!/usr/bin/env python3
"""
Apply Database Indexes and Measure Performance Improvement

This script:
1. Measures query performance BEFORE indexing
2. Creates all indexes from create_database_indexes.sql
3. Measures query performance AFTER indexing
4. Generates a performance report

Usage:
    python apply_database_indexes.py
"""

import duckdb
import time
from pathlib import Path
import sys

# Configuration
DB_PATH = "data/warehouse/climategpt.duckdb"
SQL_FILE = "create_database_indexes.sql"

# Test queries to measure performance improvement
TEST_QUERIES = [
    {
        "name": "Country-Year Lookup (Transport)",
        "sql": "SELECT * FROM transport_country_year WHERE country_name = 'United States of America' AND year = 2023"
    },
    {
        "name": "Admin1-Year Lookup (Power)",
        "sql": "SELECT * FROM power_admin1_year WHERE country_name = 'United States of America' AND admin1_name = 'California' AND year = 2023"
    },
    {
        "name": "City-Year Lookup (Waste)",
        "sql": "SELECT * FROM waste_city_year WHERE country_name = 'United States of America' AND admin1_name = 'California' AND city_name = 'Los Angeles' AND year = 2023"
    },
    {
        "name": "Large City Monthly Scan (Transport)",
        "sql": "SELECT * FROM transport_city_monthly WHERE city_name = 'New York' AND year = 2023"
    },
    {
        "name": "Year Range Aggregation",
        "sql": "SELECT year, SUM(emissions_tonnes) FROM transport_country_year WHERE country_name = 'China' AND year BETWEEN 2018 AND 2023 GROUP BY year ORDER BY year"
    },
    {
        "name": "ISO3 Lookup",
        "sql": "SELECT * FROM transport_country_year WHERE iso3 = 'USA' AND year = 2023"
    },
    {
        "name": "Multi-table Join",
        "sql": """
            SELECT
                t.country_name,
                t.year,
                t.emissions_tonnes as transport_emissions,
                p.emissions_tonnes as power_emissions
            FROM transport_country_year t
            JOIN power_country_year p ON t.country_name = p.country_name AND t.year = p.year
            WHERE t.country_name = 'Germany' AND t.year = 2023
        """
    },
    {
        "name": "Temporal Aggregation (Monthly to Yearly)",
        "sql": "SELECT year, SUM(emissions_tonnes) FROM transport_country_monthly WHERE country_name = 'India' AND year = 2023 GROUP BY year"
    }
]


def measure_query_performance(conn, query_name, sql, iterations=5):
    """Measure average query execution time"""
    times = []

    for i in range(iterations):
        start = time.time()
        try:
            result = conn.execute(sql).fetchall()
            end = time.time()
            times.append((end - start) * 1000)  # Convert to milliseconds
        except Exception as e:
            print(f"  ⚠️  Query failed: {e}")
            return None

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)

    return {
        'avg': avg_time,
        'min': min_time,
        'max': max_time,
        'times': times
    }


def get_database_stats(conn):
    """Get database and index statistics"""
    # Database size
    db_size = Path(DB_PATH).stat().st_size

    # Count indexes
    indexes = conn.execute("""
        SELECT COUNT(*) as index_count
        FROM duckdb_indexes()
    """).fetchone()[0]

    # Count tables
    tables = conn.execute("""
        SELECT COUNT(*) as table_count
        FROM information_schema.tables
        WHERE table_schema = 'main'
    """).fetchone()[0]

    return {
        'size_bytes': db_size,
        'size_gb': db_size / (1024**3),
        'index_count': indexes,
        'table_count': tables
    }


def main():
    print("=" * 80)
    print("DATABASE INDEX APPLICATION AND PERFORMANCE TESTING")
    print("=" * 80)
    print()

    # Check files exist
    if not Path(DB_PATH).exists():
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        print("Please update DB_PATH in the script.")
        sys.exit(1)

    if not Path(SQL_FILE).exists():
        print(f"❌ ERROR: SQL file not found at {SQL_FILE}")
        sys.exit(1)

    # Connect to database
    print(f"📂 Connecting to database: {DB_PATH}")
    conn = duckdb.connect(DB_PATH)
    print("✅ Connected successfully")
    print()

    # ========================================================================
    # STEP 1: Measure BEFORE performance
    # ========================================================================
    print("=" * 80)
    print("STEP 1: MEASURING PERFORMANCE BEFORE INDEXING")
    print("=" * 80)
    print()

    stats_before = get_database_stats(conn)
    print(f"Database Size: {stats_before['size_gb']:.2f} GB ({stats_before['size_bytes']:,} bytes)")
    print(f"Total Tables: {stats_before['table_count']}")
    print(f"Total Indexes: {stats_before['index_count']}")
    print()

    print("Running test queries (5 iterations each)...")
    print()

    results_before = {}
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"[{i}/{len(TEST_QUERIES)}] {query['name']}...")
        perf = measure_query_performance(conn, query['name'], query['sql'])
        if perf:
            results_before[query['name']] = perf
            print(f"  ⏱️  Avg: {perf['avg']:.2f}ms | Min: {perf['min']:.2f}ms | Max: {perf['max']:.2f}ms")
        print()

    # ========================================================================
    # STEP 2: Create indexes
    # ========================================================================
    print("=" * 80)
    print("STEP 2: CREATING INDEXES")
    print("=" * 80)
    print()

    print(f"📖 Reading SQL file: {SQL_FILE}")
    sql_content = Path(SQL_FILE).read_text()

    print("🔨 Creating indexes... (this may take a few minutes)")
    print()

    start_time = time.time()

    try:
        # Execute the SQL file
        conn.execute(sql_content)

        end_time = time.time()
        duration = end_time - start_time

        print(f"✅ Indexes created successfully in {duration:.2f} seconds ({duration/60:.2f} minutes)")
        print()

    except Exception as e:
        print(f"❌ ERROR creating indexes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # ========================================================================
    # STEP 3: Measure AFTER performance
    # ========================================================================
    print("=" * 80)
    print("STEP 3: MEASURING PERFORMANCE AFTER INDEXING")
    print("=" * 80)
    print()

    stats_after = get_database_stats(conn)
    print(f"Database Size: {stats_after['size_gb']:.2f} GB ({stats_after['size_bytes']:,} bytes)")
    print(f"Total Tables: {stats_after['table_count']}")
    print(f"Total Indexes: {stats_after['index_count']}")
    print(f"Size Increase: {(stats_after['size_bytes'] - stats_before['size_bytes']) / (1024**2):.2f} MB")
    print()

    print("Running test queries (5 iterations each)...")
    print()

    results_after = {}
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"[{i}/{len(TEST_QUERIES)}] {query['name']}...")
        perf = measure_query_performance(conn, query['name'], query['sql'])
        if perf:
            results_after[query['name']] = perf
            print(f"  ⏱️  Avg: {perf['avg']:.2f}ms | Min: {perf['min']:.2f}ms | Max: {perf['max']:.2f}ms")
        print()

    conn.close()

    # ========================================================================
    # STEP 4: Generate performance report
    # ========================================================================
    print("=" * 80)
    print("PERFORMANCE IMPROVEMENT REPORT")
    print("=" * 80)
    print()

    print(f"{'Query Name':<40} {'Before (ms)':<15} {'After (ms)':<15} {'Speedup':<15}")
    print("-" * 85)

    total_speedup = 0
    count = 0

    for query_name in results_before.keys():
        if query_name in results_after:
            before = results_before[query_name]['avg']
            after = results_after[query_name]['avg']
            speedup = before / after if after > 0 else 0

            print(f"{query_name:<40} {before:>12.2f}ms  {after:>12.2f}ms  {speedup:>12.2f}x")

            total_speedup += speedup
            count += 1

    print("-" * 85)

    if count > 0:
        avg_speedup = total_speedup / count
        print(f"{'AVERAGE SPEEDUP':<40} {'':<15} {'':<15} {avg_speedup:>12.2f}x")

    print()
    print("=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    print()
    print(f"Before Indexing:")
    print(f"  - Size: {stats_before['size_gb']:.2f} GB")
    print(f"  - Indexes: {stats_before['index_count']}")
    print()
    print(f"After Indexing:")
    print(f"  - Size: {stats_after['size_gb']:.2f} GB")
    print(f"  - Indexes: {stats_after['index_count']}")
    print(f"  - Size Increase: {(stats_after['size_bytes'] - stats_before['size_bytes']) / (1024**2):.2f} MB ({((stats_after['size_bytes'] / stats_before['size_bytes']) - 1) * 100:.1f}% increase)")
    print(f"  - New Indexes Created: {stats_after['index_count'] - stats_before['index_count']}")
    print()

    print("=" * 80)
    print("✅ INDEX APPLICATION COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Review the performance improvements above")
    print("  2. Test your application queries to verify speedup")
    print("  3. Monitor database size and performance in production")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
