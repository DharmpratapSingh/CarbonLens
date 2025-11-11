# Baseline Testing Quick Reference

**TL;DR:** ClimateGPT has two knowledge sources. Use baseline for concepts, MCP for numbers. Always combine both for best answers.

---

## The Two Knowledge Sources

### 🧠 Baseline Knowledge (Built-in)
**What it HAS:**
- ✅ Climate science concepts (greenhouse effect, feedbacks, tipping points)
- ✅ Policy frameworks (Paris Agreement, IPCC, net zero)
- ✅ Emissions concepts (Scopes 1/2/3, sectors, sources)
- ✅ Explanatory power (why, how, what if)

**What it LACKS:**
- ❌ Recent specific data (2020+)
- ❌ Precise emissions numbers
- ⚠️ **Risk:** Can hallucinate quantitative data!

**Example Hallucination:**
```
Q: "Which country increased transport most 2020-2023?"
Baseline: "China increased 25% from 2020 to 2023"  ❌ FABRICATED
MCP: "USA: +203.07 MtCO₂ (verified EDGAR data)"  ✅ ACCURATE
```

### 📊 MCP Data (EDGAR v2024)
**What it HAS:**
- ✅ Precise emissions 2000-2024 (annual) / 2000-2023 (monthly)
- ✅ 195+ countries, 3000+ states/provinces, 500+ cities
- ✅ 8 sectors × 3 resolutions × 2 temporal grains
- ✅ ~50 million verified data points

**What it LACKS:**
- ❌ Per-capita calculations
- ❌ Forecasts/projections
- ❌ Policy explanations
- ❌ Cost/financial data

---

## Decision Matrix

| Question Type | Use | Example |
|--------------|-----|---------|
| **"What is...?"** | Baseline | "What is the greenhouse effect?" |
| **"What were [X] emissions in [year]?"** | MCP | "Germany power 2023?" → 175.97 MtCO₂ |
| **"Compare X vs Y"** | MCP + Baseline | Data from MCP, context from baseline |
| **"Top N countries"** | MCP | Ranking requires data |
| **"How does...work?"** | Baseline | Mechanisms/processes |
| **"Why did X change?"** | MCP + Baseline | Data + interpretation |
| **"What will [future]?"** | Baseline (decline) | No forecasts in MCP |

---

## 🚨 Hallucination Prevention Rules

### ALWAYS use MCP tools for:
1. Questions with specific years ("in 2023", "from 2020-2023")
2. Quantitative comparisons ("X vs Y", "how much")
3. Rankings ("top N", "which country most")
4. Specific entity data ("China's emissions", "Tokyo waste")

### NEVER use baseline alone for:
1. Any question with numbers/dates after 2020
2. Comparative analysis with specific entities
3. Trend analysis requiring data
4. Rankings or "top N" queries

### Pattern to AVOID:
```
❌ "China's transport emissions increased approximately 25% from 2020 to 2023."
   (HALLUCINATION - fabricated percentage without MCP call)

✅ "Let me query the data... China: 932.43 MtCO₂ (2020) → 1,069.75 MtCO₂ (2023) = +14.7%"
   (VERIFIED - MCP call with EDGAR citation)
```

---

## Response Patterns

### Pattern 1: Conceptual (Baseline Only)
```
Q: "What is the Paris Agreement?"
A: [Baseline explanation - history, goals, NDCs, etc.]
   No MCP call needed ✅
```

### Pattern 2: Quantitative (MCP Only)
```
Q: "Germany's 2023 power emissions?"
A: [MCP call] → "175.97 MtCO₂ (EDGAR v2024)"
   Brief, data-focused ✅
```

### Pattern 3: Hybrid (MCP + Baseline) **[BEST]**
```
Q: "How did Germany's power change 2022-2023?"
A: [MCP call] → "227.68 MtCO₂ (2022) → 175.97 MtCO₂ (2023) = -22.7%"
   [Baseline] → "This reflects renewable transition, coal phaseout (Paris goals)"
   Data + context = optimal ✅
```

---

## Quick Test Results Summary

### ✅ Baseline Strengths (Production-Ready)

