#!/usr/bin/env python3
"""
ClimateGPT Persona Engine

Centralized persona definitions and processing pipeline used by both the
Streamlit UI and automated persona regression tests. Focused on four tuned
personas to keep behaviour consistent and testable.

Personas:
    - Climate Analyst (climate-data professional)
    - Research Scientist (methodology-focused expert)
    - Financial Analyst (emissions-signal interpreter)
    - Student (simplified educational framing)
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Literal
from collections.abc import Callable

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Import baseline context module for enriching MCP responses
from src.utils.baseline_context import BaselineContextProvider

load_dotenv()

# -----------------------------------------------------------------------------
# Environment & logging configuration
# -----------------------------------------------------------------------------

CONTENT_TYPE_JSON = "application/json"
DEFAULT_UNITS_MESSAGE = "All emissions data is in tonnes CO₂ (MtCO₂ for large values)"
USA_FULL_NAME = "United States of America"
DEFAULT_TIMEOUT = 30

OPENAI_BASE_URL = os.environ.get(
    "OPENAI_BASE_URL", "https://erasmus.ai/models/climategpt_8b_test/v1"
)

# API_KEY must be set and in format "username:password" - NO DEFAULTS for security
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")
if ":" not in OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be in format 'username:password'")

MODEL = os.environ.get("MODEL", "/cache/climategpt_8b_test")
USER, PASS = OPENAI_API_KEY.split(":", 1)

MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8010")

LLM_MAX_CONCURRENCY = int(os.environ.get("LLM_MAX_CONCURRENCY", "2"))
_LLM_SEMAPHORE = threading.BoundedSemaphore(LLM_MAX_CONCURRENCY)

log_level_str = os.environ.get("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_str, logging.INFO)
logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")
logger.setLevel(log_level)

# Initialize baseline context provider for enriching MCP responses
_baseline_provider = BaselineContextProvider()
logger.info("Baseline context provider initialized - ready to enrich responses")

# -----------------------------------------------------------------------------
# Persona definitions
# -----------------------------------------------------------------------------

CLIMATE_ANALYST = "Climate Analyst"
RESEARCH_SCIENTIST = "Research Scientist"
FINANCIAL_ANALYST = "Financial Analyst"
STUDENT = "Student"

PERSONA_ORDER = [
    CLIMATE_ANALYST,
    RESEARCH_SCIENTIST,
    FINANCIAL_ANALYST,
    STUDENT,
]

PERSONAS: "OrderedDict[str, Dict[str, str]]" = OrderedDict(
    {
        CLIMATE_ANALYST: {
            "name": CLIMATE_ANALYST,
            "icon": "📈",
            "description": (
                "Climate data strategist delivering actionable insights and priority areas for mitigation."
            ),
            "tone": "Analytical, confident, insight-driven",
            "expertise": (
                "Cross-sector emissions benchmarking, hotspot detection, and policy-aligned recommendations"
            ),
            "response_style": (
                "Structured insights with clear takeaways, highlighting comparative performance and priority actions"
            ),
        },
        RESEARCH_SCIENTIST: {
            "name": RESEARCH_SCIENTIST,
            "icon": "🔬",
            "description": (
                "Methodology-focused scientist emphasising data provenance and statistical interpretation."
            ),
            "tone": "Precise, evidence-first, methodical",
            "expertise": (
                "Data validation, time-series interpretation, and contextualising uncertainty in emissions inventories"
            ),
            "response_style": (
                "Explanatory analysis referencing dataset structure, data quality, and methodological caveats"
            ),
        },
        FINANCIAL_ANALYST: {
            "name": FINANCIAL_ANALYST,
            "icon": "💼",
            "description": (
                "Analyst translating emissions data into risk signals, momentum cues, and competitive positioning."
            ),
            "tone": "Concise, signal-oriented, risk-aware",
            "expertise": (
                "Trend momentum, concentration of emissions, exposure flags tied to geography and sector focus"
            ),
            "response_style": (
                "Bullet-like takeaways on direction, scale, and concentration with disciplined caveats"
            ),
        },
        STUDENT: {
            "name": STUDENT,
            "icon": "🎓",
            "description": "Learner seeking plain-language explanations and relatable context.",
            "tone": "Friendly, encouraging, clear",
            "expertise": "Foundational climate literacy, comparisons, and trend basics",
            "response_style": (
                "Step-by-step narratives, definitions of key terms, and simple comparisons"
            ),
        },
    }
)

# -----------------------------------------------------------------------------
# Persona prompts
# -----------------------------------------------------------------------------

def get_persona_system_prompt(persona_key: str) -> str:
    """Generate persona-specific system prompt for tool calling."""
    persona = PERSONAS.get(persona_key, PERSONAS[CLIMATE_ANALYST])

    base_prompt = """
You are ClimateGPT-Dev with a specialised professional persona. You MUST answer by calling HTTP tools instead of guessing.
Data source: EDGAR v2024 emissions datasets (transport, power, waste, agriculture, buildings, fuel-exploitation, ind-combustion, ind-processes).
Output units: tonnes CO₂ (use MtCO₂ for large values).

