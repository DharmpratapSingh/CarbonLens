# ClimateGPT Comprehensive Testing Plan

## Overview
This document outlines the thorough testing approach for the ClimateGPT MCP system covering:
1. MCP Server (mcp_server_stdio.py)
2. MCP HTTP Bridge (mcp_http_bridge.py)
3. LLM Runner (run_llm.py)
4. End-to-End ClimateGPT Response Flow

## Test Structure

### Phase 1: MCP Server Direct Testing
- **File**: `test_mcp_server.py`
- **Tests**:
  - Database connectivity
  - Tool availability (list_files, get_schema, query, metrics.yoy)
  - Query execution with various filters
  - Entity resolution
  - Caching functionality
  - Error handling

### Phase 2: MCP HTTP Bridge Testing
- **File**: `test_mcp_bridge.py`
- **Tests**:
  - Bridge startup and shutdown
  - HTTP endpoint availability
  - Rate limiting
  - CORS handling
  - Request/response formatting
  - Error responses

### Phase 3: LLM Runner Testing
- **File**: `test_llm_runner.py`
- **Tests**:
  - Tool routing optimization
  - Persona framework integration
  - System prompt loading
  - Request formatting
  - Response parsing

### Phase 4: End-to-End Integration Testing
- **File**: `test_e2e_integration.py`
- **Tests**:
  - Full query flow from user input to response
  - Multiple scenarios:
    - Single entity queries
    - Comparative queries
    - Trend analysis
    - Top N queries
    - Sector summaries
  - Persona-based responses

## Expected Outputs
1. Detailed test report with pass/fail status
2. Performance metrics
3. Error logs with diagnostics
4. Coverage analysis
5. Recommendations for improvement

## Running Tests
```bash
# Setup
source .venv/bin/activate

# Run all tests
python testing/comprehensive_test_runner.py

# Or run individual tests
python testing/test_mcp_server.py
python testing/test_mcp_bridge.py
python testing/test_llm_runner.py
python testing/test_e2e_integration.py
```

## Success Criteria
- [ ] MCP Server responds to all tool calls
- [ ] Bridge establishes connection and forwards requests
- [ ] LLM Runner correctly formats tool calls
- [ ] End-to-end flow produces correct responses
- [ ] Error handling is graceful
- [ ] Performance is acceptable (< 5s for queries)
