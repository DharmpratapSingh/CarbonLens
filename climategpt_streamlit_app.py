import os
import json
import time
import requests
import streamlit as st
import hashlib
from functools import lru_cache
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

st.set_page_config(page_title="ClimateGPT QA", page_icon="🌍", layout="wide")

# Configuration
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8010")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://erasmus.ai/models/climategpt_8b_test/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "ai:4climate")
MODEL = os.environ.get("MODEL", "/cache/climategpt_8b_test")
USER, PASS = OPENAI_API_KEY.split(":", 1) if ":" in OPENAI_API_KEY else ("", "")

# Initialize session state for caching
if "query_cache" not in st.session_state:
    st.session_state.query_cache = {}
if "analysis_cache" not in st.session_state:
    st.session_state.analysis_cache = {}

st.title("🌍 ClimateGPT — Multi-Sector Emissions QA")
st.write("Ask questions in plain English. ClimateGPT will analyze Transport and Power Industry data and provide natural language answers.")

# Example questions and query suggestions
with st.expander("💡 Example Questions & Query Suggestions", expanded=True):
    st.markdown("""
    ### 🚗 **Transport Questions:**
    - "What are the top 5 countries by transport emissions in 2020?"
    - "Which US states have the highest transport emissions?"
    - "How have transport emissions changed in China from 2000 to 2023?"
    - "What cities have the highest transport emissions globally?"
    
    ### ⚡ **Power Industry Questions:**
    - "What are the top 5 countries by power industry emissions in 2020?"
    - "Which countries rely most heavily on power industry for emissions?"
    - "How do power industry emissions compare across different regions?"
    - "What's the trend in power industry emissions over time?"
    
    ### 🔄 **Multi-Sector Comparisons:**
    - "Compare transport vs power emissions for China in 2020"
    - "Which countries have higher transport than power emissions?"
    - "What's the ratio of transport to power emissions in the US?"
    - "How do transport and power emissions trends compare over time?"
    - "Which sector contributes more to total emissions in India?"
    
    ### 📊 **Advanced Analysis:**
    - "Show me year-over-year changes in transport emissions for the top 10 countries"
    - "Which countries had the biggest drop in power industry emissions from 2019 to 2020?"
    - "Compare seasonal patterns in transport emissions across different countries"
    - "What's the correlation between transport and power emissions by country?"
    - "Analyze the trend in China's emissions from 2000 to 2023"
    - "Show me statistical distribution of emissions across all countries"
    - "Which countries have the most volatile emissions patterns over time?"
    - "Compare the growth rates of transport vs power emissions globally"
    """)

# Data coverage information
with st.expander("📋 Data Coverage Information"):
    st.markdown("""
    ### **Available Data:**
    - **Sectors**: Transport, Power Industry
    - **Geographic Levels**: Country, State/Province, City
    - **Time Range**: 2000-2023 (24 years)
    - **Spatial Resolution**: 0.1° grid cells
    - **Data Source**: EDGAR v2024 (European Commission)
    
    ### **Dataset Details:**
    - **Transport**: Mobile combustion (road, rail, ship, aviation)
    - **Power Industry**: Power and heat generation plants (public & autoproducers)
    - **Units**: Tonnes CO₂ (displayed as MtCO₂ for large numbers)
    - **Coverage**: Global (200+ countries, 4,500+ states/provinces, 10,000+ cities)
    """)

# ClimateGPT System Prompt for our multi-sector datasets
CLIMATEGPT_SYSTEM_PROMPT = """
You are ClimateGPT-Dev. You MUST answer by calling HTTP tools instead of guessing.
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

CRITICAL: Return ONLY the JSON object. No markdown code blocks, no explanations, no additional text, no trailing characters.
"""

def chat_with_climategpt(system: str, user_message: str, temperature: float = 0.2) -> str:
    """Send message to ClimateGPT LLM and get response"""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message}
        ],
        "temperature": temperature
    }
    
    try:
        r = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            auth=HTTPBasicAuth(USER, PASS) if USER else None,
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error communicating with ClimateGPT: {str(e)}"

def get_cache_key(query_params: dict) -> str:
    """Generate a cache key for query parameters"""
    return hashlib.md5(json.dumps(query_params, sort_keys=True).encode()).hexdigest()

def normalize_country_name(country_name: str) -> str:
    """Normalize country names to match the data format"""
    country_mapping = {
        "United States": "United States of America",
        "USA": "United States of America",
        "US": "United States of America",
        "China": "People's Republic of China",
        "Russia": "Russian Federation",
        "UK": "United Kingdom",
        "South Korea": "Republic of Korea",
        "North Korea": "Democratic People's Republic of Korea"
    }
    return country_mapping.get(country_name, country_name)

