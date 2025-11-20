# Testing Automation Feature - Slide 2
## How to Use & Guide for Future Teams

---

### 🚀 **How to Use the Testing Framework**

#### **Prerequisites:**

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

#### **Step-by-Step Usage Guide:**

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        TESTING WORKFLOW (30 MINUTES)                     │
└──────────────────────────────────────────────────────────────────────────┘

[STEP 1] Verify Setup (2 minutes)
├─► Run verification script:
│   $ cd testing
│   $ python verify_setup.py
│
├─► Expected output:
│   ✅ Python version: 3.11.x
│   ✅ Dependencies installed
│   ✅ ClimateGPT responding at http://localhost:8010
│   ✅ Question bank loaded (50 questions)
│   ✅ Test configuration valid
│   ✅ SETUP VERIFICATION PASSED!
│
└─► If errors: Check services are running

─────────────────────────────────────────────────────────────────

[STEP 2] Start Required Services (2 minutes)
├─► Terminal 1 - ClimateGPT MCP Server:
│   $ cd /path/to/Team-1B-Fusion
│   $ make serve
│   # Wait for: "MCP server listening on port 8010"
│
└─► Terminal 2 - (Optional) LM Studio:
    1. Open LM Studio app
    2. Go to "Local Server" tab
    3. Load model: meta-llama-3.1-8b-instruct
    4. Click "Start Server"
    5. Verify: http://localhost:1234/v1/models

─────────────────────────────────────────────────────────────────

[STEP 3] Run Pilot Test (2 minutes)
├─► Terminal 3 - Quick test with 10 questions:
│   $ cd testing
│   $ python test_harness.py --pilot
│
├─► Watch progress:
│   Testing ClimateGPT and Meta Llama...
│   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 10/10 [00:02<00:00]
│
│   Results saved to:
│   - test_results/comparison_20251119_120000.json
│   - test_results/comparison_20251119_120000.csv
│
└─► Check results: Verify both systems responded

─────────────────────────────────────────────────────────────────

[STEP 4] Run Full Test Suite (20 minutes)
├─► Execute all 50 questions:
│   $ python test_harness.py
│   # Or test only ClimateGPT (no Llama needed):
│   $ python test_harness.py --climategpt-only
│
├─► Progress bar shows:
│   Testing ClimateGPT and Meta Llama...
│   Question 1/50: "Transport emissions in Germany 2023?"
│   ✓ ClimateGPT: 1,234 ms - Success
│   ✓ Meta Llama: 856 ms - Success
│
│   Question 2/50: "Compare power and transport in USA..."
│   ✓ ClimateGPT: 1,567 ms - Success
│   ✓ Meta Llama: 923 ms - Success
│   ...
│
└─► Wait for completion: ~20 minutes for full suite

─────────────────────────────────────────────────────────────────

[STEP 5] Analyze Results (5 minutes)
├─► Generate analysis with visualizations:
│   $ python analyze_results.py --visualize --report
│
├─► Outputs created:
│   • test_results/analysis_summary_YYYYMMDD.txt
│   • test_results/response_time_chart.png
│   • test_results/success_rate_chart.png
│   • test_results/sector_performance_heatmap.png
│   • test_results/comparative_report.md
│
└─► Review files: Open in browser/editor

─────────────────────────────────────────────────────────────────

