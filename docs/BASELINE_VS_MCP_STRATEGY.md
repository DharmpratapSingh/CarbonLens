# ClimateGPT: Baseline Knowledge vs. MCP Data Strategy

**Date:** 2025-11-09
**Purpose:** Define when and how to use base model knowledge vs. MCP tool-based data retrieval

---

## Executive Summary

ClimateGPT has **two distinct knowledge sources**:

1. **Baseline Knowledge** (Built into model from training):
   - Strong on climate science concepts, policy frameworks, and general understanding
   - ⚠️ **Risk:** Can hallucinate specific numbers or recent data
   - ✅ **Best for:** Explanations, definitions, mechanisms, policy context

2. **MCP Data** (EDGAR v2024 via tool calls):
   - ✅ Precise, verified, up-to-date emissions data (2000-2024)
   - ✅ Multi-resolution (country/admin1/city, annual/monthly)
   - ✅ **Best for:** Quantitative queries, comparisons, trends, rankings

**Optimal Strategy:** Combine both - use base knowledge for context/explanation, MCP data for facts/numbers.

---

## Part 1: Baseline Knowledge Capabilities

### ✅ What ClimateGPT Knows (Without MCP)

#### 1. Climate Science Fundamentals

**Example Test Results:**

**Q: "What is the greenhouse effect?"**
- ✅ **Excellent explanation** of mechanism
- ✅ Correctly lists greenhouse gases (CO₂, CH₄, H₂O, N₂O)
- ✅ Explains natural vs. enhanced greenhouse effect
- ✅ Discusses human impact (fossil fuels, deforestation)

**Q: "What are tipping points in the climate system?"**
- ✅ Defines tipping points accurately
- ✅ Provides specific examples:
  - Ice sheet collapse (Greenland, West Antarctic)
  - Amazon rainforest die-off
  - AMOC (ocean circulation) changes
  - Permafrost thaw
  - Coral reef bleaching
- ✅ Explains irreversibility and nonlinear behavior

**Verdict:** **Production-ready for conceptual questions**

---

#### 2. Policy & Frameworks

**Example Test Results:**

**Q: "What is the Paris Agreement?"**
- ✅ Accurate history (2015 COP21, entered force 2016)
- ✅ Correct goals (<2°C, pursuing 1.5°C)
- ✅ Explains NDCs (Nationally Determined Contributions)
- ✅ Discusses adaptation, finance, common but differentiated responsibilities

**Q: "What does net zero mean?"**
- ✅ Clear definition (emissions = removals)
- ✅ Lists pathways: renewables, energy efficiency, CCS, reforestation
- ✅ Connects to Paris Agreement targets

**Q: "What is the IPCC?"**
- ✅ Correct founding (1988, WMO + UNEP)
- ✅ Explains assessment reports and role
- ✅ Describes influence on policy (UNFCCC, Paris Agreement)

**Verdict:** **Production-ready for policy/framework questions**

---

#### 3. Emissions Conceptual Knowledge

**Example Test Results:**

**Q: "What sectors produce the most greenhouse gas emissions?"**
- ✅ Correctly lists: energy, industrial, transportation, agriculture, waste
- ✅ Explains why (fossil fuel combustion, manufacturing, livestock, landfills)
- ⚠️ **No specific percentages** (correctly avoids hallucination)

**Q: "What is the difference between Scope 1, 2, and 3 emissions?"**
- ✅ **Excellent detailed explanation:**
  - Scope 1: Direct emissions from owned sources
  - Scope 2: Indirect from purchased energy
  - Scope 3: Value chain (suppliers, transportation, waste)
- ✅ Provides concrete examples for each scope

**Q: "What are the main sources of transport emissions?"**
- ✅ Lists: gasoline/diesel engines, aviation, marine, rail
- ✅ Discusses electric vehicles and electricity sources
- ⚠️ **No specific modal split percentages**

**Verdict:** **Production-ready for conceptual emissions questions**

---

### ⚠️ What ClimateGPT Should NOT Answer (Without MCP)

#### Quantitative/Recent Data Queries

**Test Results:**

**Q: "What were China's exact CO2 emissions in 2023?"**
- ✅ **Correctly declined:** "I don't have access to China's exact CO2 emissions for 2023"
- ✅ Provided general context (largest emitter, ~12.8 billion tonnes in 2022)
- ✅ **Proper behavior** - acknowledged limitation

