# ClimateGPT Persona Data Utilization Guide

## Overview

This guide explains how to effectively utilize ClimateGPT's internal EDGAR v2024 emissions datasets across different personas to provide tailored, data-driven responses for diverse audiences.

## Data Architecture

### Available Datasets

ClimateGPT has access to comprehensive EDGAR v2024 emissions data across 8 sectors:

| Sector | File ID Prefix | Description |
|--------|---------------|-------------|
| Transport | `transport-` | Road, rail, air, and shipping emissions |
| Power | `power-` | Electricity generation emissions |
| Waste | `waste-` | Waste management and disposal emissions |
| Agriculture | `agriculture-` | Agricultural activity emissions |
| Buildings | `buildings-` | Residential and commercial building emissions |
| Fuel Exploitation | `fuel-exploitation-` | Oil, gas, coal extraction emissions |
| Industrial Combustion | `ind-combustion-` | Industrial fuel burning emissions |
| Industrial Processes | `ind-processes-` | Manufacturing process emissions |

### Geographic Resolutions

Each sector is available at three geographic levels:

1. **Country** (`-country-`): National-level aggregations (195+ countries)
2. **Admin1** (`-admin1-`): First administrative division (states, provinces)
3. **City** (`-city-`): Major urban centers worldwide

### Temporal Resolutions

Data is available in two temporal grains:

1. **Annual** (`-year`): Yearly totals from 2000-2024
2. **Monthly** (`-month`): Monthly values from 2000-2023

### File ID Pattern

All file IDs follow the pattern: `{sector}-{level}-{grain}`

**Examples:**
- `transport-country-year` - Annual transport emissions by country
- `power-admin1-month` - Monthly power emissions by state/province
- `waste-city-year` - Annual waste emissions by city
- `ind-combustion-admin1-year` - Annual industrial combustion by state

## Four Personas & Their Data Needs

### 1. Climate Analyst
**Audience:** Climate policy professionals and mitigation planners
**Data Utilization Strategy:**
- Emphasis on **actionable insights** and **mitigation priorities**
- Frequently uses **trend analysis** (year-over-year changes)
- Prefers **admin1 and city-level** data for targeted interventions
- Highlights **top emitters** and **concentration metrics**

**Example Queries:**
```
Q: "Identify the top three countries with the largest increase in transport emissions between 2020 and 2023"
→ Uses: transport-country-year with year filtering and aggregations
→ Response: Actionable mitigation recommendations based on data

Q: "Describe seasonal patterns in Tokyo's waste emissions"
→ Uses: waste-city-month with monthly grouping
→ Response: Policy team recommendations for seasonal interventions
```

### 2. Research Scientist
**Audience:** Academic researchers and data scientists
**Data Utilization Strategy:**
- Focus on **methodology, uncertainty, and data provenance**
- References **dataset limitations** and **temporal coverage**
- Discusses **statistical patterns** and **data quality**
- Provides **context on EDGAR methodology**

**Example Queries:**
```
Q: "Evaluate the reliability of EDGAR v2024 monthly power-sector data for France in 2022"
→ Uses: power-country-month with detailed monthly breakdown
→ Response: Methodological caveats, uncertainty discussion, data quality assessment

Q: "Analyze monthly trends in industrial emissions"
→ Uses: ind-combustion-country-month or ind-processes-country-month
→ Response: Statistical analysis with confidence intervals and data quality notes
```

### 3. Financial Analyst
**Audience:** Investors, risk analysts, and portfolio managers
**Data Utilization Strategy:**
- Emphasizes **concentration risk** and **momentum signals**
- Uses **directional language** (rise, drop, acceleration)
- Focuses on **comparative metrics** and **percentage changes**
- Highlights **material shifts** in emissions profiles

**Example Queries:**
```
Q: "Summarize US state-level industrial-combustion emissions, focusing on concentration and momentum"
→ Uses: ind-combustion-admin1-year with recent year focus
→ Response: Top emitters by state, year-over-year momentum, concentration metrics

Q: "Identify emission risk signals in power sector"
→ Uses: power-country-year with trend analysis
→ Response: Risk-oriented language about emissions acceleration/deceleration
```

### 4. Student
**Audience:** Learners and general public
**Data Utilization Strategy:**
- **Simplified language** and **plain-English explanations**
- Provides **definitions** and **educational context**
- Uses **relatable comparisons** and **visual descriptions**
- Avoids technical jargon

