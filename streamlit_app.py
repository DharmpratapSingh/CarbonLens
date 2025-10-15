import os
import re
import json
import time
import textwrap
from typing import Dict, Any, List, Tuple, Optional
from requests.auth import HTTPBasicAuth

import requests
import pandas as pd
import streamlit as st
import altair as alt
from dotenv import load_dotenv
load_dotenv()

# --------------------------
# Config
# --------------------------
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8010")
# ClimateGPT LLM configuration
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://erasmus.ai/models/climategpt_8b_test/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "ai:4climate")
MODEL = os.environ.get("MODEL", "/cache/climategpt_8b_test")
USER, PASS = OPENAI_API_KEY.split(":", 1) if ":" in OPENAI_API_KEY else ("", "")

st.set_page_config(page_title="ClimateGPT QA", page_icon="🌍", layout="wide")

# --------------------------
# ClimateGPT LLM Integration
# --------------------------
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

def exec_tool_call(tool_json: str) -> Dict[str, Any]:
    """Execute tool call against MCP server"""
    try:
        obj = json.loads(tool_json)
    except json.JSONDecodeError:
        start = tool_json.find("{")
        end = tool_json.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(tool_json[start:end+1])
        else:
            return {"error": "Model did not return valid JSON tool call.", "raw": tool_json}
    
    tool = obj.get("tool")
    args = obj.get("args", {})

    if tool == "list_files":
        return requests.get(f"{MCP_URL}/list_files").json()
    if tool == "get_schema":
        fid = args["file_id"]
        return requests.get(f"{MCP_URL}/get_schema/{fid}").json()
    if tool == "query":
        return requests.post(f"{MCP_URL}/query", json=args).json()
    if tool in ("metrics.yoy", "yoy"):
        return requests.post(f"{MCP_URL}/metrics/yoy", json=args).json()

    return {"error": f"unknown tool '{tool}'"}

# --------------------------
# ClimateGPT System Prompt
# --------------------------
CLIMATEGPT_SYSTEM_PROMPT = """
You are ClimateGPT-Dev. You MUST answer by calling the HTTP tools listed below instead of guessing.
Data source: EDGAR v2024 transport (0.1°). Default units: tonnes CO₂ (use MtCO₂ when aggregating).

Routing rules:
- Use level ∈ {city, admin1, country, city_expanded} and period ∈ {year, month}.
- Prefer admin1-year for subnational yearly comparisons; use *-month for seasonality; use city-year-expanded only when the user asks for maximum city coverage or mentions small towns/edge cases.
- Always cite the table id used (e.g., "Source: admin1-year, EDGAR v2024 transport").

HTTP tools (JSON calls):
- list_files: GET http://localhost:8010/list_files
- get_schema(file_id): GET http://localhost:8010/get_schema/{file_id}
- query(file_id, select, where, group_by, order_by, limit): POST http://localhost:8010/query
- yoy(file_id, where, key_col, value_col, base_year, compare_year, top_n, direction): POST http://localhost:8010/metrics/yoy

When you call tools, NEVER use SQL strings. Use JSON with:
- select: array of column names
- where: objects (equality, {"in":[...]}, {"between":[a,b]}, {"gte":x}, {"lte":y}, {"contains":"text"})
- group_by: array
- order_by: "<column> ASC|DESC"
- limit: integer

For year-over-year comparisons, prefer POST /metrics/yoy. Otherwise use POST /query.
Return ONLY the JSON object for tool calls (no commentary). If a fact is not returned by tools, say you don't know and propose a follow-up query.
Keep temperature low and be precise with units + years.

STRICT FORMAT & SCHEMA GUARDRAILS:
- Always wrap tool calls as a single JSON object:
  {"tool":"metrics.yoy","args":{...}}  OR  {"tool":"query","args":{...}}
- Do NOT nest the tool name as a key (❌ {"yoy":{...}} or {"query":{...}}).
- Use ONLY column names present in the schema you retrieved:
  * admin1-year: admin1_name, admin1_geoid, country_name, iso3, year, emissions_tonnes, MtCO2
  * country-year: country_name, iso3, year, emissions_tonnes, MtCO2
  * city-year: city_name, city_id, admin1_name, country_name, iso3, year, emissions_tonnes, MtCO2
  * country-month/admin1-month/city-month also include month
- Common mistakes to avoid:
  * "country" → use "iso3" or "country_name" as appropriate
  * "name" → use "admin1_name" (for admin1-year)
  * "emissions" → use "emissions_tonnes"
  * direction for /metrics/yoy must be one of {"drop","rise"} (NOT "desc"/"asc")
- Examples (valid):
  {"tool":"metrics.yoy","args":{"file_id":"admin1-year","where":{"iso3":"USA"},"key_col":"admin1_name","value_col":"emissions_tonnes","base_year":2019,"compare_year":2020,"top_n":1,"direction":"drop"}}
  {"tool":"query","args":{"file_id":"country-month","select":["year","month","emissions_tonnes"],"where":{"iso3":"DEU","year":{"between":[2018,2020]}},"group_by":["year","month"],"order_by":"year ASC","limit":500}}
"""

