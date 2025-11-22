# Complex Questions Test Suite for ClimateGPT MCP Server

**Purpose:** Demonstrate advanced capabilities of enhanced ClimateGPT MCP server with quality-aware tools

**Test Date:** November 19, 2025

---

## Question Set 1: Quality-Focused Analysis

### Q1.1: High-Quality Power Sector Data
**Difficulty:** Medium

> "I need to analyze power sector emissions for the most reliable data available. Please retrieve power sector records with a quality score of at least 95/100 and uncertainty of no more than ±10%. Show me records from major industrial countries (China, USA, India, Germany, Japan) for 2020. I want to exclude synthetic data and understand what external sources validated these records."

**Expected Tools to Use:**
- `get_quality_filtered_data` (quality ≥95, uncertainty ≤10)
- `get_validated_records` (multi-source validation)
- Geographic filtering for major economies

**Expected Insights:**
- Power sector quality: 97.74/100 ✅
- Records meeting quality criteria
- 5 external sources integrated
- <7.7% synthetic records

---

### Q1.2: Uncertainty-Aware Multi-Sector Comparison
**Difficulty:** Hard

> "I'm conducting climate research and need to compare emissions trends from 2010-2023 across all 8 sectors. For each sector, show me:
> 1. The average emissions with uncertainty bounds (±%)
> 2. How confidence in the data has changed over time
> 3. Which sectors have improved their quality measurements
> 4. Recommend which sectors are suitable for academic publication"

**Expected Tools to Use:**
- `get_uncertainty_analysis` (all sectors)
- `get_data_quality` (sector ratings)
- Time series comparison

**Expected Insights:**
- Power improved: 71.77 → 97.74 (+25.97)
- Industrial sectors: 77-39 → 96-93 (+19+ pts)
- All sectors now meet publication standard (85+)
- Uncertainty ranges: ±8-14% across sectors

---

## Question Set 2: Data Governance & Transparency

### Q2.1: Multi-Source Validation Verification
**Difficulty:** Medium

> "For compliance and audit purposes, I need to verify the multi-source validation coverage in our databases. Show me:
> 1. Records in the transport and buildings sectors from 2022
> 2. How many external sources validate each record
> 3. Which sources appear most frequently across these sectors
> 4. Are there any records with fewer than 3 sources (potential risks)?"

**Expected Tools to Use:**
- `get_validated_records` (transport, buildings, 2022)
- Multi-source count parsing
- Coverage analysis

**Expected Insights:**
- Transport: 5 sources per record
- Buildings: 6 sources per record
- 95%+ coverage with multi-source validation
- Synthetic records: 0% (low-quality sectors)

---

### Q2.2: Synthetic Data Identification & Risk Assessment
**Difficulty:** Medium

> "Our policy team needs to know where synthetic data exists in our datasets. Please:
> 1. Identify all synthetic records in the power sector
> 2. Explain what proportion of power sector data is synthetic
> 3. What was the quality improvement from adding these synthetic records
> 4. Should we use synthetic power data in regulatory reporting (with caveats)?"

**Expected Tools to Use:**
- `get_quality_filtered_data` (exclude_synthetic: false)
- Quality score comparison (synthetic vs original)
- Sector quality analysis

**Expected Insights:**
- Power synthetic: 12,483 records (7.7%)
- Synthetic quality: 87.14/100
- Original quality: 98.63/100
- Suitable for analysis with caveats (noted as synthetic)

---

## Question Set 3: Research Applications

### Q3.1: Publication-Ready Dataset Selection
**Difficulty:** Hard

> "I'm preparing a manuscript on global emissions trends for Nature Climate Change. I need:
> 1. All sectors with quality scores suitable for peer-reviewed publication (>85/100)
> 2. Time series data from 2015-2023 with confidence intervals
> 3. Uncertainty quantification methodology that meets IPCC standards
> 4. Geographic coverage (how many countries/cities?)
> 5. Source documentation for methods section"

