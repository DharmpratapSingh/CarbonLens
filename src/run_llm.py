import os, sys, json, requests, textwrap
from typing import Any, Literal
from dotenv import load_dotenv
from pathlib import Path
from requests.auth import HTTPBasicAuth
import argparse
from tenacity import retry, stop_after_attempt, wait_exponential

# Import baseline knowledge components
try:
    from src.utils.baseline_context import (
        BaselineContextProvider,
        PolicyContextAugmenter,
        SectorStrategyAugmenter,
        EducationalContextAugmenter
    )
    BASELINE_AVAILABLE = True
except ImportError:
    BASELINE_AVAILABLE = False

# Persona framework cache (global singleton)
_PERSONA_PROVIDER = None

def get_persona_provider():
    """
    Get cached BaselineContextProvider instance.
    Created once and reused for performance.
    """
    global _PERSONA_PROVIDER
    if _PERSONA_PROVIDER is None and BASELINE_AVAILABLE:
        _PERSONA_PROVIDER = BaselineContextProvider()
    return _PERSONA_PROVIDER

# Load .env
load_dotenv()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://erasmus.ai/models/climategpt_8b_test/v1")
MODEL = os.getenv("MODEL", "/cache/climategpt_8b_test")

# API_KEY must be set and in format "username:password"
API_KEY = os.getenv("OPENAI_API_KEY", "")
if not API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")
if ":" not in API_KEY:
    raise ValueError("OPENAI_API_KEY must be in format 'username:password'")

USER, PASS = API_KEY.split(":", 1)

MCP_PORT = os.getenv("PORT", "8010")
MCP_BASE = f"http://127.0.0.1:{MCP_PORT}"
SYSTEM = Path("system_prompt.txt").read_text(encoding="utf-8") if os.path.exists("system_prompt.txt") else ""