def process_climategpt_question(question: str) -> str:
    """Process question through ClimateGPT LLM workflow"""
    try:
        # Step 1: Get tool call from ClimateGPT
        tool_call_response = chat_with_climategpt(
            CLIMATEGPT_SYSTEM_PROMPT,
            question + "\n\nReturn ONLY a tool call JSON as per the schema. Do not include any prose."
        ).strip()
        
        # If the model didn't return JSON, nudge once with a strict reminder
        if not (tool_call_response.startswith("{") and '"tool"' in tool_call_response):
            tool_call_response = chat_with_climategpt(
                CLIMATEGPT_SYSTEM_PROMPT,
                "Return ONLY a tool call JSON for this question:\n" + question + "\n\nReminder: never use SQL strings; use the JSON schema described."
            ).strip()
        
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
        
        # Create summary prompt
        rows_preview = json.dumps(result, ensure_ascii=False)
        summary_prompt = textwrap.dedent(f"""
        You asked: {question}

        Using the JSON below (which includes rows and meta), write a concise answer:
        - If present, compute/compare as needed (YoY deltas, rankings).
        - Always cite: "Source: {result.get('meta',{}).get('table_id','?')}, EDGAR v2024 transport."
        - Use correct units (tonnes CO₂; optionally show MtCO₂ for big numbers).
        - Keep the answer crisp (3–6 sentences).

        JSON:
        {rows_preview}
        """).strip()
        
        # Step 4: Get natural language summary
        answer = chat_with_climategpt(CLIMATEGPT_SYSTEM_PROMPT, summary_prompt, temperature=0.2)
        
        # Debug: Check if answer is empty
        if not answer or not answer.strip():
            return "ClimateGPT returned an empty response. Please try rephrasing your question."
        
        return answer
        
    except Exception as e:
        return f"I encountered an error while processing your question: {str(e)}"

# --------------------------
# Utilities
# --------------------------
def mcp_list_files() -> List[Dict[str, Any]]:
    r = requests.get(f"{MCP_URL}/list_files", timeout=30)
    r.raise_for_status()
    return r.json()

