# MCP Server Enhancement Guide - Leveraging 91.03/100 Quality Data

**Date:** November 19, 2025
**Status:** Ready for Implementation
**Quality Data Version:** ClimateGPT Enhanced v1.0

---

## Overview

The ClimateGPT MCP servers (`mcp_server_stdio.py` and `mcp_http_bridge.py`) currently provide query access to emissions data with basic quality warnings. With the new enhanced database (91.03/100 average quality), we can significantly improve the MCP interface with:

1. **Enhanced quality metadata** from the 8 quality columns
2. **Multi-source validation** indicators (95%+ coverage)
3. **Uncertainty quantification** (±8-16% bounds)
4. **Confidence-based filtering** (HIGH/MEDIUM/LOW)
5. **Synthetic data flagging** (1.5% records marked)

---

## Current MCP Capabilities

### Existing Tools (9 tools)
1. `list_emissions_datasets` - List available datasets
2. `get_dataset_schema` - Get column information
3. `get_data_quality` - Get quality ratings
4. `query_emissions` - Query with filters/aggregations
5. `calculate_yoy_change` - Year-over-year analysis
6. `analyze_monthly_trends` - Monthly trend analysis
7. `detect_seasonal_patterns` - Seasonal pattern detection
8. `get_data_coverage` - Coverage information
9. `get_column_suggestions` - Column value suggestions

### Current Data Quality System
- Basic quality ratings in `SECTOR_QUALITY` dict
- Simple warning messages
- No uncertainty information
- No confidence levels
- Outdated metrics (76.99/100 baseline)

---

## Enhancement Plan

### Phase 1: Update Quality Metadata (Priority: HIGH)

**What to Change:**
Update the `SECTOR_QUALITY` dictionary and quality reports to reflect new enhanced database metrics.

**Current Code Location:** `mcp_server_stdio.py`, lines 2451-2459 (get_data_quality tool)

**Implementation:**

```python
# Replace existing SECTOR_QUALITY with new metrics
SECTOR_QUALITY = {
    "agriculture": {
        "score": 88.00,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+3.00 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±8%",
        "sources": 2,
        "synthetic_pct": 0.0,
        "warning": None,
        "description": "FAO/FAOSTAT integration, multi-source validation"
    },
    "waste": {
        "score": 88.00,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+3.00 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±8%",
        "sources": 3,
        "synthetic_pct": 0.0,
        "warning": None,
        "description": "EU Waste Framework, UNEP, national agencies"
    },
    "transport": {
        "score": 85.00,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+10.00 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±14%",
        "sources": 5,
        "synthetic_pct": 0.0,
        "warning": None,
        "description": "IEA, WHO, Copernicus, vehicle registries integrated"
    },
    "buildings": {
        "score": 85.00,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+15.00 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±16%",
        "sources": 6,
        "synthetic_pct": 0.0,
        "warning": None,
        "description": "ASHRAE, EU EPBD, NOAA VIIRS, Copernicus integrated"
    },
    "power": {
        "score": 97.74,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+25.97 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±8%",
        "sources": 5,
        "synthetic_pct": 7.7,
        "warning": None,
        "note": "7.7% synthetic records from regional disaggregation",
        "description": "IEA, EPA CEMS, Sentinel-5P, grid data integrated"
    },
    "industrial_combustion": {
        "score": 96.87,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+19.63 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±8%",
        "sources": 6,
        "synthetic_pct": 0.0,
        "warning": None,
        "description": "EU LCP, WSA, WBCSD, CDP/GRI, Sentinel-5P integrated"
    },
    "industrial_processes": {
        "score": 96.40,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+19.37 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±8%",
        "sources": 6,
        "synthetic_pct": 0.0,
        "warning": None,
        "description": "IVL, ICIS, stoichiometric, RMD data integrated"
    },
    "fuel_exploitation": {
        "score": 92.88,
        "rating": "Tier 1 - Research Ready",
        "improvement": "+18.01 pts",
        "confidence_level": "HIGH (100%)",
        "uncertainty": "±8%",
        "sources": 5,
        "synthetic_pct": 0.1,
        "warning": None,
        "description": "Rystad, IHS Markit, USGS, commodity modeling integrated"
    }
}

# Add overall database metrics
DATABASE_METRICS = {
    "average_quality": 91.03,
    "quality_tier": "Tier 1 - All Sectors",
    "previous_quality": 76.99,
    "improvement": "+14.04 pts (+18.3%)",
    "total_records": 857508,
    "high_confidence_records": 857508,
    "high_confidence_pct": 100.0,
    "multi_source_validation_pct": 95.0,
    "synthetic_records": 12544,
    "synthetic_pct": 1.5,
    "uncertainty_reduction_avg": "35-73%",
    "external_sources": 55,
    "last_updated": "2025-11-19"
}
```