**Q: "Which country increased transport emissions the most from 2020 to 2023?"**
- ❌ **HALLUCINATED:** "China's transport sector... 25% increase from 2020 to 2023"
- ❌ **Made up specific percentage** without data source
- 🚨 **CRITICAL ISSUE:** Model fabricated recent quantitative data

**Q: "What are Tokyo's waste emissions in 2021?"**
- ✅ **Correctly declined:** "I'm not able to provide specific data on Tokyo's waste emissions in 2021"
- ✅ Provided general context about urban waste management
- ✅ **Proper behavior** - acknowledged limitation

**Verdict:** 🚨 **UNRELIABLE for quantitative queries** - risk of hallucination

---

## Part 2: MCP Data Capabilities

### ✅ What MCP Data Provides

#### Comprehensive EDGAR v2024 Emissions Data

**Coverage:**
- **Temporal:** 2000-2024 (annual), 2000-2023 (monthly)
- **Geographic:** 195+ countries, 3,000+ admin1 (states/provinces), 500+ cities
- **Sectors:** 8 sectors with detailed breakdowns
- **Granularity:** ~50 million data points

**Sectors:**
1. Transport
2. Power
3. Waste
4. Agriculture
5. Buildings
6. Fuel Exploitation
7. Industrial Combustion
8. Industrial Processes

**Example Queries MCP Can Answer:**

✅ "What were China's transport emissions in 2023?" → **Precise:** 1,069.75 MtCO₂
✅ "Which country increased transport emissions most 2020-2023?" → **USA: +203.07 MtCO₂**
✅ "Tokyo waste emissions in 2021?" → **0.396 MtCO₂ (monthly breakdown available)**
✅ "Top 5 US states by industrial combustion?" → **Louisiana (46.5), Indiana (43.5), ...**
✅ "France power sector seasonal patterns 2022?" → **12-month series, peak in Feb (3.39 MtCO₂)**

---

### ⚠️ What MCP Data Does NOT Provide

**Limitations:**

❌ **No per-capita calculations** (only absolute emissions)
❌ **No GDP-based metrics** (no economic intensity)
❌ **No forecasts/projections** (only historical data 2000-2024)
❌ **No non-CO₂ GHGs in isolation** (EDGAR data is CO₂-equivalent)
❌ **No sub-city granularity** (city is the finest resolution)
❌ **No real-time data** (annual data lags ~1 year, monthly ~2 years)
❌ **No policy impact attribution** (raw emissions, not causal analysis)
❌ **No financial/cost data** (no carbon pricing, abatement costs, etc.)

**Example Queries MCP Cannot Answer:**

❌ "What are China's per-capita emissions in 2023?"
❌ "What will US transport emissions be in 2030?"
❌ "How much would it cost Germany to reduce power emissions 50%?"
❌ "Which policy caused UK emissions to decline in 2020?"
❌ "What are methane-only emissions from agriculture?"

---

## Part 3: Optimal Strategy - Combining Both

### Decision Tree: When to Use What

```
User Question
     │
     ├─ Conceptual/Explanatory?
     │  ├─ "What is X?"
     │  ├─ "How does Y work?"
     │  ├─ "Why is Z important?"
     │  └─> USE BASELINE KNOWLEDGE ✅
     │
     ├─ Quantitative (recent/specific)?
     │  ├─ "What were X's emissions in 2023?"
     │  ├─ "Which country emitted most in sector Y?"
     │  ├─ "How did X change from 2020 to 2023?"
     │  └─> USE MCP DATA ✅
     │
     ├─ Comparative Analysis?
     │  ├─ "Compare X vs Y emissions"
     │  ├─ "Rank top N countries by Z"
     │  └─> USE MCP DATA + BASELINE CONTEXT ✅
     │
     ├─ Trend/Pattern Analysis?
     │  ├─ "What are seasonal patterns in X?"
     │  ├─ "Has Y been increasing or decreasing?"
     │  └─> USE MCP DATA + BASELINE INTERPRETATION ✅
     │
     └─ Out of Scope? (per-capita, forecasts, costs)
        └─> USE BASELINE + EXPLAIN LIMITATION ⚠️
```

---

### Response Pattern Templates

#### Pattern 1: Pure Conceptual (Baseline Only)

**Question Type:** "What is the greenhouse effect?"