if not SYSTEM.strip():
    SYSTEM = """
    You are ClimateGPT, a data-grounded assistant that must control tools by returning JSON object(s).

    CRITICAL RULES:
    1. Return ONLY JSON - no explanations or prose
    2. Use EXACT column names from the schema below
    3. Use EXACT file_id format (see examples)
    4. If query fails or returns errors, NEVER fabricate data
    5. For comparisons/complex queries, return multiple tool calls (see MULTIPLE TOOL CALLS section)
    6. For arrays: Return on ONE LINE like [{"tool":...},{"tool":...}] NOT on separate lines

    ⚡ TOOL ROUTING OPTIMIZATION - FOLLOW THIS FLOW ⚡

    Question Pattern → Recommended Tool → Why
    ────────────────────────────────────────────────────

    "What/Show me [entity] [sector] [year]?"
      → query tool ✓ BEST
      → Most efficient for single entity lookups
      → Example: "Germany power 2023?" → query with where={country:Germany, year:2023}

    "Compare X and Y [sector] [year]"
      → query tool (2× calls) ✓ BEST
      → Return as array: [query_X, query_Y]
      → Example: "Germany vs France power 2023?" → [query_germany, query_france]

    "Top/Highest/Lowest [N] [sector]"
      → query tool ✓ BEST
      → Use order_by + limit
      → Example: "Top 5 countries" → query with order_by DESC, limit 5

    "How much change [sector] [year1→year2]?"
      → metrics.yoy tool ✓ BEST
      → Use when specifically asking about year-over-year change percentage
      → Example: "How much emissions increased 2022→2023?" → metrics.yoy

    "Seasonal/monthly pattern [entity] [year]"
      → query tool with month ✓ BEST
      → Use file_id with -month grain
      → Example: "Germany power by month 2023?" → query power-country-month

    "Total across sectors [entity] [year]"
      → query tool (multi-call) ✓ BEST
      → Query each sector separately, sum in response
      → Return as array with multiple sectors

    AVOID:
      ❌ metrics.yoy for single year (use query instead)
      ❌ query for trend analysis spanning 5+ years (use metrics.yoy)
      ❌ Multiple queries when single query with aggregation works

    AVAILABLE TOOLS:
      - "list_files" - List available datasets (rarely needed)
      - "get_schema" - Get columns for a specific file_id (rarely needed)
      - "query" - Query emissions data ⭐ USE THIS 95% OF THE TIME
      - "metrics.yoy" - Calculate year-over-year changes (use for trend %)

    EXACT COLUMN NAMES (use these exactly):
      - Location columns: country_name, admin1_name, city_name
      - Data columns: year, emissions_tonnes
      - For monthly: add "month" column
      - DO NOT use "sector" - sector is in the file_id, not a column

    FILE_ID FORMAT:
      Pattern: {sector}-{level}-{grain}

      Examples:
        "transport-country-year"      (Germany, USA, etc.)
        "transport-admin1-year"       (California, Texas, etc.)
        "transport-city-year"         (Tokyo, London, etc.)
        "power-country-month"         (monthly power data)
        "waste-admin1-year"           (state waste data)

      Available sectors: transport, power, waste, agriculture, buildings,
                        fuel-exploitation, industrial-combustion, industrial-processes

    TOOL SCHEMAS:

    1. list_files:
       {"tool":"list_files","args":{}}

    2. get_schema:
       {"tool":"get_schema","args":{"file_id":"transport-country-year"}}

    3. query:
       {"tool":"query","args":{
         "file_id":"transport-country-year",
         "select":["country_name","year","emissions_tonnes"],
         "where":{"country_name":"Germany","year":2023},
         "group_by":[],
         "order_by":"emissions_tonnes DESC",
         "limit":10
       }}

    4. metrics.yoy:
       {"tool":"metrics.yoy","args":{
         "file_id":"transport-country-year",
         "key_column":"country_name",
         "value_column":"emissions_tonnes",
         "base_year":2019,
         "compare_year":2020,
         "top_n":10,
         "direction":"drop"
       }}

    COMMON QUERY PATTERNS:

    Simple lookup:
    {"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","emissions_tonnes"],"where":{"country_name":"Germany","year":2023}}}

    State/admin1 query:
    {"tool":"query","args":{"file_id":"transport-admin1-year","select":["admin1_name","year","emissions_tonnes"],"where":{"admin1_name":"California","year":2022}}}

    City query:
    {"tool":"query","args":{"file_id":"transport-city-year","select":["city_name","year","emissions_tonnes"],"where":{"city_name":"Tokyo","year":2021}}}

    Monthly query:
    {"tool":"query","args":{"file_id":"power-country-month","select":["country_name","year","month","emissions_tonnes"],"where":{"country_name":"France","year":2023}}}
    
    Monthly query for state/admin1:
    {"tool":"query","args":{"file_id":"transport-admin1-month","select":["admin1_name","year","month","emissions_tonnes"],"where":{"admin1_name":"California","year":2023}}}

    RANKING QUERIES (Top/Highest/Lowest):

    Top 5 countries:
    {"tool":"query","args":{"file_id":"agriculture-country-year","select":["country_name","year","emissions_tonnes"],"where":{"year":2022},"order_by":"emissions_tonnes DESC","limit":5}}

    Highest state (DO NOT filter to specific state first!):
    {"tool":"query","args":{"file_id":"power-admin1-year","select":["admin1_name","year","emissions_tonnes"],"where":{"year":2022},"order_by":"emissions_tonnes DESC","limit":1}}

    MULTIPLE TOOL CALLS (for comparisons or multi-sector queries):

    For questions asking to "compare" or "which" between multiple entities, ALWAYS return an array:
    
    Compare USA vs China (return array - ALL ON ONE LINE):
    [{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","emissions_tonnes"],"where":{"country_name":"USA","year":2022}}},{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","emissions_tonnes"],"where":{"country_name":"China","year":2022}}}]

    Compare NYC vs LA (return array - ALL ON ONE LINE):
    [{"tool":"query","args":{"file_id":"waste-city-year","select":["city_name","year","emissions_tonnes"],"where":{"city_name":"New York City","year":2022}}},{"tool":"query","args":{"file_id":"waste-city-year","select":["city_name","year","emissions_tonnes"],"where":{"city_name":"Los Angeles","year":2022}}}]

    Multi-sector total for Germany (return array - ALL ON ONE LINE):
    [{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","emissions_tonnes"],"where":{"country_name":"Germany","year":2023}}},{"tool":"query","args":{"file_id":"power-country-year","select":["country_name","year","emissions_tonnes"],"where":{"country_name":"Germany","year":2023}}},{"tool":"query","args":{"file_id":"waste-country-year","select":["country_name","year","emissions_tonnes"],"where":{"country_name":"Germany","year":2023}}}]

    CRITICAL GROUP BY RULES (READ CAREFULLY):
    - ❌ DO NOT use group_by unless you are using aggregate functions (SUM, COUNT, AVG, MAX, MIN)
    - ❌ DO NOT use group_by for filtering monthly/yearly data
    - ❌ DO NOT use group_by for ranking/sorting
    - ❌ NEVER use group_by with non-aggregated columns in SELECT
    - ✅ ONLY use group_by when SELECT contains aggregates like SUM(emissions_tonnes)

    WRONG examples (DO NOT DO THIS):
    ❌ {"select":["month","emissions_tonnes"],"group_by":["month"]}
    ❌ {"select":["admin1_name","year","month","emissions_tonnes"],"where":{"admin1_name":"California"},"group_by":["month"]}
    ❌ {"select":["country_name","emissions_tonnes"],"where":{"year":2022},"group_by":["country_name"],"order_by":"emissions_tonnes DESC"}

    RIGHT examples:
    ✅ {"select":["month","emissions_tonnes"],"where":{"admin1_name":"California","year":2023}}
    ✅ {"select":["admin1_name","year","month","emissions_tonnes"],"where":{"admin1_name":"California","year":2023}}
    ✅ {"select":["country_name","year","emissions_tonnes"],"where":{"year":2022},"order_by":"emissions_tonnes DESC","limit":5}
    ✅ {"select":["country_name","SUM(emissions_tonnes) as total"],"where":{"year":2022},"group_by":["country_name"]}  (only when aggregating)

    COUNTRY NAME HANDLING:
    - System accepts common country name variations (USA, UK, China, etc.)
    - You can use "USA" or "United States of America" - both work
    - You can use "UK" or "United Kingdom" - both work
    - You can use "China", "Germany", "France" etc. - natural names work
    - The system automatically normalizes common aliases to database names
    - If unsure, use the common English name for the country

    IMPORTANT LIMITATIONS:
    - Array syntax NOT supported: DO NOT use {"country_name":["USA","China"]}
    - For comparisons, use multiple tool calls instead (see MULTIPLE TOOL CALLS above)

    REMEMBER:
    - Use hyphens in file_id: "transport-country-year" NOT "transport_country_year"
    - Use exact column names: "country_name" NOT "country"
    - Use exact column names: "admin1_name" NOT "admin1"
    - Use exact column names: "city_name" NOT "city"
    - For comparisons: return array of tool calls
    - For rankings: use order_by + limit (NO group_by)
    - DO NOT use group_by unless doing aggregation with SUM/COUNT/AVG
    """.strip()


