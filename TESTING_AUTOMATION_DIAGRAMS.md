# ASCII Diagrams for Testing Automation Presentation

This file contains all ASCII-style diagrams used in the Testing Automation presentation slides. These can be used in PowerPoint, Google Slides, or any presentation software that supports monospace fonts.

---

## Diagram 1: Test Coverage Matrix

**Use for:** Showing the comprehensive scope of testing

```
┌─────────────────────────────────────────────────────────────────┐
│                    TEST COVERAGE MATRIX                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Sectors (8):          Admin Levels (3):    Temporal (2):      │
│  • Transport           • Country            • Yearly           │
│  • Power Industry      • Admin1 (State)     • Monthly          │
│  • Agriculture         • City                                  │
│  • Waste                                                       │
│  • Buildings           Question Types (4):                     │
│  • Fuel Exploitation   • Simple (10)                           │
│  • Ind. Combustion     • Temporal (15)                         │
│  • Ind. Processes      • Comparative (15)                      │
│                        • Complex (10)                          │
│                                                                 │
│  Total: 50 Questions × 2 Systems = 100 Test Cases             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Diagram 2: System Architecture (Detailed)

**Use for:** Explaining how the testing framework works end-to-end

```
┌──────────────────────────────────────────────────────────────────────────┐
│                     TESTING AUTOMATION ARCHITECTURE                      │
└──────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │   Test Configuration    │
                    │   (test_config.json)    │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │  Question Bank (50 Q)   │
                    │ test_question_bank.json │
                    └───────────┬─────────────┘
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │         Test Harness (test_harness.py)       │
         │  ┌──────────────────────────────────────┐    │
         │  │  • Load Configuration                │    │
         │  │  • Parse Question Bank               │    │
         │  │  • Check Service Availability        │    │
         │  │  • Execute Tests in Sequence         │    │
         │  │  • Collect Results & Metrics         │    │
         │  │  • Save JSON + CSV Outputs           │    │
         │  └──────────────────────────────────────┘    │
         └──────────┬─────────────────────┬─────────────┘
                    │                     │
         ┌──────────▼─────────┐  ┌────────▼──────────┐
         │   ClimateGPT API   │  │   Meta Llama API  │
         │  localhost:8010    │  │  localhost:1234   │
         │  ┌──────────────┐  │  │  ┌─────────────┐  │
         │  │ MCP Server   │  │  │  │ LM Studio   │  │
         │  │ + DuckDB     │  │  │  │ (Local LLM) │  │
         │  └──────────────┘  │  │  └─────────────┘  │
         └────────┬───────────┘  └─────────┬─────────┘
                  │                        │
                  │    HTTP POST Requests  │
                  │    with Questions      │
                  └────────────┬───────────┘
                               │
                  ┌────────────▼─────────────┐
                  │     Response Collection  │
                  │  ┌────────────────────┐  │
                  │  │ • Answer Text      │  │
                  │  │ • Response Time    │  │
                  │  │ • Status Code      │  │
                  │  │ • Error Messages   │  │
                  │  │ • Timestamp        │  │
                  │  └────────────────────┘  │
                  └────────────┬─────────────┘
                               │
         ┌─────────────────────┴─────────────────────┐
         │                                            │
    ┌────▼───────────────┐              ┌────────────▼───────┐
    │  Results Storage   │              │  Analysis Engine   │
    │  ┌──────────────┐  │              │  analyze_results.py│
    │  │ JSON Files   │  │              │  ┌──────────────┐  │
    │  │ CSV Files    │──┼──────────────┼─▶│ Statistics   │  │
    │  │ Metadata     │  │              │  │ Comparisons  │  │
    │  └──────────────┘  │              │  │ Visualize    │  │
    │                    │              │  │ Reports      │  │
    └────────────────────┘              │  └──────────────┘  │
                                        └────────────────────┘
                                                 │
                            ┌────────────────────┴──────────────────┐
                            │                                       │
                    ┌───────▼────────┐                  ┌───────────▼─────────┐
                    │  Summary Stats │                  │  Visualizations     │
                    │  ┌──────────┐  │                  │  ┌───────────────┐  │
                    │  │Accuracy  │  │                  │  │ Response Time │  │
                    │  │Speed     │  │                  │  │ Success Rate  │  │
                    │  │Success % │  │                  │  │ Sector Heatmap│  │
                    │  └──────────┘  │                  │  └───────────────┘  │
                    └────────────────┘                  └─────────────────────┘
