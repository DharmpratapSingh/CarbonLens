import os
import json
import time
import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="ClimateGPT QA", page_icon="🌍", layout="wide")

# Configuration
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8010")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://erasmus.ai/models/climategpt_8b_test/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "ai:4climate")
MODEL = os.environ.get("MODEL", "/cache/climategpt_8b_test")
USER, PASS = OPENAI_API_KEY.split(":", 1) if ":" in OPENAI_API_KEY else ("", "")

st.title("🌍 ClimateGPT — Transport Emissions QA")
st.write("Ask questions in plain English. ClimateGPT will analyze the data and provide natural language answers.")

# Simple test function
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
            auth=(USER, PASS) if USER else None,
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

# Simple chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("Ask about transport CO₂ emissions..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("ClimateGPT is thinking..."):
            try:
                answer = ""
                
                # Determine what type of query based on keywords
                prompt_lower = prompt.lower()
                
                # Extract year if mentioned
                import re
                years = re.findall(r'\b(20\d{2})\b', prompt)
                year = int(years[0]) if years else 2020
                
                # Determine geographic scope
                if any(word in prompt_lower for word in ["state", "states", "usa", "united states", "us"]):
                    # US States query
                    query_payload = {
                        "file_id": "admin1-year",
                        "select": ["admin1_name", "year", "MtCO2"],
                        "where": {"iso3": "USA", "year": year},
                        "order_by": "MtCO2 DESC",
                        "limit": 10
                    }
                    
                    response = requests.post(f"{MCP_URL}/query", json=query_payload, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        rows = data.get("rows", [])
                        
                        if rows:
                            if "highest" in prompt_lower or "top" in prompt_lower:
                                answer = f"Based on the EDGAR transport emissions data, here are the top US states by emissions in {year}:\n\n"
                                for i, row in enumerate(rows[:5], 1):
                                    answer += f"{i}. **{row['admin1_name']}**: {row['MtCO2']:.1f} MtCO₂\n"
                            else:
                                answer = f"Here are the US states with transport emissions data for {year}:\n\n"
                                for i, row in enumerate(rows[:10], 1):
                                    answer += f"{i}. **{row['admin1_name']}**: {row['MtCO2']:.1f} MtCO₂\n"
                            answer += f"\n*Source: {data.get('meta', {}).get('table_id', 'admin1-year')}, EDGAR v2024 transport*"
                        else:
                            answer = f"I couldn't find data for US states in {year}. Try a different year like 2019 or 2020."
                    else:
                        answer = f"Error querying data: {response.status_code}"
                        
                elif any(word in prompt_lower for word in ["country", "countries", "nation"]):
                    # Countries query
                    query_payload = {
                        "file_id": "country-year",
                        "select": ["country_name", "year", "MtCO2"],
                        "where": {"year": year},
                        "order_by": "MtCO2 DESC",
                        "limit": 10
                    }
                    
                    response = requests.post(f"{MCP_URL}/query", json=query_payload, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        rows = data.get("rows", [])
                        
                        if rows:
                            if "highest" in prompt_lower or "top" in prompt_lower:
                                answer = f"Based on the EDGAR transport emissions data, here are the top countries by emissions in {year}:\n\n"
                                for i, row in enumerate(rows[:5], 1):
                                    answer += f"{i}. **{row['country_name']}**: {row['MtCO2']:.1f} MtCO₂\n"
                            else:
                                answer = f"Here are the countries with transport emissions data for {year}:\n\n"
                                for i, row in enumerate(rows[:10], 1):
                                    answer += f"{i}. **{row['country_name']}**: {row['MtCO2']:.1f} MtCO₂\n"
                            answer += f"\n*Source: {data.get('meta', {}).get('table_id', 'country-year')}, EDGAR v2024 transport*"
                        else:
                            answer = f"I couldn't find data for countries in {year}. Try a different year like 2019 or 2020."
                    else:
                        answer = f"Error querying data: {response.status_code}"
                        
                elif any(word in prompt_lower for word in ["city", "cities"]):
                    # Cities query
                    query_payload = {
                        "file_id": "city-year",
                        "select": ["city_name", "admin1_name", "country_name", "year", "MtCO2"],
                        "where": {"year": year},
                        "order_by": "MtCO2 DESC",
                        "limit": 10
                    }
                    
                    response = requests.post(f"{MCP_URL}/query", json=query_payload, timeout=30)
                    if response.status_code == 200:
                        data = response.json()
                        rows = data.get("rows", [])
                        
                        if rows:
                            if "highest" in prompt_lower or "top" in prompt_lower:
                                answer = f"Based on the EDGAR transport emissions data, here are the top cities by emissions in {year}:\n\n"
                                for i, row in enumerate(rows[:5], 1):
                                    answer += f"{i}. **{row['city_name']}** ({row['admin1_name']}, {row['country_name']}): {row['MtCO2']:.1f} MtCO₂\n"
                            else:
                                answer = f"Here are the cities with transport emissions data for {year}:\n\n"
                                for i, row in enumerate(rows[:10], 1):
                                    answer += f"{i}. **{row['city_name']}** ({row['admin1_name']}, {row['country_name']}): {row['MtCO2']:.1f} MtCO₂\n"
                            answer += f"\n*Source: {data.get('meta', {}).get('table_id', 'city-year')}, EDGAR v2024 transport*"
                        else:
                            answer = f"I couldn't find data for cities in {year}. Try a different year like 2019 or 2020."
                    else:
                        answer = f"Error querying data: {response.status_code}"
                        
                else:
                    # Default response with examples
                    answer = """I can help you with questions about transport emissions data! Here are some examples:

**Countries:** "What are the top countries by emissions in 2020?"
**US States:** "Which US states have the highest emissions?"
**Cities:** "What are the top cities by transport emissions?"

Try asking about specific countries, states, or cities, and I'll provide the data from the EDGAR transport emissions database."""
                
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