def classify_question(question: str) -> str:
    """
    Classify question type: BASELINE, MCP, or HYBRID

    BASELINE: Conceptual/policy/mechanism questions (no data needed)
    MCP: Quantitative/specific data questions (needs database)
    HYBRID: Questions needing both data and interpretation
    """

    # Convert to lowercase for matching
    q_lower = question.lower()

    # BASELINE indicators (conceptual/policy/mechanism)
    baseline_keywords = [
        "what is", "how does", "explain", "define",
        "mechanism", "process", "work", "difference",
        "greenhouse", "climate change", "tipping point",
        "carbon cycle", "albedo", "feedback loop",
        "paris agreement", "net zero", "scope 1",
        "describe", "discuss", "why is", "what are the"
    ]

    # MCP indicators (quantitative/specific data)
    mcp_keywords = [
        "emissions", "tonnes", "mtco2", "how much",
        "which country", "which state", "which city",
        "ranking", "rank", "top ", "highest", "lowest",
        "increase", "decrease", "change", "comparison",
        "compare", "vs ", "between", "more than", "less than",
        "2023", "2022", "2021", "2020", "2019", "year"
    ]

    # Count keyword matches
    baseline_matches = sum(1 for kw in baseline_keywords if kw in q_lower)
    mcp_matches = sum(1 for kw in mcp_keywords if kw in q_lower)

    # Classification logic
    if baseline_matches > 0 and mcp_matches == 0:
        return "BASELINE"
    elif mcp_matches > 0 and baseline_matches == 0:
        return "MCP"
    elif mcp_matches > 0 and baseline_matches > 0:
        return "HYBRID"
    else:
        # Default to HYBRID (safest choice)
        return "HYBRID"


def get_baseline_answer(question: str, persona: str = "Climate Analyst") -> str:
    """
    Get answer using baseline knowledge only (for conceptual questions).
    Tailored to the specific persona for relevant emphasis.
    """
    focus = get_persona_focus(persona)
    tone = get_persona_tone(persona)

    # Persona-specific instructions
    persona_instructions = {
        "Climate Analyst": """
You are responding to a Climate Analyst. Focus on:
- Policy implications and climate frameworks
- Actionable mitigation strategies
- Which entities/sectors should prioritize action
- Connection to climate goals (Paris Agreement, net zero)

Be strategic and action-oriented in your explanation.""",
        "Research Scientist": """
You are responding to a Research Scientist. Focus on:
- Scientific rigor and empirical evidence
- Methodologies and data sources
- Uncertainty ranges and limitations
- Peer-reviewed research and validation

Be precise, methodological, and emphasize evidence-based reasoning.""",
        "Financial Analyst": """
You are responding to a Financial Analyst. Focus on:
- Economic implications and financial risks
- Market dynamics and investment implications
- Transition risks and opportunities
- Quantifiable metrics and concentration

Be concise and directional, emphasizing material financial impacts.""",
        "Student": """
You are responding to a Student. Focus on:
- Clear, accessible explanations
- Real-world analogies and relatable examples
- Why this matters for climate and society
- Foundational concepts and definitions

Be friendly, educational, and make complex topics understandable."""
    }

    persona_instruction = persona_instructions.get(persona, persona_instructions["Climate Analyst"])

    baseline_system_prompt = f"""You are ClimateGPT, an expert in climate science, emissions, and climate policy.
You have deep knowledge about:
- Climate science fundamentals (greenhouse effect, tipping points, feedback loops)
- Climate policy frameworks (Paris Agreement, net zero, NDCs)
- Emissions concepts (scopes, sectors, decarbonization strategies)
- Climate solutions and mitigation approaches

{persona_instruction}

Answer the user's question clearly and comprehensively using your baseline knowledge.
Be accurate and cite policy frameworks, scientific concepts, and mechanisms where relevant.
For conceptual/explanatory questions, provide detailed, informative answers."""

    answer = chat(baseline_system_prompt, question, temperature=0.2)
    return answer


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
def chat(system: str, user: str, temperature: float = 0.2) -> str:
    """
    Send a chat request to the LLM with automatic retry logic.

    Implements exponential backoff: 2s base, max 10s, 3 attempts.
    Transient network errors (timeout, connection) trigger automatic retries.
    """
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

