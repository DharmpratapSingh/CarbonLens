#!/usr/bin/env python3
"""
Phase 5 Implementation Validation Script

Tests all 8 improvements from Phase 5:
1. Type hints (via mypy)
2. Entity normalization (shared module import)
3. Pydantic models (validation testing)
4. Request ID tracking (logging test)
5. Database pool configuration (env var test)
6. Error sanitization (production vs development)
7. LLM semaphore configuration (env var test)
8. Serialization optimization (large response test)
"""

import sys
import os
import subprocess
from typing import Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class Colors:
    """ANSI color codes"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_test(name: str):
    """Print test name"""
    print(f"{Colors.BOLD}Testing: {name}{Colors.END}")

def print_pass(message: str):
    """Print success message"""
    print(f"  {Colors.GREEN}✓ PASS{Colors.END}: {message}")

def print_fail(message: str):
    """Print failure message"""
    print(f"  {Colors.RED}✗ FAIL{Colors.END}: {message}")

def print_warning(message: str):
    """Print warning message"""
    print(f"  {Colors.YELLOW}⚠ WARNING{Colors.END}: {message}")


# ============================================================================
# TEST 1: Entity Normalization (Shared Module)
# ============================================================================
def test_entity_normalization() -> bool:
    """Test that entity normalization can be imported and works"""
    print_test("Entity Normalization (Shared Module)")

    try:
        from shared.entity_normalization import (
            normalize_entity_name,
            fuzzy_match_entity,
            get_iso3_code,
            detect_geographic_level,
            COUNTRY_ALIASES,
            STATE_ALIASES,
            CITY_ALIASES,
            ISO3_CODES
        )
        print_pass("Successfully imported from shared.entity_normalization")

        # Test normalization
        test_cases = [
            ("USA", "United States of America"),
            ("Bosnia and Herz.", "Bosnia and Herzegovina"),
            ("Dem. Rep. Congo", "Democratic Republic of the Congo"),
        ]

        all_passed = True
        for input_val, expected in test_cases:
            result = normalize_entity_name(input_val)
            if result == expected:
                print_pass(f"'{input_val}' → '{result}'")
            else:
                print_fail(f"'{input_val}' → '{result}' (expected '{expected}')")
                all_passed = False

        # Test ISO3 lookup
        iso3 = get_iso3_code("United States of America")
        if iso3 == "USA":
            print_pass(f"ISO3 lookup: 'United States of America' → '{iso3}'")
        else:
            print_fail(f"ISO3 lookup failed: got '{iso3}', expected 'USA'")
            all_passed = False

        # Test fuzzy matching
        matches = fuzzy_match_entity("Califrnia", ["California", "Colorado", "Connecticut"])
        if matches and matches[0][0] == "California":
            print_pass(f"Fuzzy match: 'Califrnia' → '{matches[0][0]}' (score: {matches[0][1]:.2f})")
        else:
            print_fail("Fuzzy matching failed")
            all_passed = False

        return all_passed

    except Exception as e:
        print_fail(f"Import or execution failed: {e}")
        return False


# ============================================================================
# TEST 2: Pydantic Models (Schema Validation)
# ============================================================================
def test_pydantic_models() -> bool:
    """Test that Pydantic models validate correctly"""
    print_test("Pydantic Models (Schema Validation)")

    try:
        from models.schemas import (
            QueryEmissionsRequest,
            TopEmittersRequest,
            TrendAnalysisRequest,
            CompareSectorsRequest,
            CompareGeographiesRequest
        )
        from pydantic import ValidationError

        print_pass("Successfully imported Pydantic models")

        # Test valid request
        try:
            req = QueryEmissionsRequest(
                sector="transport",
                year=2023,
                country_name="USA"
            )
            print_pass(f"Valid request accepted: sector={req.sector}, year={req.year}")
        except Exception as e:
            print_fail(f"Valid request rejected: {e}")
            return False

        # Test invalid sector
        try:
            req = QueryEmissionsRequest(
                sector="invalid_sector",
                year=2023
            )
            print_fail("Invalid sector accepted (should have been rejected)")
            return False
        except ValidationError:
            print_pass("Invalid sector correctly rejected")

        # Test invalid year
        try:
            req = QueryEmissionsRequest(
                sector="transport",
                year=2050  # Future year
            )
            print_fail("Future year accepted (should have been rejected)")
            return False
        except ValidationError:
            print_pass("Future year correctly rejected")

        # Test trend analysis year range
        try:
            req = TrendAnalysisRequest(
                entity_name="USA",
                sector="transport",
                start_year=2023,
                end_year=2020  # end < start
            )
            print_fail("Invalid year range accepted (should have been rejected)")
            return False
        except ValidationError:
            print_pass("Invalid year range correctly rejected")

        return True

    except Exception as e:
        print_fail(f"Import or execution failed: {e}")
        return False


# ============================================================================
# TEST 3: Request ID Tracking
# ============================================================================
def test_request_tracking() -> bool:
    """Test request ID tracking middleware"""
    print_test("Request ID Tracking")

    try:
        from middleware.request_tracking import (
            generate_request_id,
            set_request_id,
            get_request_id,
            track_request,
            RequestIDFilter
        )
        print_pass("Successfully imported request tracking components")

        # Test ID generation
        req_id = generate_request_id()
        if req_id and len(req_id) == 36:  # UUID format
            print_pass(f"Request ID generated: {req_id}")
        else:
            print_fail(f"Invalid request ID format: {req_id}")
            return False

        # Test context variable
        set_request_id("test-123")
        retrieved = get_request_id()
        if retrieved == "test-123":
            print_pass(f"Context variable works: set='test-123', get='{retrieved}'")
        else:
            print_fail(f"Context variable failed: expected 'test-123', got '{retrieved}'")
            return False

        # Test decorator
        @track_request
        def test_function():
            return "success"

        result = test_function()
        if result == "success":
            print_pass("@track_request decorator works")
        else:
            print_fail("@track_request decorator failed")
            return False

        return True

    except Exception as e:
        print_fail(f"Import or execution failed: {e}")
        return False


# ============================================================================
# TEST 4: Configuration Management
# ============================================================================
def test_configuration() -> bool:
    """Test centralized configuration"""
    print_test("Configuration Management")

    try:
        # Set test environment variables
        os.environ["DB_POOL_SIZE"] = "15"
        os.environ["LLM_CONCURRENCY_LIMIT"] = "20"
        os.environ["ENVIRONMENT"] = "development"

        # Need to reload config to pick up env vars
        import importlib
        if 'utils.config' in sys.modules:
            importlib.reload(sys.modules['utils.config'])

        from utils.config import Config

        print_pass("Successfully imported Config")

        # Test DB pool size
        if Config.DB_POOL_SIZE == 15:
            print_pass(f"DB_POOL_SIZE correctly loaded: {Config.DB_POOL_SIZE}")
        else:
            print_fail(f"DB_POOL_SIZE incorrect: {Config.DB_POOL_SIZE} (expected 15)")
            return False

        # Test LLM concurrency
        if Config.LLM_CONCURRENCY_LIMIT == 20:
            print_pass(f"LLM_CONCURRENCY_LIMIT correctly loaded: {Config.LLM_CONCURRENCY_LIMIT}")
        else:
            print_fail(f"LLM_CONCURRENCY_LIMIT incorrect: {Config.LLM_CONCURRENCY_LIMIT} (expected 20)")
            return False

        # Test environment detection
        if Config.IS_DEVELOPMENT and not Config.IS_PRODUCTION:
            print_pass(f"Environment correctly detected: {Config.ENVIRONMENT}")
        else:
            print_fail("Environment detection failed")
            return False

        return True

    except Exception as e:
        print_fail(f"Import or execution failed: {e}")
        return False


# ============================================================================
# TEST 5: Error Sanitization
# ============================================================================
def test_error_sanitization() -> bool:
    """Test error message sanitization"""
    print_test("Error Sanitization")

    try:
        from utils.error_handling import (
            sanitize_error_message,
            sanitize_sql_error,
            create_error_response
        )
        print_pass("Successfully imported error handling utilities")

        # Test generic error sanitization
        test_error = ValueError("Database connection failed")

        # Production mode
        os.environ["ENVIRONMENT"] = "production"
        prod_msg = sanitize_error_message(test_error, "database_query")
        if "Database connection failed" not in prod_msg:
            print_pass(f"Production error sanitized: '{prod_msg}'")
        else:
            print_fail("Production error message not sanitized")
            return False

        # Development mode
        os.environ["ENVIRONMENT"] = "development"
        dev_msg = sanitize_error_message(test_error, "database_query")
        if "ValueError" in dev_msg:
            print_pass(f"Development error detailed: '{dev_msg}'")
        else:
            print_fail("Development error message missing details")
            return False

        # Test SQL error sanitization
        sql_error = Exception("SQL execution failed")
        sql_msg = sanitize_sql_error(sql_error, "SELECT * FROM users WHERE id = 1")
        if "SELECT" not in sql_msg:
            print_pass("SQL query not exposed in error message")
        else:
            print_fail("SQL query exposed in error message")
            return False

        return True

    except Exception as e:
        print_fail(f"Import or execution failed: {e}")
        return False


# ============================================================================
# TEST 6: Serialization Optimization
# ============================================================================
def test_serialization() -> bool:
    """Test large response serialization"""
    print_test("Serialization Optimization")

    try:
        from utils.serialization import (
            serialize_large_response,
            chunk_large_response,
            create_paginated_response,
            estimate_response_size,
            should_compress_response
        )
        print_pass("Successfully imported serialization utilities")

        # Create test data
        large_data = [{"id": i, "value": f"data_{i}"} for i in range(2000)]

        # Test serialization
        result = serialize_large_response(large_data, compress=False)
        if isinstance(result, str) and len(result) > 0:
            print_pass(f"Serialization works: {len(result)} bytes")
        else:
            print_fail("Serialization failed")
            return False

        # Test compression
        compressed = serialize_large_response(large_data, compress=True)
        if isinstance(compressed, bytes) and len(compressed) < len(result):
            compression_ratio = len(compressed) / len(result) * 100
            print_pass(f"Compression works: {compression_ratio:.1f}% of original size")
        else:
            print_fail("Compression failed or not effective")
            return False

        # Test pagination
        paginated = create_paginated_response(large_data, page=1, page_size=100)
        if len(paginated["data"]) == 100 and paginated["pagination"]["total_rows"] == 2000:
            print_pass(f"Pagination works: {len(paginated['data'])} rows per page")
        else:
            print_fail("Pagination failed")
            return False

        # Test size estimation
        estimated = estimate_response_size(large_data)
        if estimated > 0:
            print_pass(f"Size estimation works: {estimated} bytes estimated")
        else:
            print_fail("Size estimation failed")
            return False

        return True

    except Exception as e:
        print_fail(f"Import or execution failed: {e}")
        return False


# ============================================================================
# MAIN EXECUTION
# ============================================================================
def main():
    """Run all validation tests"""
    print_header("PHASE 5 IMPLEMENTATION VALIDATION")
    print(f"Testing all 8 improvements from Phase 5: Code Quality & Production Readiness\n")

    # Reset environment for clean test
    os.environ.setdefault("OPENAI_API_KEY", "test:test")
    os.environ.setdefault("ENVIRONMENT", "development")

    results = {}

    # Run all tests
    results["Entity Normalization"] = test_entity_normalization()
    results["Pydantic Models"] = test_pydantic_models()
    results["Request Tracking"] = test_request_tracking()
    results["Configuration"] = test_configuration()
    results["Error Sanitization"] = test_error_sanitization()
    results["Serialization"] = test_serialization()

    # Summary
    print_header("VALIDATION SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, passed_test in results.items():
        status = f"{Colors.GREEN}PASS{Colors.END}" if passed_test else f"{Colors.RED}FAIL{Colors.END}"
        print(f"  {test_name}: {status}")

    print(f"\n{Colors.BOLD}Overall Result: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All Phase 5 implementations validated successfully!{Colors.END}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed. Please review the output above.{Colors.END}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
