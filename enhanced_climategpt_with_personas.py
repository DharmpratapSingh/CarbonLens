#!/usr/bin/env python3
"""
Enhanced ClimateGPT Interface with Personas
Implements persona-based responses and output control for curated answers
"""

import os
import json
import time
import requests
import streamlit as st
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import altair as alt
import logging
import re
import threading
from collections import OrderedDict
from requests.auth import HTTPBasicAuth

# Optional: Response metrics evaluation (for testing/development)
try:
    from test_response_metrics import ResponseEvaluator
    RESPONSE_METRICS_AVAILABLE = True
except ImportError:
    RESPONSE_METRICS_AVAILABLE = False
    ResponseEvaluator = None  # type: ignore

from climategpt_persona_engine import PERSONAS, PERSONA_ORDER, process_persona_question

load_dotenv()

# Streamlit page config MUST be first
st.set_page_config(
    page_title="ClimateGPT with Personas", 
    page_icon="🌍", 
    layout="wide",
    # Disable caching for better testing reliability
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
CONTENT_TYPE_JSON = "application/json"
DEFAULT_UNITS_MESSAGE = "All emissions data is in tonnes CO₂ (MtCO₂ for large values)"
USA_FULL_NAME = "United States of America"
DEFAULT_TIMEOUT = 30


def validate_user_input(query: str) -> Dict[str, Any]:
    """Enhanced user input validation with comprehensive security checks"""
    if not query or not query.strip():
        return {"valid": False, "error": "Query cannot be empty", "severity": "medium"}
    
    if len(query) > 1000:
        return {"valid": False, "error": "Query too long (max 1000 characters)", "severity": "medium"}
    
    # Enhanced security patterns
    SQL_INJECTION = "SQL injection"
    dangerous_patterns = [
        (r'<script.*?>.*?</script>', "XSS script injection", "high"),
        (r'javascript:', "JavaScript injection", "high"),
        (r'data:text/html', "Data URI XSS", "high"),
        (r'\.\./', "Path traversal", "high"),
        (r'UNION.*SELECT', SQL_INJECTION, "high"),
        (r'DROP.*TABLE', SQL_INJECTION, "high"),
        (r'DELETE.*FROM', SQL_INJECTION, "high"),
        (r'INSERT.*INTO', SQL_INJECTION, "high"),
        (r'UPDATE.*SET', SQL_INJECTION, "high"),
        (r'EXEC\s*\(', "Command injection", "critical"),
        (r'<iframe', "Iframe injection", "medium"),
        (r'onload\s*=', "Event handler injection", "medium"),
    ]
    
    for pattern, description, severity in dangerous_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            return {"valid": False, "error": f"Security concern: {description}", "severity": severity}
    
    # Check for potential JSON injection
    if any(char in query for char in ['{', '}', '[', ']', '"', "'"]):
        natural_indicators = ['what', 'how', 'when', 'where', 'why', 'show', 'tell', 'find']
        if not any(indicator in query.lower() for indicator in natural_indicators):
            return {"valid": False, "error": "Query contains suspicious characters", "severity": "low"}
    
    return {"valid": True, "error": None, "severity": "low"}

def safe_json_parse(json_str: str) -> Dict[str, Any]:
    """Safely parse JSON with comprehensive error handling"""
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {"error": f"Invalid JSON format: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

def robust_request(url: str, method: str = "GET", max_retries: int = 3, **kwargs) -> Dict[str, Any]:
    """Make robust HTTP requests with retry logic and comprehensive error handling"""
    last_error = None
    
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
            logger.warning(f"Request timeout for {url} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1 * (2 ** attempt))  # Exponential backoff
                continue
        except requests.exceptions.ConnectionError as e:
            last_error = e
            logger.warning(f"Connection error for {url} (attempt {attempt + 1}/{max_retries})")
            if attempt < max_retries - 1:
                time.sleep(1 * (2 ** attempt))
                continue
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error {e.response.status_code} for {url}")
            return {"error": f"HTTP error {e.response.status_code}: {e.response.text}", "status_code": e.response.status_code}
        except Exception as e:
            last_error = e
            logger.warning(f"Request error for {url} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(1 * (2 ** attempt))
                continue
    
    # All retries failed
    if last_error:
        if isinstance(last_error, requests.exceptions.Timeout):
            return {"error": "Request timed out after multiple attempts. Please try again.", "retries": max_retries}
        elif isinstance(last_error, requests.exceptions.ConnectionError):
            return {"error": "Connection failed after multiple attempts. Please check your network.", "retries": max_retries}
        else:
            return {"error": f"Request failed after {max_retries} attempts: {last_error}", "retries": max_retries}
    
    return {"error": "Unknown error occurred", "retries": max_retries}



# Configuration
MCP_URL = os.environ.get("MCP_URL", "http://127.0.0.1:8010")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://erasmus.ai/models/climategpt_8b_test/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")
if ":" not in OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be in format 'username:password'")
MODEL = os.environ.get("MODEL", "/cache/climategpt_8b_test")
USER, PASS = OPENAI_API_KEY.split(":", 1)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_persona" not in st.session_state:
    st.session_state.selected_persona = PERSONA_ORDER[0]
if "last_result" not in st.session_state:
    st.session_state.last_result = None

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

def normalize_country_name(country_name: str) -> str:
    """Normalize country names to match the data format"""
    country_mapping = {
        "United States": USA_FULL_NAME,
        "USA": USA_FULL_NAME,
        "US": USA_FULL_NAME,
        "China": "People's Republic of China",
        "Russia": "Russian Federation",
        "UK": "United Kingdom",
        "South Korea": "Republic of Korea",
        "North Korea": "Democratic People's Republic of Korea"
    }
    return country_mapping.get(country_name, country_name)

# --- Heuristic geo-entity detection (admin1/city) ---
US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado", "connecticut",
    "delaware", "florida", "georgia", "hawaii", "idaho", "illinois", "indiana", "iowa",
    "kansas", "kentucky", "louisiana", "maine", "maryland", "massachusetts", "michigan",
    "minnesota", "mississippi", "missouri", "montana", "nebraska", "nevada", "new hampshire",
    "new jersey", "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington", "west virginia",
    "wisconsin", "wyoming"
}

# Common city name normalizations (can be extended as needed)
COMMON_CITIES = {
    "new york city": {"city_name": "New York", "country_name": USA_FULL_NAME},
    "new york": {"city_name": "New York", "country_name": USA_FULL_NAME},
    "los angeles": {"city_name": "Los Angeles", "country_name": USA_FULL_NAME},
    "san francisco": {"city_name": "San Francisco", "country_name": USA_FULL_NAME},
    "chicago": {"city_name": "Chicago", "country_name": USA_FULL_NAME},
    "london": {"city_name": "London", "country_name": "United Kingdom"},
    "paris": {"city_name": "Paris", "country_name": "France"},
    "tokyo": {"city_name": "Tokyo", "country_name": "Japan"}
}

def detect_geo_entity(question: str) -> Dict[str, Any]:
    """Detect admin1 or city from the free-text question.
    Returns a dict like {"level": "admin1"|"city", "where": {...}} or {} if none.
    """
    q = (question or "").lower()

    # City detection (exact phrase match first)
    for key, meta in COMMON_CITIES.items():
        if key in q:
            where = {"city_name": meta["city_name"]}
            if meta.get("country_name"):
                where["country_name"] = meta["country_name"]
            return {"level": "city", "where": where}

    # Admin1 detection for US states (simple heuristic)
    for state in US_STATES:
        # Match whole-word state names
        if re.search(rf"\b{re.escape(state)}\b", q):
            # Title-case state for matching stored data
            state_tc = " ".join([w.capitalize() for w in state.split()])
            return {"level": "admin1", "where": {"admin1_name": state_tc, "country_name": USA_FULL_NAME}}

    return {}

def apply_level_constraints_to_tool(tool_json: str, constraints: Dict[str, Any]) -> str:
    """Force level-specific file_id and required where filters onto a single-tool JSON string.
    Best-effort parsing; returns updated JSON string (or original if parsing fails).
    """
    try:
        obj = json.loads(tool_json)
        if not isinstance(obj, dict):
            return tool_json
        args = obj.get("args") or obj.get("tool_args") or {}
        file_id: str = args.get("file_id", "")

        level = constraints.get("level")
        where_req = constraints.get("where", {})
        if level:
            # Preserve sector and grain from existing file_id if present; only swap the level segment
            if file_id:
                file_id = file_id.replace("-country-", f"-{level}-").replace("_country_", f"_{level}_")
                file_id = file_id.replace("-admin1-", f"-{level}-").replace("_admin1_", f"_{level}_")
                file_id = file_id.replace("-city-", f"-{level}-").replace("_city_", f"_{level}_")
                # If no level segment at all, default to yearly grain and transport sector
                if ("-country-" not in file_id and "-admin1-" not in file_id and "-city-" not in file_id):
                    # Try to infer sector prefix if present; else default transport
                    sector_prefix = (file_id.split("-")[0] or "transport") if "-" in file_id else "transport"
                    grain_suffix = "month" if "-month" in file_id or file_id.endswith("month") else "year"
                    file_id = f"{sector_prefix}-{level}-{grain_suffix}"
            else:
                # No file_id provided: choose safe default
                file_id = f"transport-{level}-year"

            args["file_id"] = file_id

        if where_req:
            where = args.get("where", {})
            if not isinstance(where, dict):
                where = {}
            # Merge required keys without overwriting explicit user filters on same key
            for k, v in where_req.items():
                where.setdefault(k, v)
            args["where"] = where

        # Ensure city/admin1 select fields exist for proper display when level constrained
        sel = args.get("select", [])
        if isinstance(sel, list):
            if constraints.get("level") == "city":
                for col in ["city_name", "country_name", "year", "MtCO2"]:
                    if col not in sel:
                        sel.append(col)
            elif constraints.get("level") == "admin1":
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

# Circuit breaker for MCP server calls
class CircuitBreaker:
    """Thread-safe circuit breaker implementation"""
    def __init__(self, max_failures: int = 5, timeout: int = 60):
        self.max_failures = max_failures
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()

    def call(self, func, *args, **kwargs):
        current_time = time.time()

        # Thread-safe state check and transition
        with self._lock:
            # Reset circuit breaker if timeout has passed
            if current_time - self.last_failure_time > self.timeout and self.state == "OPEN":
                self.state = "HALF_OPEN"
                self.failures = 0

            # Check if circuit is open
            if self.state == "OPEN":
                retry_after = self.timeout - (current_time - self.last_failure_time)
                return {
                    "error": "Service temporarily unavailable (circuit breaker open)",
                    "retry_after": retry_after
                }

            # Store current state for decision making after function call
            was_half_open = (self.state == "HALF_OPEN")

        # Execute function outside of lock to avoid holding lock during I/O
        try:
            result = func(*args, **kwargs)

            # Success: update state atomically
            with self._lock:
                if was_half_open:
                    self.state = "CLOSED"
                self.failures = 0

            return result
        except Exception as e:
            # Failure: update state atomically
            with self._lock:
                self.failures += 1
                self.last_failure_time = current_time

                if self.failures >= self.max_failures:
                    self.state = "OPEN"

            raise e

# Global circuit breaker instance
mcp_circuit_breaker = CircuitBreaker()

class SimpleLRUCache:
    """Thread-safe LRU cache implementation"""
    def __init__(self, maxsize: int = 128):
        self.maxsize = maxsize
        self._store = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str):
        """Get value from cache, moving to end (most recently used)"""
        with self._lock:
            try:
                # Move to end before getting to ensure atomicity
                value = self._store.pop(key)
                self._store[key] = value
                return value
            except KeyError:
                return None

    def set(self, key: str, value: Any):
        """Set value in cache, evicting oldest if necessary"""
        with self._lock:
            try:
                # If key exists, remove it first (will be re-added at end)
                self._store.pop(key)
            except KeyError:
                pass

            # Add to end (most recently used)
            self._store[key] = value

            # Evict oldest if over capacity
            if len(self._store) > self.maxsize:
                self._store.popitem(last=False)

# Cache for tool call responses to avoid repeated MCP hits on retries/batch
_TOOL_CACHE = SimpleLRUCache(maxsize=int(os.environ.get("MCP_TOOL_CACHE_SIZE", "256")))

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
    
    # Remove any leading/trailing quotes if the entire response is quoted
    if cleaned_json.startswith('"') and cleaned_json.endswith('"'):
        cleaned_json = cleaned_json[1:-1]
        # Unescape any escaped quotes
        cleaned_json = cleaned_json.replace('\\"', '"')
    
    try:
        obj = json.loads(cleaned_json)
    except json.JSONDecodeError as e:
        # Try to extract the FIRST complete JSON object only
        start = cleaned_json.find("{")
        if start != -1:
            # Find the first complete JSON object by counting braces
            brace_count = 0
            json_end = -1
            for i, char in enumerate(cleaned_json[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end = i
                        break
            
            if json_end != -1:
                json_candidate = cleaned_json[start:json_end+1]
                try:
                    obj = json.loads(json_candidate)
                except json.JSONDecodeError as e2:
                    return {
                        "error": f"Invalid JSON format: {str(e2)}", 
                        "raw": tool_json[:200] + "..." if len(tool_json) > 200 else tool_json,
                        "debug": f"Tried to parse: {json_candidate[:200]}..."
                    }
            else:
                return {
                    "error": f"Invalid JSON format: {str(e)}", 
                    "raw": tool_json[:200] + "..." if len(tool_json) > 200 else tool_json,
                    "debug": "No complete JSON object found"
                }
        else:
            return {
                "error": f"JSON decode error: {str(e)}", 
                "raw": tool_json[:200] + "..." if len(tool_json) > 200 else tool_json,
                "debug": "No valid JSON brackets found"
            }
    
    # Handle both "tool"/"args" and "tool_call"/"tool_args" formats
    tool = obj.get("tool") or obj.get("tool_call")
    args = obj.get("args", {}) or obj.get("tool_args", {})
    
    # Define HTTP helpers with retry/backoff using robust_request
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
    
    # Define MCP server operations with circuit breaker protection
    def _list_files():
        return _http_get(f"{MCP_URL}/list_files")
    
    def _get_schema(file_id):
        return _http_get(f"{MCP_URL}/get_schema/{file_id}")
    
    def _execute_query(query_args):
        # Normalize country names in the query
        if "where" in query_args and "country_name" in query_args["where"]:
            query_args["where"]["country_name"] = normalize_country_name(query_args["where"]["country_name"])
        # Enable server-side assist by default
        query_args.setdefault("assist", True)
        return _http_post(f"{MCP_URL}/query", query_args)
    
    def _execute_yoy_metrics(metrics_args):
        return _http_post(f"{MCP_URL}/metrics/yoy", metrics_args)
    
    def _execute_batch_query(batch_args):
        return _http_post(f"{MCP_URL}/batch/query", batch_args)
    
    # Execute tool with circuit breaker protection
    try:
        # Cache key based on normalized tool+args
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
            # Primary attempt
            result = mcp_circuit_breaker.call(_execute_query, args)

            # Robust fallbacks when result is empty or error
            def _is_empty(res: dict) -> bool:
                return isinstance(res, dict) and ("rows" in res) and (not res["rows"])

            def _fuzzy_where(original_where: dict) -> dict:
                new_where = {}
                for k, v in (original_where or {}).items():
                    if isinstance(v, str) and v.strip():
                        new_where[k] = {"contains": v.strip()}
                    else:
                        new_where[k] = v
                return new_where

            def _switch_level(file_id: str, direction: str) -> str:
                # direction: "down" city->admin1->country
                if direction == "down":
                    file_id = file_id.replace("-city-", "-admin1-")
                    file_id = file_id.replace("_city_", "_admin1_")
                    if "-city-" not in file_id and "_city_" not in file_id and (
                        "-admin1-" in file_id or "_admin1_" in file_id
                    ):
                        return file_id
                    # If already admin1 or switch failed, go to country
                    file_id = file_id.replace("-admin1-", "-country-")
                    file_id = file_id.replace("_admin1_", "_country_")
                    return file_id
                return file_id

            def _strip_place_filters(where: dict, target_level: str) -> dict:
                if not isinstance(where, dict):
                    return where
                new_where = dict(where)
                if target_level == "admin1":
                    new_where.pop("city_name", None)
                    new_where.pop("city_id", None)
                if target_level == "country":
                    new_where.pop("city_name", None)
                    new_where.pop("city_id", None)
                    new_where.pop("admin1_name", None)
                    new_where.pop("admin1_geoid", None)
                return new_where

            # 1) If empty, try fuzzy contains on string filters
            if ("error" in result) or _is_empty(result):
                fuzzy_args = dict(args)
                fuzzy_args["where"] = _fuzzy_where(args.get("where", {}))
                try:
                    result2 = mcp_circuit_breaker.call(_execute_query, fuzzy_args)
                    if not ("error" in result2 or _is_empty(result2)):
                        result = result2
                except Exception:
                    pass

            # 2) If still empty and file_id is city/admin1, roll up a level
            def _level_of(fid: str) -> str:
                if ("-city-" in fid) or ("_city_" in fid):
                    return "city"
                if ("-admin1-" in fid) or ("_admin1_" in fid):
                    return "admin1"
                return "country"

            if ("error" in result) or _is_empty(result):
                current_level = _level_of(args.get("file_id", ""))
                if current_level in ("city", "admin1"):
                    rolled_args = dict(args)
                    rolled_args["file_id"] = _switch_level(args["file_id"], "down")
                    target_level = _level_of(rolled_args["file_id"])  # after switch
                    rolled_args["where"] = _strip_place_filters(args.get("where", {}), target_level)
                    try:
                        result3 = mcp_circuit_breaker.call(_execute_query, rolled_args)
                        if not ("error" in result3 or _is_empty(result3)):
                            result = result3
                    except Exception:
                        pass

            # 3) If still empty, drop filters and return a tiny default slice
            if ("error" in result) or _is_empty(result):
                loose_args = dict(args)
                loose_args.pop("where", None)
                loose_args.setdefault("limit", 5)
                try:
                    result4 = mcp_circuit_breaker.call(_execute_query, loose_args)
                    if not ("error" in result4 or _is_empty(result4)):
                        result = result4
                except Exception:
                    pass
        elif tool in ("metrics.yoy", "yoy"):
            result = mcp_circuit_breaker.call(_execute_yoy_metrics, args)
        elif tool == "batch_query":
            result = mcp_circuit_breaker.call(_execute_batch_query, args)
        else:
            return {"error": f"Unknown tool '{tool}'. Supported tools: list_files, get_schema, query, metrics.yoy, batch_query"}
        
        if cache_key and isinstance(result, dict) and "error" not in result:
            _TOOL_CACHE.set(cache_key, result)
        return result
    
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. The server is taking too long to respond.", "retry": True}
    except requests.exceptions.ConnectionError:
        return {"error": "Connection failed. Please check if the MCP server is running.", "retry": True}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}", "status_code": e.response.status_code}
    except Exception as e:
        logger.error(f"Unexpected error in exec_tool_call: {e}")
        return {"error": f"Unexpected error: {str(e)}"}

def process_climategpt_question(question: str, persona_key: str) -> Tuple[str, Dict[str, Any], str]:
    """Adapter that delegates persona handling to the shared persona engine."""
    answer, data_context, used_tool = process_persona_question(question, persona_key)

    # Persist last result for export/download features when tabular data is present
    if isinstance(data_context, dict):
        try:
            st.session_state.last_result = data_context if data_context.get("rows") else None
        except Exception:
            pass

    return answer, data_context, used_tool

# Status check functions
def test_mcp_connection():
    try:
        response = requests.get(f"{MCP_URL}/health", timeout=5)
        return response.status_code == 200
    except (requests.exceptions.RequestException, requests.exceptions.Timeout, 
              requests.exceptions.ConnectionError, json.JSONDecodeError) as e:
        logger.error(f"Connection test failed: {e}")
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
            headers={"Content-Type": CONTENT_TYPE_JSON},
            data=json.dumps(payload),
            auth=HTTPBasicAuth(USER, PASS) if USER else None,
            timeout=10,
        )
        return response.status_code == 200
    except (requests.exceptions.RequestException, requests.exceptions.Timeout, 
              requests.exceptions.ConnectionError, json.JSONDecodeError) as e:
        logger.error(f"Connection test failed: {e}")
        return False

# Main UI
st.title("🌍 ClimateGPT for Climate Analysts — Multi-Sector Emissions QA")
st.write("Select your professional role and ask questions in plain English. ClimateGPT will provide responses tailored to your analytical needs.")

# Note about caching being disabled for testing
st.info("🚀 **Testing Mode**: Caching disabled for reliable testing and development")

## (Persona selection UI moved inline with the message bar; previous persona grid removed)

# Compact status row
m_ok = test_mcp_connection()
l_ok = test_climategpt_connection()
cb_state = mcp_circuit_breaker.state

status_chip = (
    ("🟢 Healthy" if cb_state == "CLOSED" else ("🟡 Recovering" if cb_state == "HALF_OPEN" else "🔴 Overloaded"))
)
st.caption(
    f"Status: {'🟢' if m_ok else '🔴'} MCP · {'🟢' if l_ok else '🔴'} LLM · {status_chip}"
)

## (Debug & Data Troubleshooting removed per request)

## (Example Questions removed per request)

## (Data Coverage removed per request)

# Conversation and performance management
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
with col1:
    if st.button("🗑️ Clear Chat"):
        st.session_state.messages = []
        st.rerun()

with col2:
    # Export: prefer CSV of last_result rows if available, else conversation JSON
    has_rows = isinstance(st.session_state.get("last_result"), dict) and st.session_state.last_result.get("rows")
    if has_rows:
        try:
            df = pd.DataFrame(st.session_state.last_result.get("rows", []))
            if not df.empty:
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Export Last Result (CSV)",
                    data=csv_bytes,
                    file_name=f"climategpt_result_{time.strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                )
        except Exception:
            pass
    if st.button("📊 Export Chat"):
        if st.session_state.messages:
            export_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "selected_persona": st.session_state.selected_persona,
                "conversation": st.session_state.messages
            }
            json_str = json.dumps(export_data, indent=2, ensure_ascii=False)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name=f"climategpt_persona_conversation_{time.strftime('%Y%m%d_%H%M%S')}.json",
                mime=CONTENT_TYPE_JSON
            )
        else:
            st.warning("No conversation to export")