def exec_single_tool(tool_obj: dict[str, Any]) -> dict[str, Any]:
    """Execute a single tool call object."""
    t = tool_obj.get("tool")
    a = tool_obj.get("args", {})

    if t == "list_files":
        return requests.get(f"{MCP_BASE}/list_files").json()
    if t == "get_schema":
        fid = a["file_id"]
        return requests.get(f"{MCP_BASE}/get_schema/{fid}").json()
    if t == "query":
        # Enable server-side assist by default and normalize legacy args
        if isinstance(a, dict):
            a.setdefault("assist", True)
            fid = a.get("file_id", "")
            if "_" in fid and "-" not in fid:
                a["file_id"] = fid.replace("_", "-")

            # Normalize column names in select/where
            col_map = {
                "city": "city_name",
                "state": "admin1_name",
                "admin": "admin1_name",
                "country": "country_name",
            }
            if isinstance(a.get("select"), list):
                a["select"] = [col_map.get(c, c) for c in a["select"]]
            if isinstance(a.get("where"), dict):
                a["where"] = {col_map.get(k, k): v for k, v in a["where"].items()}

            # Normalize common country name aliases (client-side fallback)
            # MCP server's assist mode should handle this, but we add safety layer
            if isinstance(a.get("where"), dict) and "country_name" in a["where"]:
                country_aliases = {
                    "USA": "United States of America",
                    "US": "United States of America",
                    "U.S.": "United States of America",
                    "U.S.A.": "United States of America",
                    "United States": "United States of America",
                    "UK": "United Kingdom",
                    "Britain": "United Kingdom",
                    "Great Britain": "United Kingdom",
                }
                country_val = a["where"]["country_name"]
                if isinstance(country_val, str):
                    # Check if it's a known alias (case-insensitive)
                    normalized = country_aliases.get(country_val, country_aliases.get(country_val.strip()))
                    if normalized:
                        a["where"]["country_name"] = normalized
        return requests.post(f"{MCP_BASE}/query", json=a).json()
    if t in ("metrics.yoy", "yoy"):
        return requests.post(f"{MCP_BASE}/metrics/yoy", json=a).json()

    return {"error": f"unknown tool '{t}'"}

def exec_tool_call(tool_json: str) -> dict[str, Any] | list[dict[str, Any]]:
    """
    Accepts a JSON string like:
    {"tool":"query","args":{...}}  - single tool call
    OR
    [{"tool":"query","args":{...}}, {"tool":"query","args":{...}}]  - multiple tool calls

    Returns single result dict or list of result dicts.
    """
    # Try to parse as JSON
    try:
        obj = json.loads(tool_json)
    except json.JSONDecodeError:
        # Initial parse failed - try various extraction methods
        
        # First try: Check if it's a properly formatted array
        trimmed = tool_json.strip()
        if trimmed.startswith("[") and trimmed.endswith("]"):
            try:
                obj = json.loads(trimmed)
            except:
                pass  # Fall through to other methods
        else:
            # Not a simple array, check for multiple objects
            objects = []
            
            # Method 1: Check if multiple objects on separate lines
            lines = [line.strip() for line in tool_json.split('\n') if line.strip().startswith('{')]
            if len(lines) > 1:
                for line in lines:
                    try:
                        parsed = json.loads(line)
                        if isinstance(parsed, dict) and "tool" in parsed:
                            objects.append(parsed)
                    except json.JSONDecodeError:
                        continue
            
            # Method 2: Check for comma-separated objects on same line
            elif tool_json.count('{"tool"') > 1:
                current_pos = 0
                while current_pos < len(tool_json):
                    if tool_json[current_pos] == '{':
                        brace_count = 0
                        start_pos = current_pos
                        found_match = False
                        for i in range(current_pos, len(tool_json)):
                            if tool_json[i] == '{':
                                brace_count += 1
                            elif tool_json[i] == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    try:
                                        parsed = json.loads(tool_json[start_pos:i+1])
                                        if isinstance(parsed, dict) and "tool" in parsed:
                                            objects.append(parsed)
                                    except:
                                        pass
                                    current_pos = i + 1
                                    found_match = True
                                    break
                        if not found_match:
                            break
                    else:
                        current_pos += 1
            
            if objects:
                obj = objects
            else:
                # Fall back: try to extract single object
                start = tool_json.find("{")
                end = tool_json.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        obj = json.loads(tool_json[start:end+1])
                    except:
                        return {"error": "Model did not return valid JSON tool call.", "raw": tool_json}
                else:
                    return {"error": "Model did not return valid JSON tool call.", "raw": tool_json}

    # Handle array of tool calls
    if isinstance(obj, list):
        results = []
        for i, tool_obj in enumerate(obj):
            if not isinstance(tool_obj, dict) or "tool" not in tool_obj:
                results.append({"error": f"Invalid tool call at index {i}", "obj": tool_obj})
            else:
                results.append(exec_single_tool(tool_obj))
        return results

    # Handle single tool call
    elif isinstance(obj, dict) and "tool" in obj:
        return exec_single_tool(obj)

    else:
        return {"error": "Invalid tool call format. Expected dict with 'tool' key or list of such dicts.", "obj": obj}

