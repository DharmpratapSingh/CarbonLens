#!/usr/bin/env python3
"""
Create Materialized Views for ClimateGPT Database

This script creates pre-computed aggregations for faster queries.
"""
import duckdb
import sys
from pathlib import Path

DB_PATH = "data/warehouse/climategpt.duckdb"
SQL_FILE = "create_materialized_views.sql"

def main():
    print("=" * 80)
    print("CREATING MATERIALIZED VIEWS")
    print("=" * 80)
    print()
    
    if not Path(DB_PATH).exists():
        print(f"❌ ERROR: Database not found at {DB_PATH}")
        sys.exit(1)
    
    if not Path(SQL_FILE).exists():
        print(f"❌ ERROR: SQL file not found at {SQL_FILE}")
        sys.exit(1)
    
    print(f"📂 Connecting to database: {DB_PATH}")
    conn = duckdb.connect(DB_PATH)
    print("✅ Connected successfully")
    print()
    
    print(f"📖 Reading SQL file: {SQL_FILE}")
    sql_content = Path(SQL_FILE).read_text()
    
    print("🔨 Creating materialized views...")
    print()
    
    try:
        conn.execute(sql_content)
        print("✅ Materialized views created successfully")
        print()
        
        # Verify views were created
        views = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            AND table_name LIKE 'mv_%'
            ORDER BY table_name
        """).fetchall()
        
        print(f"Materialized views created: {len(views)}")
        for (view_name,) in views:
            count = conn.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
            print(f"  - {view_name}: {count:,} rows")
        
        print()
        
        # Check indexes on views
        indexes = conn.execute("""
            SELECT table_name, index_name
            FROM duckdb_indexes()
            WHERE table_name LIKE 'mv_%'
            ORDER BY table_name, index_name
        """).fetchall()
        
        print(f"Indexes on materialized views: {len(indexes)}")
        for table, idx in indexes:
            print(f"  - {table}.{idx}")
        
        print()
        print("=" * 80)
        print("✅ MATERIALIZED VIEWS SETUP COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("  1. Test queries using materialized views")
        print("  2. Monitor query performance improvements")
        print("  3. Use views for top emitters and total emissions queries")
        print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ ERROR creating materialized views: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