DATASET SELECTION RULES:
- "monthly" → use datasets ending with "-month"
- "annual"/"yearly" → use datasets ending with "-year"
- Ranges like "2021-2023" without month mention → prefer "-year" unless user asks for monthly detail
- City/admin1 requests must use city/admin1 datasets

RETURN FORMAT (STRICT):
- Return EXACTLY ONE JSON object: {"tool":"query","args":{"file_id":"...","select":[...],"where":{...},"order_by":"...","limit":...,"assist":true}}
- Arrays only when multiple tool calls are absolutely required; keep array on a single line.
- Inside args: file_id (string) is REQUIRED; select must be a JSON array of column names; where must be a JSON object; order_by is a string; limit is an integer; assist is a boolean.
- NEVER include SQL-style keys such as "from", "group_by", or raw SQL clauses. Encode filters purely as JSON.
- NEVER represent select or where as strings.

VALID FILE IDS (sector-level-grain):
- transport, power, waste, agriculture, buildings, fuel-exploitation, ind-combustion, ind-processes
- levels: country, admin1, city
- grains: year, month

VALID COLUMNS:
- country_name, admin1_name, city_name
- year (int), month (1-12), emissions_tonnes, MtCO2

CRITICAL RULES:
1. NEVER fabricate or estimate values.
2. Use order_by + limit for rankings; DO NOT use group_by without aggregates.
3. Include requested filters (country, admin1, city, year, month) in "where".
4. WHERE CLAUSE MUST BE A FLAT JSON OBJECT - use array values for multiple items (e.g., {"year": [2020, 2021, 2023]}).
5. NEVER use nested objects in where (NO {"year": {"in": [2020, 2023]}}).
6. If data is unavailable, return a JSON tool call that will surface empty results; do NOT switch to narration.
7. All JSON must be valid and unquoted.
8. EXTRACT YEARS EXPLICITLY: If question mentions "2023", "in 2022", "between 2020 and 2023", include those exact years in where clause.
9. WRONG EXAMPLE: {"tool":"query","args":{"select":"country_name, MtCO2","from":"transport-year","where":"year IN (2020, 2023)"}}
10. RIGHT EXAMPLE: {"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"where":{"year":[2020,2023]}, "order_by":"MtCO2 DESC","limit":3,"assist":true}}
""".strip()

    persona_specific = f"""

PERSONA: {persona['name']} {persona['icon']}
DESCRIPTION: {persona['description']}
TONE: {persona['tone']}
EXPERTISE: {persona['expertise']}
RESPONSE STYLE: {persona['response_style']}

When constructing tool calls and later summarising results:
- Lean into this persona's expertise and tone.
- Highlight the aspects the persona cares about most.
- Preserve factual accuracy and numerical precision.
"""

    guardrails = """

STRICT DATA GUARDRAILS:
- Only use available fields (country_name, admin1_name, city_name, year, month, emissions_tonnes, MtCO2).
- Do NOT invent metrics (per-capita, financial values, ESG scores, forecasts, currency conversions).
- For unsupported requests, state the limitation clearly after querying.

ALLOWED ANALYSES:
- Rankings (order_by + limit), comparisons across regions/sectors, YoY deltas when both years exist, seasonal (monthly) patterns.
- Prefer monthly datasets only when question references months or seasonality explicitly.
- Respect detected geographic level constraints (city/admin1) without falling back to broader levels unless no data exists.
"""

    persona_prefs = ""
    if persona_key == CLIMATE_ANALYST:
        persona_prefs = """

CLIMATE ANALYST PREFERENCES:
- Emphasise comparative insights and hotspots when data allows.
- Surface notable increases/decreases and actionable focus areas.
- For multi-entity results, ensure select includes MtCO2 for ranking clarity.
"""
    elif persona_key == RESEARCH_SCIENTIST:
        persona_prefs = """

RESEARCH SCIENTIST PREFERENCES:
- Prioritise datasets with the most precise temporal/spatial resolution matching the question.
- Include context columns (year/month + entity name) to support methodological commentary.
- Avoid assumptions; if uncertainty exists, plan to mention it in the summary step.
- For monthly patterns: Use file_id ending in "-month", include where={"year": XXXX}, order_by="month ASC", limit=12.
- For seasonal analysis: Always retrieve full 12-month series with select=["month", "MtCO2", "city_name" or "country_name"].
- CRITICAL: Flat where clause - {"city_name": "Tokyo", "year": 2021}, NEVER nested.
"""
    elif persona_key == FINANCIAL_ANALYST:
        persona_prefs = """

FINANCIAL ANALYST PREFERENCES:
- Focus on directionality, concentration (top emitters), and rate-of-change cues.
- Ensure select includes MtCO2 (or convert emissions_tonnes) for quick comparisons.
- Align results to yearly or monthly cadence that best signals momentum for investors.
- For concentration metrics: Query top N entities with order_by + limit, calculate percentages in summary.
- For US state-level queries: Use admin1 level with where={"country_name": "United States of America"}.
- CRITICAL: Keep where clause flat - use {"year": 2023} or {"year": [2022, 2023]}, NEVER nested dicts.
"""
    elif persona_key == STUDENT:
        persona_prefs = """

STUDENT PREFERENCES:
- Choose straightforward datasets (yearly unless month explicitly requested).
- Include columns needed to explain "where" and "when" clearly (location name + year/month + MtCO2).
- Keep limits small (≤5) to simplify explanations unless user asks for more.
- ALWAYS extract years from question: If "in 2023" appears, use where={"year": 2023}.
- For comparisons like "2023 vs 2022", use where={"year": [2022, 2023]}.
- CRITICAL: Simple flat where clause - {"country_name": "Germany", "year": [2022, 2023]}.
"""

    return base_prompt + persona_specific + guardrails + persona_prefs


# -----------------------------------------------------------------------------
# Persona output controller with tuned insights
# -----------------------------------------------------------------------------

class PersonaOutputController:
    """Persona-specific curation applied to raw LLM summaries."""

    def __init__(self):
        self.response_templates = {
            CLIMATE_ANALYST: {
                "conclusion": "From a mitigation planning perspective, prioritise:",
                "units": DEFAULT_UNITS_MESSAGE,
            },
            RESEARCH_SCIENTIST: {
                "conclusion": "Methodological notes and considerations:",
                "units": DEFAULT_UNITS_MESSAGE,
            },
            FINANCIAL_ANALYST: {
                "conclusion": "Signals to monitor (emissions only):",
                "units": DEFAULT_UNITS_MESSAGE,
            },
            STUDENT: {
                "conclusion": "Remember:",
                "units": DEFAULT_UNITS_MESSAGE,
            },
        }

    def curate_response(self, raw_response: str, persona_key: str, data_context: dict[str, Any]) -> str:
        persona = PERSONAS.get(persona_key, PERSONAS[CLIMATE_ANALYST])
        template = self.response_templates.get(persona_key, self.response_templates[CLIMATE_ANALYST])

        curated = raw_response.strip()
        rows = data_context.get("rows") if isinstance(data_context, dict) else None

        if rows:
            curated += f"\n\n{template['conclusion']}\n"
            curated += self._persona_insights(persona_key, rows)

        curated += f"\n\n*{template['units']}*"
        return curated

    def _persona_insights(self, persona_key: str, rows: list[dict[str, Any]]) -> str:
        if persona_key == CLIMATE_ANALYST:
            return self._analyst(rows)
        if persona_key == RESEARCH_SCIENTIST:
            return self._scientist(rows)
        if persona_key == FINANCIAL_ANALYST:
            return self._finance(rows)
        if persona_key == STUDENT:
            return self._student(rows)
        return ""

    def _analyst(self, rows: list[dict[str, Any]]) -> str:
        snippets = []
        if len(rows) >= 3:
            snippets.append("• Identify top emitters in this slice for immediate policy engagement.")
        if self._has_multiple_years(rows):
            snippets.append("• Track multi-year shifts to flag accelerating sources.")
        if self._top_value(rows) > 150:
            snippets.append("• Consider sector-specific mitigation for regions above ~150 MtCO₂.")
        return "\n".join(snippets) if snippets else "• No standout anomalies beyond baseline patterns."

    def _scientist(self, rows: list[dict[str, Any]]) -> str:
        snippets = []
        if self._has_multiple_years(rows):
            snippets.append("• Trend visibility: multiple years captured, enabling temporal comparisons.")
        if any(r.get("month") for r in rows if isinstance(r, dict)):
            snippets.append("• Seasonal resolution present — examine recurring peaks.")
        snippets.append("• Source: EDGAR v2024 structured datasets; refer to meta for exact table IDs.")
        return "\n".join(snippets)

    def _finance(self, rows: list[dict[str, Any]]) -> str:
        snippets = []
        share = self._top_three_share(rows)
        if share:
            snippets.append(f"• Concentration: top three entities ≈ {share:.0f}% of listed emissions.")
        if self._has_multiple_years(rows):
            snippets.append("• Momentum: year-over-year movement detectable — assess direction vs. peers.")
        snippets.append("• Treat figures as emission signals only (no direct monetary inference).")
        return "\n".join(snippets)

    def _student(self, rows: list[dict[str, Any]]) -> str:
        snippets = [
            "• Emissions measure how much CO₂ was released by the sector and place shown.",
        ]
        top_name, top_val = self._top_entity(rows)
        if top_name and top_val is not None:
            snippets.append(f"• The highest value here is {top_name} with about {top_val:.1f} MtCO₂.")
        snippets.append("• Bigger numbers mean more emissions, so those places affect the climate more.")
        return "\n".join(snippets)

    @staticmethod
    def _has_multiple_years(rows: list[dict[str, Any]]) -> bool:
        years = {r.get("year") for r in rows if isinstance(r, dict) and isinstance(r.get("year"), int)}
        return len(years) >= 2

    @staticmethod
    def _top_value(rows: list[dict[str, Any]]) -> float:
        best = 0.0
        for r in rows[:10]:
            if not isinstance(r, dict):
                continue
            mt = r.get("MtCO2")
            if not isinstance(mt, (int, float)):
                tonnes = r.get("emissions_tonnes")
                if isinstance(tonnes, (int, float)):
                    mt = tonnes / 1e6
            if isinstance(mt, (int, float)):
                best = max(best, float(mt))
        return best

    @staticmethod
    def _top_three_share(rows: list[dict[str, Any]]) -> float | None:
        values: list[float] = []
        for r in rows[:10]:
            if not isinstance(r, dict):
                continue
            mt = r.get("MtCO2")
            if not isinstance(mt, (int, float)):
                tonnes = r.get("emissions_tonnes")
                if isinstance(tonnes, (int, float)):
                    mt = tonnes / 1e6
            if isinstance(mt, (int, float)):
                values.append(float(mt))
        if not values:
            return None
        total = sum(values)
        if total <= 0:
            return None
        top3 = sum(sorted(values, reverse=True)[:3])
        return (top3 / total) * 100

    @staticmethod
    def _top_entity(rows: list[dict[str, Any]]) -> tuple[str | None, float | None]:
        best_name, best_val = None, None
        best = PersonaOutputController._top_value(rows)
        if best <= 0:
            return best_name, best_val
        for r in rows[:10]:
            if not isinstance(r, dict):
                continue
            mt = r.get("MtCO2")
            if not isinstance(mt, (int, float)):
                tonnes = r.get("emissions_tonnes")
                if isinstance(tonnes, (int, float)):
                    mt = tonnes / 1e6
            if isinstance(mt, (int, float)) and abs(mt - best) < 1e-6:
                best_name = (
                    r.get("city_name")
                    or r.get("admin1_name")
                    or r.get("country_name")
                    or "this location"
                )
                best_val = float(mt)
                break
        return best_name, best_val


output_controller = PersonaOutputController()

# -----------------------------------------------------------------------------
# Utility helpers (geo detection, normalization, caching, HTTP robustness)
# -----------------------------------------------------------------------------

US_STATES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
}

COMMON_CITIES = {
    "new york city": {"city_name": "New York", "country_name": USA_FULL_NAME},
    "new york": {"city_name": "New York", "country_name": USA_FULL_NAME},
    "los angeles": {"city_name": "Los Angeles", "country_name": USA_FULL_NAME},
    "san francisco": {"city_name": "San Francisco", "country_name": USA_FULL_NAME},
    "chicago": {"city_name": "Chicago", "country_name": USA_FULL_NAME},
    "london": {"city_name": "London", "country_name": "United Kingdom"},
    "paris": {"city_name": "Paris", "country_name": "France"},
    "tokyo": {"city_name": "Tokyo", "country_name": "Japan"},
}


def detect_geo_entity(question: str) -> dict[str, Any]:
    """Detect admin1 or city mentions to enforce level constraints."""
    q = (question or "").lower()

    for key, meta in COMMON_CITIES.items():
        if key in q:
            where = {"city_name": meta["city_name"]}
            if meta.get("country_name"):
                where["country_name"] = meta["country_name"]
            return {"level": "city", "where": where}

    for state in US_STATES:
        if re.search(rf"\\b{re.escape(state)}\\b", q):
            state_tc = " ".join([w.capitalize() for w in state.split()])
            return {
                "level": "admin1",
                "where": {"admin1_name": state_tc, "country_name": USA_FULL_NAME},
            }

    return {}


def apply_level_constraints_to_tool(tool_json: str, constraints: dict[str, Any]) -> str:
    """Force level-specific file_id and required filters onto the tool JSON."""
    try:
        obj = json.loads(tool_json)
        if not isinstance(obj, dict):
            return tool_json
        args = obj.get("args") or obj.get("tool_args") or {}
        file_id: str = args.get("file_id", "")

        level = constraints.get("level")
        where_req = constraints.get("where", {})

        if level:
            if file_id:
                file_id = file_id.replace("-country-", f"-{level}-").replace("_country_", f"_{level}_")
                file_id = file_id.replace("-admin1-", f"-{level}-").replace("_admin1_", f"_{level}_")
                file_id = file_id.replace("-city-", f"-{level}-").replace("_city_", f"_{level}_")
                if ("-country-" not in file_id and "-admin1-" not in file_id and "-city-" not in file_id):
                    sector_prefix = (file_id.split("-")[0] or "transport") if "-" in file_id else "transport"
                    grain_suffix = "month" if "-month" in file_id or file_id.endswith("month") else "year"
                    file_id = f"{sector_prefix}-{level}-{grain_suffix}"
            else:
                file_id = f"transport-{level}-year"
            args["file_id"] = file_id

        if where_req:
            where = args.get("where", {})
            if not isinstance(where, dict):
                where = {}
            for k, v in where_req.items():
                where.setdefault(k, v)
            args["where"] = where

        sel = args.get("select", [])
        if isinstance(sel, list):
            if level == "city":
                for col in ["city_name", "country_name", "year", "MtCO2"]:
                    if col not in sel:
                        sel.append(col)
            elif level == "admin1":
                for col in ["admin1_name", "country_name", "year", "MtCO2"]:
                    if col not in sel:
                        sel.append(col)
            args["select"] = sel

        if "args" in obj:
            obj["args"] = args
        else:
            obj["tool_args"] = args

        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return tool_json


def _coerce_literal(value: str) -> Any:
    stripped = value.strip()
    if stripped.startswith("'") and stripped.endswith("'") and len(stripped) >= 2:
        stripped = stripped[1:-1]
    if stripped.startswith('"') and stripped.endswith('"') and len(stripped) >= 2:
        stripped = stripped[1:-1]
    lowered = stripped.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none"}:
        return None
    try:
        if "." in stripped:
            return float(stripped)
        return int(stripped)
    except (TypeError, ValueError):
        return stripped


def _parse_where_string(where_str: str) -> dict[str, Any] | None:
    try:
        clauses = [clause.strip() for clause in re.split(r"\bAND\b", where_str, flags=re.IGNORECASE) if clause.strip()]
        if not clauses:
            return None
        where: dict[str, Any] = {}
        for clause in clauses:
            in_match = re.match(r"^([a-zA-Z0-9_]+)\s+IN\s*\((.+)\)$", clause, flags=re.IGNORECASE)
            between_match = re.match(r"^([a-zA-Z0-9_]+)\s+BETWEEN\s+(.+)\s+AND\s+(.+)$", clause, flags=re.IGNORECASE)
            eq_match = re.match(r"^([a-zA-Z0-9_]+)\s*=\s*(.+)$", clause)

            if in_match:
                column, values_str = in_match.groups()
                values = [v.strip() for v in values_str.split(",") if v.strip()]
                where[column] = {"in": [_coerce_literal(v) for v in values]}
                continue

            if between_match:
                column, lower, upper = between_match.groups()
                where[column] = {"between": [_coerce_literal(lower), _coerce_literal(upper)]}
                continue

            if eq_match:
                column, raw_value = eq_match.groups()
                where[column] = _coerce_literal(raw_value)
                continue

            return None

        return where
    except Exception:
        return None


def sanitize_tool_call_object(tool_obj: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(tool_obj, dict):
        return tool_obj

    args = tool_obj.get("args") or tool_obj.get("tool_args") or {}
    if not isinstance(args, dict):
        args = {}
    tool_obj["args"] = args
    tool_obj.pop("tool_args", None)

    file_id = args.get("file_id") or args.get("from")
    if isinstance(file_id, str):
        normalized_file_id = file_id.replace("_", "-")
        if "-country-" not in normalized_file_id and "-admin1-" not in normalized_file_id and "-city-" not in normalized_file_id:
            if normalized_file_id.endswith("-year") or normalized_file_id.endswith("-month"):
                normalized_file_id = f"transport-country-{normalized_file_id.split('-')[-1]}"
            else:
                normalized_file_id = "transport-country-year"
        args["file_id"] = normalized_file_id
    else:
        args.setdefault("file_id", "transport-country-year")

    select_value = args.get("select")
    if isinstance(select_value, str):
        select_list = [col.strip() for col in select_value.split(",") if col.strip()]
        args["select"] = select_list
    elif not isinstance(select_value, list):
        args["select"] = ["country_name", "year", "MtCO2"]
    else:
        args["select"] = [col for col in select_value if isinstance(col, str) and col.strip()]
        if not args["select"]:
            args["select"] = ["country_name", "year", "MtCO2"]

    where_value = args.get("where")
    if isinstance(where_value, str):
        parsed_where = _parse_where_string(where_value)
        args["where"] = parsed_where if parsed_where is not None else {}
    elif not isinstance(where_value, dict):
        args["where"] = {}

    if "order_by" in args and isinstance(args["order_by"], list):
        args["order_by"] = ", ".join([str(item) for item in args["order_by"] if item])

    limit_value = args.get("limit")
    if isinstance(limit_value, str):
        try:
            args["limit"] = int(limit_value)
        except ValueError:
            args["limit"] = 5
    elif not isinstance(limit_value, int):
        args["limit"] = 5

    args.setdefault("assist", True)

    return tool_obj


def normalize_country_name(country_name: str) -> str:
    mapping = {
        "United States": USA_FULL_NAME,
        "USA": USA_FULL_NAME,
        "US": USA_FULL_NAME,
        "China": "People's Republic of China",
        "Russia": "Russian Federation",
        "UK": "United Kingdom",
        "South Korea": "Republic of Korea",
        "North Korea": "Democratic People's Republic of Korea",
    }
    return mapping.get(country_name, country_name)


def robust_request(url: str, method: str = "GET", max_retries: int = 3, **kwargs: Any) -> dict[str, Any]:
    """HTTP helper with retries/backoff to the MCP server."""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                response = requests.get(url, timeout=DEFAULT_TIMEOUT, **kwargs)
            elif method.upper() == "POST":
                response = requests.post(url, timeout=DEFAULT_TIMEOUT, **kwargs)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}

            response.raise_for_status()
            return {"success": True, "data": response.json() if response.content else {}}

        except requests.exceptions.Timeout as e:
            last_error = e
            logger.warning(f"Timeout for {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Connection error for {url} (attempt {attempt + 1}/{max_retries})")
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            return {
                "error": f"HTTP error {e.response.status_code}: {e.response.text}",
                "status_code": e.response.status_code,
            }
        except Exception as e:
            last_error = e
            logger.warning(f"Request error for {url} (attempt {attempt + 1}/{max_retries}): {e}")

        time.sleep(1 * (2 ** attempt))

    if last_error:
        return {"error": str(last_error), "retries": max_retries}
    return {"error": "Unknown request failure", "retries": max_retries}


class SimpleLRUCache:
    """Thread-safe LRU cache for tool responses."""

    def __init__(self, maxsize: int = 128) -> None:
        self.maxsize: int = maxsize
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._lock: threading.Lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                return self._store[key]
            return None

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = value
            if len(self._store) > self.maxsize:
                self._store.popitem(last=False)


class CircuitBreaker:
    def __init__(self, max_failures: int = 5, timeout: int = 60) -> None:
        self.max_failures: int = max_failures
        self.timeout: int = timeout
        self.failures: int = 0
        self.last_failure_time: float = 0.0
        self.state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"

    def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        now = time.time()

        if self.state == "OPEN" and now - self.last_failure_time > self.timeout:
            self.state = "HALF_OPEN"
            self.failures = 0

        if self.state == "OPEN":
            return {
                "error": "Service temporarily unavailable (circuit breaker open)",
                "retry_after": self.timeout - (now - self.last_failure_time),
            }

        try:
            result = func(*args, **kwargs)
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result["error"])
            self.failures = 0
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
            return result
        except Exception as exc:
            self.failures += 1
            self.last_failure_time = now
            if self.failures >= self.max_failures:
                self.state = "OPEN"
            logger.error(f"Circuit breaker error: {exc}")
            return {"error": str(exc)}


_TOOL_CACHE = SimpleLRUCache(maxsize=int(os.environ.get("MCP_TOOL_CACHE_SIZE", "256")))
mcp_circuit_breaker = CircuitBreaker()


def chat_with_climategpt(system: str, user_message: str, temperature: float = 0.2) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
    }
    try:
        with _LLM_SEMAPHORE:
            r = requests.post(
                f"{OPENAI_BASE_URL}/chat/completions",
                headers={"Content-Type": CONTENT_TYPE_JSON},
                data=json.dumps(payload),
                auth=HTTPBasicAuth(USER, PASS) if USER else None,
                timeout=120,
            )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error communicating with ClimateGPT: {str(e)}"


def exec_tool_call(tool_json: str) -> dict[str, Any]:
    """Execute tool call against MCP server with caching and resilience."""
    cleaned_json = tool_json.strip()

    if cleaned_json.startswith("```json"):
        cleaned_json = cleaned_json[7:]
    if cleaned_json.startswith("```"):
        cleaned_json = cleaned_json[3:]
    if cleaned_json.endswith("```"):
        cleaned_json = cleaned_json[:-3]
    cleaned_json = cleaned_json.strip()

    if cleaned_json.startswith('"') and cleaned_json.endswith('"'):
        cleaned_json = cleaned_json[1:-1].replace('\\"', '"')

    try:
        obj = json.loads(cleaned_json)
    except json.JSONDecodeError:
        start = cleaned_json.find("{")
        if start == -1:
            return {"error": "Model did not return valid JSON tool call.", "raw": tool_json}
        brace_count = 0
        end_idx = -1
        for idx, char in enumerate(cleaned_json[start:], start):
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = idx
                    break
        if end_idx == -1:
            return {"error": "Model did not return valid JSON tool call.", "raw": tool_json}
        try:
            obj = json.loads(cleaned_json[start : end_idx + 1])
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON format: {e}", "raw": tool_json}

    tool = obj.get("tool") or obj.get("tool_call")
    args = obj.get("args", {}) or obj.get("tool_args", {})

    def _http_get(url: str) -> Any:
        rr = robust_request(url, method="GET")
        if rr.get("success"):
            return rr.get("data", {})
        raise requests.exceptions.RequestException(rr.get("error", "GET failed"))

    def _http_post(url: str, payload: dict) -> Any:
        rr = robust_request(url, method="POST", json=payload)
        if rr.get("success"):
            return rr.get("data", {})
        raise requests.exceptions.RequestException(rr.get("error", "POST failed"))

    def _list_files():
        return _http_get(f"{MCP_URL}/list_files")

    def _get_schema(file_id):
        return _http_get(f"{MCP_URL}/get_schema/{file_id}")

    def _execute_query(query_args):
        if "where" in query_args and "country_name" in query_args["where"]:
            query_args["where"]["country_name"] = normalize_country_name(query_args["where"]["country_name"])
        query_args.setdefault("assist", True)
        return _http_post(f"{MCP_URL}/query", query_args)

    def _execute_yoy_metrics(metrics_args):
        return _http_post(f"{MCP_URL}/metrics/yoy", metrics_args)

    def _execute_batch_query(batch_args):
        return _http_post(f"{MCP_URL}/batch/query", batch_args)

    try:
        cache_key = None
        try:
            cache_key = json.dumps({"tool": tool, "args": args}, sort_keys=True)
        except Exception:
            cache_key = None

        if cache_key:
            cached = _TOOL_CACHE.get(cache_key)
            if cached is not None:
                return cached

        if tool == "list_files":
            result = mcp_circuit_breaker.call(_list_files)
        elif tool == "get_schema":
            if "file_id" not in args:
                return {"error": "Missing required parameter: file_id"}
            result = mcp_circuit_breaker.call(_get_schema, args["file_id"])
        elif tool == "query":
            result = mcp_circuit_breaker.call(_execute_query, args)
        elif tool == "metrics.yoy":
            result = mcp_circuit_breaker.call(_execute_yoy_metrics, args)
        elif tool == "batch_query":
            result = mcp_circuit_breaker.call(_execute_batch_query, args)
        else:
            return {"error": f"Unsupported tool: {tool}"}

        if cache_key and isinstance(result, dict) and "error" not in result:
            _TOOL_CACHE.set(cache_key, result)
        return result
    except Exception as error:
        logger.error(f"Unexpected error in exec_tool_call: {error}")
        return {"error": str(error)}


def create_fallback_response(question: str, context: dict[str, Any]) -> str:
    fallback_responses = {
        "timeout": "The data request timed out. Please try again in a moment.",
        "network_error": "I couldn't reach the data service. Please check that the MCP server is running.",
        "data_not_found": (
            "I couldn't find data for your specific query. This usually happens when the geographic name or "
            "time period is not present in the dataset. Try a different year, sector, or location spelling."
        ),
        "invalid_query": "I didn't understand the request format. Try rephrasing with a clear sector and location.",
        "server_error": "There was a temporary issue with the data server. Please retry shortly.",
        "json_error": "I received an unexpected response format. Please rephrase or simplify the question.",
        "circuit_breaker": "The data service is temporarily unavailable. Please wait a minute and retry.",
        "llm_error": "I'm having trouble processing your question. Please try rephrasing it.",
        "empty_response": "I couldn't generate a response. Please try a different question.",
        "unexpected_error": "An unexpected error occurred. Please try again.",
    }

    base_response = fallback_responses.get(
        context.get("error_type"), "I encountered an unexpected error. Please try again."
    )

    suggestions: list[str] = []
    lower_q = (question or "").lower()
    if "emissions" in lower_q:
        suggestions.append("Try specifying a sector like transport, power, or waste along with the year.")
    if "top" in lower_q:
        suggestions.append("Ask for a specific number of results, e.g., 'top 5 countries'.")
    if "monthly" in lower_q:
        suggestions.append("Make sure to mention the year when asking for monthly data.")

    if suggestions:
        base_response += f"\n\n💡 **Suggestions:** {suggestions[0]}"
    return base_response


# -----------------------------------------------------------------------------
# Persona question processor (primary export)
# -----------------------------------------------------------------------------

def process_persona_question(question: str, persona_key: str) -> tuple[str, dict[str, Any], str]:
    """Main workflow for persona-aware ClimateGPT answer generation."""
    try:
        system_prompt = get_persona_system_prompt(persona_key)
        geo_constraints = detect_geo_entity(question)

        if geo_constraints:
            must_level = geo_constraints.get("level")
            must_where = {k: v for k, v in geo_constraints.get("where", {}).items()}
            where_str = ", ".join([f'"{k}": "{v}"' for k, v in must_where.items()])
            system_prompt += (
                f"\n\nHARD CONSTRAINTS:\n- You MUST use a file_id with '-{must_level}-'."
                f"\n- You MUST include where: {{{where_str}}}.\n- Do NOT alter these constraints.\n"
            )

        tool_call_response = chat_with_climategpt(
            system_prompt,
            f"Question: {question}\n\nReturn ONLY ONE valid JSON tool call. No markdown, no text.",
        ).strip()

        tool_call_response = tool_call_response.replace("```json", "").replace("```", "").strip()
        logger.debug("Raw tool call response: %s", tool_call_response)

        if not (tool_call_response.startswith("{") and '"tool"' in tool_call_response):
            tool_call_response = chat_with_climategpt(
                system_prompt,
                (
                    f"Question: {question}\n\nReturn ONLY this JSON format: "
                    '{"tool":"query","args":{"file_id":"transport-country-year","select":["country_name","year","MtCO2"],"limit":10}}'
                ),
            ).strip()
            tool_call_response = tool_call_response.replace("```json", "").replace("```", "").strip()
            logger.debug("Retry tool call response: %s", tool_call_response)

        used_tool = "unknown"
        sanitized_tool_json = tool_call_response
        try:
            json_start = tool_call_response.find("{")
            json_end = tool_call_response.rfind("}") + 1
            if json_start != -1 and json_end > json_start:
                json_candidate = tool_call_response[json_start:json_end]
                tool_call_obj = json.loads(json_candidate)
                tool_call_obj = sanitize_tool_call_object(tool_call_obj)
                if geo_constraints:
                    constrained_json = apply_level_constraints_to_tool(
                        json.dumps(tool_call_obj, ensure_ascii=False), geo_constraints
                    )
                    try:
                        tool_call_obj = json.loads(constrained_json)
                    except json.JSONDecodeError:
                        logger.warning("Failed to re-decode constrained tool JSON, falling back to sanitized object.")
                    else:
                        sanitized_tool_json = constrained_json
                if sanitized_tool_json == tool_call_response:
                    sanitized_tool_json = json.dumps(tool_call_obj, ensure_ascii=False)
                used_tool = tool_call_obj.get("tool") or tool_call_obj.get("tool_call") or "unknown"
                logger.debug("Parsed tool call: %s", json_candidate)
        except Exception as parse_error:
            logger.warning(f"Failed to parse tool call response: {parse_error}")
            used_tool = "unknown"
            sanitized_tool_json = tool_call_response

        if geo_constraints and sanitized_tool_json == tool_call_response:
            sanitized_tool_json = apply_level_constraints_to_tool(tool_call_response, geo_constraints)

        result = exec_tool_call(sanitized_tool_json)

        # Enrich MCP result with baseline context
        baseline_context = {}
        try:
            enriched_data = _baseline_provider.enrich_response(
                mcp_data=result,
                question=question,
                persona=persona_key
            )
            baseline_context = enriched_data.get("baseline_context", {})
            logger.debug(f"Baseline context added: {list(baseline_context.keys())}")
        except Exception as ctx_err:
            logger.warning(f"Could not enrich with baseline context: {ctx_err}")
            baseline_context = {}

        if "error" in result:
            error_msg = result["error"]
            if "circuit breaker" in error_msg.lower():
                return create_fallback_response(question, {"error_type": "circuit_breaker"}), {}, used_tool
            if "timeout" in error_msg.lower():
                return create_fallback_response(question, {"error_type": "timeout"}), {}, used_tool
            if "connection" in error_msg.lower():
                return create_fallback_response(question, {"error_type": "network_error"}), {}, used_tool
            return f"I encountered an error while processing your question: {error_msg}", {}, used_tool

        if isinstance(result, dict) and "rows" in result:
            rows = result["rows"]
            for row in rows:
                if (
                    isinstance(row, dict)
                    and "MtCO2" not in row
                    and "emissions_tonnes" in row
                    and isinstance(row["emissions_tonnes"], (int, float))
                ):
                    row["MtCO2"] = row["emissions_tonnes"] / 1e6

        if isinstance(result, dict):
            if "rows" in result and not result["rows"]:
                return create_fallback_response(question, {"error_type": "data_not_found"}), {}, used_tool

            if "rows" in result and result["rows"]:
                has_valid_data = False
                for row in result["rows"]:
                    if isinstance(row, dict) and any(
                        row.get(key)
                        for key in ["emissions_tonnes", "MtCO2", "country_name", "admin1_name", "city_name"]
                    ):
                        has_valid_data = True
                        break
                if not has_valid_data:
                    return create_fallback_response(question, {"error_type": "data_not_found"}), {}, used_tool

        rows_preview = json.dumps(result, ensure_ascii=False)
        persona = PERSONAS.get(persona_key, PERSONAS[CLIMATE_ANALYST])

        tool_description = {
            "query": "single dataset query",
            "batch_query": "aggregated multi-sector query",
            "metrics.yoy": "year-over-year analysis",
        }.get(used_tool, f"{used_tool} tool")

        # Build context section from baseline knowledge
        context_section = ""
        if baseline_context:
            context_parts = []
            for key, value in baseline_context.items():
                if value:
                    context_parts.append(f"- {key.replace('_', ' ').title()}: {value}")
            if context_parts:
                context_section = f"""

BASELINE CONTEXT (Use to enrich your interpretation):
{chr(10).join(context_parts)}
"""

        summary_prompt = f"""
You are responding as a {persona['name']} with expertise in {persona['expertise']}.
Maintain a tone that is {persona['tone']} and follow the response style: {persona['response_style']}.

User question: {question}

Using the JSON data below AND the baseline context provided, craft a persona-aligned answer:
- Cite precise emissions figures (convert tonnes to MtCO₂ when > 1e6).
- Reference relevant years, months, and geographies appearing in the data.
- Add persona-specific insights aligned with your expertise.
- Use baseline context to provide interpretation, policy alignment, or explanations.
- Combine MCP data (numbers) with baseline knowledge (meaning) for optimal responses.
- Keep the answer concise (4–8 sentences).
- End with: "Data retrieved using MCP {tool_description}."
{context_section}

Data:
{rows_preview}
"""

        raw_answer = ""
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                raw_answer = chat_with_climategpt(system_prompt, summary_prompt, temperature=0.2)
                if raw_answer and not raw_answer.strip().lower().startswith("error communicating"):
                    break
            except Exception as err:
                last_error = err
            time.sleep(0.5 * (2 ** attempt))

        if not raw_answer or raw_answer.strip().lower().startswith("error communicating"):
            if last_error:
                logger.error(f"LLM summary retries failed with error: {last_error}")
            return create_fallback_response(question, {"error_type": "llm_error"}), {}, used_tool

        try:
            curated_answer = output_controller.curate_response(raw_answer, persona_key, result)
        except Exception as cur_err:
            logger.error(f"Error in persona curation: {cur_err}")
            curated_answer = raw_answer

        if not curated_answer or not curated_answer.strip():
            return create_fallback_response(question, {"error_type": "empty_response"}), {}, used_tool

        return curated_answer, result if isinstance(result, dict) else {}, used_tool
    except Exception as e:
        logger.error(f"Unexpected error in process_persona_question: {e}")
        return create_fallback_response(question, {"error_type": "unexpected_error"}), {}, "unknown"


__all__ = [
    "CLIMATE_ANALYST",
    "RESEARCH_SCIENTIST",
    "FINANCIAL_ANALYST",
    "STUDENT",
    "PERSONAS",
    "PERSONA_ORDER",
    "output_controller",
    "get_persona_system_prompt",
    "process_persona_question",
    "detect_geo_entity",
    "apply_level_constraints_to_tool",
    "exec_tool_call",
    "create_fallback_response",
]