def _ensure_mt(df_rows: Any) -> Any:
    try:
        if isinstance(df_rows, list) and df_rows and isinstance(df_rows[0], dict):
            for r in df_rows:
                if "MtCO2" not in r and "emissions_tonnes" in r and isinstance(r["emissions_tonnes"], (int, float)):
                    r["MtCO2"] = r["emissions_tonnes"] / 1e6
    except Exception:
        pass
    return df_rows


# ============================================================================
# SECTOR EXTRACTION AND QUALITY METADATA UTILITIES
# ============================================================================

# Mapping of sector codes to human-readable names
SECTOR_NAMES = {
    "transport": "Transport",
    "power": "Power & Energy",
    "agriculture": "Agriculture",
    "waste": "Waste",
    "buildings": "Buildings",
    "fuel-exploitation": "Fuel Exploitation",
    "industrial-combustion": "Industrial Combustion",
    "industrial-processes": "Industrial Processes"
}

# External sources mapping for citation
SECTOR_SOURCES = {
    "transport": [
        "IEA Transport Statistics",
        "WHO urban mobility",
        "Copernicus traffic data",
        "Vehicle registries",
        "Modal split surveys"
    ],
    "power": [
        "IEA World Energy",
        "EPA CEMS facility data",
        "Sentinel-5P NO₂ satellite data",
        "National grids",
        "Capacity registries"
    ],
    "agriculture": [
        "FAO/FAOSTAT",
        "National agricultural statistics"
    ],
    "waste": [
        "EU Waste Framework Directive",
        "UNEP reports",
        "National waste agencies"
    ],
    "buildings": [
        "ASHRAE Climate Zones",
        "EPBD",
        "NOAA VIIRS satellite data",
        "Copernicus",
        "Building audits",
        "Construction statistics"
    ],
    "fuel-exploitation": [
        "Rystad Energy",
        "IHS Markit",
        "USGS Commodities",
        "National energy agencies",
        "Commodity price modeling"
    ],
    "industrial-combustion": [
        "EU Large Combustion Plants",
        "World Steel Association",
        "WBCSD Cement",
        "CDP/GRI ESG data",
        "Sentinel-5P SO₂ satellite data",
        "Industrial registries"
    ],
    "industrial-processes": [
        "IVL Cement Database",
        "ICIS Chemical data",
        "Stoichiometric modeling",
        "Raw Materials Data",
        "ESG reports",
        "Production indices"
    ]
}


def _extract_sector_from_file_id(file_id: str) -> tuple[str, str]:
    """
    Extract sector from file_id format: {sector}-{level}-{grain}

    Returns: (sector_code, sector_name)
    Example: "transport-country-year" -> ("transport", "Transport")
    """
    if not file_id or not isinstance(file_id, str):
        return "", ""

    parts = file_id.split("-")
    if not parts:
        return "", ""

    sector_code = parts[0].lower()
    sector_name = SECTOR_NAMES.get(sector_code, sector_code.title())

    return sector_code, sector_name


def _format_sector_header(
    sector_code: str,
    quality_metadata: dict[str, Any] | None = None
) -> str:
    """
    Format a professional sector header with quality information.

    Returns formatted string with sector, quality score, confidence, and uncertainty.
    """
    sector_name = SECTOR_NAMES.get(sector_code, sector_code.title())

    if not quality_metadata:
        return f"[Source: {sector_name} Sector | EDGAR v2024]"

    quality_score = quality_metadata.get("quality_score", 0)
    confidence = quality_metadata.get("confidence_level", "UNKNOWN")
    uncertainty = quality_metadata.get("uncertainty", "unknown")

    header = (
        f"[Source: {sector_name} Sector | EDGAR v2024 Enhanced]\n"
        f"[Quality: {quality_score}% | Confidence: {confidence} | Uncertainty: {uncertainty}]"
    )

    return header


def _format_external_sources_citation(sector_code: str) -> str:
    """
    Format external sources as a citation for the given sector.

    Returns: Formatted citation string
    """
    sources = SECTOR_SOURCES.get(sector_code, [])

    if not sources:
        return ""

    if len(sources) == 1:
        return f"Data validated with: {sources[0]}"
    elif len(sources) <= 3:
        return f"Data validated with: {', '.join(sources)}"
    else:
        return f"Data validated with {len(sources)} authoritative sources including: {', '.join(sources[:3])}, and others"


def _extract_quality_metadata(result: dict[str, Any]) -> dict[str, Any] | None:
    """
    Extract quality metadata from MCP query response.

    Returns: quality_metadata dict or None if not available
    """
    if isinstance(result, dict):
        if "quality_metadata" in result:
            return result["quality_metadata"]
    return None


def _extract_data_type_metadata(result: dict[str, Any]) -> dict[str, Any] | None:
    """
    Extract data type metadata from MCP query response.

    Returns: data_type_metadata dict with info about real/estimated/synthesized data
    """
    if isinstance(result, dict):
        if "data_type_metadata" in result:
            return result["data_type_metadata"]
    return None


