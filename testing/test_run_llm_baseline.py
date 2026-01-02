"""
Test if run_llm.py is using baseline knowledge to enrich answers
"""
import subprocess
import json
import re

test_cases = [
    {
        "name": "Pure Conceptual (should use baseline)",
        "question": "What is the greenhouse effect?",
        "expect_baseline": True,
        "expect_mcp": False,
        "expect_citations": False
    },
    {
        "name": "Pure Quantitative (should use MCP)",
        "question": "What were Germany's power emissions in 2023?",
        "expect_baseline": False,
        "expect_mcp": True,
        "expect_citations": True
    },
    {
        "name": "Hybrid (should use both)",
        "question": "How did Germany's power emissions change from 2022 to 2023 and what does it mean for climate goals?",
        "expect_baseline": True,
        "expect_mcp": True,
        "expect_citations": True
    }
]

print("\n" + "="*80)
print("TESTING RUN_LLM.PY BASELINE USAGE")
print("="*80)

results_summary = {
    "tests_passed": 0,
    "tests_failed": 0,
    "baseline_findings": [],
    "test_details": []
}

for i, test in enumerate(test_cases, 1):
    print(f"\n[TEST {i}] {test['name']}")
    print(f"Question: {test['question']}")
    print(f"Expected - Baseline: {test['expect_baseline']}, MCP: {test['expect_mcp']}, Citations: {test['expect_citations']}")
    
    try:
        # Run the query through run_llm.py
        result = subprocess.run(
            ['python', 'run_llm.py', test['question']],
            capture_output=True,
            text=True,
            timeout=60,
            cwd='/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT'
        )
        
        output = result.stdout + result.stderr
        
        # Analyze output
        has_tool_call = '"tool"' in output and 'TOOL CALL' in output
        has_mcp_data = 'rows' in output and 'TOOL RESULT' in output
        has_edgar_citation = 'EDGAR' in output or 'EDGAR v2024' in output
        has_baseline_context = any(phrase in output for phrase in [
            'greenhouse', 'climate science', 'policy', 'mechanism', 'understand',
            'means', 'significance', 'decarbonization', 'renewable', 'strategy'
        ])
        
        # Check against expectations
        baseline_check = (has_baseline_context == test['expect_baseline'])
        mcp_check = (has_mcp_data == test['expect_mcp'])
        citation_check = (has_edgar_citation == test['expect_citations']) if test['expect_citations'] else True
        
        test_passed = baseline_check and mcp_check and citation_check
        
        print(f"\nResults:")
        print(f"  Tool Call Present: {has_tool_call}")
        print(f"  MCP Data Present: {has_mcp_data} {'✓' if mcp_check else '✗ EXPECTED: ' + str(test['expect_mcp'])}")
        print(f"  EDGAR Citation: {has_edgar_citation} {'✓' if citation_check else '✗ EXPECTED: ' + str(test['expect_citations'])}")
        print(f"  Baseline Context: {has_baseline_context} {'✓' if baseline_check else '✗ EXPECTED: ' + str(test['expect_baseline'])}")
        
        if test_passed:
            print(f"\n✓ TEST PASSED")
            results_summary["tests_passed"] += 1
        else:
            print(f"\n✗ TEST FAILED")
            results_summary["tests_failed"] += 1
            if not baseline_check:
                results_summary["baseline_findings"].append(f"Test {i}: Baseline context {'missing' if test['expect_baseline'] else 'present when not expected'}")
            if not mcp_check:
                results_summary["baseline_findings"].append(f"Test {i}: MCP data {'missing' if test['expect_mcp'] else 'present when not expected'}")
        
        # Extract answer snippet
        answer_match = re.search(r'=== ANSWER ===(.+?)(?:$|\n\n)', output, re.DOTALL)
        if answer_match:
            answer = answer_match.group(1).strip()[:200]
            results_summary["test_details"].append({
                "test": test['name'],
                "answer_snippet": answer
            })
        
    except subprocess.TimeoutExpired:
        print(f"✗ TEST TIMEOUT")
        results_summary["tests_failed"] += 1
        results_summary["baseline_findings"].append(f"Test {i}: Timeout executing query")
    except Exception as e:
        print(f"✗ TEST ERROR: {str(e)[:100]}")
        results_summary["tests_failed"] += 1
        results_summary["baseline_findings"].append(f"Test {i}: {str(e)[:80]}")

# Summary
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"Tests Passed: {results_summary['tests_passed']}/{len(test_cases)}")
print(f"Tests Failed: {results_summary['tests_failed']}/{len(test_cases)}")

if results_summary["baseline_findings"]:
    print(f"\nFindings:")
    for finding in results_summary["baseline_findings"]:
        print(f"  - {finding}")

# Determine overall status
if results_summary['tests_passed'] == len(test_cases):
    status = "✓ BASELINE KNOWLEDGE INTEGRATION WORKING WELL"
elif results_summary['tests_passed'] >= len(test_cases) // 2:
    status = "⚠ BASELINE KNOWLEDGE PARTIALLY INTEGRATED"
else:
    status = "✗ BASELINE KNOWLEDGE NOT BEING USED EFFECTIVELY"

print(f"\nStatus: {status}")

# Save results
with open("run_llm_baseline_test.txt", "w") as f:
    f.write("="*80 + "\n")
    f.write("RUN_LLM.PY BASELINE KNOWLEDGE USAGE TEST\n")
    f.write("="*80 + "\n\n")
    f.write(f"Tests Passed: {results_summary['tests_passed']}/{len(test_cases)}\n")
    f.write(f"Tests Failed: {results_summary['tests_failed']}/{len(test_cases)}\n\n")
    f.write(f"Status: {status}\n\n")
    f.write("Findings:\n")
    for finding in results_summary["baseline_findings"]:
        f.write(f"  - {finding}\n")
    f.write("\nTest Details:\n")
    f.write(json.dumps(results_summary["test_details"], indent=2))

print(f"\nResults saved to: run_llm_baseline_test.txt")