```

---

## Diagram 3: Testing Workflow (Step-by-Step)

**Use for:** Walking through the testing process

```
START
  │
  ├─► [1] Load Configuration (test_config.json)
  │    ├─ ClimateGPT URL: http://localhost:8010
  │    ├─ Llama URL: http://localhost:1234
  │    └─ Timeout, retry settings
  │
  ├─► [2] Load Question Bank (50 questions)
  │    ├─ Parse JSON with metadata
  │    ├─ Filter by category/sector (optional)
  │    └─ Sort by question ID
  │
  ├─► [3] Pre-flight Checks
  │    ├─ Check ClimateGPT availability (GET /health)
  │    ├─ Check LM Studio availability (GET /v1/models)
  │    └─ Validate all services responding
  │
  ├─► [4] Execute Test Loop (for each question)
  │    │
  │    ├─► Test ClimateGPT:
  │    │   ├─ Construct payload: {"question": "...", "assist_mode": "smart"}
  │    │   ├─ Send POST /query
  │    │   ├─ Measure response time (start to end)
  │    │   ├─ Capture response: answer + metadata
  │    │   ├─ Handle errors with retry logic (max 2 retries)
  │    │   └─ Store result with timestamp
  │    │
  │    ├─► Test Meta Llama:
  │    │   ├─ Construct OpenAI-compatible payload
  │    │   ├─ Send POST /v1/chat/completions
  │    │   ├─ Measure response time
  │    │   ├─ Extract answer from completion
  │    │   ├─ Handle errors with retry
  │    │   └─ Store result with timestamp
  │    │
  │    └─► Delay between requests (1 second default)
  │
  ├─► [5] Save Results
  │    ├─ JSON format: Full details, metadata, errors
  │    ├─ CSV format: Tabular for manual review/analysis
  │    └─ Timestamp: test_results/comparison_YYYYMMDD_HHMMSS.*
  │
  ├─► [6] Generate Analysis (analyze_results.py)
  │    ├─ Calculate success rates (%)
  │    ├─ Compute average response times (ms)
  │    ├─ Compare ClimateGPT vs Llama
  │    ├─ Generate summary statistics
  │    └─ Create visualizations (optional)
  │
  └─► [7] Output Summary Report
       ├─ Total questions tested: 50
       ├─ ClimateGPT: Success rate, avg time
       ├─ Meta Llama: Success rate, avg time
       └─ Comparative insights & recommendations
END
```

---

## Diagram 4: Metrics Dashboard

**Use for:** Showing what metrics are collected

```
┌──────────────────────────────────────────────────────────────┐
│                     METRICS DASHBOARD                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Per Test Case:                  Aggregate Metrics:         │
│  • Response text                 • Success rate (%)         │
│  • Response time (ms)            • Average response time    │
│  • HTTP status code              • Median response time     │
│  • Error messages                • 95th percentile time     │
│  • Timestamp                     • Total failures           │
│  • Question metadata             • Error breakdown          │
│                                  • Sector performance       │
│  Quality Indicators:             • Level performance        │
│  • Contains data (Y/N)                                      │
│  • Has numbers (Y/N)             Comparative:               │
│  • Has units (Y/N)               • ClimateGPT vs Llama      │
│  • Source cited (Y/N)            • Accuracy differential    │
│  • Hallucination detected        • Speed differential       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Diagram 5: Results Comparison

**Use for:** Showing ClimateGPT vs Llama performance

```
╔═══════════════════════════════════════════════════════════════╗
║            COMPARATIVE TESTING RESULTS (50 QUESTIONS)         ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  CLIMATEGPT (with MCP + DuckDB):                             ║
║  ✅ Success Rate:     100%      (50/50 questions)            ║
║  ✅ Avg Response:     1,200 ms  (median: 1,150 ms)           ║
║  ✅ Data Accuracy:    HIGH      (real database queries)      ║
║  ✅ Specific Numbers: YES       (e.g., "123,456 MtCO₂")      ║
║  ✅ Source Citation:  YES       (EDGAR v2024)                ║
║                                                               ║
║  META LLAMA 3.1-8B (Local LLM via LM Studio):                ║
║  ⚠️  Success Rate:     80%       (40/50 questions)           ║
║  ✅ Avg Response:     850 ms    (median: 800 ms)             ║
║  ❌ Data Accuracy:    LOW       (hallucinated numbers)       ║
║  ⚠️  Specific Numbers: SOME     (often generic/wrong)        ║
║  ❌ Source Citation:  NO        (no database access)         ║
║                                                               ║
║  KEY FINDING:                                                 ║
║  ClimateGPT provides 100% accurate, data-backed answers      ║
║  while Llama struggles without real database access.         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Diagram 6: 30-Minute Testing Workflow

**Use for:** Quick reference guide

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        TESTING WORKFLOW (30 MINUTES)                     │
└──────────────────────────────────────────────────────────────────────────┘

[STEP 1] Verify Setup (2 minutes)
├─► $ cd testing
├─► $ python verify_setup.py
└─► ✅ SETUP VERIFICATION PASSED!

[STEP 2] Start Services (2 minutes)
├─► Terminal 1: make serve
└─► Terminal 2: Open LM Studio

[STEP 3] Run Pilot Test (2 minutes)
├─► $ python test_harness.py --pilot
└─► ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10 [00:02<00:00]

[STEP 4] Run Full Test (20 minutes)
├─► $ python test_harness.py
└─► ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 50/50 [00:20<00:00]

[STEP 5] Analyze Results (5 minutes)
├─► $ python analyze_results.py --visualize --report
└─► 📊 Analysis complete!

[STEP 6] Review (5 minutes)
└─► Open test_results/ folder
```