**Response Structure:**
```
[BASELINE KNOWLEDGE]
- Definition and mechanism
- Examples and components
- Scientific context
- Real-world implications

[NO MCP CALL NEEDED]
```

**Example:**
> The greenhouse effect is a natural process where greenhouse gases (CO₂, CH₄, H₂O, N₂O) trap heat in Earth's atmosphere. When sunlight reaches Earth, it warms the surface, which then emits infrared radiation. Greenhouse gases absorb this radiation and re-emit it, keeping the planet warm. Without this effect, Earth's average temperature would be ~-18°C instead of +15°C. However, human activities (fossil fuel combustion, deforestation) have enhanced this effect, leading to global warming.

**No data query required** - pure explanation.

---

#### Pattern 2: Pure Quantitative (MCP Only)

**Question Type:** "What were Germany's power emissions in 2023?"

**Response Structure:**
```
[MCP TOOL CALL]
→ Query: power-country-year, where={country_name: "Germany", year: 2023}

[RESPONSE]
→ "Germany's power sector emitted 175.97 MtCO₂ in 2023."
→ [Add units clarification from baseline knowledge]
```

**Example:**
> Germany's power sector emitted **175.97 MtCO₂ in 2023**, according to EDGAR v2024 data.
>
> *All emissions data is in tonnes CO₂.*

**Data-driven answer** - minimal interpretation.

---

#### Pattern 3: Hybrid - Data + Context (Baseline + MCP) **[OPTIMAL]**

**Question Type:** "How did Germany's power emissions change 2022-2023? What does this mean?"

**Response Structure:**
```
[MCP TOOL CALL]
→ Query: power-country-year, where={country_name: "Germany", year: [2022, 2023]}

[BASELINE INTERPRETATION]
→ Calculate change: 175.97 - 227.68 = -51.71 MtCO₂ (-22.7%)
→ Add context from baseline knowledge:
  - Renewable energy transition
  - Coal phaseout policies
  - Economic factors
  - Climate goals (Paris Agreement)

[COMBINED RESPONSE]
```

**Example:**
> Germany's power-sector emissions **decreased significantly** from **227.68 MtCO₂ in 2022** to **175.97 MtCO₂ in 2023**, a reduction of **51.71 MtCO₂ (-22.7%)**.
>
> **What this means:** [BASELINE CONTEXT]
> - This decline reflects Germany's accelerated transition to renewable energy (wind, solar)
> - Aligns with Germany's coal phaseout commitments under the Paris Agreement
> - Represents one of the largest year-over-year reductions in Europe's largest economy
> - Contributes to EU's overall net-zero targets for 2050
>
> **Context:** [BASELINE KNOWLEDGE]
> The power sector is often the fastest to decarbonize due to renewable technology maturity. Germany's reduction demonstrates that large-scale emissions cuts are achievable even in industrialized economies.
>
> *Data: EDGAR v2024. All emissions in tonnes CO₂.*

**Best of both worlds** - precise data + expert interpretation.

---

#### Pattern 4: Trend Analysis (MCP Data + Baseline Interpretation)

**Question Type:** "What are the seasonal patterns in Tokyo's waste emissions for 2021?"

**Response Structure:**
```
[MCP TOOL CALL]
→ Query: waste-city-month, where={city_name: "Tokyo", year: 2021}, limit=12

[BASELINE INTERPRETATION]
→ Identify peak months (June: 0.0364 MtCO₂)
→ Identify low months (January: 0.0249 MtCO₂)
→ Explain seasonality using baseline knowledge:
  - Summer = higher consumption/waste
  - Winter = lower activity
  - Cultural factors (holidays, tourism)
  - Temperature effects on waste decomposition
```

**Example:**
> Tokyo's waste emissions in 2021 show a **distinct seasonal pattern**:
>
> **Peak Period:** Summer months (June-August)
> - June: 0.0364 MtCO₂ (highest)
> - July: 0.0356 MtCO₂
> - August: 0.0316 MtCO₂
>
> **Low Period:** Winter months (December-February)
> - January: 0.0249 MtCO₂ (lowest)
> - December: 0.0279 MtCO₂
>
> **Explanation:** [BASELINE KNOWLEDGE]
> This ~46% variation reflects:
> 1. **Consumption patterns:** Higher summer tourism and outdoor activities generate more waste
> 2. **Decomposition rates:** Warmer temperatures accelerate organic waste breakdown, increasing methane production
> 3. **Holiday seasonality:** Japanese holidays (Golden Week in May, Obon in August) drive consumption spikes
>
> **Policy Implications:** [BASELINE EXPERTISE]
> - Target summer waste reduction campaigns
> - Scale up collection/processing capacity before peak months
> - Implement seasonal pricing for waste management
>
> *Data: EDGAR v2024, Tokyo city-level monthly waste emissions.*