@lru_cache(maxsize=100)
def cached_mcp_query(query_params_str: str) -> dict:
    """Cached MCP query to improve performance"""
    query_params = json.loads(query_params_str)
    try:
        response = requests.post(f"{MCP_URL}/query", json=query_params, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def exec_tool_call(tool_json: str) -> dict:
    """Execute tool call against MCP server with caching"""
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
    
    # Debug: Print the cleaned JSON for troubleshooting
    print(f"DEBUG: Attempting to parse JSON: {cleaned_json[:100]}...")
    
    try:
        obj = json.loads(cleaned_json)
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
                print("DEBUG: Extracted JSON parsing successful!")
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
                        print("DEBUG: Brace-counted JSON parsing successful!")
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
    
    tool = obj.get("tool")
    args = obj.get("args", {})

    if tool == "list_files":
        return requests.get(f"{MCP_URL}/list_files").json()
    if tool == "get_schema":
        fid = args["file_id"]
        return requests.get(f"{MCP_URL}/get_schema/{fid}").json()
    if tool == "query":
        # Normalize country names in the query
        if "where" in args and "country_name" in args["where"]:
            args["where"]["country_name"] = normalize_country_name(args["where"]["country_name"])
        
        # Use caching for query operations
        cache_key = get_cache_key(args)
        if cache_key in st.session_state.query_cache:
            return st.session_state.query_cache[cache_key]
        
        # Use cached MCP query
        result = cached_mcp_query(json.dumps(args, sort_keys=True))
        st.session_state.query_cache[cache_key] = result
        return result
    if tool in ("metrics.yoy", "yoy"):
        return requests.post(f"{MCP_URL}/metrics/yoy", json=args).json()

    return {"error": f"unknown tool '{tool}'"}


def process_climategpt_question(question: str) -> str:
    """Process question through ClimateGPT LLM workflow"""
    try:
        # Step 1: Get tool call from ClimateGPT
        tool_call_response = chat_with_climategpt(
            CLIMATEGPT_SYSTEM_PROMPT,
            f"Question: {question}\n\nReturn ONLY a valid JSON tool call. No other text."
        ).strip()
        
        # Clean up the response to ensure it's valid JSON
        tool_call_response = tool_call_response.replace('```json', '').replace('```', '').strip()
        
        # Debug: Print the raw response
        print(f"DEBUG: Raw LLM response: {tool_call_response[:200]}...")
        
        # If the model didn't return JSON, try again with a simpler prompt
        if not (tool_call_response.startswith("{") and '"tool"' in tool_call_response):
            print("DEBUG: First attempt failed, trying simpler prompt...")
            tool_call_response = chat_with_climategpt(
                CLIMATEGPT_SYSTEM_PROMPT,
                f"Question: {question}\n\nReturn ONLY this JSON format: {{\"tool\":\"query\",\"args\":{{\"file_id\":\"transport-country-year\",\"select\":[\"country_name\",\"year\",\"MtCO2\"],\"limit\":10}}}}"
            ).strip()
            tool_call_response = tool_call_response.replace('```json', '').replace('```', '').strip()
            print(f"DEBUG: Second attempt response: {tool_call_response[:200]}...")
        
        # Step 2: Execute tool call
        result = exec_tool_call(tool_call_response)
        
        # Step 3: Generate natural language response
        if "error" in result:
            return f"I encountered an error while processing your question: {result['error']}"
        
        # Add MtCO2 column if missing to reduce unit mistakes
        if isinstance(result, dict) and "rows" in result:
            rows = result["rows"]
            for row in rows:
                if "MtCO2" not in row and "emissions_tonnes" in row and isinstance(row["emissions_tonnes"], (int, float)):
                    row["MtCO2"] = row["emissions_tonnes"] / 1e6
        
        
        # Create enhanced summary prompt
        rows_preview = json.dumps(result, ensure_ascii=False)
        
        summary_prompt = f"""
        You asked: {question}

        Using the JSON data below (which includes rows and meta), write a comprehensive answer:
        - If present, compute/compare as needed (YoY deltas, rankings, trends).
        - Always cite: "Source: {result.get('meta',{}).get('table_id','?')}, EDGAR v2024 transport."
        - Use correct units (tonnes CO₂; optionally show MtCO₂ for big numbers).
        - Include statistical insights when relevant (trends, correlations, distributions).
        - Keep the answer informative but concise (4–8 sentences).

        Data:
        {rows_preview}
        """
        
        # Step 4: Get natural language summary
        answer = chat_with_climategpt(CLIMATEGPT_SYSTEM_PROMPT, summary_prompt, temperature=0.2)
        
        # Debug: Check if answer is empty
        if not answer or not answer.strip():
            return "ClimateGPT returned an empty response. Please try rephrasing your question."
        
        return answer
        
    except Exception as e:
        return f"I encountered an error while processing your question: {str(e)}"

# Status check functions
def test_mcp_connection():
    try:
        response = requests.get(f"{MCP_URL}/health", timeout=5)
        return response.status_code == 200
    except:
        return False

def test_climategpt_connection():
    try:
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.2
        }
        response = requests.post(
            f"{OPENAI_BASE_URL}/chat/completions",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
            auth=HTTPBasicAuth(USER, PASS) if USER else None,
            timeout=10,
        )
        return response.status_code == 200
    except:
        return False

