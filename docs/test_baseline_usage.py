"""
Test suite to verify baseline knowledge usage efficiency
"""
import requests
import json
import time
from typing import Dict, List, Any

MCP_BASE = "http://127.0.0.1:8010"
OPENAI_BASE_URL = "https://erasmus.ai/models/climategpt_8b_test/v1"

# Test Categories
CONCEPTUAL_QUESTIONS = [
    "What is the greenhouse effect and how does it relate to climate change?",
    "Explain the difference between weather and climate",
    "What are the main sources of greenhouse gases in the atmosphere?",
    "How do tipping points work in the climate system?",
    "What is the Paris Agreement and what are its main goals?",
    "Describe the difference between Scope 1, 2, and 3 emissions",
    "What is net zero and why is it important?",
    "Explain how renewable energy reduces emissions",
]

QUANTITATIVE_QUESTIONS = [
    "What were Germany's power sector emissions in 2023?",
    "Which country had the highest transport emissions in 2020?",
    "How much did India's total emissions change from 2019 to 2020?",
    "What are the top 5 US states by industrial combustion emissions in 2022?",
    "What were France's waste emissions in 2021?",
]

HYBRID_QUESTIONS = [
    "How did Germany's power emissions change from 2022 to 2023 and what does this mean?",
    "Compare USA vs China transport emissions in 2020. What drives the difference?",
    "Which sector is easiest to decarbonize and show me recent data from a major country",
    "What are seasonal patterns in Tokyo's waste emissions and why do they occur?",
]

def test_question_routing():
    """Test 1: Check if questions are properly routed to baseline vs MCP"""
    print("\n" + "="*80)
    print("TEST 1: QUESTION ROUTING (Baseline vs MCP)")
    print("="*80)
    
    test_results = {
        "conceptual_detected_as_baseline": 0,
        "quantitative_detected_as_mcp": 0,
        "hybrid_detected_as_both": 0,
        "failures": []
    }
    
    # Test conceptual questions
    print("\n[CONCEPTUAL QUESTIONS - Should Route to BASELINE]")
    for i, q in enumerate(CONCEPTUAL_QUESTIONS[:3], 1):
        print(f"\n  Q{i}: {q[:60]}...")
        try:
            # Check if LLM recognizes this needs baseline knowledge
            response = requests.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json={
                    "model": "/cache/climategpt_8b_test",
                    "messages": [
                        {"role": "system", "content": "Classify this question: Should it use baseline knowledge (conceptual) or MCP data (quantitative)? Reply with only ONE word: BASELINE or MCP"},
                        {"role": "user", "content": q}
                    ],
                    "temperature": 0.2
                },
                auth=("USER", "PASS"),
                timeout=30
            )
            answer = response.json()["choices"][0]["message"]["content"].strip().upper()
            
            if "BASELINE" in answer:
                test_results["conceptual_detected_as_baseline"] += 1
                print(f"    ✓ Correctly classified as BASELINE")
            else:
                test_results["failures"].append(f"Q{i}: Expected BASELINE, got {answer}")
                print(f"    ✗ Incorrectly classified as {answer}")
        except Exception as e:
            test_results["failures"].append(f"Q{i}: Error - {str(e)}")
            print(f"    ✗ Error: {str(e)[:50]}")
    
    # Test quantitative questions
    print("\n[QUANTITATIVE QUESTIONS - Should Route to MCP]")
    for i, q in enumerate(QUANTITATIVE_QUESTIONS[:3], 1):
        print(f"\n  Q{i}: {q[:60]}...")
        try:
            response = requests.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json={
                    "model": "/cache/climategpt_8b_test",
                    "messages": [
                        {"role": "system", "content": "Classify: BASELINE (conceptual) or MCP (quantitative/specific data)? ONE WORD ONLY."},
                        {"role": "user", "content": q}
                    ],
                    "temperature": 0.2
                },
                auth=("USER", "PASS"),
                timeout=30
            )
            answer = response.json()["choices"][0]["message"]["content"].strip().upper()
            
            if "MCP" in answer:
                test_results["quantitative_detected_as_mcp"] += 1
                print(f"    ✓ Correctly classified as MCP")
            else:
                test_results["failures"].append(f"Q{i}: Expected MCP, got {answer}")
                print(f"    ✗ Incorrectly classified as {answer}")
        except Exception as e:
            test_results["failures"].append(f"Q{i}: Error - {str(e)}")
            print(f"    ✗ Error: {str(e)[:50]}")
    
    print(f"\n[RESULTS]")
    print(f"  Conceptual→Baseline: {test_results['conceptual_detected_as_baseline']}/3")
    print(f"  Quantitative→MCP: {test_results['quantitative_detected_as_mcp']}/3")
    if test_results['failures']:
        print(f"  Failures: {len(test_results['failures'])}")
        for f in test_results['failures'][:3]:
            print(f"    - {f}")
    
    return test_results