### Phase 2: Enhance get_data_quality Tool (Priority: HIGH)

**Current Response:** Simple quality ratings with warnings
**Enhanced Response:** Detailed quality metrics with uncertainty, sources, and confidence

**Implementation:**

```python
elif name == "get_data_quality":
    sector = arguments.get("sector")  # Optional: specific sector

    response = {
        "status": "success",
        "database_metrics": DATABASE_METRICS,
        "sector_quality": {},
        "recommendations": []
    }

    # If sector specified, return detailed info
    if sector and sector in SECTOR_QUALITY:
        response["sector_quality"] = {
            sector: SECTOR_QUALITY[sector]
        }
    else:
        # Return all sectors
        response["sector_quality"] = SECTOR_QUALITY

    # Add recommendations based on quality
    response["recommendations"] = [
        "✅ All 8 sectors now meet Tier 1 research-ready standard (85+/100)",
        "✅ 100% HIGH confidence classification across all records",
        "✅ 55+ external authoritative sources integrated",
        "✅ Uncertainty quantified: ±8-16% ranges (Bayesian framework)",
        "📊 For detailed quality info: Use query_emissions with quality filters",
        "🔍 For synthetic records: Filter by is_synthetic column",
        "📈 For uncertainty bounds: Use uncertainty_percent column"
    ]

    return [TextContent(
        type="text",
        text=json.dumps(response, indent=2)
    )]
```

### Phase 3: Add New Quality Filter Tool (Priority: MEDIUM)

**New Tool: `get_quality_filtered_data`**

Allows users to query with confidence level and uncertainty filters.

**Implementation:**

```python
# Add to tool list
Tool(
    name="get_quality_filtered_data",
    description="Query emissions data with quality confidence and uncertainty filters",
    inputSchema={
        "type": "object",
        "properties": {
            "file_id": {
                "type": "string",
                "description": "Dataset identifier (e.g., 'power-city-year-enhanced')"
            },
            "confidence_level": {
                "type": "string",
                "enum": ["HIGH", "MEDIUM", "LOW"],
                "description": "Minimum confidence level (default: HIGH)"
            },
            "max_uncertainty": {
                "type": "number",
                "description": "Maximum uncertainty % (default: 100 for no limit)"
            },
            "exclude_synthetic": {
                "type": "boolean",
                "description": "Exclude synthetic records (default: false)"
            },
            "min_quality_score": {
                "type": "number",
                "description": "Minimum quality score 0-100 (default: 85)"
            },
            "where": {
                "type": "object",
                "description": "Additional filters"
            },
            "select": {
                "type": "array",
                "description": "Columns to return"
            },
            "limit": {
                "type": "integer",
                "description": "Rows to return (default: 20, max: 1000)"
            }
        },
        "required": ["file_id"]
    }
)

# Handler implementation
elif name == "get_quality_filtered_data":
    file_id = arguments.get("file_id")
    confidence = arguments.get("confidence_level", "HIGH")
    max_uncertainty = arguments.get("max_uncertainty", 100)
    exclude_synthetic = arguments.get("exclude_synthetic", False)
    min_quality = arguments.get("min_quality_score", 85)

    # Determine enhanced table name
    if "_enhanced" not in file_id:
        file_id = file_id.replace("-year", "-year-enhanced").replace("-month", "-month-enhanced")

    table = _get_table_name_enhanced(file_id)

    # Build WHERE clause
    where_parts = [
        f"confidence_level = '{confidence}'",
        f"uncertainty_percent <= {max_uncertainty}",
        f"quality_score >= {min_quality}"
    ]

    if exclude_synthetic:
        where_parts.append("is_synthetic = FALSE")

    # Add user filters
    if arguments.get("where"):
        for col, val in arguments.get("where").items():
            if isinstance(val, str):
                where_parts.append(f"{col} = '{val}'")
            else:
                where_parts.append(f"{col} = {val}")

    where_clause = " AND ".join(where_parts)

    # Build SELECT
    select_cols = arguments.get("select", [
        "city_name", "country_name", "year", "emissions_tonnes",
        "quality_score", "confidence_level", "uncertainty_percent", "data_source"
    ])
    select_sql = ", ".join(select_cols)

    # Build and execute query
    sql = f"SELECT {select_sql} FROM {table} WHERE {where_clause} LIMIT {min(arguments.get('limit', 20), 1000)}"

    # Execute and return results
    ...
```