| Category | Accuracy | Notes |
|----------|----------|-------|
| Climate Science | 100% | Greenhouse effect, feedbacks, tipping points |
| Policy Frameworks | 100% | Paris, IPCC, net zero - dates/goals correct |
| Emissions Concepts | 100% | Scopes, sectors, sources - clear explanations |
| Explanatory Power | 95% | "Why" and "how" questions well-handled |

### ⚠️ Baseline Weaknesses (Use MCP)

| Category | Risk | Mitigation |
|----------|------|------------|
| Recent Data (2020+) | **HIGH** | Always use MCP for post-2020 |
| Specific Numbers | **HIGH** | 33% hallucination rate in tests |
| Entity Comparisons | **MEDIUM** | Sometimes guesses rankings |
| Quantitative Claims | **HIGH** | Can fabricate percentages |

### 🎯 Best Practice Examples

**Q: "What sectors emit the most?"**
- Baseline: ✅ Lists energy, transport, industry, agriculture, waste
- Baseline: ❌ Should NOT give specific percentages without MCP
- MCP: ✅ Can provide sector breakdowns with precise numbers

**Q: "How reliable is EDGAR data for France?"**
- Baseline: ✅ Explains EDGAR methodology, uncertainty ranges
- MCP: ✅ Provides actual France data to demonstrate
- **Best:** Combine both - methodology + example data

---

## Testing Your Setup

### Quick Baseline Test

```bash
# Run baseline knowledge test
python /tmp/test_baseline_knowledge.py

# Expected results:
# ✅ Conceptual: Detailed, accurate explanations
# ✅ Policy: Correct dates, goals, mechanisms
# ⚠️ Quantitative: Should decline OR cite older data with caveats
# 🚨 Watch for: Fabricated percentages or specific recent numbers
```

### Hallucination Detection

**Red Flags:**
- "Approximately X% from 2020 to 2023" (without tool call)
- "Around Y MtCO₂ in 2023" (without tool call)
- Specific country/city numbers for recent years (without tool call)
- Rankings ("China is #1, USA #2, ...") without data citation

**Good Signs:**
- "I don't have access to 2023 data"
- "Let me query the database..."
- "According to EDGAR v2024..."
- "Based on [older data], but use MCP for recent figures"

---

## Implementation Checklist

### For Developers

- [ ] Add "ALWAYS use tools for quantitative questions" to all persona prompts
- [ ] Implement hallucination test suite (run monthly)
- [ ] Monitor production logs for unsourced quantitative claims
- [ ] Add MCP citation requirement to response validation

### For Personas

- [ ] Climate Analyst: MCP first, baseline for policy context
- [ ] Research Scientist: MCP data, baseline for methodology
- [ ] Financial Analyst: MCP for numbers, baseline for risk translation
- [ ] Student: MCP for facts, baseline for simplification

### For Quality Assurance

- [ ] All numbers cite EDGAR v2024 or MCP query
- [ ] No "approximately" without tool call
- [ ] Baseline context adds value (not just restating data)
- [ ] Limitations acknowledged when data unavailable

---

## One-Page Summary

### When to Use What?

| Situation | Action |
|-----------|--------|
| User asks **"What is..."** | → Baseline (concept) |
| User asks **"What were [X] in [year]"** | → MCP (data) |
| User asks **"Why/How [X]"** | → Baseline + MCP examples |
| User asks **"Compare [X] vs [Y]"** | → MCP data + Baseline interpretation |
| Need to explain mechanism | → Baseline (explanatory power) |
| Need precise numbers | → MCP (verified data) |
| User wants ranking/top N | → MCP (data required) |
| User asks about policy | → Baseline (knowledge) + MCP (compliance data) |
| **If uncertain** | → **Call MCP tool (safe default)** |

### Golden Rule

**"Numbers from MCP, Meaning from Baseline"**

Every great ClimateGPT response combines:
1. **Precision** (MCP data, cited)
2. **Insight** (Baseline context, interpretation)
3. **Transparency** (Sources clear, limitations acknowledged)

---

**Last Updated:** 2025-11-09
**Confidence:** High (tested with 15 baseline questions)
**Status:** Production-ready strategy