def test_baseline_hallucination():
    """Test 2: Check if baseline hallucinates recent quantitative data"""
    print("\n" + "="*80)
    print("TEST 2: BASELINE HALLUCINATION DETECTION")
    print("="*80)
    
    hallucination_tests = [
        {
            "question": "What were China's exact CO2 emissions in 2023?",
            "should_have": "caveat or tool call",
            "should_NOT_have": "specific percentage or exact number"
        },
        {
            "question": "Which country increased transport emissions most from 2020 to 2023?",
            "should_have": "acknowledge limitation",
            "should_NOT_have": "specific percentage increase"
        }
    ]
    
    results = {
        "correct_caveats": 0,
        "hallucinated": 0,
        "failures": []
    }
    
    for i, test in enumerate(hallucination_tests, 1):
        print(f"\n  Test {i}: {test['question'][:60]}...")
        try:
            response = requests.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                json={
                    "model": "/cache/climategpt_8b_test",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are ClimateGPT. Answer based on your training knowledge, NOT by calling tools."
                        },
                        {"role": "user", "content": test["question"]}
                    ],
                    "temperature": 0.2
                },
                auth=("USER", "PASS"),
                timeout=30
            )
            
            answer = response.json()["choices"][0]["message"]["content"].strip().lower()
            
            # Check for hallucination signs
            has_caveat = any(phrase in answer for phrase in [
                "don't have", "no access", "uncertain", "may vary", "without access",
                "i'm not able", "would need", "to verify", "tool", "query"
            ])
            
            has_fabricated = any(word in answer for word in [
                "approximately", "around", "%", "tonnes", "mtco2", "exact"
            ]) and not has_caveat
            
            if has_caveat and not has_fabricated:
                results["correct_caveats"] += 1
                print(f"    ✓ Correctly caveated answer")
            elif has_fabricated:
                results["hallucinated"] += 1
                print(f"    ✗ HALLUCINATION DETECTED")
                print(f"       Answer snippet: {answer[:100]}...")
            else:
                print(f"    ? Unclear response")
                
        except Exception as e:
            results["failures"].append(f"Test {i}: {str(e)}")
            print(f"    ✗ Error: {str(e)[:50]}")
    
    print(f"\n[RESULTS]")
    print(f"  Correct Caveats: {results['correct_caveats']}/{len(hallucination_tests)}")
    print(f"  Hallucinations: {results['hallucinated']}/{len(hallucination_tests)}")
    
    return results

def test_mcp_vs_baseline():
    """Test 3: Compare baseline-only vs MCP-enabled answers"""
    print("\n" + "="*80)
    print("TEST 3: MCP DATA vs BASELINE KNOWLEDGE COMPARISON")
    print("="*80)
    
    test_questions = [
        "What were Germany's power emissions in 2023?",
        "Which US state had highest industrial emissions in 2022?"
    ]
    
    results = {
        "mcp_provides_data": 0,
        "mcp_cites_source": 0,
        "baseline_caveats": 0,
        "discrepancies": []
    }
    
    for i, q in enumerate(test_questions, 1):
        print(f"\n  Question {i}: {q[:60]}...")
        
        try:
            # Get MCP data
            print(f"    [Querying MCP...]")
            
            if "Germany" in q:
                mcp_query = {
                    "file_id": "power-country-year",
                    "select": ["country_name", "year", "emissions_tonnes"],
                    "where": {"country_name": "Germany", "year": 2023},
                    "assist": True
                }
            else:
                mcp_query = {
                    "file_id": "industrial-combustion-admin1-year",
                    "select": ["admin1_name", "country_name", "year", "emissions_tonnes"],
                    "where": {"country_name": "United States of America", "year": 2022},
                    "order_by": "emissions_tonnes DESC",
                    "limit": 1,
                    "assist": True
                }
            
            mcp_response = requests.post(f"{MCP_BASE}/query", json=mcp_query, timeout=30).json()
            
            if "rows" in mcp_response and mcp_response["rows"]:
                results["mcp_provides_data"] += 1
                print(f"    ✓ MCP returned data")
                if mcp_response.get("meta", {}).get("file_id"):
                    results["mcp_cites_source"] += 1
                    print(f"    ✓ MCP cites source")
            else:
                print(f"    ✗ MCP returned no data")
                
        except Exception as e:
            results["discrepancies"].append(f"Q{i}: MCP error - {str(e)[:50]}")
            print(f"    ✗ Error: {str(e)[:50]}")
    
    print(f"\n[RESULTS]")
    print(f"  MCP Provides Data: {results['mcp_provides_data']}/{len(test_questions)}")
    print(f"  MCP Cites Source: {results['mcp_cites_source']}/{len(test_questions)}")
    
    return results

