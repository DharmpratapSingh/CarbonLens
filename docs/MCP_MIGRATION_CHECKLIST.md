# MCP Server Migration Checklist

## Goal
Port all tuning, optimizations, and features from `mcp_server.py` (4143 lines) to `mcp_server_stdio.py` (1170 lines)

## Overview
- **Source:** `mcp_server.py` (FastAPI REST server with extensive tuning)
- **Target:** `mcp_server_stdio.py` (TRUE MCP protocol server)
- **Lines to migrate:** ~3000 lines of code
- **Status:** 🔴 NOT STARTED

---

## Phase 1: Core Infrastructure (PRIORITY: CRITICAL)

### 1.1 Connection Management
- [ ] `DuckDBConnectionPool` class (lines ~250-300 in old server)
  - Connection pooling for performance
  - Thread-safe connection handling
  - Connection lifecycle management
- [ ] `_get_db_connection()` optimizations
- [ ] Connection timeout handling
- [ ] Connection error recovery

### 1.2 File Resolution & Validation
- [ ] `_resolve_file_id()` - File ID normalization
- [ ] `_resolve_db_path()` - Database path resolution with env vars
- [ ] `_validate_file_id()` - File ID validation with detailed errors
- [ ] `_validate_table_schema()` - Schema validation
- [ ] `_get_file_meta()` - Enhanced metadata retrieval
- [ ] File ID aliasing/shortcuts support

### 1.3 Logging & Monitoring
- [ ] `_setup_logging()` - Structured logging setup
- [ ] `request_logging_middleware()` - Request/response logging
- [ ] Performance timing logs
- [ ] Error rate tracking
- [ ] Query pattern logging

---

## Phase 2: Query Validation & Safety (PRIORITY: HIGH)

### 2.1 Column Validation
- [ ] `_validate_column_name()` - Column existence checks
- [ ] Column type validation
- [ ] Reserved keyword handling
- [ ] SQL injection prevention
- [ ] Case sensitivity handling

### 2.2 Filter/Where Validation
- [ ] `_validate_filter_value()` - Type-safe filter values
- [ ] Filter operator validation
- [ ] Nested filter support
- [ ] Array filter validation
- [ ] Date/time filter handling

### 2.3 Query Complexity
- [ ] `_validate_query_complexity()` - Resource limit checks
  - Max joins limit
  - Max group by columns
  - Max result rows
  - Query timeout detection
  - Memory estimation

### 2.4 Query Intent Detection
- [ ] `_validate_query_intent()` - Semantic query validation
- [ ] `_detect_query_patterns()` - Pattern recognition
  - Time series detection
  - Aggregation detection
  - Trend analysis detection
  - Comparison query detection

---

## Phase 3: Advanced Query Features (PRIORITY: HIGH)

### 3.1 Computed Columns
- [ ] `_validate_computed_expression()` - Expression validation
- [ ] `_build_computed_columns_sql()` - SQL generation
- [ ] Safe expression evaluation
- [ ] Column dependency resolution
- [ ] Circular dependency detection

### 3.2 Aggregations
- [ ] `_validate_aggregation_function()` - Function whitelist
- [ ] `_build_aggregation_sql()` - Aggregation SQL builder
- [ ] Support for: SUM, AVG, COUNT, MIN, MAX, STDDEV
- [ ] Nested aggregations
- [ ] Window functions

### 3.3 Having Clauses
- [ ] `_build_having_sql()` - Having clause builder
- [ ] Post-aggregation filtering
- [ ] Having clause validation

### 3.4 Advanced SQL Building
- [ ] `_build_where_sql()` - Enhanced where builder
  - IN operator support
  - BETWEEN operator
  - LIKE/ILIKE patterns
  - NULL handling
  - Array contains
- [ ] JOIN support (if exists in old server)
- [ ] UNION support (if exists)
- [ ] Subquery support (if exists)

### 3.5 DuckDB Optimizations
- [ ] `_duckdb_pushdown()` - Query pushdown to DuckDB
  - Predicate pushdown
  - Projection pushdown
  - Limit pushdown
  - Order pushdown
- [ ] `_duckdb_yoy()` - Optimized YoY calculations
- [ ] Parallel query execution
- [ ] Result caching

---

## Phase 4: Error Handling & User Experience (PRIORITY: HIGH)