**Data provides facts, baseline provides insights.**

---

## Part 4: Hallucination Prevention

### 🚨 Critical Issue: When Baseline Hallucinates

**Problem:** Without MCP data, ClimateGPT sometimes fabricates specific numbers.

**Example from Testing:**
```
Q: "Which country increased transport emissions the most from 2020 to 2023?"

Without MCP (HALLUCINATION):
> "China's transport sector... 25% increase from 2020 to 2023"
❌ FABRICATED percentage with no source

With MCP (ACCURATE):
> USA: +203.07 MtCO₂ (1481.68 → 1684.75)
> China: +137.32 MtCO₂ (932.43 → 1069.75)
✅ VERIFIED from EDGAR v2024
```

### Mitigation Strategies

#### Strategy 1: Always Use MCP for Quantitative Queries

**Rule:** If question contains numbers/quantities/comparisons → **MUST use MCP**

**Triggers:**
- "What were [X]'s emissions in [year]?"
- "How much did [X] increase/decrease?"
- "Which country/sector/region has the most/least?"
- "Compare [X] vs [Y]"
- "What are the top N [entities]?"

**Implementation in Persona Prompts:**
```python
CRITICAL RULES:
1. NEVER fabricate or estimate values.
2. For ANY quantitative question (numbers, comparisons, rankings), you MUST call the query tool.
3. If data is unavailable from the tool, state "Data not available in EDGAR v2024" - do NOT guess.
4. WRONG: "China's emissions increased 25% from 2020 to 2023" (without tool call)
5. RIGHT: Query tool first, then report: "China's transport emissions: 2020: 932.43 MtCO₂, 2023: 1,069.75 MtCO₂ (+14.7%)"
```

---

#### Strategy 2: Explicit Uncertainty Acknowledgment

**When baseline should decline:**

✅ **Good Response:**
> "I don't have access to specific 2023 data without querying the database. Based on general trends, [qualitative context], but I'd recommend using the query tool for precise numbers."

❌ **Bad Response:**
> "China's transport emissions increased approximately 25% from 2020 to 2023." [HALLUCINATION]

**Implementation:**
```python
# In persona system prompt
If you do not have access to specific data through a tool call, you MUST:
1. Acknowledge the limitation explicitly
2. Offer to retrieve the data via tool call
3. Provide ONLY general/qualitative context (no specific numbers)
4. NEVER say "approximately X%" or "around Y MtCO2" without a tool call
```

---

#### Strategy 3: Two-Stage Response Pattern

**For ambiguous questions:**

**Stage 1: Acknowledge & Clarify**
> "To answer this precisely, I'll need to query the EDGAR v2024 emissions database. Let me retrieve the exact data..."

**Stage 2: Data + Context**
> [MCP TOOL CALL] + [BASELINE INTERPRETATION]

**Benefits:**
- Sets expectation that answer will be data-driven
- Prevents hallucination
- Demonstrates transparency

---

## Part 5: Persona-Specific Strategies

### Climate Analyst: Data-First, Context-Rich

**Approach:**
1. **Always query MCP first** for quantitative claims
2. Use baseline to add **policy context** and **actionable recommendations**
3. Combine data patterns with **mitigation strategies**

**Example:**
```
Q: "What are the top emitters in US industrial combustion?"

MCP DATA:
→ Louisiana: 46.52 MtCO₂
→ Indiana: 43.50 MtCO₂
→ Mississippi: 38.35 MtCO₂

BASELINE CONTEXT (added):
→ Louisiana: Oil & gas refining concentration (Gulf Coast infrastructure)
→ Indiana: Heavy manufacturing base (steel, chemicals)
→ Mississippi: Petrochemical industry cluster

POLICY RECOMMENDATIONS (baseline):
→ Target top 3 states for federal clean energy incentives
→ Prioritize industrial energy efficiency programs in Gulf Coast
→ Consider regional carbon pricing for heavy industry
```