**Expected Tools to Use:**
- `get_quality_filtered_data` (min_quality ≥85)
- `get_data_quality` (methodology documentation)
- `get_uncertainty_analysis` (confidence intervals)

**Expected Insights:**
- All 8 sectors: 85-98/100 ✅ publication-ready
- Geographic: 305+ countries, 3,431+ cities
- Temporal: 24 years (2000-2023)
- Methodology: Bayesian hierarchical IPCC/EPA framework
- Average uncertainty: ±10% (acceptable for publication)

---

### Q3.2: Climate Policy Scenario Analysis
**Difficulty:** Very Hard

> "We're modeling climate policy impacts for the EU's 2030 NDC (Nationally Determined Contribution). We need:
> 1. High-confidence emissions data for all EU countries (quality ≥90/100)
> 2. Data for agriculture, transport, buildings, and power sectors only
> 3. 2015-2023 historical trend with uncertainty bounds
> 4. Confidence that data is suitable for official climate reporting
> 5. Total emissions by sector with ±% bounds for policy targets"

**Expected Tools to Use:**
- `get_quality_filtered_data` (EU countries, quality ≥90)
- `get_uncertainty_analysis` (2015-2023)
- `get_data_quality` (sector ratings for reporting)

**Expected Insights:**
- Power: 97.74/100 (highest confidence)
- Buildings: 85.00/100 (Tier 1, suitable)
- Transport: 85.00/100 (Tier 1, suitable)
- Agriculture: 88.00/100 (good quality)
- All suitable for NDC reporting with quality noted

---

## Question Set 4: Industry & ESG Applications

### Q4.1: Corporate Carbon Accounting Verification
**Difficulty:** Medium

> "We're an industrial company verifying our Scope 3 emissions from purchased energy (power sector). We need:
> 1. Power sector data with highest quality (quality ≥95/100)
> 2. Data for 2021-2023 (recent years)
> 3. Facility-level validation with multiple sources
> 4. Uncertainty estimates for carbon offset calculations
> 5. Documentation of external sources for ESG audit trail"

**Expected Tools to Use:**
- `get_quality_filtered_data` (power, quality ≥95, recent years)
- `get_validated_records` (facility-level, multi-source)
- `get_uncertainty_analysis` (uncertainty for offset calculation)

**Expected Insights:**
- Power quality: 97.74/100 (suitable for ESG)
- External sources: IEA, EPA CEMS, Sentinel-5P, national grids
- Uncertainty: ±8% (excellent for precise accounting)
- Full audit trail available via data_source field

---

### Q4.2: Supply Chain Emissions Benchmarking
**Difficulty:** Hard

> "We manufacture cement and need to benchmark our supply chain emissions against:
> 1. Industrial processes sector data for major producing countries (China, India, Vietnam, Turkey, Egypt)
> 2. Quality assessment of available data
> 3. How many data sources support each country's emissions?
> 4. What's the confidence range (with bounds) for setting realistic targets?
> 5. Which countries have the most reliable data for fair comparison?"

**Expected Tools to Use:**
- `get_validated_records` (industrial processes, major countries)
- `get_quality_filtered_data` (filter for high confidence)
- `get_data_quality` (sector assessment)
- `get_uncertainty_analysis` (confidence ranges)

**Expected Insights:**
- Industrial Processes: 96.40/100 (Tier 1)
- External sources: 6 per record (IVL Cement, ICIS Chemical, etc.)
- Multi-source validation: 95%+ coverage
- Uncertainty: ±9% (reasonable for benchmarking)
- Synthetic: 1.8% (minimal impact on comparison)

---

## Question Set 5: Climate Science & Modeling

### Q5.1: Temporal Uncertainty Evolution Analysis
**Difficulty:** Very Hard

> "We're building a machine learning model to predict emissions by 2030. For model training, we need to understand:
> 1. How has measurement uncertainty decreased over 2000-2023?
> 2. In which years did we achieve high-confidence measurements (<10% uncertainty)?
> 3. Is there a pattern (by sector) of improving data quality?
> 4. For the transport sector specifically, what's the uncertainty trend?
> 5. Can we train on this data with confidence in model generalization?"