### 4.1 Advanced Error Responses
- [ ] `_error_response()` - Rich error objects
  - Error codes
  - Detailed messages
  - User-friendly hints
  - Context information
  - Actionable suggestions
  - Recovery steps

### 4.2 Error Parsing & Analysis
- [ ] `_parse_duckdb_column_error()` - Parse DuckDB errors
- [ ] Extract available columns from errors
- [ ] Extract invalid columns from errors
- [ ] Suggest column corrections

### 4.3 Data Type Handling
- [ ] `_coerce_numeric()` - Type coercion
- [ ] Date/time parsing
- [ ] String normalization
- [ ] Null handling strategies

---

## Phase 5: Suggestions & Intelligence (PRIORITY: MEDIUM)

### 5.1 Fuzzy Matching
- [ ] `_fuzzy_match()` - String similarity matching
  - Levenshtein distance
  - Soundex matching
  - Partial matching
- [ ] Column name suggestions
- [ ] Value suggestions
- [ ] Query correction

### 5.2 Context-Aware Suggestions
- [ ] `_get_suggestions_for_column()` - Column-specific suggestions
- [ ] `_get_distinct_values()` - Fetch distinct values
- [ ] Query-based filtering of suggestions
- [ ] Limit and pagination for suggestions

### 5.3 Coverage Analysis
- [ ] `_parse_temporal_coverage()` - Parse date ranges
- [ ] `_get_cities_data_coverage()` - City coverage info
- [ ] `_get_cities_suggestions()` - City name suggestions
- [ ] `_coverage_index()` - Build coverage index
- [ ] `_top_matches()` - Top coverage matches

---

## Phase 6: New MCP Tools (PRIORITY: MEDIUM)

Convert existing FastAPI endpoints to MCP tools:

### 6.1 Coverage Tools
- [ ] `get_data_coverage` tool (from `/coverage` endpoint)
- [ ] `get_cities_coverage` tool (from `/data-coverage` endpoint)
- [ ] `resolve_file_id` tool (from `/resolve` endpoint)

### 6.2 Validation Tools
- [ ] `validate_schema` tool (from `/validate/schema/{file_id}`)
- [ ] `validate_all_schemas` tool (from `/validate/all`)

### 6.3 Suggestions Tools
- [ ] `get_column_suggestions` tool (from `/suggestions/{file_id}`)
- [ ] `get_value_suggestions` tool
- [ ] `get_query_corrections` tool

### 6.4 Advanced Metrics Tools
- [ ] `calculate_rankings` tool (from `/metrics/rankings`)
- [ ] `analyze_trends` tool (from `/metrics/trends`)
- [ ] `query_metrics` tool (from `/metrics/query`)

### 6.5 Batch Operations
- [ ] Enhanced `batch_query` tool (from `/batch/query`)
- [ ] `batch_export` tool (from `/batch/export`)
- [ ] `batch_validate` tool (from `/batch/validate`)

### 6.6 System Tools
- [ ] `get_usage_stats` tool (from `/metrics/usage`)
- [ ] `get_error_stats` tool (from `/metrics/errors`)
- [ ] `get_tools_info` tool (from `/tools`)

---

## Phase 7: Webhook System (PRIORITY: LOW)

### 7.1 Webhook as MCP Resources
- [ ] Register webhooks as MCP resources
- [ ] Webhook payload formatting
- [ ] Webhook delivery queue
- [ ] Retry logic
- [ ] Webhook history tracking

### 7.2 Webhook Tools
- [ ] `create_webhook` tool (from `POST /webhooks`)
- [ ] `list_webhooks` tool (from `GET /webhooks`)
- [ ] `get_webhook` tool (from `GET /webhooks/{id}`)
- [ ] `delete_webhook` tool
- [ ] `get_webhook_history` tool (from `GET /webhooks/{id}/history`)

---

## Phase 8: Testing & Validation (PRIORITY: CRITICAL)

### 8.1 Unit Tests
- [ ] Test all validation functions
- [ ] Test query builders
- [ ] Test error handling
- [ ] Test fuzzy matching
- [ ] Test coverage analysis

### 8.2 Integration Tests
- [ ] Test all MCP tools
- [ ] Test HTTP bridge compatibility
- [ ] Test ClimateGPT UI integration
- [ ] Test error scenarios
- [ ] Test edge cases