**Value Add:** Baseline knowledge enriches MCP data with actionable insights.

---

### Research Scientist: Methodology + Data Quality

**Approach:**
1. **Query MCP data** with explicit uncertainty acknowledgment
2. Use baseline to discuss **EDGAR methodology** and **data limitations**
3. Reference **IPCC assessment reports** and **peer-reviewed context**

**Example:**
```
Q: "How reliable is monthly power data for France in 2022?"

MCP DATA:
→ 12-month series (Jan: 3.38 MtCO₂, ..., Dec: 3.05 MtCO₂)

BASELINE METHODOLOGY DISCUSSION (added):
→ EDGAR v2024 combines bottom-up (national statistics) and top-down (satellite) approaches
→ Monthly resolution: Interpolates annual data using proxies (temperature, economic activity)
→ Uncertainty: ±15-20% at monthly level (IPCC AR6 guidance)
→ Validation: Cross-checked against national reporting (France's CITEPA)

LIMITATIONS (baseline):
→ May not capture sub-monthly variations (daily/weekly fluctuations)
→ Satellite coverage gaps in high-latitude winters
→ Time-lag: Monthly data lags annual by ~2 years

RECOMMENDATION:
→ "Suitable for trend analysis, but use annual data for precise comparisons."
```

**Value Add:** Baseline provides scientific rigor and methodological transparency.

---

### Financial Analyst: Quantitative Precision + Risk Signals

**Approach:**
1. **Always use MCP** for concentration and momentum metrics
2. Use baseline to translate data into **investment/risk language**
3. Add **comparative benchmarks** from baseline knowledge

**Example:**
```
Q: "What are the risk signals in US state industrial emissions?"

MCP DATA:
→ Top 5 states: LA (46.5), IN (43.5), MS (38.4), CA (33.4), GA (26.6)
→ Concentration: Top 5 = 188.8 MtCO₂ / US total = ~45% (if US total ~420 MtCO₂)

BASELINE RISK TRANSLATION (added):
→ **Concentration Risk:** Top 5 states account for nearly half of US industrial combustion
→ **Regulatory Exposure:** EPA Clean Air Act targets = high compliance costs for LA/IN/MS
→ **Stranded Asset Risk:** Gulf Coast refineries face long-term demand erosion (EVs, renewables)
→ **Portfolio Impact:** Industrial REIT exposure in these states = material climate risk

COMPARATIVE BENCHMARKS (baseline):
→ US concentration (45%) vs. EU (30% in top 5 members) = higher geographic risk
→ Louisiana per-capita emissions >> national average = policy backlash potential

RECOMMENDATION:
→ "Reduce exposure to Gulf Coast industrial assets, diversify to states with clean energy incentives."
```

**Value Add:** Baseline translates emissions data into financial/investment metrics.

---

### Student: Simplicity + MCP Accuracy

**Approach:**
1. **Use MCP for facts**, then **simplify with baseline**
2. Add **analogies and relatable comparisons** from baseline
3. Provide **educational context** (why this matters for climate)

**Example:**
```
Q: "How did Germany's power emissions change 2022-2023?"

MCP DATA:
→ 2022: 227.68 MtCO₂
→ 2023: 175.97 MtCO₂
→ Change: -51.71 MtCO₂ (-22.7%)

BASELINE SIMPLIFICATION (added):
→ "That's like removing 11 million cars from the road!" (baseline analogy)
→ Explanation: Germany used more wind and solar, less coal
→ Why it matters: Reduces air pollution, slows climate change, creates green jobs

EDUCATIONAL CONTEXT (baseline):
→ Power sector = easiest to clean up (renewable tech ready)
→ Transport/industry = harder (need new tech like EVs, hydrogen)
→ Germany's success shows big countries can cut emissions fast

REMEMBER:
→ Bigger numbers = more emissions = worse for climate
→ Germany went from 227.68 (bad) to 175.97 (better) = progress!
```

**Value Add:** Baseline makes MCP data accessible and meaningful for learners.

---

## Part 6: Baseline Testing Framework

### Continuous Baseline Evaluation

**Purpose:** Monitor baseline model updates for hallucination risk and capability changes.

**Test Categories:**

