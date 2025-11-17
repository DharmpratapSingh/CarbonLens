#!/usr/bin/env python3
"""Quick test to verify the unhashable type fix"""
import sys
sys.path.insert(0, '/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT')

from climategpt_persona_engine import process_persona_question

# Test the query that was failing
print("Testing query: What are the emissions of United States of America?")
print("-" * 60)

answer, metadata, tool_used = process_persona_question(
    "What are the emissions of United States of America?",
    "Climate Analyst"
)

print(f"Answer: {answer}")
print(f"\nMetadata: {metadata}")
print(f"Tool used: {tool_used}")
print("-" * 60)
print("✅ Test completed!")