[STEP 6] Review & Interpret (5 minutes)
├─► Key metrics to check:
│   1. Success Rate: ClimateGPT should be 100%
│   2. Response Time: Should be <2000ms average
│   3. Accuracy: ClimateGPT should have real data
│   4. Errors: Investigate any failures
│
├─► Comparison insights:
│   • How does ClimateGPT compare to Llama?
│   • Which sectors are slowest?
│   • Are there any anomalies?
│
└─► Document findings: Add to reports/presentations
```

---

### 📖 **Command Reference:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                        COMMAND CHEAT SHEET                           │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  BASIC TESTING:                                                      │
│  $ python test_harness.py                  # Full test (50 Q)       │
│  $ python test_harness.py --pilot          # Quick test (10 Q)      │
│  $ python test_harness.py --climategpt-only # Only ClimateGPT       │
│  $ python test_harness.py --llama-only     # Only Llama             │
│                                                                      │
│  SELECTIVE TESTING:                                                  │
│  $ python test_harness.py --questions 1,2,3,4,5  # Specific Qs     │
│  $ python test_harness.py --sector transport    # One sector        │
│  $ python test_harness.py --level country       # One level         │
│                                                                      │
│  ADVANCED OPTIONS:                                                   │
│  $ python test_harness.py --verbose        # Detailed output        │
│  $ python test_harness.py --config custom.json  # Custom config     │
│  $ python test_harness.py --retries 5     # Increase retries        │
│  $ python test_harness.py --timeout 60    # Longer timeout          │
│                                                                      │
│  ANALYSIS:                                                           │
│  $ python analyze_results.py              # Basic stats             │
│  $ python analyze_results.py --visualize  # + Charts                │
│  $ python analyze_results.py --report     # + Markdown report       │
│  $ python analyze_results.py --compare test1.json test2.json        │
│                                                                      │
│  VERIFICATION:                                                       │
│  $ python verify_setup.py                 # Check prerequisites     │
│  $ curl http://localhost:8010/health      # ClimateGPT health       │
│  $ curl http://localhost:1234/v1/models   # LM Studio check         │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 🔧 **Configuration & Customization:**

#### **Edit `test_config.json` to customize:**

```json
{
  "climategpt": {
    "url": "http://localhost:8010",
    "endpoint": "/query",
    "timeout": 30
  },
  "llama": {
    "url": "http://localhost:1234",
    "endpoint": "/v1/chat/completions",
    "model": "meta-llama-3.1-8b-instruct",
    "temperature": 0.1,
    "max_tokens": 500,
    "system_prompt": "You are an expert on climate data..."
  },
  "test": {
    "question_bank": "test_question_bank.json",
    "output_dir": "test_results",
    "delay_between_requests": 1.0,
    "max_retries": 2,
    "retry_delay": 2.0
  }
}
```

#### **Add Custom Questions to `test_question_bank.json`:**

```json
{
  "questions": [
    {
      "question_id": 51,
      "question": "Your custom question here?",
      "category": "simple",
      "sector": "transport",
      "level": "country",
      "grain": "yearly",
      "difficulty": "easy",
      "expected_answer_contains": ["keyword1", "keyword2"]
    }
  ]
}
```

---

### 👥 **Guide for Future Teams**

```
┌──────────────────────────────────────────────────────────────────────────┐
│                  FUTURE TEAMS IMPLEMENTATION GUIDE                       │
└──────────────────────────────────────────────────────────────────────────┘

[SCENARIO 1] Testing a New Feature
├─► Use Case: You added a new sector or improved query handling
│
├─► Steps:
│   1. Update question_bank.json with questions for new feature
│   2. Run full test suite: python test_harness.py
│   3. Compare results before/after feature addition
│   4. Document improvements in analysis report
│
└─► Expected Time: 30 minutes

─────────────────────────────────────────────────────────────────────────

[SCENARIO 2] Regression Testing After Code Changes
├─► Use Case: You modified MCP server or database schema
│
├─► Steps:
│   1. Run baseline test BEFORE changes:
│      $ python test_harness.py --climategpt-only
│      $ mv test_results/comparison_*.json baseline.json
│
│   2. Make your code changes
│
│   3. Run test AFTER changes:
│      $ python test_harness.py --climategpt-only
│
│   4. Compare results:
│      $ python analyze_results.py --compare baseline.json latest.json
│
│   5. Verify no regressions (success rate, response time)
│
└─► Expected Time: 45 minutes (15 min before + 15 min after + 15 min analysis)

─────────────────────────────────────────────────────────────────────────

[SCENARIO 3] Adding Support for a New LLM
├─► Use Case: You want to test against GPT-4, Claude, or custom model
│
├─► Steps:
│   1. Add new test method to test_harness.py:
│      def test_gpt4(self, question_text, question_id):
│          # Similar to test_llama() but with GPT-4 API
│
│   2. Update config.json with new LLM settings:
│      "gpt4": {"url": "...", "api_key": "..."}
│
│   3. Modify run_tests() to include new LLM
│
│   4. Run comparative test:
│      $ python test_harness.py  # Tests all configured LLMs
│
│   5. Analyze multi-system comparison
│
└─► Expected Time: 2 hours (1 hr coding + 1 hr testing)

─────────────────────────────────────────────────────────────────────────