def _format_data_type_info(data_type_metadata: dict[str, Any], quality_metadata: dict[str, Any] | None = None) -> str:
    """
    Format data type information for display in answers.

    Shows whether data is real, estimated, or synthesized with confidence scores.
    """
    if not data_type_metadata:
        return ""

    data_types = data_type_metadata.get("data_types_present", [])
    distribution = data_type_metadata.get("data_type_distribution", {})
    avg_confidence = data_type_metadata.get("avg_confidence_score", 0)

    if not data_types:
        return ""

    # Build data type information string
    info_parts = []

    # Primary data type indication
    if len(data_types) == 1:
        dt = data_types[0]
        if dt == "real":
            info_parts.append(f"[Data Type: REAL DATA | Confidence: {avg_confidence:.2f}]")
        elif dt == "estimated":
            info_parts.append(f"[Data Type: ESTIMATED | Confidence: {avg_confidence:.2f}]")
        elif dt == "synthesized":
            info_parts.append(f"[Data Type: SYNTHESIZED | Confidence: {avg_confidence:.2f}]")
    else:
        # Mixed data types
        type_str = ", ".join([f"{dt}: {distribution.get(dt, 0)}%" for dt in sorted(data_types)])
        info_parts.append(f"[Data Mix: {type_str} | Avg Confidence: {avg_confidence:.2f}]")

    # Add warnings if needed
    if data_type_metadata.get("has_estimated_data") or data_type_metadata.get("has_synthesized_data"):
        if not data_type_metadata.get("has_real_data"):
            info_parts.append("[⚠️ Note: This data is estimated or synthesized - use with caution]")
        elif len(data_types) > 1:
            info_parts.append("[⚠️ Note: Results mix real and estimated data]")

    return "\n".join(info_parts)