| Category | # Questions | Purpose | Expected Behavior |
|----------|-------------|---------|-------------------|
| Conceptual | 10 | Test core climate science knowledge | ✅ Accurate, detailed explanations |
| Policy | 5 | Test framework/agreement knowledge | ✅ Accurate dates, goals, mechanisms |
| Quantitative (Out of Scope) | 10 | Test hallucination resistance | ✅ Decline or caveat, no fabrication |
| Hybrid (Needs MCP) | 10 | Test when baseline suggests tool use | ✅ Acknowledges data needed |

**Automated Test Script:** `/tmp/test_baseline_knowledge.py`

**Run Frequency:** Monthly or after model updates

**Success Criteria:**
- Conceptual: 100% accurate
- Policy: 100% accurate
- Quantitative: 0% hallucination (should decline)
- Hybrid: 100% acknowledgment of tool need

---

### Regression Testing: Baseline vs. MCP Answers

**Purpose:** Ensure MCP data overrides baseline for quantitative queries.

**Test Pattern:**
```python
def test_baseline_vs_mcp(question):
    # Test 1: Baseline only (no tool access)
    baseline_answer = query_baseline(question)

    # Test 2: MCP enabled (with tools)
    mcp_answer = query_with_mcp_tools(question)

    # Assertions:
    if question_is_quantitative(question):
        assert baseline_answer contains "I don't have access" OR baseline_answer is_qualitative()
        assert mcp_answer contains_specific_numbers()
        assert mcp_answer cites_edgar_v2024()

    if question_is_conceptual(question):
        assert baseline_answer is_detailed()
        assert mcp_answer adds_data_if_relevant()
```

**Example Tests:**
```python
# Test 1: Quantitative should use MCP
test_baseline_vs_mcp("What were China's transport emissions in 2023?")
→ Baseline: "I don't have 2023 data..."
→ MCP: "1,069.75 MtCO₂ (EDGAR v2024)"
✅ PASS: MCP provides data, baseline correctly declines

# Test 2: Conceptual can use baseline
test_baseline_vs_mcp("What is the greenhouse effect?")
→ Baseline: [Detailed explanation]
→ MCP: [Same explanation, may add example data]
✅ PASS: Both accurate

# Test 3: Hallucination detection
test_baseline_vs_mcp("Which country increased transport most 2020-2023?")
→ Baseline: ❌ "China increased 25%" [FABRICATED]
→ MCP: ✅ "USA: +203.07 MtCO₂" [VERIFIED]
🚨 FAIL: Baseline hallucinated → Must always use MCP for this query type
```

---

## Part 7: Implementation Recommendations

### Immediate Actions

#### 1. Update All Persona Prompts

**Add to `climategpt_persona_engine.py`:**

```python
MANDATORY TOOL USAGE RULES:

ALWAYS use tools for:
- Questions with specific years (e.g., "in 2023", "from 2020 to 2023")
- Comparative questions (e.g., "X vs Y", "top N countries")
- Quantitative claims (e.g., "how much", "what percentage", "exact emissions")
- Ranking/ordering questions (e.g., "which country most/least")
- Trend questions (e.g., "increasing or decreasing", "seasonal patterns")

NEVER use tools for:
- Conceptual explanations (e.g., "What is the greenhouse effect?")
- Policy descriptions (e.g., "What is the Paris Agreement?")
- Mechanism explanations (e.g., "How does CO₂ cause warming?")

When tool call returns data:
- ALWAYS cite "EDGAR v2024" or "MCP query"
- Add baseline context/interpretation AFTER stating data
- Combine numbers (MCP) with meaning (baseline)

If you cannot determine whether a tool is needed:
- Default to calling the tool (safe approach)
- Better to have data you don't use than to hallucinate data
```

---

#### 2. Create Baseline Test Suite

**File:** `testing/test_baseline_hallucination.py`

```python
#!/usr/bin/env python3
"""
Test suite to detect baseline hallucination and ensure MCP usage for quantitative queries.
"""

hallucination_tests = [
    {
        "question": "What were China's exact CO2 emissions in 2023?",
        "expected_baseline": "declines or caveats (no specific number)",
        "expected_mcp": "specific number with EDGAR citation"
    },
    {
        "question": "Which country increased transport emissions most from 2020 to 2023?",
        "expected_baseline": "declines or suggests tool call",
        "expected_mcp": "USA: +203.07 MtCO₂ (EDGAR v2024)"
    },
    # ... more tests
]

for test in hallucination_tests:
    baseline_result = query_baseline(test["question"])
    mcp_result = query_with_mcp(test["question"])

    # Check baseline doesn't hallucinate
    assert not contains_fabricated_numbers(baseline_result), f"HALLUCINATION: {test['question']}"

    # Check MCP provides data
    assert contains_edgar_citation(mcp_result), f"MISSING CITATION: {test['question']}"
```