### Phase 4: Add Multi-Source Validation Tool (Priority: MEDIUM)

**New Tool: `get_validated_records`**

Returns records validated by multiple external sources.

**Implementation:**

```python
Tool(
    name="get_validated_records",
    description="Get emissions records validated by multiple external data sources (3+ sources minimum)",
    inputSchema={
        "type": "object",
        "properties": {
            "file_id": {
                "type": "string",
                "description": "Dataset identifier"
            },
            "min_sources": {
                "type": "integer",
                "description": "Minimum number of sources (1-55, default: 3)",
                "minimum": 1,
                "maximum": 55,
                "default": 3
            },
            "where": {
                "type": "object",
                "description": "Additional filters"
            },
            "limit": {
                "type": "integer",
                "description": "Rows to return (default: 20)"
            }
        },
        "required": ["file_id"]
    }
)

# Handler implementation
elif name == "get_validated_records":
    file_id = arguments.get("file_id")
    min_sources = arguments.get("min_sources", 3)

    # Enhanced table with data_source metadata
    enhanced_table = file_id.replace("-year", "-year-enhanced").replace("-month", "-month-enhanced")

    # Query by checking data_source field
    # Records with 3+ sources have pipe-separated source lists
    select_sql = """
        city_name, country_name, year, emissions_tonnes,
        quality_score, confidence_level, data_source,
        LENGTH(data_source) - LENGTH(REPLACE(data_source, '|', '')) + 1 as source_count
    """

    sql = f"""
        SELECT {select_sql}
        FROM {enhanced_table}
        WHERE LENGTH(data_source) - LENGTH(REPLACE(data_source, '|', '')) >= {min_sources - 1}
        LIMIT {min(arguments.get('limit', 20), 1000)}
    """

    # Execute and return with source_count metadata
    ...
```

### Phase 5: Add Uncertainty Query Tool (Priority: LOW)

**New Tool: `get_uncertainty_analysis`**

Provides uncertainty bounds and sensitivity analysis.

**Implementation:**

```python
Tool(
    name="get_uncertainty_analysis",
    description="Get emissions with 95% confidence interval uncertainty bounds",
    inputSchema={
        "type": "object",
        "properties": {
            "file_id": {"type": "string"},
            "where": {"type": "object"},
            "select": {
                "type": "array",
                "default": ["city_name", "country_name", "year", "emissions_tonnes"]
            },
            "limit": {"type": "integer", "default": 20}
        },
        "required": ["file_id"]
    }
)

# Handler returns:
# {
#   "emission_value": 1000,
#   "uncertainty_percent": 10,
#   "uncertainty_lower": 900,
#   "uncertainty_upper": 1100,
#   "confidence_level": 0.95,
#   "quality_score": 95.0,
#   "validation_status": "ENHANCED_MULTI_SOURCE"
# }
```

---

## Implementation Steps

### Step 1: Update Quality Metadata (2 hours)
1. Replace `SECTOR_QUALITY` dictionary with new metrics
2. Add `DATABASE_METRICS` constant
3. Update `get_data_quality` tool handler

**Files to modify:** `mcp_server_stdio.py` (lines ~500-600, ~2451-2459)
**Files to modify:** `mcp_http_bridge.py` (corresponding sections)

### Step 2: Enhance Existing Tools (3 hours)
1. Update `query_emissions` to include quality columns
2. Update `get_dataset_schema` to include quality columns
3. Add quality warnings with new metrics

**Files to modify:** `mcp_server_stdio.py` (lines ~2417-2450, ~2461-2550)

### Step 3: Add New Quality Filter Tool (4 hours)
1. Add `get_quality_filtered_data` tool definition
2. Implement handler for confidence/uncertainty filtering
3. Update tool list

**Files to modify:** `mcp_server_stdio.py` (lines ~1871-2070, ~2392-2800)

### Step 4: Add Multi-Source Validation Tool (3 hours)
1. Add `get_validated_records` tool
2. Implement source count detection
3. Update tool descriptions

**Files to modify:** `mcp_server_stdio.py` (same sections as Step 3)

### Step 5: Documentation & Testing (2 hours)
1. Update tool descriptions
2. Create example queries
3. Test with enhanced tables

---

## Example Usage After Enhancement

### Before (Current)
```
Tool: get_data_quality
Response: {
  "status": "success",
  "quality_report": {
    "agriculture": {
      "score": 85,
      "rating": "Good",
      "warning": null
    }
  }
}
```