**Example Queries:**
```
Q: "Explain how Germany's power-sector emissions changed in 2023 compared with 2022 in simple terms"
→ Uses: power-country-year with year=2022,2023
→ Response: Simple explanations, percentage decreases, what it means for climate

Q: "What are waste emissions?"
→ Uses: Appropriate waste-* dataset
→ Response: Definition, examples, why it matters, simple comparisons
```

## Best Practices for Data Utilization

### 1. Match Resolution to Question Scope

| Question Scope | Best Resolution |
|---------------|-----------------|
| Global/continental trends | `country-year` |
| National seasonal patterns | `country-month` |
| State/province analysis | `admin1-year` or `admin1-month` |
| Urban policy planning | `city-year` or `city-month` |

### 2. Temporal Grain Selection

- **Annual (`-year`)**: Best for trend analysis, year-over-year comparisons, long-term planning
- **Monthly (`-month`)**: Best for seasonal patterns, policy impact timing, short-term fluctuations

### 3. Data Availability Considerations

**Important Limitations:**
- Not all states/provinces available in admin1 datasets (check data coverage)
- City data limited to major urban centers
- Monthly data typically lags annual data by 1-2 years
- Some sectors have better coverage than others

**Checking Data Availability:**
```bash
# List all available datasets
curl http://localhost:8010/list_files

# Query dataset to check what entities are available
curl -X POST http://localhost:8010/query \
  -H "Content-Type: application/json" \
  -d '{"file_id": "transport-admin1-year", "select": ["admin1_name"], "where": {"country_name": "United States of America", "year": 2023}, "limit": 100}'
```

### 4. Sector Name Mapping

**Critical:** Use the abbreviated file_id format in queries:

| Full Name | File ID Prefix |
|-----------|---------------|
| Industrial Combustion | `ind-combustion-` |
| Industrial Processes | `ind-processes-` |
| Fuel Exploitation | `fuel-exploitation-` |
| (all others) | (use full name) |

### 5. Country Name Normalization

Some countries have multiple name variations. The system auto-normalizes:
- "United States" / "USA" / "US" → "United States of America"
- "China" → "People's Republic of China"
- "Russia" → "Russian Federation"
- "UK" → "United Kingdom"

## Common Query Patterns

### Pattern 1: Top N Emitters
```json
{
  "file_id": "transport-country-year",
  "select": ["country_name", "year", "MtCO2"],
  "where": {"year": 2023},
  "order_by": "MtCO2 DESC",
  "limit": 10
}
```

### Pattern 2: Year-over-Year Comparison
```json
{
  "file_id": "power-country-year",
  "select": ["country_name", "year", "MtCO2"],
  "where": {"country_name": "Germany", "year": [2022, 2023]},
  "order_by": "year ASC"
}
```

### Pattern 3: Seasonal Analysis
```json
{
  "file_id": "waste-city-month",
  "select": ["city_name", "month", "MtCO2"],
  "where": {"city_name": "Tokyo", "year": 2021"},
  "order_by": "month ASC",
  "limit": 12
}
```

### Pattern 4: Regional Concentration
```json
{
  "file_id": "ind-combustion-admin1-year",
  "select": ["admin1_name", "country_name", "year", "MtCO2"],
  "where": {"country_name": "United States of America", "year": 2023},
  "order_by": "MtCO2 DESC",
  "limit": 20
}
```

## Persona-Specific Response Formatting

### Climate Analyst Response Template
```
[Data-driven insight]

Priority mitigation areas:
• [Specific recommendation with data backing]
• [Targeted intervention suggestion]
• [Threshold-based action items]

Data retrieved using MCP [tool type].

From a mitigation planning perspective, prioritise:
• [Strategic consideration]
• [Policy-relevant metric]

*All emissions data is in tonnes CO₂ (MtCO₂ for large values)*
```

### Research Scientist Response Template
```
[Methodological context and data description]

Analysis:
• [Statistical observation]
• [Data quality consideration]
• [Methodological caveat]

The [dataset name] relies on [methodology description]. While this provides [strength], it is subject to [limitation].

Data retrieved using MCP [tool type].

Methodological notes and considerations:
• [Temporal resolution note]
• [Source provenance]
• [Uncertainty discussion]

*All emissions data is in tonnes CO₂ (MtCO₂ for large values)*
```