**Expected Tools to Use:**
- `get_uncertainty_analysis` (full 2000-2023 timeline, all sectors)
- `get_uncertainty_analysis` (transport sector specific)
- Quality trend analysis

**Expected Insights:**
- Quality improvement: 76.99 → 91.03 (+18.3%)
- Recent uncertainty: ±8-14% (excellent)
- Transport: ±12% (good for modeling)
- Most uncertainty reduced in power, industrial sectors
- Data suitable for ML training (sufficient confidence)

---

### Q5.2: Satellite Validation Cross-Check
**Difficulty:** Hard

> "We're validating our emissions model against satellite observations. Can you show me:
> 1. Which external data sources in our database come from satellites?
> 2. Which sectors use satellite validation (NOAA VIIRS, Sentinel-5P)?
> 3. How much of the global data is backed by satellite observations?
> 4. For the power sector, what's the satellite validation coverage?
> 5. Are there geographic gaps in satellite validation we should know about?"

**Expected Tools to Use:**
- `get_validated_records` (filter for satellite sources)
- `get_data_quality` (document satellite sources)

**Expected Insights:**
- Satellite sources: NOAA VIIRS, Copernicus Sentinel-2/5P, USGS
- Power: Sentinel-5P NO2 validation
- Buildings: NOAA VIIRS nighttime lights
- Industrial: Sentinel-5P SO2 atmospheric validation
- Geographic coverage: Global (305+ countries)

---

## Question Set 6: Data Exploration & Discovery

### Q6.1: Dataset Feature Discovery
**Difficulty:** Easy-Medium

> "I'm new to the ClimateGPT database. Can you help me understand:
> 1. What are all the available datasets and their quality ratings?
> 2. Which sectors are most reliable (quality ≥90/100)?
> 3. What quality columns are now available in the data?
> 4. How are the new quality columns documented?
> 5. What's the overall database health score?"

**Expected Tools to Use:**
- `list_emissions_datasets` (overview with quality)
- `get_dataset_schema` (quality columns)
- `get_data_quality` (overall assessment)

**Expected Insights:**
- All 8 sectors available and documented
- Power, Ind Combustion, Ind Processes: ≥96/100
- 8 new quality columns: quality_score, confidence_level, uncertainty_percent, uncertainty_low/high, is_synthetic, data_source, validation_status
- Database average: 91.03/100 (Tier 1)

---

### Q6.2: Geographic & Temporal Coverage Questions
**Difficulty:** Medium

> "I want to analyze emissions in Southeast Asia from 2010-2023. Before I write my analysis:
> 1. What countries in Southeast Asia are covered (Vietnam, Thailand, Indonesia, Philippines, Malaysia)?
> 2. For each sector, how many cities/locations are represented?
> 3. Are there data gaps (years or locations) I should know about?
> 4. What's the data quality for this region specifically?
> 5. Should I focus on certain sectors or are all sectors equally reliable for Southeast Asia?"

**Expected Tools to Use:**
- `get_validated_records` (Southeast Asia countries)
- `get_data_coverage` (geographic completeness)
- `get_data_quality` (sector reliability)

**Expected Insights:**
- Coverage: 305+ countries including SE Asia nations
- Temporal: 24-year coverage (2000-2023)
- Quality: All sectors 85+/100 (uniform reliability)
- Multi-source validation: 95%+ even for regions

---

## Question Set 7: Advanced Analytics

### Q7.1: Anomaly Detection with Confidence
**Difficulty:** Hard

> "We detected an unusual spike in transport emissions for India in 2019. Before publishing, we need to verify:
> 1. What's the actual emissions value for India transport 2019?
> 2. What's the quality score and uncertainty bounds?
> 3. How many sources confirm this value?
> 4. Is this a real spike or a data artifact (synthetic)?
> 5. Can we confidently attribute this to economic activity or is it a measurement anomaly?"

