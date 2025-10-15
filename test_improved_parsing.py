#!/usr/bin/env python3
"""
Test the improved JSON parsing logic
"""

import json

def improved_json_parsing(tool_json: str):
    """Improved JSON parsing with multiple fallback strategies"""
    # Clean the JSON string first
    cleaned_json = tool_json.strip()
    
    # Remove markdown code blocks if present
    if cleaned_json.startswith("```json"):
        cleaned_json = cleaned_json[7:]
    if cleaned_json.startswith("```"):
        cleaned_json = cleaned_json[3:]
    if cleaned_json.endswith("```"):
        cleaned_json = cleaned_json[:-3]
    cleaned_json = cleaned_json.strip()
    
    print(f"DEBUG: Attempting to parse JSON: {cleaned_json[:100]}...")
    
    try:
        obj = json.loads(cleaned_json)
        print("✅ Direct parsing successful!")
        return obj
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON decode error: {e}")
        print(f"DEBUG: Full cleaned JSON: {cleaned_json}")
        
        # Try to extract JSON from the response
        start = cleaned_json.find("{")
        end = cleaned_json.rfind("}")
        if start != -1 and end != -1 and end > start:
            json_candidate = cleaned_json[start:end+1]
            print(f"DEBUG: Extracted JSON candidate: {json_candidate[:100]}...")
            try:
                obj = json.loads(json_candidate)
                print("✅ Extracted JSON parsing successful!")
                return obj
            except json.JSONDecodeError as e2:
                print(f"DEBUG: Extracted JSON also failed: {e2}")
                # Try one more approach: find the first complete JSON object
                try:
                    # Look for the first complete JSON object by counting braces
                    brace_count = 0
                    json_end = -1
                    for i, char in enumerate(cleaned_json):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_end = i
                                break
                    
                    if json_end != -1:
                        json_candidate = cleaned_json[start:json_end+1]
                        print(f"DEBUG: Brace-counted JSON candidate: {json_candidate[:100]}...")
                        obj = json.loads(json_candidate)
                        print("✅ Brace-counted JSON parsing successful!")
                        return obj
                    else:
                        return {
                            "error": f"Invalid JSON format: {str(e2)}", 
                            "raw": tool_json[:200] + "..." if len(tool_json) > 200 else tool_json,
                            "debug": f"Tried to parse: {json_candidate[:200]}...",
                            "position": f"Error at position {e2.pos} in: {json_candidate[max(0, e2.pos-20):e2.pos+20]}"
                        }
                except json.JSONDecodeError as e3:
                    return {
                        "error": f"Invalid JSON format: {str(e3)}", 
                        "raw": tool_json[:200] + "..." if len(tool_json) > 200 else tool_json,
                        "debug": f"Tried to parse: {json_candidate[:200]}...",
                        "position": f"Error at position {e3.pos} in: {json_candidate[max(0, e3.pos-20):e3.pos+20]}"
                    }
        else:
            return {
                "error": f"JSON decode error: {str(e)}", 
                "raw": tool_json[:200] + "..." if len(tool_json) > 200 else tool_json,
                "debug": "No valid JSON brackets found"
            }

def test_improved_parsing():
    """Test the improved parsing with various cases"""
    
    test_cases = [
        # Case 1: Valid JSON
        '{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}}',
        
        # Case 2: JSON with extra text after (this was causing the "Extra data" error)
        '{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}} some extra text',
        
        # Case 3: JSON with explanation before and after
        'Here is the query: {"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}} This will get the data.',
        
        # Case 4: JSON with markdown
        '```json\n{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":2020},"limit":10}}\n```',
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i}")
        print(f"{'='*60}")
        print(f"Input: {repr(test_case)}")
        
        result = improved_json_parsing(test_case)
        
        if isinstance(result, dict) and "error" not in result:
            print(f"✅ SUCCESS! Tool: {result.get('tool')}")
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_improved_parsing()