### 8.3 Performance Tests
- [ ] Query performance benchmarks
- [ ] Connection pool stress tests
- [ ] Memory usage tests
- [ ] Concurrent query tests

### 8.4 Backward Compatibility
- [ ] Ensure HTTP bridge still works
- [ ] Ensure ClimateGPT UI works unchanged
- [ ] Verify all existing queries work
- [ ] Check response format compatibility

---

## Phase 9: Documentation (PRIORITY: MEDIUM)

### 9.1 Code Documentation
- [ ] Add docstrings to all functions
- [ ] Document MCP tool parameters
- [ ] Add usage examples
- [ ] Document error codes

### 9.2 User Documentation
- [ ] Update MCP_ARCHITECTURE.md with new features
- [ ] Document new MCP tools
- [ ] Add troubleshooting guide
- [ ] Create migration notes for users

### 9.3 Developer Documentation
- [ ] Add development setup guide
- [ ] Document testing procedures
- [ ] Add contribution guidelines
- [ ] Create architecture diagrams

---

## Migration Progress Tracking

### Lines Migrated: 0 / ~3000 (0%)

### Completion by Phase:
- [ ] Phase 1: Core Infrastructure (0%)
- [ ] Phase 2: Query Validation (0%)
- [ ] Phase 3: Advanced Query Features (0%)
- [ ] Phase 4: Error Handling (0%)
- [ ] Phase 5: Suggestions & Intelligence (0%)
- [ ] Phase 6: New MCP Tools (0%)
- [ ] Phase 7: Webhook System (0%)
- [ ] Phase 8: Testing (0%)
- [ ] Phase 9: Documentation (0%)

---

## Key Functions to Migrate (Reference)

### From mcp_server.py (4143 lines):

**Core Utilities:**
- `_resolve_file_id()`
- `_resolve_db_path()`
- `_setup_logging()`
- `_get_db_connection()`
- `DuckDBConnectionPool` class

**Validation:**
- `_validate_file_id()`
- `_validate_column_name()`
- `_validate_filter_value()`
- `_validate_query_complexity()`
- `_validate_query_intent()`
- `_validate_aggregation_function()`
- `_validate_computed_expression()`
- `_validate_table_schema()`

**Query Building:**
- `_build_where_sql()`
- `_build_aggregation_sql()`
- `_build_having_sql()`
- `_build_computed_columns_sql()`
- `_duckdb_pushdown()`
- `_duckdb_yoy()`

**Error Handling:**
- `_error_response()`
- `_parse_duckdb_column_error()`

**Intelligence:**
- `_fuzzy_match()`
- `_get_suggestions_for_column()`
- `_get_distinct_values()`
- `_parse_temporal_coverage()`
- `_get_cities_data_coverage()`
- `_get_cities_suggestions()`
- `_coverage_index()`
- `_top_matches()`
- `_detect_query_patterns()`

**Data Processing:**
- `_load_csv()`
- `_load_table()`
- `_apply_filter()`
- `_coerce_numeric()`
- `_response()`

---

## Migration Strategy

### Recommended Order:
1. **Start with Phase 1** (Core Infrastructure) - Foundation
2. **Then Phase 4** (Error Handling) - Better debugging
3. **Then Phase 2** (Validation) - Safety & correctness
4. **Then Phase 3** (Query Features) - Functionality
5. **Then Phase 5** (Suggestions) - UX improvements
6. **Then Phase 6** (New Tools) - Extended capabilities
7. **Then Phase 8** (Testing) - Verification
8. **Then Phase 9** (Documentation) - Knowledge capture
9. **Finally Phase 7** (Webhooks) - Optional advanced feature

### After Each Phase:
1. ✅ Test the changes
2. ✅ Commit to git
3. ✅ Update this checklist
4. ✅ Verify ClimateGPT still works

---

## Notes

- Backup created: `mcp_server_stdio.py.backup`
- Original server: `mcp_server.py` (preserved for reference)
- Target server: `mcp_server_stdio.py` (to be enhanced)

## Status Legend
- [ ] Not started
- [🔄] In progress
- [✅] Completed
- [⏸️] Blocked
- [❌] Skipped

---

**Last Updated:** 2025-11-09
**Migration Owner:** Claude Code
**Estimated Time:** Multiple sessions (10-20 hours of work)
