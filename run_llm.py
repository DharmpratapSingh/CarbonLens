import os, sys, json, requests, textwrap
from typing import Any, Dict
from dotenv import load_dotenv
from pathlib import Path
from requests.auth import HTTPBasicAuth

# Load .env
load_dotenv()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://erasmus.ai/models/climategpt_8b_test/v1")
MODEL = os.getenv("MODEL", "/cache/climategpt_8b_test")
API_KEY = os.getenv("OPENAI_API_KEY", "")  # expects "username:password" (e.g., ai:4climate)
USER, PASS = API_KEY.split(":", 1) if ":" in API_KEY else ("", "")

MCP_PORT = os.getenv("PORT", "8010")
MCP_BASE = f"http://127.0.0.1:{MCP_PORT}"
SYSTEM = Path("system_prompt.txt").read_text(encoding="utf-8") if os.path.exists("system_prompt.txt") else ""

if not SYSTEM.strip():
    SYSTEM = """
    You are ClimateGPT, a data-grounded assistant that must control tools by returning a single JSON object.
    Return ONLY a JSON object with:
      - "tool": one of ["list_files","get_schema","query","metrics.yoy"]
      - "args": the parameters for that tool.
    Schemas:
      - list_files: {"tool":"list_files","args":{}}
      - get_schema: {"tool":"get_schema","args":{"file_id": "<id>"}}
      - query: {"tool":"query","args":{
          "file_id": "<id>",
          "select": ["col1","col2",...],
          "where": { ... },            # optional filter object
          "group_by": ["colA","colB"], # optional
          "order_by": "col DESC",      # optional
          "limit": 10                  # optional
        }}
      - metrics.yoy: {"tool":"metrics.yoy","args":{
          "file_id": "<id>",
          "key_col": "<name column>",
          "value_col": "emissions_tonnes",
          "base_year": 2019,
          "compare_year": 2020,
          "top_n": 10,
          "direction": "rise"          # or "drop"
        }}
    Use annual tables by default:
      country -> transport_country_year
      admin1  -> transport_admin1_year
      city    -> transport_city_year
    If the user says monthly, use the corresponding *_month tables.
    Prefer returning MtCO2 in SELECT when available.
    """.strip()


def chat(system: str, user: str, temperature: float = 0.2) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        "temperature": temperature
    }
    r = requests.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={"Content-Type": "application/json"},
        data=json.dumps(payload),
        auth=HTTPBasicAuth(USER, PASS) if USER else None,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def exec_tool_call(tool_json: str) -> Dict[str, Any]:
    """
    Accepts a JSON string like:
    {"tool":"query","args":{...}}  or  {"tool":"metrics.yoy","args":{...}}
    and executes against our MCP FastAPI server.
    """
    # Try strict JSON first; if it fails, extract the first {...} block
    try:
        obj = json.loads(tool_json)
    except json.JSONDecodeError:
        start = tool_json.find("{")
        end = tool_json.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(tool_json[start:end+1])
        else:
            return {"error": "Model did not return valid JSON tool call.", "raw": tool_json}
    t = obj.get("tool")
    a = obj.get("args", {})

    if t == "list_files":
        return requests.get(f"{MCP_BASE}/list_files").json()
    if t == "get_schema":
        fid = a["file_id"]
        return requests.get(f"{MCP_BASE}/get_schema/{fid}").json()
    if t == "query":
        return requests.post(f"{MCP_BASE}/query", json=a).json()
    if t in ("metrics.yoy", "yoy"):
        return requests.post(f"{MCP_BASE}/metrics/yoy", json=a).json()

    return {"error": f"unknown tool '{t}'"}

def _ensure_mt(df_rows: Any) -> Any:
    try:
        if isinstance(df_rows, list) and df_rows and isinstance(df_rows[0], dict):
            for r in df_rows:
                if "MtCO2" not in r and "emissions_tonnes" in r and isinstance(r["emissions_tonnes"], (int, float)):
                    r["MtCO2"] = r["emissions_tonnes"] / 1e6
    except Exception:
        pass
    return df_rows

def summarize(result: Dict[str, Any], question: str) -> str:
    # add MtCO2 column if missing to reduce unit mistakes
    preview_obj = dict(result)
    if isinstance(preview_obj, dict) and "rows" in preview_obj:
        preview_obj["rows"] = _ensure_mt(preview_obj["rows"])
    rows_preview = json.dumps(preview_obj, ensure_ascii=False)

    prompt = textwrap.dedent(f"""
    You asked: {question}

    Using the JSON below (which includes rows and meta), write a concise answer:
    - If present, compute/compare as needed (YoY deltas, rankings).
    - Always cite: "Source: {result.get('meta',{}).get('table_id','?')}, EDGAR v2024 transport."
    - Use correct units (tonnes CO₂; optionally show MtCO₂ for big numbers).
    - Keep the answer crisp (3–6 sentences).

    JSON:
    {rows_preview}
    """).strip()

    return chat(SYSTEM, prompt, temperature=0.2)

def main():
    if len(sys.argv) < 2:
        print('Usage: uv run python run_llm.py "<your question>"')
        print('Example: uv run python run_llm.py "Which US state had the biggest drop in 2020 vs 2019?"')
        sys.exit(1)

    question = sys.argv[1]

    # 1) Ask the model to return ONLY a tool call JSON
    tool_call = chat(
        SYSTEM,
        question + "\n\nReturn ONLY a tool call JSON as per the schema. Do not include any prose."
    ).strip()

    # If the model didn't return JSON, nudge once with a strict reminder
    if not (tool_call.startswith("{") and '"tool"' in tool_call):
        tool_call = chat(
            SYSTEM,
            "Return ONLY a tool call JSON for this question:\n" + question + "\n\nReminder: never use SQL strings; use the JSON schema described."
        ).strip()

    print("\n--- TOOL CALL ---")
    print(tool_call)

    # 2) Execute tool call
    result = exec_tool_call(tool_call)
    print("\n--- TOOL RESULT (first 10 rows) ---")
    if isinstance(result, dict) and "rows" in result:
        preview = {**result, "rows": result["rows"][:10]}
        print(json.dumps(preview, indent=2)[:2000])
    else:
        print(json.dumps(result, indent=2)[:2000])

    # 3) Summarize via LLM
    answer = summarize(result, question)
    print("\n=== ANSWER ===")
    print(answer)

if __name__ == "__main__":
    main()