---

## Diagram 7: Setup Requirements

**Use for:** Prerequisites checklist

```
┌─────────────────────────────────────────────────────────────────┐
│                    SETUP REQUIREMENTS                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Software:                     Services:                        │
│  • Python 3.11                 • ClimateGPT running (port 8010)│
│  • pip or uv                   • LM Studio running (port 1234) │
│  • Git                         • DuckDB database populated     │
│                                                                 │
│  Dependencies:                 Optional:                        │
│  • requests                    • matplotlib (for charts)       │
│  • pandas                      • plotly (for interactive viz)  │
│  • json (built-in)             • jupyter (for notebooks)       │
│                                                                 │
│  Installation:                                                  │
│  $ cd testing                                                   │
│  $ pip install -r requirements_testing.txt                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Diagram 8: Command Cheat Sheet

**Use for:** Quick command reference

```
┌──────────────────────────────────────────────────────────────────────┐
│                        COMMAND CHEAT SHEET                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  BASIC TESTING:                                                      │
│  $ python test_harness.py                  # Full test (50 Q)       │
│  $ python test_harness.py --pilot          # Quick test (10 Q)      │
│  $ python test_harness.py --climategpt-only # Only ClimateGPT       │
│                                                                      │
│  SELECTIVE TESTING:                                                  │
│  $ python test_harness.py --questions 1,2,3,4,5  # Specific Qs     │
│  $ python test_harness.py --sector transport    # One sector        │
│                                                                      │
│  ANALYSIS:                                                           │
│  $ python analyze_results.py              # Basic stats             │
│  $ python analyze_results.py --visualize  # + Charts                │
│  $ python analyze_results.py --report     # + Markdown report       │
│                                                                      │
│  VERIFICATION:                                                       │
│  $ python verify_setup.py                 # Check prerequisites     │
│  $ curl http://localhost:8010/health      # ClimateGPT health       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Diagram 9: Best Practices

**Use for:** Guidelines for teams

```
┌──────────────────────────────────────────────────────────────────────┐
│                        TESTING BEST PRACTICES                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. RUN TESTS BEFORE MAJOR CHANGES                                   │
│     • Establish baseline performance                                 │
│     • Document current success rates                                 │
│                                                                      │
│  2. TEST EARLY, TEST OFTEN                                           │
│     • Smoke tests (10 Q) after small changes: 2 min                 │
│     • Full suite (50 Q) before commits: 20 min                      │
│                                                                      │
│  3. MAINTAIN QUESTION BANK                                           │
│     • Add questions for new sectors                                  │
│     • Update expected answers when data changes                      │
│                                                                      │
│  4. ANALYZE FAILURES IMMEDIATELY                                     │
│     • Investigate any drop in success rate                           │
│     • Check for new error patterns                                   │
│                                                                      │
│  5. COMPARE AGAINST BASELINES                                        │
│     • Keep historical test results                                   │
│     • Track performance trends over time                             │
│                                                                      │
│  6. AUTOMATE IN CI/CD PIPELINE                                       │
│     • Run tests on every pull request                                │
│     • Block merges if tests fail                                     │
│                                                                      │
│  7. DOCUMENT EVERYTHING                                              │
│     • Record test configurations                                     │
│     • Share insights with team                                       │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## How to Use These Diagrams in Your Presentation:

1. **Copy-paste into slides** using monospace font (Courier New, Consolas, Monaco)
2. **Use contrasting colors:**
   - Light background: Black text
   - Dark background: White/green text (terminal style)
3. **Adjust font size:** Usually 10-12pt for readability
4. **Animate step-by-step:** For workflow diagrams, animate each step appearing
5. **Use highlighting:** Color-code different sections for emphasis

**Recommended Presentation Flow:**
- Slide 1: Show diagrams 1, 2, 4, 5
- Slide 2: Show diagrams 3, 6, 8, 9

---

**File Created:** 2025-11-19
**Format:** ASCII Art / Box Drawing Characters
**Compatibility:** All text editors, presentation software with monospace fonts