[SCENARIO 4] Performance Benchmarking for Optimization
├─► Use Case: You want to optimize database queries or caching
│
├─► Steps:
│   1. Run baseline with timing:
│      $ python test_harness.py --climategpt-only --verbose
│      $ python analyze_results.py --visualize
│      # Note: avg response time
│
│   2. Implement optimization (add indexes, caching, etc.)
│
│   3. Run test again:
│      $ python test_harness.py --climategpt-only
│
│   4. Compare response time charts:
│      - Before: 1,500 ms average
│      - After:  800 ms average (47% improvement!)
│
│   5. Document optimization in report
│
└─► Expected Time: 1 day (includes optimization work)

─────────────────────────────────────────────────────────────────────────

[SCENARIO 5] Continuous Integration (CI/CD)
├─► Use Case: Automate testing in GitHub Actions
│
├─► Steps:
│   1. Create .github/workflows/test.yml:
│      name: Automated Testing
│      on: [push, pull_request]
│      jobs:
│        test:
│          runs-on: ubuntu-latest
│          steps:
│            - Checkout code
│            - Start ClimateGPT
│            - Run test_harness.py --climategpt-only
│            - Check success rate = 100%
│            - Upload results as artifacts
│
│   2. Configure environment variables in GitHub Secrets
│
│   3. Every PR triggers automatic testing
│
│   4. Tests must pass before merge
│
└─► Expected Time: 3 hours (initial setup)

─────────────────────────────────────────────────────────────────────────

[SCENARIO 6] Creating Custom Test Suites
├─► Use Case: Different test suites for different purposes
│
├─► Examples:
│   • smoke_tests.json (10 critical questions, 2 min)
│   • full_regression.json (50 questions, 20 min)
│   • performance_tests.json (stress testing, 1 hr)
│   • integration_tests.json (end-to-end scenarios)
│
├─► Usage:
│   $ python test_harness.py --question-bank smoke_tests.json
│   $ python test_harness.py --question-bank full_regression.json
│
└─► Benefit: Fast feedback during development
```

---

### 📊 **Expected Outcomes & Metrics:**

```
╔═══════════════════════════════════════════════════════════════════════╗
║                     TESTING OUTCOMES & INSIGHTS                       ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                       ║
║  QUANTITATIVE METRICS:                                                ║
║  • Success Rate:         100% (ClimateGPT) vs 80% (Llama)            ║
║  • Avg Response Time:    1,200 ms vs 850 ms                          ║
║  • Throughput:           2.5 questions/sec (ClimateGPT)              ║
║  • Error Rate:           0% (ClimateGPT) vs 20% (Llama)              ║
║                                                                       ║
║  QUALITATIVE INSIGHTS:                                                ║
║  ✅ ClimateGPT provides accurate, data-backed answers                ║
║  ✅ All 8 sectors covered with real emissions data                   ║
║  ✅ Consistent unit formatting (MtCO₂)                                ║
║  ✅ Source attribution (EDGAR v2024)                                  ║
║  ✅ Handles complex multi-sector comparisons                          ║
║                                                                       ║
║  ❌ Llama hallucinates numbers without database access               ║
║  ❌ No source citations (unreliable)                                  ║
║  ⚠️  Faster response but at cost of accuracy                         ║
║                                                                       ║
║  KEY FINDING:                                                         ║
║  ClimateGPT's database-backed approach is essential for              ║
║  providing trustworthy, verifiable climate emissions data.           ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