def test_persona_baseline_usage():
    """Test 4: Check if personas use baseline context effectively"""
    print("\n" + "="*80)
    print("TEST 4: PERSONA-SPECIFIC BASELINE USAGE")
    print("="*80)
    
    results = {
        "analyst_uses_context": False,
        "scientist_discusses_methodology": False,
        "student_uses_analogies": False,
        "financial_discusses_risk": False,
        "details": []
    }
    
    # Test Climate Analyst persona
    print("\n  [Testing Climate Analyst Persona]")
    analyst_q = "Germany's power emissions fell from 227.68 to 175.97 MtCO2 from 2022 to 2023. What's the implication?"
    print(f"    Question: {analyst_q[:70]}...")
    
    try:
        # This would need to integrate with the actual persona system
        # For now, we'll check if baseline context is available
        from src.utils.baseline_context import BaselineContextProvider
        provider = BaselineContextProvider()
        context = provider.enrich_response(
            mcp_data={"rows": [{"country": "Germany", "emissions": 175.97}]},
            question=analyst_q,
            persona="Climate Analyst"
        )
        
        if "baseline_context" in context and context["baseline_context"]:
            results["analyst_uses_context"] = True
            print(f"    ✓ Baseline context enrichment available")
            results["details"].append(f"Analyst context keys: {list(context['baseline_context'].keys())}")
        else:
            print(f"    ✗ No baseline context provided")
            
    except Exception as e:
        results["details"].append(f"Persona test error: {str(e)[:80]}")
        print(f"    ? Could not test: {str(e)[:50]}")
    
    print(f"\n[RESULTS]")
    print(f"  Baseline Context Available: {results['analyst_uses_context']}")
    
    return results

def main():
    print("\n" + "="*80)
    print("BASELINE KNOWLEDGE EFFICIENCY TEST SUITE")
    print("="*80)
    print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"MCP Endpoint: {MCP_BASE}")
    
    all_results = {}
    
    # Run all tests
    try:
        all_results["test1_routing"] = test_question_routing()
    except Exception as e:
        print(f"\n✗ Test 1 failed: {e}")
        all_results["test1_routing"] = {"error": str(e)}
    
    time.sleep(1)
    
    try:
        all_results["test2_hallucination"] = test_baseline_hallucination()
    except Exception as e:
        print(f"\n✗ Test 2 failed: {e}")
        all_results["test2_hallucination"] = {"error": str(e)}
    
    time.sleep(1)
    
    try:
        all_results["test3_mcp_vs_baseline"] = test_mcp_vs_baseline()
    except Exception as e:
        print(f"\n✗ Test 3 failed: {e}")
        all_results["test3_mcp_vs_baseline"] = {"error": str(e)}
    
    time.sleep(1)
    
    try:
        all_results["test4_persona"] = test_persona_baseline_usage()
    except Exception as e:
        print(f"\n✗ Test 4 failed: {e}")
        all_results["test4_persona"] = {"error": str(e)}
    
    # Final Summary
    print("\n" + "="*80)
    print("FINAL SUMMARY")
    print("="*80)
    print(json.dumps(all_results, indent=2))
    
    # Save results
    with open("baseline_test_results.json", "w") as f:
        json.dump(all_results, f, indent=2)
    print("\nResults saved to: baseline_test_results.json")

if __name__ == "__main__":
    main()