### Financial Analyst Response Template
```
[Risk-oriented summary with directional language]

Key signals:
• Top emitters: [List with momentum indicators]
• Concentration: [Percentage of total from top N]
• Momentum: [Rising/falling trend description]

Implications for portfolio risk:
• [Material shift observation]
• [Comparative position]

Data retrieved using MCP [tool type].

*All emissions data is in tonnes CO₂ (MtCO₂ for large values)*
```

### Student Response Template
```
[Simple, plain-language explanation]

Here's what the data shows:
• [First fact in simple terms]
• [Second fact with relatable comparison]
• [Why this matters for climate]

This [increase/decrease] means [simple consequence explanation].

Data retrieved using MCP [tool type].

Remember:
• Emissions measure how much CO₂ was released
• Bigger numbers mean more emissions
• [Simple contextual note]

*All emissions data is in tonnes CO₂ (MtCO₂ for large values)*
```

## Troubleshooting Common Issues

### Issue 1: "file_not_found" Error
**Cause:** Incorrect file_id (e.g., using "industrial-combustion" instead of "ind-combustion")
**Solution:** Use abbreviated forms: `ind-combustion-`, `ind-processes-`

### Issue 2: "couldn't find data" for Geographic Entities
**Cause:** Entity not present in dataset (e.g., California/Texas missing from some admin1 datasets)
**Solution:**
1. Check available entities using a sample query
2. Adjust question to use entities that exist in the data
3. Use country-level data as fallback

### Issue 3: "query_failed" Errors
**Cause:** Malformed query JSON or incompatible filters
**Solution:**
1. Ensure `select` is an array of strings
2. Ensure `where` is a flat object (no nested dicts)
3. Use `order_by` as a single string (e.g., "MtCO2 DESC")

### Issue 4: Empty Results
**Cause:** Year out of range or entity name mismatch
**Solution:**
1. Use years 2000-2024 for annual, 2000-2023 for monthly
2. Check exact entity names (case-sensitive)
3. Verify temporal coverage for that sector

## Performance Optimization

### Caching Strategy
- Identical queries are cached (256 entry LRU cache)
- Cache key includes tool name + all arguments
- Personas with consistent query patterns benefit most

### Query Limits
- Default limit: 20 rows
- Maximum limit: 1000 rows
- Use appropriate limits based on use case:
  - Top N analysis: limit=10-20
  - Full year monthly: limit=12
  - State/province scan: limit=50-100

### Concurrent Requests
- LLM concurrency: 2 simultaneous requests
- MCP bridge handles multiple personas in parallel
- Circuit breaker protects against cascading failures

## Testing & Validation

### Persona Regression Tests
Located in `testing/run_persona_tests.py`, these tests verify:
1. Each persona generates valid queries for their focus areas
2. Response tone matches persona characteristics
3. Data utilization patterns align with audience needs

### Test Question Bank Structure
```json
{
  "id": 1,
  "prompt": "Question text",
  "personas": ["Climate Analyst"],
  "category": "trend_hotspot",
  "notes": "Expected behavior description"
}
```

### Running Tests
```bash
PYTHONPATH=/path/to/ClimateGPT python testing/run_persona_tests.py --verbose
```

## Advanced Features

### Aggregations
For sum, avg, min, max calculations:
```json
{
  "file_id": "transport-country-year",
  "select": ["country_name"],
  "aggregations": {"MtCO2": "sum"},
  "where": {"year": 2023},
  "group_by": ["country_name"]
}
```

### Multi-Year Filtering
```json
{
  "where": {"year": [2020, 2021, 2022, 2023]}
}
```

### Month-Specific Queries
```json
{
  "file_id": "power-country-month",
  "where": {"country_name": "Germany", "year": 2022, "month": [6, 7, 8]}
}
```

## Future Enhancements

1. **Expanded Coverage**: More admin1 and city entities
2. **Sector Breakdowns**: Sub-sector disaggregation
3. **Forecast Data**: Projected emissions scenarios
4. **Uncertainty Bounds**: Confidence intervals for all values
5. **Real-time Updates**: More frequent data refreshes

---

**Generated:** 2025-11-09
**Version:** 2.0
**ClimateGPT Data Architecture Team**
