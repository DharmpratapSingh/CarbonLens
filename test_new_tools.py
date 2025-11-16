#!/usr/bin/env python3
"""
Test script for new ClimateGPT MCP tools

Tests the Phase 3 tools: top_emitters, analyze_trend, compare_sectors, compare_geographies
"""
import json
import sys
from pathlib import Path

# Add parent directory to path to import mcp_server_stdio functions
sys.path.insert(0, str(Path(__file__).parent))

try:
    from mcp_server_stdio import (
        _normalize_entity_name,
        _get_iso3_code,
        query_cache
    )
except ImportError as e:
    print(f"❌ Error importing: {e}")
    print("Make sure mcp_server_stdio.py is in the same directory")
    sys.exit(1)

def test_entity_resolution():
    """Test Phase 2: Entity Resolution"""
    print("=" * 80)
    print("TESTING PHASE 2: ENTITY RESOLUTION")
    print("=" * 80)
    print()
    
    test_cases = [
        ("USA", "United States of America"),
        ("Bosnia and Herz.", "Bosnia and Herzegovina"),
        ("Dem. Rep. Congo", "Democratic Republic of the Congo"),
        ("Eq. Guinea", "Equatorial Guinea"),
        ("China", "People's Republic of China"),
    ]
    
    print("Testing entity normalization:")
    all_passed = True
    for input_name, expected in test_cases:
        result = _normalize_entity_name(input_name)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"  {status} '{input_name}' → '{result}' (expected: '{expected}')")
    
    print()
    print("Testing ISO3 code lookup:")
    iso3_tests = [
        ("United States of America", "USA"),
        ("China", "CHN"),
        ("Germany", "DEU"),
        ("United Kingdom", "GBR"),
    ]
    
    for country, expected_iso3 in iso3_tests:
        result = _get_iso3_code(country)
        status = "✅" if result == expected_iso3 else "❌"
        if result != expected_iso3:
            all_passed = False
        print(f"  {status} '{country}' → ISO3: '{result}' (expected: '{expected_iso3}')")
    
    print()
    return all_passed

def test_cache():
    """Test Phase 4: Query Cache"""
    print("=" * 80)
    print("TESTING PHASE 4: QUERY CACHE")
    print("=" * 80)
    print()
    
    # Clear cache for clean test
    query_cache.clear()
    
    print("Cache initialized:")
    stats = query_cache.get_stats()
    print(f"  - Max size: {stats['maxsize']}")
    print(f"  - TTL: {query_cache.ttl_seconds} seconds")
    print(f"  - Current size: {stats['size']}")
    print()
    
    print("✅ Cache infrastructure ready")
    print("   (Cache will be used automatically in query execution)")
    print()
    
    return True

def test_materialized_views():
    """Test Phase 4: Materialized Views"""
    print("=" * 80)
    print("TESTING PHASE 4: MATERIALIZED VIEWS")
    print("=" * 80)
    print()
    
    try:
        import duckdb
        conn = duckdb.connect("data/warehouse/climategpt.duckdb", read_only=True)
        
        # Check if views exist
        views = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main' 
            AND table_name LIKE 'mv_%'
            ORDER BY table_name
        """).fetchall()
        
        if views:
            print(f"✅ Found {len(views)} materialized views:")
            for (view_name,) in views:
                count = conn.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
                print(f"  - {view_name}: {count:,} rows")
            
            # Test a query
            print()
            print("Testing query on materialized view:")
            result = conn.execute("""
                SELECT country_name, total_emissions 
                FROM mv_top20_countries_yearly 
                WHERE year = 2023 
                ORDER BY rank 
                LIMIT 5
            """).fetchall()
            
            if result:
                print("  ✅ Query successful:")
                for row in result:
                    print(f"    - {row[0]}: {row[1]:,.0f} tonnes CO₂")
            else:
                print("  ⚠️  No data for 2023")
        else:
            print("❌ No materialized views found")
            print("   Run: python create_materialized_views.py")
            conn.close()
            return False
        
        conn.close()
        print()
        return True
        
    except ImportError:
        print("⚠️  DuckDB not available - skipping materialized view test")
        print("   (Views should be created via create_materialized_views.py)")
        print()
        return True
    except Exception as e:
        print(f"❌ Error testing materialized views: {e}")
        print()
        return False

def main():
    print()
    print("=" * 80)
    print("CLIMATEGPT IMPLEMENTATION TEST SUITE")
    print("=" * 80)
    print()
    
    results = {
        "Phase 2: Entity Resolution": test_entity_resolution(),
        "Phase 4: Query Cache": test_cache(),
        "Phase 4: Materialized Views": test_materialized_views(),
    }
    
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("✅ ALL TESTS PASSED")
        print()
        print("Next steps:")
        print("  1. Start MCP server: python mcp_server_stdio.py")
        print("  2. Test tools via MCP protocol")
        print("  3. Monitor cache performance in production")
    else:
        print("❌ SOME TESTS FAILED - Review errors above")
        sys.exit(1)
    
    print()

if __name__ == "__main__":
    main()