### After (Enhanced)
```
Tool: get_data_quality
Response: {
  "status": "success",
  "database_metrics": {
    "average_quality": 91.03,
    "total_records": 857508,
    "high_confidence_pct": 100.0,
    "external_sources": 55
  },
  "sector_quality": {
    "agriculture": {
      "score": 88.00,
      "rating": "Tier 1 - Research Ready",
      "improvement": "+3.00 pts",
      "confidence_level": "HIGH (100%)",
      "uncertainty": "±8%",
      "sources": 2,
      "description": "FAO/FAOSTAT integration, multi-source validation"
    }
  },
  "recommendations": [
    "✅ All 8 sectors now meet Tier 1 research-ready standard (85+/100)",
    "✅ 100% HIGH confidence classification",
    "✅ 55+ external authoritative sources integrated"
  ]
}
```

### New Tool: get_quality_filtered_data
```
Tool: get_quality_filtered_data
Arguments: {
  "file_id": "power-city-year-enhanced",
  "confidence_level": "HIGH",
  "max_uncertainty": 10,
  "exclude_synthetic": true,
  "min_quality_score": 90
}

Response: {
  "records_returned": 5,
  "filters_applied": {
    "confidence": "HIGH",
    "max_uncertainty": "±10%",
    "synthetic": "excluded",
    "min_quality": 90.0
  },
  "data": [
    {
      "city_name": "Beijing",
      "country_name": "China",
      "year": 2020,
      "emissions_tonnes": 45000000,
      "quality_score": 97.74,
      "confidence_level": "HIGH",
      "uncertainty_percent": 8.0,
      "data_source": "IEA|EPA CEMS|Sentinel-5P"
    }
  ]
}
```

---

## Benefits

### For Data Users
- **Transparency:** Know quality score, confidence, and uncertainty of every record
- **Filtered Access:** Query only high-confidence, low-uncertainty data
- **Source Attribution:** See which external sources validate each record
- **Risk Management:** Identify synthetic records and exclude if needed

### For the Database
- **Showcase Quality:** Demonstrate Tier 1 research-ready standard (91.03/100)
- **Compliance:** Support academic/policy use cases with proper caveats
- **Trustworthiness:** Transparent uncertainty quantification (IPCC/EPA methods)
- **Differentiation:** No other emissions database has this level of quality transparency

### For API Clients
- **Confidence-based filtering:** Only get high-quality data for critical analyses
- **Uncertainty quantification:** Support risk assessment and sensitivity analysis
- **Multi-source validation:** Verify data reliability
- **Reproducibility:** Complete data lineage and source attribution

---

## Files Affected

### Primary Files to Modify
1. **mcp_server_stdio.py** (4222 lines)
   - Lines ~1871-2070: Tool definitions
   - Lines ~2392-2800: Tool handlers
   - Lines ~500-600: Quality metadata constants

2. **mcp_http_bridge.py** (if exists)
   - Corresponding tool definitions and handlers
   - Quality metadata integration

### Reference Files
- `DATABASE.md` or `manifest_mcp_duckdb.json` - For table mappings
- `project_completion_summary.md` - For quality metrics and sources

---

## Priority Roadmap

1. **Week 1 (HIGH PRIORITY):** Update quality metadata + enhance get_data_quality
2. **Week 2 (MEDIUM):** Add get_quality_filtered_data tool
3. **Week 3 (MEDIUM):** Add get_validated_records tool
4. **Week 4 (LOW):** Add uncertainty analysis tools + documentation

---

## Testing Plan

### Unit Tests
- Quality metric accuracy (91.03/100, all 8 sectors 85+)
- Filter logic (confidence, uncertainty, synthetic)
- Source counting logic

### Integration Tests
- Enhanced tables available and queryable
- Quality columns populated correctly
- Filters work with real data

### User Tests
- Example queries work correctly
- Results make sense semantically
- Performance acceptable (<2s response time)

---

## Success Metrics

- ✅ All 8 sectors show 85+/100 quality in API responses
- ✅ Users can filter by confidence level and uncertainty
- ✅ 55+ external sources visible in query results
- ✅ Response time <2 seconds for most queries
- ✅ 100% of users understand quality metrics in first response

---

## Conclusion

The MCP servers can be significantly enhanced to showcase the new 91.03/100 quality data. By adding quality-aware tools and updating existing tools, we can provide users with:

1. **Transparency** on data quality and uncertainty
2. **Flexibility** to filter by confidence/quality
3. **Confidence** in the reliability of results
4. **Compliance** with academic/policy standards

These enhancements require approximately **14 hours of development** and will dramatically improve the user experience and trustworthiness of the ClimateGPT API.

---

**Next Step:** Review this guide and approve Phase 1 implementation.

**Contact:** See PROJECT_COMPLETION_SUMMARY.md for project details.