**Expected Tools to Use:**
- `get_quality_filtered_data` (India, transport, 2019)
- `get_validated_records` (India, transport, 2019)
- `get_uncertainty_analysis` (2019 specific)

**Expected Insights:**
- Quality: 85/100 ✅ suitable for analysis
- Uncertainty: ±12% bounds
- Sources: 5 external sources
- Synthetic: 0% (original data)
- Confidence: HIGH (can publish with caveats)

---

### Q7.2: Trend Decomposition with Quality Context
**Difficulty:** Very Hard

> "We're decomposing emissions into trend, seasonal, and random components for the buildings sector (2000-2023, global average). We need:
> 1. Average emissions by year with uncertainty bounds
> 2. Is the trend statistically significant given uncertainty?
> 3. Quality improvement over time (affecting uncertainty bands)?
> 4. What external factors might explain structural breaks?
> 5. Which sub-periods have most reliable data for decomposition?"

**Expected Tools to Use:**
- `get_uncertainty_analysis` (full 2000-2023, buildings)
- `get_data_quality` (quality evolution)
- Time series filtering

**Expected Insights:**
- Buildings quality: 85.00/100 (Tier 1)
- Uncertainty: ±14% (acceptable for decomposition)
- Data reliability improves in recent years
- 6 external sources per record
- Suitable for time series decomposition

---

## Scoring Rubric

**Easy Questions (Q6.1, Q6.2):**
- Should use 1-2 tools
- Single sector or dataset
- Direct answers

**Medium Questions (Q1.1, Q2.1, Q2.2, Q4.1, Q7.1):**
- Should use 2-3 tools
- Multi-sector or complex filters
- Some interpretation needed

**Hard Questions (Q1.2, Q3.1, Q4.2, Q5.2, Q7.2):**
- Should use 3-4 tools
- Multi-sector, multi-year analysis
- Significant interpretation and insights

**Very Hard Questions (Q3.2, Q5.1, Q7.2):**
- Should use all available tools creatively
- Cross-cutting analysis across dimensions
- Deep insights and recommendations

---

## Success Criteria

✅ Questions demonstrate all 3 new quality tools
✅ Answers show quality-aware decision making
✅ Responses cite actual metrics (91.03/100, 85-98 ranges, etc.)
✅ Uncertainty is explicitly addressed
✅ Multi-source validation is verified
✅ Synthetic data is identified and handled
✅ Use cases are realistic and practical
✅ Backward compatibility is preserved

---

## Expected Tool Usage Summary

| Tool | Q1.1 | Q1.2 | Q2.1 | Q2.2 | Q3.1 | Q3.2 | Q4.1 | Q4.2 | Q5.1 | Q5.2 | Q6.1 | Q6.2 | Q7.1 | Q7.2 |
|------|------|------|------|------|------|------|------|------|------|------|------|------|------|------|
| list_emissions_datasets | – | – | – | – | ✅ | – | – | – | – | – | ✅ | – | – | – |
| get_dataset_schema | – | – | – | – | ✅ | – | – | – | – | – | ✅ | – | – | – |
| get_data_quality | – | ✅ | – | ✅ | ✅ | ✅ | – | ✅ | – | – | ✅ | ✅ | – | ✅ |
| query_emissions | – | – | ✅ | ✅ | – | ✅ | – | ✅ | – | – | – | ✅ | ✅ | ✅ |
| get_quality_filtered_data | ✅ | ✅ | – | ✅ | ✅ | ✅ | ✅ | ✅ | – | – | – | – | ✅ | – |
| get_validated_records | ✅ | – | ✅ | – | – | ✅ | ✅ | ✅ | – | ✅ | – | ✅ | ✅ | – |
| get_uncertainty_analysis | – | ✅ | – | – | ✅ | ✅ | ✅ | ✅ | ✅ | – | – | – | ✅ | ✅ |

---

**Ready to test?** Present these questions to ClimateGPT and have it use the MCP server tools to answer them!

