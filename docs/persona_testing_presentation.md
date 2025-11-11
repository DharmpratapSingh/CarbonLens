# Slide 1 – Program Context & Goals
- ClimateGPT couples baseline reasoning with MCP-sourced emissions data across four personas (`Climate Analyst`, `Research Scientist`, `Financial Analyst`, `Student`).
- Review scope: demonstrate automated persona testing flow, restate baseline-vs-MCP guardrails, and surface persona outcomes.
- Data foundation: EDGAR v2024 (country/admin1/city × annual/monthly) plus curated baseline policy/science knowledge.
- Test coverage: six question families (`trend_hotspot`, `methodology_review`, `risk_signal`, `foundational_explanation`, `shared_comparison`, `shared_seasonality`) → 12 persona runs per cycle.

---

# Slide 2 – Automated Persona Testing Architecture
- Harness: `testing/run_persona_tests.py` loads `testing/persona_question_bank.json`, health-checks MCP bridge (`wait_for_mcp_server`), and drives each persona through `process_persona_question()` in `climategpt_persona_engine.py`.
- Resiliency features: retries on MCP health, per-persona try/except with rich error payloads, and millisecond timing to monitor latency regressions.
- Output JSON in `testing/test_results/persona_results_YYYYMMDD_HHMMSS.json` logs success flag, response time, tool usage, MCP `file_id`, returned row counts, and trimmed answer previews for audit trails.
- Automation extras: consistent persona ordering (`PERSONA_ORDER`), CLI filters (`--questions`, `--skip-health-check`, `--verbose`), and timestamped artifacts that make diffs between runs trivial.
- Flow overview:

```
┌──────────────┐   ┌─────────────────────┐   ┌────────────────┐   ┌────────────────────┐
| Question Bank|→→ | Persona Engine (LLM)|→→ | MCP HTTP Bridge|→→ | Timestamped Results|
└─────┬────────┘   └─────────┬──────────┘   └──────────┬──────┘   └──────────┬────────┘
      | verbose logs          | tool invocations        | EDGAR query IDs     | JSON for diffing
```

---

# Slide 3 – Baseline Testing Guardrails
- Source: `docs/BASELINE_TESTING_QUICK_REFERENCE.md` (updated 2025-11-09).
- Doctrine: Baseline covers concepts/policy; MCP is mandatory for specific numbers, post-2020 dates, comparisons, rankings, and “top N” requests.
- Decision matrix: “What is...?” → Baseline; “What were X emissions in year Y?” → MCP; “Compare X vs Y” → MCP data + baseline interpretation; if unsure → default to MCP query.
- Mandatory behaviors: cite EDGAR v2024, extract explicit years from prompts, decline approximations without a tool call, and combine MCP figures with baseline explanation for insight.
- QA checklist: verify MCP call ID + citation, ensure “approximately/around” phrasing is absent without data, confirm limitations mentioned when data unavailable, and log any unsourced numeric claims for review.

```
✅ "Let me query the data... China: 932.43 MtCO₂ (2020) → 1,069.75 MtCO₂ (2023) = +14.7%"  (with MCP call)
❌ "China's transport emissions increased ~25% from 2020 to 2023."  (hallucination without data)
```

---

# Slide 4 – Persona Regression Metrics (2025-11-09 Run)
- Overall pass rate improved from 4/12 (33%) to 9/12 (75%) with zero MCP outages or crashes logged by the harness.
- Financial Analyst persona fixed nested `where` clauses (0% → 100%); Tokyo seasonal prompt now reliable across all personas with full 12-row retrievals.
- Baseline guardrail validation: successful answers cite EDGAR v2024, pull explicit year ranges, and blend qualitative context—no hallucinated numbers detected in logs.
- Persistent issue: Q5 (Florida vs Illinois comparison) still fails for three personas due to list-based `where` filters; Financial Analyst run confirms the correct MCP-first pattern.
- ASCII summaries:

```
Overall Success Rate
Before: [####............] 33%
After : [###########.....] 75%

Persona Pass Share
CA 67% → 67%  ████████░░░░  (stable tone)
RS 33% → 67%  ███░ → ████████  ↑ methodology alignment
FA  0% →100%  ░░░ → ████████████  ↑ flat where fix
ST 33% → 67%  ███░ → ████████  ↑ clearer year extraction
```

---

# Slide 5 – Discussion Topics for Review
- Analyze failing personas’ `where` clauses on the Florida vs Illinois prompt versus the Financial Analyst’s successful query to finalize prompt rules.
- Evaluate persona-specific prompt inserts (monthly patterns, flat filters, year extraction) and whether additional worked examples are needed to lock tone + data usage.
- Review response-time dispersion (1.5–9.4s). Confirm tolerance for longer successful queries and consider pre-execution validation for malformed filters.
- Align on monitoring expectations: spotting unsourced numbers in logs, verifying EDGAR citations through response validation, and scheduling combined baseline/persona regression reruns.


