#!/usr/bin/env python3
"""
Simple test to debug JSON parsing issues
"""

import json

def test_json_parsing():
    """Test various JSON parsing scenarios"""
    
    # Test cases that might cause the "Extra data" error
    test_cases = [
        # Case 1: Valid JSON
        '{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}}',
        
        # Case 2: JSON with extra text after
        '{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}} some extra text',
        
        # Case 3: JSON with markdown
        '```json\n{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}}\n```',
        
        # Case 4: JSON with explanation
        'Here is the query: {"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}} This will get the data.',
        
        # Case 5: Malformed JSON (missing quote)
        '{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}',
        
        # Case 6: JSON with trailing comma
        '{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10,}}',
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i}")
        print(f"{'='*60}")
        print(f"Input: {repr(test_case)}")
        
        # Clean the JSON
        cleaned_json = test_case.strip()
        cleaned_json = cleaned_json.replace('```json', '').replace('```', '').strip()
        
        print(f"Cleaned: {repr(cleaned_json)}")
        
        try:
            obj = json.loads(cleaned_json)
            print("✅ Direct parsing successful!")
            print(f"Tool: {obj.get('tool')}")
        except json.JSONDecodeError as e:
            print(f"❌ Direct parsing failed: {e}")
            print(f"Error position: {e.pos}")
            print(f"Context: {cleaned_json[max(0, e.pos-20):e.pos+20]}")
            
            # Try extraction method
            start = cleaned_json.find("{")
            end = cleaned_json.rfind("}")
            if start != -1 and end != -1 and end > start:
                json_candidate = cleaned_json[start:end+1]
                print(f"Extracted candidate: {repr(json_candidate)}")
                try:
                    obj = json.loads(json_candidate)
                    print("✅ Extracted parsing successful!")
                    print(f"Tool: {obj.get('tool')}")
                except json.JSONDecodeError as e2:
                    print(f"❌ Extracted parsing also failed: {e2}")
                    print(f"Error position: {e2.pos}")
                    print(f"Context: {json_candidate[max(0, e2.pos-20):e2.pos+20]}")
            else:
                print("❌ No JSON brackets found")

if __name__ == "__main__":
    test_json_parsing()


