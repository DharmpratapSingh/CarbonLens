#!/bin/bash
# Comprehensive test runner for all ClimateGPT components

set -e

echo "========================================================================"
echo "ClimateGPT Comprehensive Testing Suite"
echo "========================================================================"
echo ""

# Activate virtual environment
source .venv/bin/activate

echo "1. Running environment and component tests..."
echo ""
python testing/comprehensive_test_runner.py
echo ""

echo "========================================================================"
echo "2. Running MCP server functional tests..."
echo ""
python testing/test_mcp_functionality.py
echo ""

echo "========================================================================"
echo "3. Running bridge integration tests (will attempt to start bridge)..."
echo ""
timeout 30 python testing/test_bridge_integration.py || true
echo ""

echo "========================================================================"
echo "TESTING COMPLETE"
echo "========================================================================"
echo ""
echo "Results saved to:"
echo "  - testing/test_results.txt (Component tests)"
echo "  - testing/test_results.json (Component tests - JSON)"
echo "  - testing/test_results_functional.txt (MCP functional tests)"
echo "  - testing/test_results_bridge.txt (Bridge integration tests)"
echo ""
