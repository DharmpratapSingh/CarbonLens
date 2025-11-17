# Smart Query System - User Guide

## Overview

The Smart Query System intelligently handles entity name variations, automatically detects geographic levels, and provides intelligent fallback when data isn't available. This solves the common problem of entity name confusion (USA vs United States of America, etc.).

---

## Problem Solved

### Before (Without Smart Query)

❌ **User:** "What are USA's emissions?"
**System:** Error - "USA not found in database"

❌ **User:** "Compare USA vs China"
**System:** Error - Must use exact names "United States of America" and "People's Republic of China"

❌ **User:** "What about Germny?"
**System:** Error - No suggestions

### After (With Smart Query)

✅ **User:** "What are USA's emissions?"
**System:** Automatically resolves "USA" → "United States of America" and returns data

✅ **User:** "Compare USA vs China"
**System:** Resolves both names automatically and compares

✅ **User:** "What about Germny?"
**System:** "Did you mean Germany?" + suggests similar entities

---

## Features

### 1. Entity Name Normalization

The system recognizes common aliases and abbreviations:

#### Country Aliases
- **USA** → United States of America
- **US**, **U.S.**, **U.S.A.**, **United States**, **America** → United States of America
- **UK**, **U.K.**, **Britain**, **Great Britain**, **England** → United Kingdom
- **China**, **PRC**, **Mainland China** → People's Republic of China
- **Russia** → Russian Federation
- **South Korea**, **ROK** → Republic of Korea
- **North Korea**, **DPRK** → Democratic People's Republic of Korea
- **Holland** → Netherlands
- **UAE** → United Arab Emirates
- **Vietnam** → Viet Nam
- And more...

#### State/Province Aliases
- **CA**, **Calif**, **Cali** → California
- **NY** → New York
- **TX** → Texas
- **FL** → Florida
- **MA**, **Mass** → Massachusetts
- **PA**, **Penn** → Pennsylvania
- And more...

#### City Aliases
- **NYC** → New York City
- **LA** → Los Angeles
- **SF** → San Francisco
- **DC** → Washington
- **Philly** → Philadelphia

### 2. Fuzzy Matching

Handles typos and partial matches:

- **Germny** → Suggests "Germany" (80%+ similarity)
- **Frane** → Suggests "France"
- **Unted States** → Suggests "United States of America"
- Returns top 5 suggestions when exact match not found

### 3. Auto-Level Detection

Automatically determines if entity is:
- **Country**: "United States of America", "Germany", "China"
- **Admin1** (state/province): "California", "Texas", "Ontario"
- **City**: "New York City", "Los Angeles", "Paris"

Searches in order: exact match → case-insensitive → fuzzy match

### 4. Intelligent Fallback

When data not available at requested level:
1. Try **city** level
2. If not found, try **admin1** (state/province) level
3. If still not found, try **country** level
4. Return metadata showing which level was actually used

---

## Usage

### Tool: `smart_query_emissions`

**When to use:**
- Entity name is ambiguous (USA, LA, NYC)
- You don't know the correct level (country vs state vs city)
- You want automatic fallback if data not available

**Parameters:**
- `entity` (required): Entity name in any format
- `sector` (optional): Sector to query (default: "transport")
- `year` (optional): Year to query (default: 2023)
- `grain` (optional): "year" or "month" (default: "year")
- `level` (optional): "country", "admin1", "city", or "auto" (default: "auto")
- `enable_fallback` (optional): Enable fallback to higher levels (default: true)

### Examples

#### Example 1: USA Query
```json
{
  "entity": "USA",
  "sector": "transport",
  "year": 2023
}
```

**Response:**
```json
{
  "query": {
    "original_entity": "USA",
    "resolved_entity": "United States of America",
    "requested_level": "auto",
    "detected_level": "country",
    "actual_level_used": "country"
  },
  "resolution": {
    "normalized": "United States of America",
    "detected_level": "country",
    "suggestions": [],
    "fallback_used": false
  },
  "data": [
    {"country_name": "United States of America", "year": 2023, "emissions_tonnes": 1563200000, "emissions_mtco2": 1563.2}
  ],
  "metadata": {
    "rows_returned": 1,
    "fallback_trace": [
      {"level": "country", "status": "success", "rows_found": 1}
    ],
    "data_source": "transport-country-year"
  }
}
```

#### Example 2: California with Fallback
```json
{
  "entity": "California",
  "sector": "transport",
  "year": 2023,
  "enable_fallback": true
}
```

**If admin1 data available:**
```json
{
  "query": {
    "original_entity": "California",
    "resolved_entity": "California",
    "detected_level": "admin1",
    "actual_level_used": "admin1"
  },
  "resolution": {
    "fallback_used": false
  },
  "data": [...],
  "metadata": {
    "fallback_trace": [
      {"level": "admin1", "status": "success", "rows_found": 1}
    ]
  }
}
```

**If admin1 data NOT available (fallback to country):**
```json
{
  "query": {
    "original_entity": "California",
    "resolved_entity": "United States of America",
    "detected_level": "admin1",
    "actual_level_used": "country"
  },
  "resolution": {
    "fallback_used": true
  },
  "data": [...],
  "metadata": {
    "fallback_trace": [
      {"level": "admin1", "status": "no_data"},
      {"level": "country", "status": "success", "rows_found": 1}
    ]
  }
}
```

#### Example 3: Typo Correction
```json
{
  "entity": "Germny",
  "sector": "transport",
  "year": 2023
}
```