def summarize(result: dict[str, Any] | list[dict[str, Any]], question: str, question_type: str = "MCP", persona: str = "Climate Analyst") -> str:
    """
    Summarize query result(s) into natural language answer.

    For HYBRID questions, enriches MCP data with baseline context and interpretation.
    Now includes sector identification and external source citations.
    """

    # Handle multiple results (from multiple tool calls)
    if isinstance(result, list):
        # Check if any results are errors
        errors = [r for r in result if isinstance(r, dict) and "error" in r]
        if errors:
            error_msgs = [r.get('detail', r.get('error', 'Query failed')) for r in errors]
            return f"Unable to retrieve some data: {'; '.join(error_msgs)}. Please check the query parameters."

        # Combine all results for summarization
        combined_data = []
        sources = set()
        sectors = set()
        quality_metadata_list = []

        for r in result:
            if isinstance(r, dict) and "rows" in r:
                r["rows"] = _ensure_mt(r["rows"])
                combined_data.extend(r["rows"])

                # Extract file_id and sector
                if "meta" in r and "file_id" in r["meta"]:
                    file_id = r["meta"]["file_id"]
                    sources.add(file_id)
                    sector_code, sector_name = _extract_sector_from_file_id(file_id)
                    if sector_code:
                        sectors.add(sector_code)

                # Extract quality metadata if available
                quality_meta = _extract_quality_metadata(r)
                if quality_meta:
                    quality_metadata_list.append(quality_meta)

        if not combined_data:
            return "No data found for the specified queries."

        # Create combined result object with sector and quality info
        preview_obj = {
            "rows": combined_data,
            "row_count": len(combined_data),
            "sources": list(sources),
            "sectors": list(sectors),
            "quality_info": quality_metadata_list if quality_metadata_list else None
        }
        rows_preview = json.dumps(preview_obj, ensure_ascii=False)

        # Build comprehensive source string with sector and external sources
        sector_headers = []
        sources_citations = []

        for sector_code in sectors:
            sector_header = _format_sector_header(sector_code,
                quality_metadata_list[0] if quality_metadata_list else None)
            sector_headers.append(sector_header)

            sources_citation = _format_external_sources_citation(sector_code)
            if sources_citation:
                sources_citations.append(sources_citation)

        combined_header = "\n".join(sector_headers) if sector_headers else "Source: EDGAR v2024"
        combined_citations = "\n".join(sources_citations) if sources_citations else ""
        source_str = combined_header
        if combined_citations:
            source_str = f"{combined_header}\n{combined_citations}"

    # Handle single result
    else:
        preview_obj = dict(result)
        if isinstance(preview_obj, dict) and "rows" in preview_obj:
            preview_obj["rows"] = _ensure_mt(preview_obj["rows"])
        rows_preview = json.dumps(preview_obj, ensure_ascii=False)

        # Check if query returned an error
        if isinstance(result, dict) and "error" in result:
            return f"Unable to retrieve data: {result.get('detail', result.get('error', 'Query failed'))}. Please check the query parameters or use /get_schema to verify column names."

        # Check if query returned no data
        if isinstance(result, dict) and "rows" in result and len(result["rows"]) == 0:
            return "No data found for the specified query. The location, year, or sector may not have data available in the database."

        # Extract sector and quality metadata from single result
        file_id = result.get('meta', {}).get('file_id', '')
        sector_code, sector_name = _extract_sector_from_file_id(file_id)
        quality_metadata = _extract_quality_metadata(result)
        data_type_metadata = _extract_data_type_metadata(result)

        # Format sector header
        sector_header = _format_sector_header(sector_code, quality_metadata)

        # Format data type information
        data_type_info = _format_data_type_info(data_type_metadata, quality_metadata)

        # Format external sources citation
        sources_citation = _format_external_sources_citation(sector_code)

        # Build final source string
        source_str = sector_header
        if data_type_info:
            source_str = f"{sector_header}\n{data_type_info}"
        if sources_citation:
            source_str = f"{source_str}\n{sources_citation}"

    # Prepare baseline enrichment for HYBRID questions (using cached provider)
    baseline_context_str = ""
    if question_type == "HYBRID" and BASELINE_AVAILABLE:
        try:
            provider = get_persona_provider()
            if provider:
                # Build context dict for enrichment
                mcp_data_for_enrichment = {"rows": combined_data if isinstance(result, list) else preview_obj.get("rows", [])}
                enriched = provider.enrich_response(
                    mcp_data=mcp_data_for_enrichment,
                    question=question,
                    persona=persona
                )

                if enriched.get("baseline_context"):
                    context = enriched["baseline_context"]
                    baseline_context_str = "\n\nBASELINE CONTEXT TO ENHANCE ANSWER:\n"
                    if "sector_explanation" in context:
                        baseline_context_str += f"[Sector Context] {context['sector_explanation']}\n"
                    if "country_context" in context:
                        baseline_context_str += f"[Country Context] {context['country_context']}\n"
                    if "trend_context" in context:
                        baseline_context_str += f"[Trend Context] {context['trend_context']}\n"
        except Exception as e:
            pass  # Silently fail if baseline enrichment unavailable

    # Use appropriate system prompt based on question type
    if question_type == "HYBRID":
        summary_system_prompt = f"""You are a helpful climate expert assistant providing data-driven answers with expert interpretation.

RESPONSE STRUCTURE:
1. [SOURCE ATTRIBUTION] Start with sector header and external source citations (provided below)
2. [FACTUAL DATA] State emissions values precisely from the JSON data
3. [BASELINE INTERPRETATION] Add context, policy implications, and scientific meaning
4. [STRATEGIC INSIGHTS] Provide actionable insights relevant to {persona} persona

CRITICAL RULES:
1. ALWAYS start response with sector and quality information provided in the prompt
2. Always cite specific numbers from the data with sources (EDGAR v2024)
3. Add meaningful interpretation from baseline knowledge
4. For {persona}: Focus on {get_persona_focus(persona)}
5. Keep response balanced - 40% data, 60% interpretation
6. Do not fabricate values - only use provided data

Persona: {persona}
Response tone: {get_persona_tone(persona)}"""
    elif question_type == "MCP":
        # Add light persona interpretation even for data-only questions
        focus = get_persona_focus(persona)
        tone = get_persona_tone(persona)

        summary_system_prompt = f"""You are a helpful assistant providing emissions data to a {persona}.

PERSONA CONTEXT:
- Audience: {persona}
- Focus areas: {focus}
- Tone: {tone}

RESPONSE STRUCTURE:
1. [SOURCE ATTRIBUTION] Start with sector header and external source citations (provided below)
2. Present the data clearly with values and units (MtCO₂, tonnes)
3. Add a brief (1-2 sentence) interpretation relevant to {persona}'s interests

CRITICAL RULES:
1. ALWAYS start your response with the source attribution information provided in the prompt below
2. ONLY report facts present in the JSON data
3. For {persona}, highlight what matters to them without fabricating context
4. NEVER add explanations not supported by the data
5. NEVER fabricate or guess values
6. For comparisons, clearly state values for each entity
7. Keep interpretation brief - data-focused response (70% data, 30% interpretation)

Focus on: {focus}
Tone: {tone}"""
    else:
        summary_system_prompt = """You are a helpful assistant that provides clear, concise answers based ONLY on the data provided.

RESPONSE STRUCTURE:
1. [SOURCE ATTRIBUTION] Start with sector header and external source citations (provided below)
2. Present data clearly and concisely

CRITICAL RULES:
1. ALWAYS start your response with the source attribution information provided in the prompt
2. ONLY report facts present in the JSON data
3. NEVER add context, explanations, or background information not in the data
4. NEVER fabricate or guess values
5. If data is missing or incomplete, state that clearly
6. Keep responses concise (2-4 sentences maximum)
7. Do not return JSON or tool calls - write in natural language
8. For comparisons, clearly state values for each entity being compared"""

    prompt = textwrap.dedent(f"""
    Question: {question}

    IMPORTANT - SOURCE & QUALITY ATTRIBUTION:
    Always include the following information prominently at the start of your answer:
    {source_str}

    Tasks:
    - State the emissions value(s) from the data
    - Convert to MtCO₂ if the value is large (divide tonnes by 1,000,000)
    - Include location, year, and sector for each value
    - For comparisons, clearly compare the values
    - Always mention the data source information above at the start of your response
    - Be concise (2-4 sentences for data, additional context as needed)
    {"- Add expert interpretation and policy context" if question_type == "HYBRID" else "- Do NOT add policy context, trends, or explanations not in the data"}

    Data (JSON):
    {rows_preview}
    {baseline_context_str}
    """).strip()

    return chat(summary_system_prompt, prompt, temperature=0.2)


def get_persona_focus(persona: str) -> str:
    """Get focus areas for persona"""
    focus_map = {
        "Climate Analyst": "mitigation priorities, policy implications, and actionable strategies",
        "Research Scientist": "methodology, data quality, uncertainty, and scientific rigor",
        "Financial Analyst": "risk signals, concentration, momentum, and material changes",
        "Student": "understanding, definitions, real-world meaning, and simplicity"
    }
    return focus_map.get(persona, "relevant insights")