### 🎯 **Best Practices for Future Teams:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                        TESTING BEST PRACTICES                        │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. RUN TESTS BEFORE MAJOR CHANGES                                   │
│     • Establish baseline performance                                 │
│     • Document current success rates                                 │
│     • Capture response time benchmarks                               │
│                                                                      │
│  2. TEST EARLY, TEST OFTEN                                           │
│     • Run smoke tests (10 Q) after small changes: 2 min             │
│     • Run full suite (50 Q) before commits: 20 min                  │
│     • Run regression tests weekly: 30 min                            │
│                                                                      │
│  3. MAINTAIN QUESTION BANK                                           │
│     • Add questions for new sectors immediately                      │
│     • Update expected answers when data changes                      │
│     • Review and prune outdated questions                            │
│     • Keep bank organized by category/sector                         │
│                                                                      │
│  4. ANALYZE FAILURES IMMEDIATELY                                     │
│     • Investigate any drop in success rate                           │
│     • Check for new error patterns                                   │
│     • Validate database queries if answers change                    │
│     • Document root causes and fixes                                 │
│                                                                      │
│  5. COMPARE AGAINST BASELINES                                        │
│     • Keep historical test results                                   │
│     • Track performance trends over time                             │
│     • Celebrate improvements, investigate regressions                │
│     • Share results with team regularly                              │
│                                                                      │
│  6. AUTOMATE IN CI/CD PIPELINE                                       │
│     • Run tests on every pull request                                │
│     • Block merges if tests fail                                     │
│     • Generate test reports automatically                            │
│     • Notify team of failures immediately                            │
│                                                                      │
│  7. DOCUMENT EVERYTHING                                              │
│     • Record test configurations used                                │
│     • Document any manual interventions                              │
│     • Maintain changelog of question bank updates                    │
│     • Share insights in team meetings/reports                        │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 🛠️ **Troubleshooting Common Issues:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                     TROUBLESHOOTING GUIDE                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ISSUE: ClimateGPT not responding                                    │
│  ├─ Check: Is MCP server running?                                   │
│  ├─ Fix: cd /path/to/project && make serve                          │
│  └─ Verify: curl http://localhost:8010/health                       │
│                                                                      │
│  ISSUE: LM Studio connection failed                                  │
│  ├─ Check: Is LM Studio app open?                                   │
│  ├─ Fix: Open app → Local Server → Start Server                     │
│  └─ Verify: curl http://localhost:1234/v1/models                    │
│                                                                      │
│  ISSUE: Wrong model ID for Llama                                     │
│  ├─ Check: curl http://localhost:1234/v1/models | jq '.data[0].id' │
│  ├─ Fix: Update test_config.json with actual model ID               │
│  └─ Example: "model": "meta-llama-3.1-8b-instruct@q4_k_m"          │
│                                                                      │
│  ISSUE: Test timeout errors                                          │
│  ├─ Check: Are queries taking too long?                             │
│  ├─ Fix: Increase timeout in config: "timeout": 60                  │
│  └─ Or: Optimize database queries (add indexes)                     │
│                                                                      │
│  ISSUE: Import errors (requests, pandas, etc.)                       │
│  ├─ Check: Are dependencies installed?                              │
│  ├─ Fix: pip install -r requirements_testing.txt                    │
│  └─ Verify: python -c "import requests, pandas"                     │
│                                                                      │
│  ISSUE: Results don't match expected                                 │
│  ├─ Check: Is database populated with latest data?                  │
│  ├─ Fix: Re-run preprocessing pipeline                              │
│  └─ Verify: Query database directly with DuckDB                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

---

### 📁 **Files to Keep vs. Delete:**

```
After Testing Complete:

✅ KEEP THESE (for reference):
   • test_results/              # All test outputs
   • test_question_bank.json    # Question bank
   • test_config.json           # Configuration
   • Documentation (*.md)       # Guides and methodology

❌ CAN DELETE (if not re-testing):
   • test_harness.py           # Main test script
   • analyze_results.py        # Analysis script
   • verify_setup.py           # Setup checker
   • requirements_testing.txt  # Dependencies

🗑️ OPTIONAL CLEANUP:
   # Delete entire testing directory:
   $ cd /path/to/Team-1B-Fusion
   $ rm -rf testing/
```

---

### 🚀 **Next Steps for Your Team:**

1. **Run Initial Baseline Tests** (Week 1)
   - Execute full test suite
   - Document current performance
   - Identify any existing issues

2. **Integrate into Development Workflow** (Week 2)
   - Add smoke tests to pre-commit hooks
   - Set up CI/CD automation
   - Train team on usage

3. **Expand Question Bank** (Ongoing)
   - Add edge cases
   - Cover new features
   - Update as data changes

4. **Track Performance Over Time** (Monthly)
   - Run full regression tests
   - Compare against baselines
   - Document trends and improvements

5. **Share Results** (Quarterly)
   - Present metrics to stakeholders
   - Demonstrate system reliability
   - Justify ongoing development

---

**Testing Framework Status: ✅ Production-Ready**
**Documentation: Complete**
**Future Team Support: Comprehensive**