**Response:**
```json
{
  "query": {
    "original_entity": "Germny",
    "resolved_entity": "Germany",
    "detected_level": "country",
    "actual_level_used": "country"
  },
  "resolution": {
    "normalized": "Germany",
    "detected_level": "country",
    "suggestions": ["Germany", "Jersey", "Grenada"],
    "fallback_used": false
  },
  "data": [...]
}
```

#### Example 4: Not Found
```json
{
  "entity": "NonExistentCountry",
  "sector": "transport",
  "year": 2023
}
```

**Response:**
```json
{
  "error": "no_data_found",
  "query": {
    "original_entity": "NonExistentCountry",
    "resolved_entity": "NonExistentCountry",
    "detected_level": "country"
  },
  "resolution": {
    "suggestions": ["Norway (country)", "Netherlands (country)", "New Zealand (country)"]
  },
  "fallback_trace": [
    {"level": "country", "status": "no_data"}
  ],
  "suggestions": [
    "Try a different entity (suggestions: Norway, Netherlands, New Zealand)",
    "Try a different year (requested: 2023)",
    "Try a different sector (requested: transport)"
  ]
}
```

---

## Enhanced Existing Tools

All major tools now automatically normalize entity names:

### 1. `aggregate_across_sectors`
```json
{
  "entity": "USA",  // ✅ Automatically normalized to "United States of America"
  "sectors": "all",
  "year": 2023
}
```

### 2. `compare_emissions`
```json
{
  "entities": ["USA", "UK", "China"],  // ✅ All normalized automatically
  "sector": "transport",
  "year": 2023
}
```

### 3. `analyze_emissions_trend`
```json
{
  "entity": "USA",  // ✅ Automatically normalized
  "sector": "transport",
  "start_year": 2000,
  "end_year": 2023
}
```

---

## Technical Details

### Normalization Algorithm

1. **Exact alias match** (case-insensitive)
   - Check country aliases
   - Check admin1 aliases (if level specified)
   - Check city aliases (if level specified)

2. **Level detection** (if not specified)
   - Search coverage index at each level
   - Exact match → return that level
   - Case-insensitive match → return that level
   - Fuzzy match (85%+ similarity) → return that level

3. **Fuzzy matching**
   - Use difflib.SequenceMatcher
   - Calculate similarity ratio (0.0 to 1.0)
   - Return matches above threshold (default 75%)
   - Sort by similarity score descending

4. **Fallback cascade**
   - Try detected level first
   - If `enable_fallback=true`:
     - City → Admin1 → Country
     - Admin1 → Country
   - Track all attempts in fallback_trace

### Performance

- **Coverage index cached**: Built once on server startup, cached with LRU
- **Normalization is O(1)**: Dictionary lookups for aliases
- **Fuzzy matching is O(n)**: Where n = number of entities in database (~200 countries, ~50 states, ~100 cities)
- **Fast enough for real-time queries**: < 10ms for most cases

---

## Best Practices

### When to Use smart_query_emissions

✅ **Use when:**
- User input is free-form (chat, voice, etc.)
- Entity name might be abbreviated (USA, UK, NYC)
- You don't know the correct level
- You want automatic fallback

❌ **Don't use when:**
- You have exact entity names from database
- You need precise control over level
- You're doing bulk operations (use direct query tools)

### Handling Responses

Always check the `resolution` section:
```python
if response["resolution"]["fallback_used"]:
    print(f"Note: Used {response['query']['actual_level_used']} data instead of {response['query']['detected_level']}")

if response["resolution"]["suggestions"]:
    print(f"FYI: '{original_entity}' was matched to '{resolved_entity}'")
    print(f"Other suggestions: {response['resolution']['suggestions'][:3]}")
```

### Error Handling

```python
if "error" in response:
    error_type = response["error"]

    if error_type == "no_data_found":
        suggestions = response["resolution"]["suggestions"]
        print(f"Entity not found. Did you mean: {suggestions[0]}?")

    elif error_type == "resolution_failed":
        print(f"Could not resolve entity: {response['detail']}")
```

---

## Extending the System

### Adding New Aliases

Edit `mcp_server_stdio.py`, function `_normalize_entity_name()`:

```python
# Add to country_aliases dict
country_aliases = {
    # ... existing aliases ...
    "NewAlias": "Canonical Name",
}

# Or admin1_aliases for states/provinces
admin1_aliases = {
    # ... existing aliases ...
    "NewStateAbbr": "Full State Name",
}
```

### Adjusting Fuzzy Match Threshold

Default is 0.75 (75% similarity). Adjust in `_smart_entity_resolution()`:

```python
fuzzy_matches = _fuzzy_match_entity(normalized, level_data, threshold=0.75)
# Change to 0.8 for stricter matching, 0.7 for more lenient
```

---

## Limitations

1. **Ambiguous names**: "Washington" could be Washington DC (city) or Washington (state)
   - Solution: Prioritizes by level (city > admin1 > country)
   - Override by specifying `level` parameter

2. **Multiple matches**: Some names exist at multiple levels
   - Example: "Paris" (city in France) vs "Paris" (city in Texas)
   - Solution: Returns first match found, use `level` parameter for precision

3. **Language variations**: Only handles English names
   - "Deutschland" won't resolve to "Germany"
   - Solution: Add aliases manually or use translation API

4. **Historical names**: Doesn't handle country name changes
   - "USSR" won't resolve (doesn't exist in modern data)
   - Solution: Use current country names

---

## Support

For issues or questions about the Smart Query System:
- Check this guide first
- Review fallback_trace in response for debugging
- Check entity normalization aliases in source code
- Open an issue with example query that fails

---

**Version:** 1.0
**Last Updated:** 2025-11-16
**Status:** Production Ready ✅