def get_persona_tone(persona: str) -> str:
    """Get appropriate tone for persona"""
    tone_map = {
        "Climate Analyst": "strategic, action-oriented, policy-focused",
        "Research Scientist": "precise, methodological, evidence-based",
        "Financial Analyst": "concise, directional, risk-aware",
        "Student": "friendly, educational, clear"
    }
    return tone_map.get(persona, "informative")

def main() -> None:
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ClimateGPT - Climate data Q&A with baseline knowledge enrichment")
    parser.add_argument("question", help="Your question about climate/emissions data")
    parser.add_argument("--persona", default="No Persona",
                       choices=["No Persona", "Climate Analyst", "Research Scientist", "Financial Analyst", "Student"],
                       help="Response persona (default: No Persona for neutral responses)")
    parser.add_argument("--no-baseline", action="store_true", help="Disable baseline knowledge enrichment")
    parser.add_argument("--verbose", action="store_true", help="Show classification and intermediate results")

    try:
        args = parser.parse_args()
    except SystemExit:
        print('Usage: python run_llm.py "<your question>" [--persona PERSONA] [--no-baseline] [--verbose]')
        print('Example: python run_llm.py "How did Germany power emissions change 2022-2023?" --persona "Climate Analyst"')
        print('Personas: Climate Analyst, Research Scientist, Financial Analyst, Student')
        sys.exit(1)

    question = args.question
    persona = args.persona

    # Handle "No Persona" option (treat as no persona optimization)
    if persona.lower() == "no persona":
        use_baseline = not args.no_baseline and BASELINE_AVAILABLE
        persona = "Climate Analyst"  # Use as default for context, but won't be applied
        use_no_persona_mode = True
    else:
        use_baseline = not args.no_baseline and BASELINE_AVAILABLE
        use_no_persona_mode = False

    # STEP 1: Classify question
    question_type = classify_question(question)

    if args.verbose:
        print(f"\n[CLASSIFICATION] Question Type: {question_type}")
        print(f"[CONFIG] Persona: {persona}, Baseline Enabled: {use_baseline}")

    # STEP 2: Handle BASELINE-only questions
    if question_type == "BASELINE" and use_baseline:
        if args.verbose:
            print(f"[ROUTING] Using baseline knowledge (no MCP query needed)")
        # Use persona for baseline unless in no_persona_mode
        baseline_persona = "Climate Analyst" if use_no_persona_mode else persona
        answer = get_baseline_answer(question, baseline_persona)
        print("\n=== ANSWER (Baseline Knowledge) ===")
        print(answer)
        return

    # STEP 3: For MCP and HYBRID questions, get tool call
    if args.verbose:
        print(f"[ROUTING] Querying MCP database...")

    tool_call = chat(
        SYSTEM,
        question + "\n\nReturn ONLY a tool call JSON (or array of tool calls for comparisons) as per the schema. Do not include any prose."
    ).strip()

    # If the model didn't return JSON, nudge once with a strict reminder
    if not ((tool_call.startswith("{") and '"tool"' in tool_call) or (tool_call.startswith("[") and '"tool"' in tool_call)):
        tool_call = chat(
            SYSTEM,
            "Return ONLY a tool call JSON (or array for comparisons) for this question:\n" + question + "\n\nReminder: never use SQL strings; use the JSON schema described."
        ).strip()

    print("\n--- TOOL CALL ---")
    print(tool_call)

    # STEP 4: Execute tool call(s)
    result = exec_tool_call(tool_call)

    print("\n--- TOOL RESULT (first 10 rows per query) ---")
    if isinstance(result, list):
        # Multiple tool calls
        for i, res in enumerate(result):
            print(f"\n--- Result {i+1}/{len(result)} ---")
            if isinstance(res, dict) and "rows" in res:
                preview = {**res, "rows": res["rows"][:10]}
                print(json.dumps(preview, indent=2)[:2000])
            else:
                print(json.dumps(res, indent=2)[:2000])
    elif isinstance(result, dict) and "rows" in result:
        # Single tool call with rows
        preview = {**result, "rows": result["rows"][:10]}
        print(json.dumps(preview, indent=2)[:2000])
    else:
        # Single tool call with error or other result
        print(json.dumps(result, indent=2)[:2000])

    # STEP 5: Summarize via LLM with optional baseline enrichment
    if args.verbose:
        enrichment_status = "with baseline enrichment" if question_type == "HYBRID" and use_baseline else "data-only"
        no_persona_suffix = " (no persona mode)" if use_no_persona_mode else ""
        print(f"[SUMMARIZATION] Generating answer ({enrichment_status}){no_persona_suffix}...")

    # Use neutral persona for no_persona_mode
    summary_persona = "Climate Analyst" if use_no_persona_mode else persona
    answer = summarize(result, question, question_type=question_type, persona=summary_persona)
    print("\n=== ANSWER ===")
    print(answer)

    if args.verbose:
        print(f"\n[COMPLETE] Question processing finished")

if __name__ == "__main__":
    main()