def mcp_query(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{MCP_URL}/query", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def mcp_yoy(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(f"{MCP_URL}/metrics/yoy", json=payload, timeout=60)
    r.raise_for_status()
    return r.json()

def _extract_years(text: str) -> List[int]:
    # find 4-digit years between 1950 and 2100
    years = [int(y) for y in re.findall(r"\b(19[5-9]\d|20\d{2}|2100)\b", text)]
    return years

def _infer_grain(text: str) -> str:
    t = text.lower()
    if "city" in t:
        return "city"
    if any(k in t for k in ["state", "province", "admin1", "region (admin1)"]):
        return "admin1"
    if "country" in t or "countries" in t or "national" in t:
        return "country"
    return "country"

def _infer_temporal(text: str) -> str:
    t = text.lower()
    if "monthly" in t or "per month" in t or "by month" in t or re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", text, re.I):
        return "month"
    return "year"

def _is_yoy(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in ["yoy", "year over year", "year-on-year", "compare", "difference", "rise", "drop", "increase", "decrease", "bigger than last year"])

def _top_or_bottom(text: str) -> Tuple[str, int]:
    t = text.lower()
    # detect N
    n = 10
    m = re.search(r"\btop\s+(\d{1,3})\b", t)
    if m:
        n = min(50, int(m.group(1)))
        return ("top", n)
    m = re.search(r"\bbottom\s+(\d{1,3})\b", t)
    if m:
        n = min(50, int(m.group(1)))
        return ("bottom", n)
    return ("top", n)

def _find_geo_filters(text: str) -> Dict[str, Any]:
    """Heuristic: let users type 'India', 'United States', 'Texas', 'Delhi'."""
    # naive, but useful: infer column and add equals filter
    # we’ll try common columns in expanded datasets:
    # country_name, iso3, admin1_name, city_name
    filters = {}
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', text)
    candidates = [q[0] or q[1] for q in quoted]
    # also single bareword with capital letter (very light heuristic)
    words = re.findall(r"\b[A-Z][a-zA-Z\-\.]+\b", text)
    for w in words:
        if len(w) >= 3:
            candidates.append(w)
    # prefer longer strings
    candidates = sorted(set(candidates), key=len, reverse=True)[:3]
    if not candidates:
        return filters
    # just attach as OR across likely columns
    name = candidates[0]
    filters["$or"] = [
        {"country_name": name},
        {"admin1_name": name},
        {"city_name": name},
        {"iso3": name.upper()[:3]}
    ]
    return filters

def _merge_or_filters(df: pd.DataFrame, f: Dict[str, Any]) -> pd.DataFrame:
    if "$or" not in f:
        return df
    mask = False
    for cond in f["$or"]:
        col, val = next(iter(cond.items()))
        if col in df.columns:
            mask = (mask | (df[col].astype(str).str.lower() == str(val).lower()))
    return df[mask] if isinstance(mask, pd.Series) else df

# --------------------------
# Router: NL question -> MCP call(s)
# --------------------------
def route_and_execute(question: str) -> Dict[str, Any]:
    years = _extract_years(question)
    grain = _infer_grain(question)
    temporal = _infer_temporal(question)
    yoy = _is_yoy(question)
    topbot, n = _top_or_bottom(question)
    geo_filters = _find_geo_filters(question)

    # map (grain, temporal) -> file_id (using correct MCP server file IDs)
    file_id = {
        ("country", "year"): "country-year",
        ("country", "month"): "country-month",
        ("admin1", "year"): "admin1-year",
        ("admin1", "month"): "admin1-month",
        ("city", "year"): "city-year",
        ("city", "month"): "city-month",
    }[(grain, temporal)]

    if yoy:
        # Need exactly two years; if one year present, compare to previous
        if len(years) >= 2:
            base, compare = sorted(years)[:2]
        elif len(years) == 1:
            compare = years[0]
            base = compare - 1
        else:
            # default recent YoY window
            compare = 2023
            base = 2022

        key_col = {
            "country": "country_name",
            "admin1": "admin1_name",
            "city": "city_name"
        }[grain]

        payload = {
            "file_id": file_id,
            "key_col": key_col,
            "value_col": "emissions_tonnes",
            "base_year": base,
            "compare_year": compare,
            "top_n": n,
            "direction": "drop" if "drop" in question.lower() or topbot == "top" else "rise",
            "where": {}
        }
        # Optional geo narrowing
        if geo_filters:
            payload["where"].update(geo_filters)
        res = mcp_yoy(payload)
        res["_routed"] = {"file_id": file_id, "type": "yoy", "grain": grain, "temporal": temporal}
        return res

    # Non-YoY: regular query
    where: Dict[str, Any] = {}
    if temporal == "year":
        if len(years) >= 2:
            where["year"] = {"between": [min(years), max(years)]}
        elif len(years) == 1:
            where["year"] = years[0]
        else:
            where["year"] = {"between": [2019, 2023]}
    else:
        # monthly: force a sensible time window
        if len(years) == 1:
            where["year"] = years[0]
        elif len(years) >= 2:
            where["year"] = {"between": [min(years), max(years)]}
        else:
            where["year"] = {"between": [2021, 2023]}

    select = ["MtCO2", "year"]
    group_by = []
    order_by = "MtCO2 DESC"
    # choose name column
    name_col = {
        "country": "country_name",
        "admin1": "admin1_name",
        "city": "city_name"
    }[grain]
    select = [name_col, "year", "MtCO2"]
    group_by = [name_col, "year"]

    # add geography filters if present
    if geo_filters:
        where.update(geo_filters)

    payload = {
        "file_id": file_id,
        "select": select,
        "where": where,
        "group_by": group_by,
        "order_by": order_by,
        "limit": n
    }
    res = mcp_query(payload)
    res["_routed"] = {"file_id": file_id, "type": "query", "grain": grain, "temporal": temporal}
    return res

def render_dataframe_with_chart(res: Dict[str, Any], title: str):
    rows = res.get("rows", [])
    if not rows:
        st.info("No rows returned. Try adjusting the time window or filters.")
        return
    df = pd.DataFrame(rows)

    st.caption(f"Source: {res.get('meta', {}).get('source', 'EDGAR transport')}")
    
    # Limit display to first 1000 rows to prevent UI hanging
    display_df = df.head(1000)
    st.dataframe(display_df, use_container_width=True)
    
    if len(df) > 1000:
        st.info(f"Showing first 1000 rows out of {len(df)} total rows. Use the download button to get all data.")

    # Download CSV
    st.download_button(
        "⬇️ Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="results.csv",
        mime="text/csv",
        use_container_width=True
    )

    # Draw a sensible chart when 'year' present
    if "year" in df.columns:
        # If multiple names present, stack line chart by name
        name_cols = [c for c in ["country_name", "admin1_name", "city_name"] if c in df.columns]
        if name_cols:
            name_col = name_cols[0]
            ycol = "MtCO2" if "MtCO2" in df.columns else ("emissions_tonnes" if "emissions_tonnes" in df.columns else None)
            if ycol:
                # Limit chart data to prevent performance issues
                chart_df = df.head(500) if len(df) > 500 else df
                chart = (
                    alt.Chart(chart_df)
                    .mark_line(point=True)
                    .encode(
                        x="year:O",
                        y=alt.Y(f"{ycol}:Q", title=ycol),
                        color=alt.Color(f"{name_col}:N", legend=alt.Legend(title=name_col)),
                        tooltip=list(chart_df.columns)
                    )
                    .properties(height=300, title=title)
                )
                st.altair_chart(chart, use_container_width=True)
                if len(df) > 500:
                    st.caption("Chart shows first 500 rows for performance. Download full data for complete analysis.")

# --------------------------
# UI
# --------------------------
st.title("🌍 ClimateGPT — Transport Emissions QA")
st.write("Ask questions in plain English. ClimateGPT will analyze the data and provide natural language answers.")
with st.sidebar:
    st.header("Settings")
    MCP_URL = st.text_input("MCP base URL", value=MCP_URL)
    st.caption("Example: http://127.0.0.1:8000")
    if st.button("↻ Refresh manifest"):
        try:
            st.session_state["files"] = mcp_list_files()
            st.success("Manifest loaded.")
        except Exception as e:
            st.error(f"Failed to load manifest: {e}")

if "files" not in st.session_state:
    try:
        st.session_state["files"] = mcp_list_files()
    except Exception as e:
        st.session_state["files"] = []
        st.warning(f"Could not load manifest yet: {e}")

st.text_area("Available files (from /list_files):",
             value=json.dumps(st.session_state.get("files", []), indent=2)[:2000],
             height=160)

if "chat" not in st.session_state:
    st.session_state["chat"] = []

# Chat history
for role, msg in st.session_state["chat"]:
    with st.chat_message(role):
        st.markdown(msg)

prompt = st.chat_input("Ask about transport CO₂ (e.g., “Which countries had the biggest drop from 2019 to 2020?”)")
if prompt:
    st.session_state["chat"].append(("user", prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("ClimateGPT is analyzing your question..."):
            t0 = time.time()
            try:
                # Use ClimateGPT to process the question
                answer = process_climategpt_question(prompt)
                if answer and answer.strip():
                    st.markdown(answer)
                    st.caption(f"Response time: {time.time()-t0:.2f}s")
                else:
                    st.error("ClimateGPT returned an empty response. Please try again.")
            except Exception as e:
                st.error(f"Error: {e}")
                import traceback
                st.code(traceback.format_exc())

    st.rerun()