with col3:
    if st.button("🔄 Refresh App"):
        st.rerun()

with col4:
    st.caption(f"💬 {len(st.session_state.messages)} messages", unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Add export button for assistant messages with data
        if message["role"] == "assistant" and "Source:" in message["content"]:
            # Try to extract data from the message for export
            if st.button("📥 Export Data", key="export_" + str(len(st.session_state.messages))):
                # This would need to be enhanced to extract actual data
                st.info("Data export feature - would extract tabular data from response")

st.divider()
c_msg, c_persona = st.columns([0.8, 0.2])

with c_persona:
    persona_options = PERSONA_ORDER
    current_idx = persona_options.index(st.session_state.selected_persona) if st.session_state.selected_persona in persona_options else 0
    new_persona = st.selectbox(
        "Persona",
        options=persona_options,
        index=current_idx,
        format_func=lambda k: f"{PERSONAS[k]['icon']} {PERSONAS[k]['name']}",
        label_visibility="collapsed",
        key="persona_inline_select",
    )
    if new_persona != st.session_state.selected_persona:
        st.session_state.selected_persona = new_persona
        try:
            # Streamlit modern API for query params
            try:
                st.query_params["persona"] = new_persona
            except Exception:
                st.query_params.from_dict({"persona": new_persona})
        except Exception:
            pass

with c_msg:
    try:
        qp = st.query_params
        qp_persona = qp.get("persona")
        if isinstance(qp_persona, list):
            qp_persona = qp_persona[0] if qp_persona else None
        if qp_persona and qp_persona in PERSONAS and qp_persona != st.session_state.selected_persona:
            st.session_state.selected_persona = qp_persona
    except Exception:
        pass
    placeholder = f"Ask {PERSONAS[st.session_state.selected_persona]['name']} about climate emissions data..."
    prompt = st.chat_input(placeholder)

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        with st.spinner(f"{PERSONAS[st.session_state.selected_persona]['name']} is analyzing your question..."):
            try:
                start_time = time.time()
                answer, data_context, used_tool = process_climategpt_question(prompt, st.session_state.selected_persona)
                response_time = time.time() - start_time

                st.markdown(answer)

                if data_context and RESPONSE_METRICS_AVAILABLE:
                    try:
                        evaluator = ResponseEvaluator()
                        evaluation = evaluator.evaluate_response(
                            question=prompt,
                            response=answer,
                            data_context=data_context,
                            tool_used=used_tool,
                        )

                        with st.expander("📊 Response Quality Metrics", expanded=False):
                            col1, col2, col3 = st.columns(3)

                            accuracy_data = evaluation.get("accuracy", {}) if isinstance(evaluation, dict) else {}
                            groundedness_data = evaluation.get("groundedness", {}) if isinstance(evaluation, dict) else {}
                            completeness_data = evaluation.get("completeness", {}) if isinstance(evaluation, dict) else {}

                            accuracy_score = accuracy_data.get("score", 0) if isinstance(accuracy_data, dict) else 0
                            groundedness_score = groundedness_data.get("score", 0) if isinstance(groundedness_data, dict) else 0
                            completeness_score = completeness_data.get("score", 0) if isinstance(completeness_data, dict) else 0

                            with col1:
                                st.metric("Accuracy", f"{accuracy_score:.2f}", help="Verifies numerical claims against actual data")
                            with col2:
                                st.metric("Groundedness", f"{groundedness_score:.2f}", help="Checks if response references available data points")
                            with col3:
                                st.metric("Completeness", f"{completeness_score:.2f}", help="Ensures all question aspects are addressed")

                            overall_score = evaluation.get("overall_score", 0) if isinstance(evaluation, dict) else 0
                            grade = evaluation.get("grade", "F") if isinstance(evaluation, dict) else "F"
                            st.markdown(f"**Overall Grade: {grade} ({overall_score:.2f})**")

                            if st.checkbox("Show detailed evaluation", key=f"details_{len(st.session_state.messages)}"):
                                st.markdown("### Detailed Evaluation Report")
                                evaluator.print_evaluation_report(evaluation)

                    except Exception as eval_error:
                        st.warning(f"Could not evaluate response: {str(eval_error)}")

                st.caption(f"⏱️ Response time: {response_time:.2f}s | Persona: {PERSONAS[st.session_state.selected_persona]['name']}")
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                error_msg = f"Sorry, I encountered an error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