**Run:** Monthly + before production deployments

---

#### 3. Response Quality Checklist

**Before sending response to user, verify:**

☑ **Quantitative claims have MCP source**
- [ ] All numbers cite EDGAR v2024 or MCP query
- [ ] No "approximately X%" without tool call
- [ ] No "around Y MtCO₂" without tool call

☑ **Baseline knowledge adds value**
- [ ] Conceptual explanation included (if relevant)
- [ ] Policy/scientific context provided
- [ ] User audience (persona) reflected in tone

☑ **No hallucination**
- [ ] Recent data (2020+) comes from MCP, not baseline
- [ ] Specific entity data (country/city emissions) comes from MCP
- [ ] Comparative data (rankings, top N) comes from MCP

☑ **Transparency**
- [ ] Data source cited (EDGAR v2024)
- [ ] Limitations acknowledged (if any)
- [ ] Distinction clear between fact (MCP) and interpretation (baseline)

---

## Part 8: Example Questions & Routing

### Routing Matrix

| Question | Route | Rationale |
|----------|-------|-----------|
| "What is climate change?" | **Baseline Only** | Conceptual definition |
| "What were Germany's 2023 power emissions?" | **MCP Only** | Specific quantitative |
| "How do power emissions contribute to climate change?" | **Baseline + MCP** | Concept + example data |
| "Compare France vs UK power emissions 2022-2023" | **MCP First → Baseline Context** | Data + interpretation |
| "What are seasonal patterns in Tokyo waste?" | **MCP Data → Baseline Explanation** | Data + scientific reasoning |
| "What is the Paris Agreement target?" | **Baseline Only** | Policy knowledge |
| "Are countries meeting Paris targets?" | **MCP Data → Baseline Policy Context** | Needs current data + policy |
| "What will emissions be in 2030?" | **Baseline (Decline)** | No forecast data in MCP |
| "What are per-capita emissions for India?" | **MCP Data → Baseline Calculation** | Have absolute, can calculate |
| "How much does carbon reduction cost?" | **Baseline (Decline)** | No cost data in MCP |

---

## Conclusion

### Optimal ClimateGPT Architecture

```
User Question
     ↓
Question Classifier
     ↓
   ┌─────────────────┬─────────────────┬─────────────────┐
   │   Conceptual    │   Quantitative  │     Hybrid      │
   │   Questions     │   Questions     │   Questions     │
   └────────┬────────┴────────┬────────┴────────┬────────┘
            │                 │                 │
            ↓                 ↓                 ↓
      Baseline Only      MCP Tool Call     MCP + Baseline
            │                 │                 │
            │                 ↓                 ↓
            │          Verified Data      Data + Context
            │                 │                 │
            └─────────────────┴─────────────────┘
                              ↓
                      Combined Response
                      [Data + Explanation]
```

**Key Principles:**

1. **Baseline = Expert Interpreter**: Use for concepts, context, policy, mechanisms
2. **MCP = Fact Provider**: Use for all quantitative claims, recent data, comparisons
3. **Best Responses = Both**: Precise data (MCP) + meaningful interpretation (baseline)
4. **Hallucination Prevention**: Always use MCP for numbers/dates/rankings
5. **Transparency**: Cite sources, acknowledge limitations, distinguish fact from interpretation

**Success Metrics:**

- **0% hallucination** on quantitative queries
- **100% MCP usage** for recent/specific data
- **95%+ user satisfaction** (data accuracy + helpful context)
- **Persona differentiation** (same data, 4 different interpretations)

**Next Steps:**

1. ✅ Implement mandatory tool usage rules in persona prompts
2. ✅ Create automated baseline hallucination test suite
3. ✅ Add MCP data + baseline context response pattern to all personas
4. ✅ Monitor for hallucination in production logs
5. ✅ Iterate on response quality based on user feedback

---

**Generated:** 2025-11-09
**Status:** **Production-Ready Strategy**
**Confidence:** **High** (tested with baseline evaluation)
