"""
Direct test of baseline knowledge usage without API auth issues
"""
import sys
sys.path.insert(0, '/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT')

from src.utils.baseline_context import BaselineContextProvider, PolicyContextAugmenter, EducationalContextAugmenter
import json

print("\n" + "="*80)
print("DIRECT BASELINE KNOWLEDGE EFFICIENCY TEST")
print("="*80)

results = {
    "sector_context_available": False,
    "country_context_available": False,
    "policy_context_available": False,
    "persona_frameworks_loaded": False,
    "enrichment_works": False,
    "augmenters_functional": False,
    "details": []
}

# Test 1: Check if BaselineContextProvider loads
print("\n[TEST 1] Loading BaselineContextProvider...")
try:
    provider = BaselineContextProvider()
    results["details"].append("✓ BaselineContextProvider loaded successfully")
    print("  ✓ Provider initialized")
    
    # Test 2: Check sector context
    print("\n[TEST 2] Checking sector-specific baseline knowledge...")
    transport_context = provider.get_sector_explanation("transport")
    if transport_context and len(transport_context) > 50:
        results["sector_context_available"] = True
        results["details"].append(f"✓ Transport sector context: {len(transport_context)} chars")
        print(f"  ✓ Sector context loaded ({len(transport_context)} chars)")
        print(f"    Sample: {transport_context[:100]}...")
    
    # Test 3: Check country context
    print("\n[TEST 3] Checking country-specific baseline knowledge...")
    germany_policy = provider.get_policy_context("Germany", "policy")
    if germany_policy and len(germany_policy) > 30:
        results["country_context_available"] = True
        results["details"].append(f"✓ Germany policy context available")
        print(f"  ✓ Country context loaded")
        print(f"    Sample: {germany_policy[:100]}...")
    
    # Test 4: Check persona frameworks
    print("\n[TEST 4] Checking persona interpretation frameworks...")
    analyst_framework = provider.get_interpretation_framework("Climate Analyst")
    if analyst_framework and "focus" in analyst_framework:
        results["persona_frameworks_loaded"] = True
        results["details"].append(f"✓ Persona frameworks: {list(analyst_framework.keys())}")
        print(f"  ✓ Persona frameworks loaded")
        print(f"    Analyst focus: {analyst_framework['focus']}")
    
    # Test 5: Test enrichment functionality
    print("\n[TEST 5] Testing response enrichment with baseline context...")
    mcp_data = {
        "rows": [
            {"country_name": "Germany", "year": 2022, "emissions_tonnes": 227.68e6},
            {"country_name": "Germany", "year": 2023, "emissions_tonnes": 175.97e6}
        ],
        "meta": {"file_id": "power-country-year", "row_count": 2}
    }
    
    enriched = provider.enrich_response(
        mcp_data=mcp_data,
        question="How did Germany's power emissions change from 2022 to 2023?",
        persona="Climate Analyst"
    )
    
    if "baseline_context" in enriched and enriched["baseline_context"]:
        results["enrichment_works"] = True
        context_keys = list(enriched["baseline_context"].keys())
        results["details"].append(f"✓ Enrichment adds context: {context_keys}")
        print(f"  ✓ Enrichment successful")
        print(f"    Context added: {context_keys}")
        print(f"    Full context:")
        for key, val in enriched["baseline_context"].items():
            print(f"      [{key}]: {str(val)[:80]}...")
    
    # Test 6: Test augmenters
    print("\n[TEST 6] Testing context augmenters...")
    
    # Policy augmenter
    policy_aug = PolicyContextAugmenter.add_paris_alignment_context(
        country="Germany",
        sector="power",
        reduction_pct=22.7
    )
    
    # Educational augmenter
    analogy = EducationalContextAugmenter.create_analogy(51.71, "cars")
    significance = EducationalContextAugmenter.explain_significance(-22.7)
    
    if policy_aug and analogy and significance:
        results["augmenters_functional"] = True
        results["details"].append("✓ All augmenters functional")
        print(f"  ✓ Policy augmenter: {policy_aug[:80]}...")
        print(f"  ✓ Educational analogy: {analogy}")
        print(f"  ✓ Significance: {significance}")
    
except Exception as e:
    results["details"].append(f"✗ Error: {str(e)}")
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Test 7: Check if baseline is being used in actual responses
print("\n[TEST 7] Checking if baseline is used in MCP query responses...")
import requests

try:
    # Query MCP directly
    mcp_response = requests.post(
        "http://127.0.0.1:8010/query",
        json={
            "file_id": "power-country-year",
            "select": ["country_name", "year", "emissions_tonnes"],
            "where": {"country_name": "Germany", "year": 2023},
            "assist": True
        },
        timeout=30
    ).json()
    
    if "rows" in mcp_response and mcp_response["rows"]:
        # Check if response includes baseline context
        has_quality_metadata = "quality_metadata" in mcp_response
        has_explanation = "baseline_context" in mcp_response
        
        results["details"].append(f"✓ MCP query returned data with quality metadata: {has_quality_metadata}")
        print(f"  ✓ MCP response received")
        print(f"    Has quality metadata: {has_quality_metadata}")
        print(f"    Has baseline context: {has_explanation}")
        
        if has_quality_metadata:
            print(f"    Quality score: {mcp_response['quality_metadata'].get('quality_score')}%")
    
except Exception as e:
    results["details"].append(f"✗ MCP query test failed: {str(e)}")
    print(f"  ✗ Error: {e}")

# SUMMARY
print("\n" + "="*80)
print("EFFICIENCY ASSESSMENT")
print("="*80)

efficiency_score = sum([
    results["sector_context_available"],
    results["country_context_available"],
    results["persona_frameworks_loaded"],
    results["enrichment_works"],
    results["augmenters_functional"]
])

print(f"\nBaseline Knowledge Components:")
print(f"  Sector Context: {'✓' if results['sector_context_available'] else '✗'}")
print(f"  Country Context: {'✓' if results['country_context_available'] else '✗'}")
print(f"  Policy Context: {'✓' if results['policy_context_available'] else '✗'}")
print(f"  Persona Frameworks: {'✓' if results['persona_frameworks_loaded'] else '✗'}")
print(f"  Response Enrichment: {'✓' if results['enrichment_works'] else '✗'}")
print(f"  Context Augmenters: {'✓' if results['augmenters_functional'] else '✗'}")

print(f"\nEfficiency Score: {efficiency_score}/5 components working")

if efficiency_score == 5:
    print("Status: ✓ BASELINE KNOWLEDGE SYSTEM FULLY OPERATIONAL")
elif efficiency_score >= 3:
    print("Status: ⚠ BASELINE KNOWLEDGE SYSTEM PARTIALLY WORKING")
else:
    print("Status: ✗ BASELINE KNOWLEDGE SYSTEM ISSUES DETECTED")

print(f"\nDetailed Findings:")
for detail in results["details"]:
    print(f"  {detail}")

# Save results
with open("baseline_efficiency_results.txt", "w") as f:
    f.write("="*80 + "\n")
    f.write("BASELINE KNOWLEDGE EFFICIENCY TEST RESULTS\n")
    f.write("="*80 + "\n\n")
    f.write(json.dumps(results, indent=2))

print(f"\nResults saved to: baseline_efficiency_results.txt")