# Status check
col1, col2 = st.columns(2)
with col1:
    if test_mcp_connection():
        st.success("✅ MCP Server Connected")
    else:
        st.error("❌ MCP Server Not Connected")

with col2:
    if test_climategpt_connection():
        st.success("✅ ClimateGPT Connected")
    else:
        st.error("❌ ClimateGPT Not Connected")

# Chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Conversation and performance management
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

with col2:
    if st.button("📊 Export Chat"):
        if st.session_state.messages:
            # Create export data
            export_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "conversation": st.session_state.messages,
                "cache_stats": {
                    "query_cache_size": len(st.session_state.query_cache),
                    "analysis_cache_size": len(st.session_state.analysis_cache)
                }
            }
            
            # Create downloadable JSON
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"climategpt_conversation_{time.strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
        else:
            st.warning("No conversation to export")

with col3:
    if st.button("⚡ Clear Cache"):
        st.session_state.query_cache = {}
        st.session_state.analysis_cache = {}
        st.success("Cache cleared!")

with col4:
    st.caption(f"💬 {len(st.session_state.messages)} messages<br/>🗄️ {len(st.session_state.query_cache)} cached queries", unsafe_allow_html=True)

# Help section
with st.expander("❓ Help & Tips"):
    st.markdown("""
    ### **How to Ask Questions:**
    
    **✅ Good Examples:**
    - "What are the top 5 countries by transport emissions in 2020?"
    - "Compare transport vs power emissions for China in 2020"
    - "Which US states have the highest power industry emissions?"
    - "How have transport emissions changed in India from 2000 to 2023?"
    
    **❌ Avoid:**
    - "Show me data" (too vague)
    - "What's the emissions?" (missing context)
    - "Tell me about climate" (not specific to our data)
    
    ### **Tips for Better Results:**
    1. **Be specific**: Include country names, years, or sectors
    2. **Use comparisons**: Ask to compare transport vs power, or different countries
    3. **Ask for trends**: Request year-over-year changes or time series
    4. **Request rankings**: Ask for top/bottom countries, states, or cities
    
    ### **Available Data:**
    - **Sectors**: Transport, Power Industry
    - **Geographic Levels**: Country, State/Province, City
    - **Time Range**: 2000-2023
    - **Countries**: 200+ countries worldwide
    - **States/Provinces**: 4,500+ administrative regions
    - **Cities**: 10,000+ urban centers
    
    ### **Features:**
    - 📊 **Advanced Visualizations**: Multiple chart types, correlation analysis, trend charts
    - 📥 **Export Data**: Download conversation and results with cache statistics
    - 🔄 **Multi-Sector Analysis**: Compare transport vs power emissions
    - ⏱️ **Performance Optimization**: Query caching for faster responses
    - 📈 **Statistical Analysis**: Automatic trend analysis, correlations, and insights
    - 💾 **Session Memory**: Conversation history and cache management
    - 🎯 **Smart Caching**: Repeated queries load instantly from cache
    """)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Add export button for assistant messages with data
        if message["role"] == "assistant" and "Source:" in message["content"]:
            # Try to extract data from the message for export
            if st.button(f"📥 Export Data", key=f"export_{len(st.session_state.messages)}"):
                # This would need to be enhanced to extract actual data
                st.info("Data export feature - would extract tabular data from response")

# Chat input
if prompt := st.chat_input("Ask about transport and power industry CO₂ emissions..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response using ClimateGPT
    with st.chat_message("assistant"):
        with st.spinner("ClimateGPT is analyzing your question..."):
            try:
                start_time = time.time()
                answer = process_climategpt_question(prompt)
                response_time = time.time() - start_time
                
                st.markdown(answer)
                
                # Add performance metrics
                cache_hits = len(st.session_state.query_cache)
                st.caption(f"⏱️ Response time: {response_time:.2f}s | 🗄️ Cache: {cache_hits} queries")
                
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
