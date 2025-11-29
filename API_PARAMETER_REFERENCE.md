# ClimateGPT API Parameter Reference Guide

## Overview
This document defines the **EXACT parameter names** that the MCP server expects. The LLM must use these exact names to communicate with the backend APIs.

---

## ✅ CORRECT Parameter Names (Use These)

### 1. **query** Tool
Returns raw data from database tables.

```json
{
  "tool": "query",
  "args": {
    "file_id": "transport-country-year",
    "select": ["country_name", "year", "emissions_tonnes"],
    "where": {"country_name": "Germany", "year": 2023},
    "group_by": ["country_name"],
    "order_by": "emissions_tonnes DESC",
    "aggregations": {"emissions_tonnes": "SUM"},
    "limit": 20
  }
}
```

**Parameters:**
- ✅ `file_id` (required): File identifier
- ✅ `select` (optional): List of columns to return
- ✅ `where` (optional): Filter conditions as key-value pairs
- ✅ `group_by` (optional): List of columns to group by
- ✅ `order_by` (optional): Column name with ASC or DESC
- ✅ `aggregations` (optional): Map of column to aggregation function
- ✅ `limit` (optional): Max rows to return (default 20, max 1000)

---

### 2. **metrics.yoy** Tool
Year-over-year comparison between two years.

```json
{
  "tool": "metrics.yoy",
  "args": {
    "file_id": "transport-country-year",
    "key_column": "country_name",
    "value_column": "emissions_tonnes",
    "base_year": 2020,
    "compare_year": 2023,
    "top_n": 10,
    "direction": "drop"
  }
}
```

**Parameters:**
- ✅ `file_id` (required): Must be a yearly dataset (ends with "-year")
- ✅ `key_column` (required): Column to group by (e.g., "country_name", "admin1_name", "city_name")
- ✅ `value_column` (optional): Column to measure (default: "emissions_tonnes")
- ✅ `base_year` (required): Starting year for comparison
- ✅ `compare_year` (required): Ending year for comparison
- ✅ `top_n` (optional): Number of top results (default: 10)
- ✅ `direction` (optional): "drop" (decreases) or "rise" (increases) (default: "drop")

---

### 3. **analyze_monthly_trends** Tool
Analyze monthly patterns within a single year.

```json
{
  "tool": "analyze_monthly_trends",
  "args": {
    "file_id": "transport-country-month",
    "entity_column": "country_name",
    "entity_value": "Germany",
    "year": 2023,
    "value_column": "emissions_tonnes"
  }
}
```

**Parameters:**
- ✅ `file_id` (required): Must be a monthly dataset (ends with "-month")
- ✅ `entity_column` (required): The grouping column (country_name, admin1_name, city_name)
- ✅ `entity_value` (required): The specific entity to analyze
- ✅ `year` (optional): Year to analyze (default: 2020)
- ✅ `value_column` (optional): Column to measure (default: "MtCO2")

---

### 4. **sector_statistics** Tool
Get sector-wide statistics and summaries.

```json
{
  "tool": "sector_statistics",
  "args": {
    "file_id": "transport-country-year",
    "value_column": "emissions_tonnes",
    "year": 2023
  }
}
```

**Parameters:**
- ✅ `file_id` (required): Sector to analyze
- ✅ `value_column` (optional): Column to measure (default: "MtCO2")
- ✅ `year` (optional): Year for statistics

---

## ❌ WRONG Parameter Names (DO NOT USE)

| Wrong | Correct | Impact |
|-------|---------|--------|
| `key_col` | `key_column` | API returns 400 validation error |
| `value_col` | `value_column` | API returns 400 validation error |
| `keyColumn` | `key_column` | API returns 400 validation error |
| `valueColumn` | `value_column` | API returns 400 validation error |

---

## Common Mistakes & Fixes

### ❌ Mistake 1: Using camelCase
```json
{
  "key_col": "country_name",      // ❌ WRONG
  "value_col": "emissions_tonnes"  // ❌ WRONG
}
```

### ✅ Fix: Use snake_case
```json
{
  "key_column": "country_name",      // ✅ CORRECT
  "value_column": "emissions_tonnes"  // ✅ CORRECT
}
```

---

### ❌ Mistake 2: Using abbreviated names
```json
{
  "file_id": "transport-country-year",
  "key_col": "country_name",        // ❌ key_col is wrong
  "base_year": 2020,
  "compare_year": 2023
}
```

### ✅ Fix: Use full parameter names
```json
{
  "file_id": "transport-country-year",
  "key_column": "country_name",     // ✅ key_column is correct
  "base_year": 2020,
  "compare_year": 2023
}
```

---

## Testing Parameters

To verify the correct parameter names work:

```bash
# Test metrics.yoy with CORRECT names
curl -X POST http://localhost:8010/metrics/yoy \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "transport-country-year",
    "key_column": "country_name",
    "value_column": "emissions_tonnes",
    "base_year": 2020,
    "compare_year": 2023,
    "top_n": 5,
    "direction": "drop"
  }'
```

Expected response: 200 OK with data

```bash
# Test metrics.yoy with WRONG names (will fail)
curl -X POST http://localhost:8010/metrics/yoy \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "transport-country-year",
    "key_col": "country_name",      # ❌ WRONG
    "value_col": "emissions_tonnes",  # ❌ WRONG
    "base_year": 2020,
    "compare_year": 2023
  }'
```

Expected response: 400 Bad Request - "key_column is a required property"

---

## LLM System Prompt Directives

The LLM system prompt includes:

✅ **ALWAYS use these parameter names for metrics.yoy:**
- `key_column` (not `key_col`)
- `value_column` (not `value_col`)

✅ **ALWAYS use snake_case** for all parameters

✅ **NEVER abbreviate** parameter names

✅ **FOLLOW THE EXACT EXAMPLES** in the system prompt

---

## Summary

| Tool | Key Parameter | Value Parameter | Status |
|------|---------------|-----------------|--------|
| query | N/A | N/A | ✅ Works |
| metrics.yoy | `key_column` | `value_column` | ✅ Fixed |
| analyze_monthly_trends | `entity_column` | `value_column` | ✅ Works |
| sector_statistics | N/A | `value_column` | ✅ Works |

---

## Related Files

- **LLM System Prompt**: `src/run_llm.py` (lines 50-250)
- **MCP Server Schemas**: `src/mcp_server_stdio.py` (lines 2063-3250)
- **HTTP Bridge**: `src/mcp_http_bridge.py`

---

## Version History

- **v1.0** (2025-11-29): Initial documentation
  - Fixed `key_col` → `key_column`
  - Fixed `value_col` → `value_column`
  - Added comprehensive parameter reference

