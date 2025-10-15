#!/usr/bin/env python3
"""
Test script to debug JSON parsing issues
"""

import json
import requests

def test_llm_response():
    """Test what the LLM is actually returning"""
    
    # Test the LLM directly
    payload = {
        "model": "/cache/climategpt_8b_test",
        "messages": [
            {
                "role": "system",
                "content": """You are ClimateGPT-Dev. You MUST answer by calling HTTP tools instead of guessing.
Data sources: EDGAR v2024 transport + power industry. Units: tonnes CO₂ (use MtCO₂ for large numbers).

Available datasets:
- Transport: transport-country-year, transport-admin1-year, transport-city-year
- Power Industry: power-country-year, power-admin1-year, power-city-year

CRITICAL: Return ONLY valid JSON for tool calls. No other text, no markdown, no explanations, no extra characters.

Tool call format:
{"tool":"query","args":{"file_id":"dataset-name","select":["col1","col2"],"where":{"col":"value"},"limit":10}}

Valid file_ids:
- transport-country-year, transport-admin1-year, transport-city-year
- power-country-year, power-admin1-year, power-city-year

Valid columns:
- country_name, iso3, year, emissions_tonnes, MtCO2
- admin1_name, admin1_geoid (for admin1 datasets)
- city_name, city_id (for city datasets)

IMPORTANT: Use exact country names from the data:
- "United States of America" (NOT "United States" or "USA")
- "People's Republic of China" (NOT "China")
- "Russian Federation" (NOT "Russia")

IMPORTANT RULES:
1. For "top N countries" queries: ALWAYS use order_by="MtCO2 DESC" and limit=N
2. For "by year" queries: include year in where clause
3. For "excluding invalid" queries: add where clause to filter out invalid data
4. ALWAYS include the requested number in limit (e.g., limit:25 for top 25)

Examples:
{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"order_by":"MtCO2 DESC","limit":25}}
{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020,"iso3":{"neq":"-99"}},"order_by":"MtCO2 DESC","limit":25}}
{"tool":"query","args":{"file_id":"power-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"order_by":"MtCO2 DESC","limit":10}}

CRITICAL: Return ONLY the JSON object. No markdown code blocks, no explanations, no additional text, no trailing characters."""
            },
            {
                "role": "user",
                "content": "Question: What were emissions in Transport and Power in India from 2015 to 2023?\n\nReturn ONLY a valid JSON tool call. No other text."
            }
        ],
        "temperature": 0.2
    }
    
    try:
        response = requests.post("https://erasmus.ai/models/climategpt_8b_test/v1/chat/completions", json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            llm_response = result["choices"][0]["message"]["content"].strip()
            
            print("=" * 80)
            print("LLM RAW RESPONSE:")
            print("=" * 80)
            print(repr(llm_response))
            print("=" * 80)
            print("LLM RESPONSE (readable):")
            print("=" * 80)
            print(llm_response)
            print("=" * 80)
            
            # Test JSON parsing
            cleaned_json = llm_response.strip()
            cleaned_json = cleaned_json.replace('```json', '').replace('```', '').strip()
            
            print("CLEANED JSON:")
            print("=" * 80)
            print(repr(cleaned_json))
            print("=" * 80)
            
            try:
                obj = json.loads(cleaned_json)
                print("✅ JSON parsing successful!")
                print(f"Tool: {obj.get('tool')}")
                print(f"Args: {obj.get('args')}")
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing failed: {e}")
                print(f"Error position: {e.pos}")
                print(f"Context: {cleaned_json[max(0, e.pos-20):e.pos+20]}")
                
                # Try to extract JSON
                start = cleaned_json.find("{")
                end = cleaned_json.rfind("}")
                if start != -1 and end != -1 and end > start:
                    json_candidate = cleaned_json[start:end+1]
                    print(f"JSON candidate: {repr(json_candidate)}")
                    try:
                        obj = json.loads(json_candidate)
                        print("✅ Extracted JSON parsing successful!")
                    except json.JSONDecodeError as e2:
                        print(f"❌ Extracted JSON also failed: {e2}")
        else:
            print(f"❌ LLM request failed: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_llm_response()
