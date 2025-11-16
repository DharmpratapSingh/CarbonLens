#!/usr/bin/env python3
"""
ClimateGPT MCP Server (TRUE MCP Protocol)
Communicates via stdio using MCP protocol
"""
import asyncio
import calendar
import json
import logging
import os
import re
import time
import hashlib
import uuid
from pathlib import Path
from typing import Any, Optional, Dict, List, Tuple, Set
from datetime import datetime, timedelta
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    Prompt,
    PromptMessage,
    PromptArgument,
)

import duckdb
from functools import lru_cache
import threading
from queue import Queue, Empty, Full
from contextlib import contextmanager

# ---------------------------------------------------------------------
# Logging Infrastructure (from mcp_server.py)
# ---------------------------------------------------------------------
def _setup_logging():
    """Setup structured logging with JSON format for production."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("LOG_FORMAT", "json")  # "json" or "text"

    # Create logger
    logger = logging.getLogger("climategpt_mcp")
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # Create formatter
    if log_format == "json":
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                if hasattr(record, "request_id"):
                    log_entry["request_id"] = record.request_id
                if hasattr(record, "query_context"):
                    log_entry["query_context"] = record.query_context
                if record.exc_info:
                    log_entry["exception"] = self.formatException(record.exc_info)
                return json.dumps(log_entry)

        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional)
    log_file = os.getenv("LOG_FILE")
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

logger = _setup_logging()

# Initialize MCP server
app = Server("climategpt")

# Load manifest (same logic as mcp_server.py)
manifest_env = os.getenv("MCP_MANIFEST_PATH")
manifest_path = Path(manifest_env) if manifest_env else Path("data/curated-2/manifest_mcp_duckdb.json")

if not manifest_path.exists():
    raise FileNotFoundError(f"Manifest not found at {manifest_path}")

with open(manifest_path, "r") as f:
    MANIFEST = json.load(f)

# Database path resolution (from mcp_server.py)
def _resolve_db_path(db_path: str) -> str:
    """Resolve database path (relative or absolute)"""
    if Path(db_path).is_absolute():
        return db_path
    # Get project root (parent of this file)
    project_root = Path(__file__).parent
    resolved = project_root / db_path
    return str(resolved)

# Get DB path from manifest
first_file = MANIFEST["files"][0] if MANIFEST.get("files") else None
if first_file and first_file.get("path", "").startswith("duckdb://"):
    db_uri = first_file["path"]
    db_path_raw = db_uri[len("duckdb://"):].split("#")[0]
    DB_PATH = _resolve_db_path(db_path_raw)
else:
    DB_PATH = _resolve_db_path("data/warehouse/climategpt.duckdb")

# ---------------------------------------------------------------------
# Security and Input Validation (from mcp_server.py)
# ---------------------------------------------------------------------
# Project root for path resolution
_PROJECT_ROOT = Path(__file__).parent

# Valid characters for identifiers (file_id, column names)
_IDENTIFIER_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
_MAX_QUERY_COMPLEXITY = {
    "max_columns": 50,
    "max_filters": 20,
    "max_list_items": 100,
    "max_string_length": 500,
    "max_query_size": 10000,  # bytes
}

# Config defaults (env-driven)
ASSIST_DEFAULT = os.getenv("ASSIST_DEFAULT", "true").lower() == "true"
PROXY_DEFAULT = os.getenv("PROXY_DEFAULT", "false").lower() == "true"
PROXY_MAX_K_DEFAULT = int(os.getenv("PROXY_MAX_K", "3") or 3)
PROXY_RADIUS_KM_DEFAULT = int(os.getenv("PROXY_RADIUS_KM", "150") or 150)

# ---------------------------------------------------------------------
# File ID resolver (for future alias support)
# ---------------------------------------------------------------------
def _resolve_file_id(fid: str) -> str:
    """Resolve file_id, potentially applying aliases in the future."""
    # Aliases removed - they referenced non-existent .expanded datasets
    # Keep function for future alias support if needed
    return fid

# ---------------------------------------------------------------------
# Enhanced Validation Functions (from mcp_server.py)
# ---------------------------------------------------------------------
def _validate_file_id_enhanced(file_id: str) -> Tuple[bool, Optional[str]]:
    """Validate file_id format and prevent path traversal."""
    if not file_id or not isinstance(file_id, str):
        return False, "file_id must be a non-empty string"

    if len(file_id) > 200:
        return False, "file_id too long (max 200 characters)"

    # Prevent path traversal
    if '..' in file_id or '/' in file_id or '\\' in file_id:
        return False, "file_id contains invalid characters"

    # Check for valid identifier pattern
    if not _IDENTIFIER_PATTERN.match(file_id):
        return False, "file_id contains invalid characters (only alphanumeric, _, -, . allowed)"

    return True, None


def _validate_column_name_enhanced(col: str) -> Tuple[bool, Optional[str]]:
    """Validate column name to prevent SQL injection."""
    if not col or not isinstance(col, str):
        return False, "Column name must be a non-empty string"

    if len(col) > 100:
        return False, "Column name too long (max 100 characters)"

    # Whitelist approach - only allow safe characters
    if not _IDENTIFIER_PATTERN.match(col):
        return False, "Column name contains invalid characters"

    # Prevent SQL keywords (basic check)
    sql_keywords = {'select', 'from', 'where', 'insert', 'update', 'delete',
                    'drop', 'create', 'alter', 'exec', 'execute', 'union'}
    if col.lower() in sql_keywords:
        return False, f"Column name cannot be SQL keyword: {col}"

    return True, None


def _validate_filter_value(value: Any, filter_type: str) -> Tuple[bool, Optional[str]]:
    """Validate filter values for safety and size limits."""
    if filter_type == "list" and isinstance(value, list):
        if len(value) > _MAX_QUERY_COMPLEXITY["max_list_items"]:
            return False, f"Filter list too large (max {_MAX_QUERY_COMPLEXITY['max_list_items']} items)"
        for item in value:
            if isinstance(item, str) and len(item) > _MAX_QUERY_COMPLEXITY["max_string_length"]:
                return False, f"Filter list item too long (max {_MAX_QUERY_COMPLEXITY['max_string_length']} chars)"

    if isinstance(value, str):
        if len(value) > _MAX_QUERY_COMPLEXITY["max_string_length"]:
            return False, f"Filter value too long (max {_MAX_QUERY_COMPLEXITY['max_string_length']} chars)"
        # Check for potential injection patterns
        if re.search(r'[;\'"\\]', value):
            return False, "Filter value contains potentially dangerous characters"

    return True, None


# ---------------------------------------------------------------------
# Error handling helpers (from mcp_server.py)
# ---------------------------------------------------------------------
def _parse_duckdb_column_error(error_str: str) -> Optional[Tuple[List[str], List[str]]]:
    """
    Parse DuckDB error to detect invalid column errors.
    Returns (bad_columns, candidate_columns) if it's a column error, None otherwise.

    Example: "Binder Error: Referenced column \"x\" not found...\nCandidate bindings: \"a\", \"b\""
    """
    error_lower = error_str.lower()

    # Check if it's a column not found error
    if "referenced column" not in error_lower or "not found" not in error_lower:
        return None

    # Extract column names from error message
    # Find quoted column names (the ones that don't exist)
    missing_pattern = r'Referenced column\s+"([^"]+)"'
    missing_match = re.search(missing_pattern, error_str, re.IGNORECASE)
    if not missing_match:
        return None

    bad_columns = [missing_match.group(1)]

    # Extract candidate bindings
    candidate_pattern = r'Candidate bindings:\s*"([^"]+)"(?:\s*,\s*"([^"]+)")*'
    candidate_match = re.search(candidate_pattern, error_str)
    candidate_columns = []
    if candidate_match:
        # Get all quoted values after "Candidate bindings:"
        all_matches = re.findall(r'"([^"]+)"', error_str[error_str.find("Candidate bindings:"):])
        candidate_columns = all_matches if all_matches else []

    return bad_columns, candidate_columns


def _error_response(code: str, detail: str, hint: Optional[str] = None,
                   context: Optional[Dict[str, Any]] = None,
                   suggestions: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Create a standardized error response with enhanced context.

    Args:
        code: Error code (e.g., "file_not_found", "read_failed")
        detail: Detailed error message
        hint: Optional hint for resolving the error
        context: Additional context about the error
        suggestions: List of suggested actions

    Returns:
        Standardized error dict
    """
    response: Dict[str, Any] = {
        "error": code,
        "detail": detail,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    if hint:
        response["hint"] = hint
    if context:
        response["context"] = context
    if suggestions:
        response["suggestions"] = suggestions

    return response


# ---------------------------------------------------------------------
# Query Validation and Intent Detection (from mcp_server.py)
# ---------------------------------------------------------------------
def _parse_temporal_coverage(coverage_str: str) -> Optional[Tuple[int, int]]:
    """Parse temporal coverage string like '2000-2023' into (start, end)."""
    if not coverage_str or '-' not in coverage_str:
        return None
    try:
        parts = coverage_str.split('-')
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        pass
    return None


def _validate_query_complexity(
    select: List[str],
    where: Dict[str, Any],
    group_by: List[str],
    order_by: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """Validate query complexity to prevent DoS."""
    issues = []

    # Check column count
    if len(select) > _MAX_QUERY_COMPLEXITY["max_columns"]:
        issues.append(f"Too many columns in select (max {_MAX_QUERY_COMPLEXITY['max_columns']})")

    # Check filter count
    if len(where) > _MAX_QUERY_COMPLEXITY["max_filters"]:
        issues.append(f"Too many filters (max {_MAX_QUERY_COMPLEXITY['max_filters']})")

    # Check group_by count
    if len(group_by) > _MAX_QUERY_COMPLEXITY["max_columns"]:
        issues.append(f"Too many group_by columns (max {_MAX_QUERY_COMPLEXITY['max_columns']})")

    # Validate all column names
    all_columns = set(select) | set(group_by)
    if order_by:
        order_col = order_by.split()[0]
        all_columns.add(order_col)

    for col in all_columns:
        valid, error = _validate_column_name_enhanced(col)
        if not valid:
            issues.append(f"Invalid column name '{col}': {error}")

    # Validate filter values
    for key, value in where.items():
        if isinstance(value, dict):
            if "in" in value and isinstance(value["in"], list):
                valid, error = _validate_filter_value(value["in"], "list")
                if not valid:
                    issues.append(f"Invalid filter value for '{key}': {error}")
        else:
            valid, error = _validate_filter_value(value, "single")
            if not valid:
                issues.append(f"Invalid filter value for '{key}': {error}")

    if issues:
        return False, "; ".join(issues), {
            "max_columns": _MAX_QUERY_COMPLEXITY["max_columns"],
            "max_filters": _MAX_QUERY_COMPLEXITY["max_filters"],
        }

    return True, None, None


# ---------------------------------------------------------------------
# Phase 3: Advanced Query Features (from mcp_server.py)
# ---------------------------------------------------------------------

def _validate_aggregation_function(func: str) -> Tuple[bool, Optional[str]]:
    """Validate aggregation function name."""
    valid_functions = {"sum", "avg", "mean", "min", "max", "count", "distinct", "std", "stddev", "variance"}
    if func.lower() not in valid_functions:
        return False, f"Invalid aggregation function: {func}. Allowed: {', '.join(sorted(valid_functions))}"
    return True, None


def _build_aggregation_sql(aggregations: Dict[str, str], select: List[str]) -> Tuple[str, List[str]]:
    """
    Build SQL for aggregations.
    Returns (SQL fragment, list of aggregated columns for SELECT).
    """
    if not aggregations:
        return "", select if select else []

    agg_parts = []
    agg_cols = []

    for col, func in aggregations.items():
        # Validate column name (basic validation - schema check happens later)
        valid_col, col_error = _validate_column_name_enhanced(col)
        if not valid_col:
            raise ValueError(f"Invalid column in aggregation: {col_error}")

        # Validate function
        valid_func, func_error = _validate_aggregation_function(func)
        if not valid_func:
            raise ValueError(func_error)

        func_upper = func.upper()
        # Quote column name for safety
        quoted_col = f'"{col}"'
        if func_upper == "DISTINCT":
            agg_parts.append(f"COUNT(DISTINCT {quoted_col}) AS \"{col}_distinct_count\"")
            agg_cols.append(f"{col}_distinct_count")
        elif func_upper == "COUNT":
            agg_parts.append(f"COUNT({quoted_col}) AS \"{col}_count\"")
            agg_cols.append(f"{col}_count")
        elif func_upper in ("AVG", "MEAN"):
            agg_parts.append(f"AVG({quoted_col}) AS \"{col}_avg\"")
            agg_cols.append(f"{col}_avg")
        elif func_upper == "SUM":
            agg_parts.append(f"SUM({quoted_col}) AS \"{col}_sum\"")
            agg_cols.append(f"{col}_sum")
        elif func_upper == "MIN":
            agg_parts.append(f"MIN({quoted_col}) AS \"{col}_min\"")
            agg_cols.append(f"{col}_min")
        elif func_upper == "MAX":
            agg_parts.append(f"MAX({quoted_col}) AS \"{col}_max\"")
            agg_cols.append(f"{col}_max")
        elif func_upper in ("STD", "STDDEV"):
            agg_parts.append(f"STDDEV({quoted_col}) AS \"{col}_stddev\"")
            agg_cols.append(f"{col}_stddev")
        elif func_upper == "VARIANCE":
            agg_parts.append(f"VAR({quoted_col}) AS \"{col}_variance\"")
            agg_cols.append(f"{col}_variance")

    # Combine with regular select columns
    all_cols = (select if select else []) + agg_cols
    sql_fragment = ", ".join(agg_parts) if agg_parts else ""

    return sql_fragment, all_cols


def _build_having_sql(having: Dict[str, Any]) -> Tuple[str, list]:
    """
    Build SQL HAVING clause for post-aggregation filtering.
    Similar to WHERE but for aggregated columns.
    """
    if not having:
        return "", []

    clauses = []
    params = []

    for key, val in having.items():
        # Validate column name (can be aggregated column alias)
        valid, error = _validate_column_name_enhanced(key)
        if not valid:
            raise ValueError(f"Invalid column in HAVING: {error}")

        if isinstance(val, dict):
            if "in" in val:
                placeholders = ", ".join(["?" for _ in val["in"]])
                clauses.append(f'"{key}" IN ({placeholders})')
                params.extend(val["in"])
            elif "between" in val:
                lo, hi = val["between"]
                clauses.append(f'"{key}" BETWEEN ? AND ?')
                params.extend([lo, hi])
            elif "gte" in val:
                clauses.append(f'"{key}" >= ?')
                params.append(val["gte"])
            elif "lte" in val:
                clauses.append(f'"{key}" <= ?')
                params.append(val["lte"])
            elif "gt" in val:
                clauses.append(f'"{key}" > ?')
                params.append(val["gt"])
            elif "lt" in val:
                clauses.append(f'"{key}" < ?')
                params.append(val["lt"])
            elif "contains" in val:
                clauses.append(f'CAST("{key}" AS VARCHAR) LIKE ?')
                params.append(f"%{val['contains']}%")
        else:
            # Equality
            clauses.append(f'"{key}" = ?')
            params.append(val)

    if not clauses:
        return "", []
    return " HAVING " + " AND ".join(clauses), params


# ---------------------------------------------------------------------
# Phase 3.5: DuckDB Query Optimizations (from mcp_server.py)
# ---------------------------------------------------------------------

def _duckdb_pushdown(
    file_meta: Dict[str, Any],
    select: List[str],
    where: Dict[str, Any],
    group_by: List[str],
    order_by: Optional[str],
    limit: Optional[int],
    offset: Optional[int] = 0,
    aggregations: Optional[Dict[str, str]] = None,
    having: Optional[Dict[str, Any]] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Pushdown query to DuckDB for maximum performance.
    Returns list of row dicts, or None if not DuckDB engine.
    """
    if file_meta.get("engine") != "duckdb":
        return None

    uri = file_meta.get("path")
    if not uri or not uri.startswith("duckdb://"):
        return None

    db_path, _, table = uri[len("duckdb://"):].partition("#")
    if not table:
        return None

    # Security: Validate table name
    valid_table, table_error = _validate_column_name_enhanced(table)
    if not valid_table:
        raise ValueError(f"Invalid table name in pushdown: {table_error}")

    # Security: Validate all column names
    all_cols = set(select) | set(group_by)
    if order_by:
        order_col = order_by.split()[0]
        # For aggregated columns, the order_by might use the aggregated name
        if aggregations:
            is_agg_col = False
            for orig_col, func in aggregations.items():
                func_upper = func.upper()
                expected_names = {
                    "SUM": f"{orig_col}_sum",
                    "AVG": f"{orig_col}_avg", "MEAN": f"{orig_col}_avg",
                    "COUNT": f"{orig_col}_count",
                    "DISTINCT": f"{orig_col}_distinct_count",
                    "MIN": f"{orig_col}_min",
                    "MAX": f"{orig_col}_max"
                }
                if func_upper in expected_names and order_col == expected_names[func_upper]:
                    is_agg_col = True
                    break
                elif order_col == orig_col:
                    is_agg_col = True
                    break
            if not is_agg_col:
                all_cols.add(order_col)
        else:
            all_cols.add(order_col)

    for col in all_cols:
        valid, error = _validate_column_name_enhanced(col)
        if not valid:
            raise ValueError(f"Invalid column name in pushdown: {error}")

    # Build SELECT clause with aggregations
    if aggregations:
        agg_sql, agg_cols = _build_aggregation_sql(aggregations, select)
        if agg_sql:
            group_select_cols = [f'"{col}"' for col in group_by] if group_by else []
            select_cols = [f'"{col}"' for col in select] if select else []
            all_select_cols = list(dict.fromkeys(group_select_cols + select_cols))
            if all_select_cols and agg_sql:
                cols = ", ".join(all_select_cols) + ", " + agg_sql
            elif agg_sql:
                cols = agg_sql
                if group_by and not select:
                    group_cols = ", ".join([f'"{col}"' for col in group_by])
                    cols = group_cols + ", " + agg_sql if cols else group_cols
            else:
                cols = ", ".join(all_select_cols) if all_select_cols else "*"
        else:
            cols = ", ".join([f'"{col}"' for col in select]) if select else "*"
    else:
        cols = ", ".join([f'"{col}"' for col in select]) if select else "*"

    where_sql, params = _build_where_sql(where)

    if group_by:
        quoted_cols = [f'"{col}"' for col in group_by]
        group_sql = f" GROUP BY {', '.join(quoted_cols)}"
    else:
        group_sql = ""

    # Add HAVING clause
    having_sql, having_params = _build_having_sql(having) if having else ("", [])
    params.extend(having_params)

    order_sql = ""
    if order_by:
        parts = order_by.split()
        col = parts[0]
        dirc = parts[1] if len(parts) > 1 else ""

        # If using aggregations, check if order_by column needs aggregated name
        if aggregations:
            for orig_col, func in aggregations.items():
                func_upper = func.upper()
                expected_names = {
                    "SUM": f"{orig_col}_sum",
                    "AVG": f"{orig_col}_avg", "MEAN": f"{orig_col}_avg",
                    "COUNT": f"{orig_col}_count",
                    "DISTINCT": f"{orig_col}_distinct_count",
                    "MIN": f"{orig_col}_min",
                    "MAX": f"{orig_col}_max"
                }
                if func_upper in expected_names:
                    expected_name = expected_names[func_upper]
                    if col == orig_col:
                        col = expected_name
                        break
                    elif col == expected_name:
                        break

        order_sql = f' ORDER BY "{col}" {dirc}'

    limit_sql = ""
    if offset:
        limit_sql += f" OFFSET {int(offset)}"
    if limit:
        limit_sql = f" LIMIT {int(limit)}" + limit_sql

    sql = f"SELECT {cols} FROM {table}{where_sql}{group_sql}{having_sql}{order_sql}{limit_sql}"

    try:
        with _get_db_connection() as conn:
            cursor = conn.execute(sql, params)
            # Get column names from cursor (avoid re-executing query)
            column_names = [desc[0] for desc in cursor.description]
            result = cursor.fetchall()
            # Convert to list of dicts
            return [dict(zip(column_names, row)) for row in result]
    except Exception as e:
        logger.error(f"DuckDB pushdown error: {e}")
        logger.error(f"SQL: {sql}")
        logger.error(f"Params: {params}")
        raise


def _duckdb_yoy(
    file_meta: Dict[str, Any],
    key_col: str,
    value_col: str,
    base_year: int,
    compare_year: int,
    extra_where: Dict[str, Any],
    top_n: int,
    direction: str,
) -> Optional[List[Dict[str, Any]]]:
    """
    Optimized year-over-year calculation using DuckDB.
    Returns list of row dicts with YoY changes.
    """
    if file_meta.get("engine") != "duckdb":
        return None

    uri = file_meta.get("path")
    if not uri or not uri.startswith("duckdb://"):
        return None

    db_path, _, table = uri[len("duckdb://"):].partition("#")
    if not table:
        return None

    # Security: Validate table name
    valid_table, table_error = _validate_column_name_enhanced(table)
    if not valid_table:
        raise ValueError(f"Invalid table name: {table_error}")

    # Security: Validate column names
    for col in [key_col, value_col]:
        valid, error = _validate_column_name_enhanced(col)
        if not valid:
            raise ValueError(f"Invalid column name in yoy: {error}")

    # Build WHERE with enforced years
    where = dict(extra_where or {})
    where["year"] = {"in": [base_year, compare_year]}
    where_sql, params = _build_where_sql(where)

    sql = f"""
        WITH t AS (
            SELECT {key_col} AS k, CAST(year AS INT) AS y, SUM({value_col}) AS v
            FROM {table}
            {where_sql}
            GROUP BY {key_col}, y
        )
        SELECT a.k AS key,
               a.v AS base,
               b.v AS compare,
               (a.v - b.v) AS delta,
               CASE WHEN a.v <> 0 THEN (a.v - b.v) / a.v * 100.0 ELSE NULL END AS pct
        FROM t a
        JOIN t b ON a.k = b.k AND a.y = ? AND b.y = ?
        ORDER BY delta {'DESC' if direction == 'drop' else 'ASC'}
        LIMIT {int(top_n)}
    """

    try:
        with _get_db_connection() as conn:
            result = conn.execute(sql, params + [base_year, compare_year]).fetchall()
            column_names = ['key', 'base', 'compare', 'delta', 'pct']
            return [dict(zip(column_names, row)) for row in result]
    except Exception as e:
        logger.error(f"DuckDB YoY error: {e}")
        raise


# Note: Computed columns are complex and require pandas
# They may not be needed for the MCP stdio server initially
# Keeping stub for future implementation
def _validate_computed_expression(expression: str, available_columns: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate computed column expression for security.
    Placeholder for future implementation.
    """
    import ast

    # Length limit to prevent abuse
    if len(expression) > 500:
        return False, "Expression too long (max 500 characters)"

    # Forbidden patterns (case-insensitive)
    forbidden = ['import', 'exec', 'eval', '__', 'compile', 'globals', 'locals', 'open', 'file']
    expr_lower = expression.lower()
    for pattern in forbidden:
        if pattern in expr_lower:
            return False, f"Forbidden pattern '{pattern}' in expression"

    return True, None


# ---------------------------------------------------------------------
# Phase 5: Suggestions & Intelligence (from mcp_server.py)
# ---------------------------------------------------------------------

def _get_distinct_values(file_meta: Dict[str, Any], column: str, limit: int = 100) -> List[str]:
    """
    Get distinct values for a column from a table.
    Returns list of distinct values (sorted, limited).
    """
    if not file_meta:
        return []

    # Validate column name (enhanced validation)
    valid, error = _validate_column_name_enhanced(column)
    if not valid:
        return []

    try:
        if file_meta.get("engine") == "duckdb":
            uri = file_meta.get("path")
            db_path, _, table = uri[len("duckdb://"):].partition("#")
            if not table:
                return []

            # Validate table name
            valid_table, _ = _validate_column_name_enhanced(table)
            if not valid_table:
                return []

            # Security: validate column again for SQL
            sql = f'SELECT DISTINCT "{column}" FROM {table} WHERE "{column}" IS NOT NULL ORDER BY "{column}" LIMIT {limit}'
            with _get_db_connection() as conn:
                result = conn.execute(sql).fetchall()
                if result:
                    values = [str(row[0]) for row in result]
                    return sorted(values)[:limit]
    except Exception as e:
        logger.warning(f"Error getting distinct values for {column}: {e}")
        return []

    return []


def _fuzzy_match(query: str, options: List[str], limit: int = 5) -> List[str]:
    """
    Find similar strings using simple string matching.
    Returns list of matching options sorted by similarity.
    """
    if not query or not options:
        return []

    query_lower = query.lower().strip()
    if not query_lower:
        return options[:limit]

    # Simple scoring: exact match > starts with > contains
    scores = []
    for opt in options:
        opt_lower = opt.lower()
        if opt_lower == query_lower:
            scores.append((0, opt))  # Exact match - highest priority
        elif opt_lower.startswith(query_lower):
            scores.append((1, opt))  # Starts with - high priority
        elif query_lower in opt_lower:
            scores.append((2, opt))  # Contains - medium priority
        elif query_lower[:3] in opt_lower or opt_lower[:3] in query_lower:
            scores.append((3, opt))  # Partial match - low priority

    # Sort by score, then alphabetically
    scores.sort(key=lambda x: (x[0], x[1].lower()))
    return [opt for _, opt in scores[:limit]]


def _get_suggestions_for_column(file_meta: Dict[str, Any], column: str,
                                query: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """
    Get suggestions for a column, optionally filtered by query string.
    Returns dict with suggestions and metadata.
    """
    if not file_meta:
        return {"suggestions": [], "column": column, "total_available": 0}

    # Get all distinct values
    all_values = _get_distinct_values(file_meta, column, limit=500)  # Get more for filtering
    total_available = len(all_values)

    if not all_values:
        return {"suggestions": [], "column": column, "total_available": 0}

    # If query provided, do fuzzy matching
    if query:
        suggestions = _fuzzy_match(query, all_values, limit=limit)
    else:
        # No query - return first N values
        suggestions = all_values[:limit]

    return {
        "suggestions": suggestions,
        "column": column,
        "total_available": total_available,
        "showing": len(suggestions)
    }


def _get_cities_data_coverage() -> Dict[str, Any]:
    """Get cities dataset coverage information dynamically from database"""
    try:
        # Find a city-level dataset to query
        city_datasets = [f for f in MANIFEST.get("files", []) if "-city-" in f.get("file_id", "")]

        if not city_datasets:
            return {
                "available_countries": [],
                "total_countries": 0,
                "total_cities": 0,
                "coverage_period": "N/A",
                "status": "no_city_data",
                "major_cities_included": []
            }

        # Use first city dataset to get coverage info
        city_file = city_datasets[0]
        uri = city_file.get("path")

        if not uri or not uri.startswith("duckdb://"):
            return {"error": "Invalid city dataset URI"}

        db_path, _, table = uri[len("duckdb://"):].partition("#")
        if not table:
            return {"error": "No table specified in URI"}

        with _get_db_connection() as conn:
            # Get unique countries with city data
            countries_sql = f"SELECT DISTINCT country_name FROM {table} WHERE city_name IS NOT NULL ORDER BY country_name"
            countries_result = conn.execute(countries_sql).fetchall()
            available_countries = [row[0] for row in countries_result if row[0]]

            # Get total cities count
            cities_sql = f"SELECT COUNT(DISTINCT city_name) FROM {table} WHERE city_name IS NOT NULL"
            cities_count = conn.execute(cities_sql).fetchone()[0]

            # Get major cities (cities with most data points or highest values)
            major_cities_sql = f"""
                SELECT DISTINCT city_name
                FROM {table}
                WHERE city_name IS NOT NULL
                LIMIT 15
            """
            major_cities_result = conn.execute(major_cities_sql).fetchall()
            major_cities = [row[0] for row in major_cities_result if row[0]]

            # Get temporal coverage
            temporal_coverage = city_file.get("temporal_coverage", "2000-2023")

        return {
            "available_countries": available_countries,
            "total_countries": len(available_countries),
            "total_cities": cities_count,
            "coverage_period": temporal_coverage,
            "status": "comprehensive",
            "major_cities_included": major_cities
        }

    except Exception as e:
        logger.error(f"Error getting cities coverage: {e}")
        # Fallback to empty response
        return {
            "available_countries": [],
            "total_countries": 0,
            "total_cities": 0,
            "coverage_period": "Unknown",
            "status": "error",
            "error": str(e)
        }


def _get_cities_suggestions(country_name: str) -> Dict[str, Any]:
    """Get smart suggestions for unavailable cities data"""
    # Get available countries dynamically
    coverage = _get_cities_data_coverage()
    available_countries = coverage.get("available_countries", [])

    if not available_countries:
        return {
            "message": f"City data is not available for {country_name}",
            "available_alternatives": [
                f"What are {country_name}'s total transport emissions by year?",
                "Which countries have the highest emissions?",
                "Show me admin1 (state/province) level data instead"
            ],
            "available_countries": [],
            "suggestions": [
                "No city-level data is currently available",
                "Ask about country-level emissions instead",
                "Try admin1 (state/province) level queries"
            ]
        }

    return {
        "message": f"City data is not available for {country_name}",
        "available_alternatives": [
            f"Which {available_countries[0]} city has the highest emissions?",
            f"Which {available_countries[1] if len(available_countries) > 1 else available_countries[0]} city has the highest emissions?",
            f"What are {country_name}'s total transport emissions by year?"
        ],
        "available_countries": available_countries,
        "suggestions": [
            f"Try asking about one of these countries: {', '.join(available_countries[:3])}",
            "Ask about country-level emissions instead of city-level",
            "Try admin1 (state/province) level if available"
        ]
    }


@lru_cache(maxsize=1)
def _coverage_index() -> Dict[str, List[str]]:
    """Build coverage index for all datasets (cached)"""
    idx = {"city": set(), "admin1": set(), "country": set()}

    for file_meta in MANIFEST.get("files", []):
        try:
            if file_meta.get("engine") == "duckdb":
                uri = file_meta.get("path")
                db_path, _, table = uri[len("duckdb://"):].partition("#")
                if not table:
                    continue

                with _get_db_connection() as conn:
                    # Check which columns exist
                    table_info_sql = f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}'"
                    columns_result = conn.execute(table_info_sql).fetchall()
                    cols = {row[0] for row in columns_result}

                    if "city_name" in cols:
                        result = conn.execute(f'SELECT DISTINCT city_name FROM {table} WHERE city_name IS NOT NULL').fetchall()
                        idx["city"].update(str(row[0]) for row in result)
                    if "admin1_name" in cols:
                        result = conn.execute(f'SELECT DISTINCT admin1_name FROM {table} WHERE admin1_name IS NOT NULL').fetchall()
                        idx["admin1"].update(str(row[0]) for row in result)
                    if "country_name" in cols:
                        result = conn.execute(f'SELECT DISTINCT country_name FROM {table} WHERE country_name IS NOT NULL').fetchall()
                        idx["country"].update(str(row[0]) for row in result)
        except Exception as e:
            logger.warning(f"Error building coverage index for {file_meta.get('file_id', 'unknown')}: {e}")
            continue

    return {k: sorted(v) for k, v in idx.items()}


def _normalize_entity_name(name: str, level: Optional[str] = None) -> str:
    """
    Normalize entity names to match database values.
    Handles common aliases, abbreviations, and variations.
    """
    if not name:
        return name

    normalized = name.strip()

    # Comprehensive country name mappings
    country_aliases = {
        # United States variations
        "USA": "United States of America",
        "US": "United States of America",
        "U.S.": "United States of America",
        "U.S.A.": "United States of America",
        "United States": "United States of America",
        "America": "United States of America",

        # United Kingdom variations
        "UK": "United Kingdom",
        "U.K.": "United Kingdom",
        "Britain": "United Kingdom",
        "Great Britain": "United Kingdom",
        "England": "United Kingdom",  # Note: England is part of UK

        # China variations
        "China": "People's Republic of China",
        "PRC": "People's Republic of China",
        "Mainland China": "People's Republic of China",

        # Russia variations
        "Russia": "Russian Federation",

        # Korea variations
        "South Korea": "Republic of Korea",
        "North Korea": "Democratic People's Republic of Korea",
        "DPRK": "Democratic People's Republic of Korea",
        "ROK": "Republic of Korea",

        # Other common variations
        "Holland": "Netherlands",
        "Myanmar": "Burma",
        "Czech Republic": "Czechia",
        "Ivory Coast": "Côte d'Ivoire",
        "UAE": "United Arab Emirates",
        "Vietnam": "Viet Nam",
        
        # Database-specific abbreviations (from EDGAR data)
        "bosnia and herz.": "Bosnia and Herzegovina",
        "bosnia and herz": "Bosnia and Herzegovina",
        "dem. rep. congo": "Democratic Republic of the Congo",
        "eq. guinea": "Equatorial Guinea",
        "n. mariana islands": "Northern Mariana Islands",
        "st. kitts and nevis": "Saint Kitts and Nevis",
        "st. lucia": "Saint Lucia",
        "st. vincent and the grenadines": "Saint Vincent and the Grenadines",
        "são tomé and príncipe": "Sao Tome and Principe",
        "trinidad and tobago": "Trinidad and Tobago",
        "u.s. virgin islands": "United States Virgin Islands",
        "united rep. of tanzania": "United Republic of Tanzania",
        
        # Additional common variations
        "czech rep.": "Czechia",
        "central african rep.": "Central African Republic",
        "dom. rep.": "Dominican Republic",
    }

    # Admin1 (state/province) mappings
    admin1_aliases = {
        "Calif": "California",
        "Cali": "California",
        "CA": "California",
        "NY": "New York",
        "TX": "Texas",
        "FL": "Florida",
        "Mass": "Massachusetts",
        "MA": "Massachusetts",
        "Penn": "Pennsylvania",
        "PA": "Pennsylvania",
    }

    # City mappings
    city_aliases = {
        "NYC": "New York City",
        "LA": "Los Angeles",
        "SF": "San Francisco",
        "DC": "Washington",
        "Philly": "Philadelphia",
    }

    # Try exact match first (case-insensitive)
    for alias, canonical in country_aliases.items():
        if normalized.lower() == alias.lower():
            return canonical

    # Try admin1 if level specified
    if level == "admin1":
        for alias, canonical in admin1_aliases.items():
            if normalized.lower() == alias.lower():
                return canonical

    # Try city if level specified
    if level == "city":
        for alias, canonical in city_aliases.items():
            if normalized.lower() == alias.lower():
                return canonical

    # If no level specified, try all
    if not level:
        # Check admin1
        for alias, canonical in admin1_aliases.items():
            if normalized.lower() == alias.lower():
                return canonical
        # Check city
        for alias, canonical in city_aliases.items():
            if normalized.lower() == alias.lower():
                return canonical

    return normalized


def _get_iso3_code(country_name: str) -> str | None:
    """
    Get ISO3 country code for faster database queries.

    ISO3 codes are 4x faster than full country names in WHERE clauses.
    Falls back to None if country not found.
    """
    ISO3_CODES = {
        "United States of America": "USA",
        "People's Republic of China": "CHN",
        "China": "CHN",
        "India": "IND",
        "Germany": "DEU",
        "United Kingdom": "GBR",
        "France": "FRA",
        "Japan": "JPN",
        "Canada": "CAN",
        "Australia": "AUS",
        "Brazil": "BRA",
        "Russian Federation": "RUS",
        "Russia": "RUS",
        "Republic of Korea": "KOR",
        "South Korea": "KOR",
        "Mexico": "MEX",
        "Indonesia": "IDN",
        "Saudi Arabia": "SAU",
        "Turkey": "TUR",
        "Italy": "ITA",
        "Spain": "ESP",
        "Netherlands": "NLD",
        "Poland": "POL",
        "South Africa": "ZAF",
        "Argentina": "ARG",
        "Thailand": "THA",
        "Egypt": "EGY",
        "Malaysia": "MYS",
        "Pakistan": "PAK",
        "Bangladesh": "BGD",
        "Viet Nam": "VNM",
        "Vietnam": "VNM",
        "Philippines": "PHL",
        "Nigeria": "NGA",
        "Iran": "IRN",
        "United Arab Emirates": "ARE",
        "UAE": "ARE",
        "Singapore": "SGP",
        "Switzerland": "CHE",
        "Belgium": "BEL",
        "Sweden": "SWE",
        "Norway": "NOR",
        "Denmark": "DNK",
        "Finland": "FIN",
        "Austria": "AUT",
        "Greece": "GRC",
        "Portugal": "PRT",
        "Czechia": "CZE",
        "Czech Republic": "CZE",
        "Romania": "ROU",
        "Hungary": "HUN",
        "Ireland": "IRL",
        "New Zealand": "NZL",
        "Chile": "CHL",
        "Colombia": "COL",
        "Peru": "PER",
        "Venezuela": "VEN",
        "Ukraine": "UKR",
        "Kazakhstan": "KAZ",
        "Algeria": "DZA",
        "Morocco": "MAR",
        "Kenya": "KEN",
        "Ethiopia": "ETH",
        "Ghana": "GHA",
        "Tanzania": "TZA",
        "United Republic of Tanzania": "TZA",
        "Uganda": "UGA",
        "Angola": "AGO",
        "Mozambique": "MOZ",
        "Madagascar": "MDG",
        "Cameroon": "CMR",
        "Côte d'Ivoire": "CIV",
        "Ivory Coast": "CIV",
        "Niger": "NER",
        "Burkina Faso": "BFA",
        "Mali": "MLI",
        "Malawi": "MWI",
        "Zambia": "ZMB",
        "Zimbabwe": "ZWE",
        "Senegal": "SEN",
        "Chad": "TCD",
        "Guinea": "GIN",
        "Rwanda": "RWA",
        "Benin": "BEN",
        "Burundi": "BDI",
        "Tunisia": "TUN",
        "South Sudan": "SSD",
        "Togo": "TGO",
        "Sierra Leone": "SLE",
        "Libya": "LBY",
        "Liberia": "LBR",
        "Central African Republic": "CAF",
        "Mauritania": "MRT",
        "Eritrea": "ERI",
        "Gambia": "GMB",
        "Botswana": "BWA",
        "Namibia": "NAM",
        "Gabon": "GAB",
        "Lesotho": "LSO",
        "Guinea-Bissau": "GNB",
        "Equatorial Guinea": "GNQ",
        "Mauritius": "MUS",
        "Eswatini": "SWZ",
        "Djibouti": "DJI",
        "Comoros": "COM",
        "Cape Verde": "CPV",
        "São Tomé and Príncipe": "STP",
        "Sao Tome and Principe": "STP",
        "Seychelles": "SYC",
    }
    
    # Normalize country name first
    normalized = _normalize_entity_name(country_name)
    return ISO3_CODES.get(normalized)


def _fuzzy_match_entity(name: str, candidates: List[str], threshold: float = 0.8) -> List[Tuple[str, float]]:
    """
    Find fuzzy matches for entity name using similarity scoring.
    Returns list of (candidate, similarity_score) tuples, sorted by score (descending).
    """
    from difflib import SequenceMatcher

    if not name or not candidates:
        return []

    name_lower = name.lower()
    matches = []

    for candidate in candidates:
        candidate_lower = candidate.lower()

        # Exact match
        if name_lower == candidate_lower:
            matches.append((candidate, 1.0))
            continue

        # Substring match
        if name_lower in candidate_lower or candidate_lower in name_lower:
            matches.append((candidate, 0.9))
            continue

        # Fuzzy similarity
        similarity = SequenceMatcher(None, name_lower, candidate_lower).ratio()
        if similarity >= threshold:
            matches.append((candidate, similarity))

    # Sort by similarity score (descending)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches


def _detect_entity_level(entity: str, coverage: Optional[Dict[str, List[str]]] = None) -> Optional[str]:
    """
    Auto-detect whether entity is a country, admin1 (state/province), or city.
    Returns: "country", "admin1", "city", or None if not found.
    """
    if not coverage:
        coverage = _coverage_index()

    # Normalize first
    normalized = _normalize_entity_name(entity)

    # Try exact match at each level
    if normalized in coverage.get("city", []):
        return "city"
    if normalized in coverage.get("admin1", []):
        return "admin1"
    if normalized in coverage.get("country", []):
        return "country"

    # Try case-insensitive match
    normalized_lower = normalized.lower()

    for city in coverage.get("city", []):
        if city.lower() == normalized_lower:
            return "city"

    for admin1 in coverage.get("admin1", []):
        if admin1.lower() == normalized_lower:
            return "admin1"

    for country in coverage.get("country", []):
        if country.lower() == normalized_lower:
            return "country"

    # Try fuzzy matching as last resort
    for level_name, level_key in [("city", "city"), ("admin1", "admin1"), ("country", "country")]:
        matches = _fuzzy_match_entity(normalized, coverage.get(level_key, []), threshold=0.85)
        if matches:
            return level_name

    return None


def _smart_entity_resolution(entity: str, level: Optional[str] = None) -> Tuple[str, str, List[str]]:
    """
    Resolve entity name with normalization, auto-detection, and fuzzy matching.

    Returns: (normalized_name, detected_level, suggestions)
    """
    coverage = _coverage_index()

    # Step 1: Normalize the entity name
    normalized = _normalize_entity_name(entity, level)

    # Step 2: Detect level if not provided
    if not level:
        detected_level = _detect_entity_level(normalized, coverage)
    else:
        detected_level = level

    # Step 3: Verify entity exists at detected level
    if detected_level:
        level_data = coverage.get(detected_level, [])

        # Exact match (case-insensitive)
        exact_match = next((item for item in level_data if item.lower() == normalized.lower()), None)
        if exact_match:
            return exact_match, detected_level, []

        # Fuzzy match
        fuzzy_matches = _fuzzy_match_entity(normalized, level_data, threshold=0.75)
        if fuzzy_matches:
            best_match, score = fuzzy_matches[0]
            suggestions = [m[0] for m in fuzzy_matches[:5]]
            return best_match, detected_level, suggestions

    # Step 4: If still not found, search across all levels
    all_suggestions = []
    for level_name in ["country", "admin1", "city"]:
        fuzzy_matches = _fuzzy_match_entity(normalized, coverage.get(level_name, []), threshold=0.75)
        for match, score in fuzzy_matches[:3]:
            all_suggestions.append(f"{match} ({level_name})")

    return normalized, detected_level or "country", all_suggestions


def _top_matches(name: str, pool: List[str], k: int = 5) -> List[str]:
    """Find top matching strings from a pool"""
    nm = (name or "").lower()
    scored = []
    for p in pool:
        pl = p.lower()
        score = 0 if pl == nm else (1 if nm in pl else 2)
        scored.append((p, score, len(p)))
    scored.sort(key=lambda x: (x[1], x[2]))
    return [p for p, _, _ in scored[:k]]


# ---------------------------------------------------------------------
# Phase 2 & 4: Remaining Validation and Data Handling
# ---------------------------------------------------------------------

def _get_file_meta(file_id: str) -> Optional[Dict[str, Any]]:
    """Get file metadata from manifest"""
    return next((f for f in MANIFEST.get("files", []) if f.get("file_id") == file_id), None)


def _validate_query_intent(
    file_id: str,
    where: Dict[str, Any],
    select: List[str],
    file_meta: Optional[Dict[str, Any]] = None,
    assist: bool = True
) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]], Optional[List[str]]]:
    """
    Validate query and detect potential issues before execution.
    Returns: (is_valid, warning_message, suggestions_dict, suggestions_list)
    """
    warnings = []
    suggestions_dict: Dict[str, Any] = {}
    suggestions_list: List[str] = []

    if not file_meta:
        return False, "File metadata not found", None, ["Check available datasets"]

    # Check temporal coverage
    if "year" in where:
        year_val = where["year"]
        if isinstance(year_val, int):
            temporal = file_meta.get("temporal_coverage", "")
            coverage = _parse_temporal_coverage(temporal)
            if coverage:
                start, end = coverage
                if year_val < start or year_val > end:
                    warnings.append(f"Year {year_val} outside dataset coverage ({start}-{end})")
                    # Suggest nearest available year
                    nearest = max(start, min(end, year_val))
                    suggestions_dict["nearest_year"] = nearest
                    suggestions_list.append(f"Try year {nearest} (dataset covers {start}-{end})")

    # Check spatial coverage for city queries
    if "city" in file_id and "country_name" in where:
        country = where.get("country_name")
        if isinstance(country, str):
            coverage_info = _get_cities_data_coverage()
            available = coverage_info.get("available_countries", [])
            if country not in available:
                warnings.append(f"City data not available for '{country}'")
                suggestions_dict.update(_get_cities_suggestions(country))
                suggestions_list.extend([
                    f"City data available for: {', '.join(available[:5])}",
                    "Try querying at country or admin1 level instead"
                ])

    # Check for ambiguous filters
    if not where and assist:
        warnings.append("No filters specified - returning sample data")
        suggestions_list.append("Add filters like 'year' or 'country_name' to narrow results")

    # Check if select columns exist in manifest
    if file_meta.get("columns") and select:
        manifest_cols = {col.get("name") for col in file_meta.get("columns", []) if isinstance(col, dict)}
        missing_cols = [c for c in select if c not in manifest_cols]
        if missing_cols:
            warnings.append(f"Some requested columns may not exist: {missing_cols}")
            suggestions_list.append(f"Available columns: {', '.join(sorted(manifest_cols)[:10])}...")

    warning_msg = "; ".join(warnings) if warnings else None
    return True, warning_msg, suggestions_dict if suggestions_dict else None, suggestions_list if suggestions_list else None


def _detect_query_patterns(
    where: Dict[str, Any],
    group_by: List[str],
    order_by: Optional[str],
    limit: Optional[int]
) -> Dict[str, Any]:
    """Detect query patterns to provide better suggestions."""
    patterns = {
        "is_top_n": False,
        "is_comparison": False,
        "is_trend": False,
        "has_temporal_filter": "year" in where or "month" in where,
        "has_spatial_filter": any(k in where for k in ["country_name", "admin1_name", "city_name"]),
        "needs_aggregation": bool(group_by),
    }

    # Detect top N pattern
    if order_by and "DESC" in order_by.upper():
        if limit and limit <= 20:
            patterns["is_top_n"] = True

    # Detect comparison pattern
    if "year" in where and isinstance(where["year"], dict) and "in" in where["year"]:
        if len(where["year"]["in"]) == 2:
            patterns["is_comparison"] = True

    # Detect trend pattern
    if "year" in where or (group_by and "year" in group_by):
        patterns["is_trend"] = True

    return patterns


# ========================================
# QUERY CACHE
# ========================================

class QueryCache:
    """LRU cache for query results with TTL"""
    
    def __init__(self, maxsize=1000, ttl_seconds=300):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache = {}
        self._timestamps = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
    
    def _get_cache_key(self, sql: str, params: list) -> str:
        """Generate cache key from SQL and parameters"""
        cache_str = sql + json.dumps(params, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def get(self, sql: str, params: list):
        """Get cached result if exists and not expired"""
        with self._lock:
            key = self._get_cache_key(sql, params)
            
            if key not in self._cache:
                self.misses += 1
                return None
            
            # Check TTL
            if time.time() - self._timestamps[key] > self.ttl_seconds:
                del self._cache[key]
                del self._timestamps[key]
                self.misses += 1
                return None
            
            self.hits += 1
            return self._cache[key]
    
    def set(self, sql: str, params: list, result):
        """Cache query result"""
        with self._lock:
            key = self._get_cache_key(sql, params)
            
            # Evict oldest if at capacity
            if len(self._cache) >= self.maxsize:
                oldest_key = min(self._timestamps.keys(), key=lambda k: self._timestamps[k])
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
            
            self._cache[key] = result
            self._timestamps[key] = time.time()
    
    def clear(self):
        """Clear all cached results"""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self.hits = 0
            self.misses = 0
    
    def get_stats(self):
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": round(hit_rate, 2),
            "size": len(self._cache),
            "maxsize": self.maxsize
        }

# Initialize cache
query_cache = QueryCache(maxsize=1000, ttl_seconds=300)

# ========================================
# CONNECTION POOL
# ========================================

class DuckDBConnectionPool:
    """
    Thread-safe connection pool for DuckDB connections.

    Features:
    - Configurable pool size
    - Connection reuse
    - Health checking
    - Automatic connection cleanup
    - Thread-safe operations
    """

    def __init__(self, db_path: str, pool_size: int = 10, max_overflow: int = 5):
        """
        Initialize connection pool.

        Args:
            db_path: Path to DuckDB database
            pool_size: Number of connections to maintain in pool
            max_overflow: Maximum connections above pool_size (total = pool_size + max_overflow)
        """
        self.db_path = _resolve_db_path(db_path)
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.max_connections = pool_size + max_overflow

        # Connection pool (FIFO queue)
        self._pool = Queue(maxsize=self.max_connections)
        self._lock = threading.Lock()
        self._connection_count = 0
        self._connections_created = 0
        self._connections_reused = 0

        # Pre-populate pool with initial connections
        logger.info(f"Initializing DuckDB connection pool: size={pool_size}, max_overflow={max_overflow}")
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.put(conn)

    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """Create a new DuckDB connection."""
        with self._lock:
            if self._connection_count >= self.max_connections:
                raise RuntimeError(f"Maximum connections ({self.max_connections}) reached")

            conn = duckdb.connect(self.db_path, read_only=True)
            self._connection_count += 1
            self._connections_created += 1
            logger.debug(f"Created new connection (total: {self._connection_count})")
            return conn

    def _is_connection_healthy(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """Check if connection is still healthy."""
        try:
            # Simple health check query
            conn.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            logger.warning(f"Connection health check failed: {e}")
            return False

    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool (context manager).

        Usage:
            with pool.get_connection() as conn:
                result = conn.execute("SELECT * FROM table").fetchall()
        """
        conn = None
        created_new = False

        try:
            # Try to get connection from pool (non-blocking)
            try:
                conn = self._pool.get_nowait()
                self._connections_reused += 1

                # Health check
                if not self._is_connection_healthy(conn):
                    logger.warning("Unhealthy connection detected, creating new one")
                    conn.close()
                    with self._lock:
                        self._connection_count -= 1
                    conn = self._create_connection()
                    created_new = True

            except Empty:
                # Pool is empty, create new connection if allowed
                logger.debug("Pool empty, creating new connection")
                conn = self._create_connection()
                created_new = True

            yield conn

        finally:
            # Return connection to pool
            if conn is not None:
                try:
                    # Try to return to pool
                    self._pool.put_nowait(conn)
                except Full:
                    # Pool is full (overflow connection), close it
                    logger.debug("Pool full, closing overflow connection")
                    conn.close()
                    with self._lock:
                        self._connection_count -= 1

    def get_stats(self) -> dict:
        """Get pool statistics."""
        return {
            "pool_size": self.pool_size,
            "max_connections": self.max_connections,
            "current_connections": self._connection_count,
            "available_connections": self._pool.qsize(),
            "connections_created": self._connections_created,
            "connections_reused": self._connections_reused,
            "reuse_ratio": self._connections_reused / max(1, self._connections_created + self._connections_reused)
        }

    def close_all(self):
        """Close all connections in pool."""
        logger.info("Closing all connections in pool")
        while not self._pool.empty():
            try:
                conn = self._pool.get_nowait()
                conn.close()
                with self._lock:
                    self._connection_count -= 1
            except Empty:
                break
        logger.info(f"Connection pool closed (remaining connections: {self._connection_count})")


# Initialize global connection pool
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
POOL_MAX_OVERFLOW = int(os.getenv("DB_POOL_MAX_OVERFLOW", "5"))

_connection_pool = DuckDBConnectionPool(DB_PATH, pool_size=POOL_SIZE, max_overflow=POOL_MAX_OVERFLOW)

def _get_db_connection():
    """
    Get a database connection from the pool.

    Returns a context manager that yields a connection.
    Usage:
        with _get_db_connection() as conn:
            result = conn.execute("SELECT * FROM table").fetchall()
    """
    return _connection_pool.get_connection()

def execute_cached(conn, sql: str, params: list = None):
    """
    Execute query with caching.
    
    Checks cache first, executes if not found, then caches result.
    Returns cached or fresh result.
    """
    params = params or []
    
    # Check cache
    cached = query_cache.get(sql, params)
    if cached is not None:
        return cached
    
    # Execute query
    result = conn.execute(sql, params).fetchall()
    
    # Cache result
    query_cache.set(sql, params, result)
    
    return result

# ========================================
# HELPER FUNCTIONS (from mcp_server.py)
# ========================================

def _validate_file_id(file_id: str) -> tuple[bool, Optional[str]]:
    """Validate file_id format - calls enhanced version"""
    return _validate_file_id_enhanced(file_id)

def _find_file_meta(file_id: str):
    """Find file metadata in manifest - calls _get_file_meta"""
    return _get_file_meta(file_id)

def _get_table_name(file_meta: dict) -> Optional[str]:
    """Extract table name from file metadata"""
    path = file_meta.get("path", "")
    if path.startswith("duckdb://"):
        return path.split("#")[1] if "#" in path else None
    return None

def _build_where_sql(where: dict[str, Any]) -> tuple[str, list]:
    """
    Build WHERE clause SQL with parameterized queries (enhanced version).
    Supports: equality, in, between, comparisons, contains/ILIKE
    Optimizes country_name queries by using ISO3 codes when available (4x faster).
    """
    if not where:
        return "", []

    conditions = []
    params = []

    for key, value in where.items():
        # Optimize country_name queries with ISO3 codes (4x faster)
        if key == "country_name" and isinstance(value, str):
            iso3 = _get_iso3_code(value)
            if iso3:
                # Use ISO3 for faster lookup
                conditions.append("iso3 = ?")
                params.append(iso3)
                continue
            # Fall back to normalized country name
            value = _normalize_entity_name(value)
        if isinstance(value, list):
            # List values are treated as IN operator
            placeholders = ",".join(["?"] * len(value))
            conditions.append(f"{key} IN ({placeholders})")
            params.extend(value)
        elif isinstance(value, dict):
            # Support various operators
            if "in" in value and isinstance(value["in"], list):
                placeholders = ",".join(["?"] * len(value["in"]))
                conditions.append(f"{key} IN ({placeholders})")
                params.extend(value["in"])
            elif "between" in value and isinstance(value["between"], (list, tuple)) and len(value["between"]) == 2:
                conditions.append(f"{key} BETWEEN ? AND ?")
                params.extend(list(value["between"]))
            elif "gte" in value:
                conditions.append(f"{key} >= ?")
                params.append(value["gte"])
            elif "lte" in value:
                conditions.append(f"{key} <= ?")
                params.append(value["lte"])
            elif "gt" in value or "$gt" in value:
                val = value.get("gt", value.get("$gt"))
                conditions.append(f"{key} > ?")
                params.append(val)
            elif "lt" in value or "$lt" in value:
                val = value.get("lt", value.get("$lt"))
                conditions.append(f"{key} < ?")
                params.append(val)
            elif "ne" in value or "$ne" in value:
                val = value.get("ne", value.get("$ne"))
                conditions.append(f"{key} != ?")
                params.append(val)
            elif "contains" in value:
                # Case-insensitive substring search
                conditions.append(f"CAST({key} AS VARCHAR) ILIKE ?")
                params.append(f"%{value['contains']}%")
        else:
            # Simple equality
            conditions.append(f"{key} = ?")
            params.append(value)

    sql = " WHERE " + " AND ".join(conditions) if conditions else ""
    return sql, params

def _validate_column_name(column: str, file_meta: dict) -> tuple[bool, Optional[str]]:
    """Validate column name exists in dataset schema (prevents SQL injection)"""
    # First, do security validation
    valid, error = _validate_column_name_enhanced(column)
    if not valid:
        return False, error

    # Then check against schema
    valid_columns = [col["name"] for col in file_meta.get("columns", [])]
    if column not in valid_columns:
        return False, f"Invalid column '{column}'. Valid columns: {', '.join(valid_columns[:10])}"

    return True, None

# ========================================
# TOOLS - Functions LLM can call
# ========================================

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="list_emissions_datasets",
            description="List all available emissions datasets with sectors, resolutions, and temporal coverage",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            },
        ),
        Tool(
            name="get_dataset_schema",
            description="Get the schema (columns and types) for a specific dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "Dataset identifier (e.g., 'transport-country-year')"
                    }
                },
                "required": ["file_id"]
            }
        ),
        Tool(
            name="query_emissions",
            description="Query emissions data from ClimateGPT database with filters, aggregations, and sorting",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "Dataset identifier (e.g., 'transport-country-year')"
                    },
                    "select": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Columns to return (default: all)"
                    },
                    "where": {
                        "type": "object",
                        "description": "Filter conditions (e.g., {'year': 2020, 'country_name': 'United States of America'})"
                    },
                    "group_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Columns to group by"
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Column to sort by (e.g., 'MtCO2 DESC')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return (default: 20, max: 1000)",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 1000
                    },
                    "aggregations": {
                        "type": "object",
                        "description": "Aggregations to apply (e.g., {'MtCO2': 'sum'})"
                    }
                },
                "required": ["file_id"]
            }
        ),
        Tool(
            name="calculate_yoy_change",
            description="Calculate year-over-year changes in emissions between two years",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "key_column": {"type": "string", "description": "Column to group by (e.g., 'country_name')"},
                    "value_column": {"type": "string", "default": "emissions_tonnes"},
                    "base_year": {"type": "integer", "default": 2019},
                    "compare_year": {"type": "integer", "default": 2020},
                    "top_n": {"type": "integer", "default": 10},
                    "direction": {"type": "string", "enum": ["rise", "drop"], "default": "drop"}
                },
                "required": ["file_id", "key_column"]
            }
        ),
        Tool(
            name="analyze_monthly_trends",
            description="Analyze monthly emissions trends for a specific entity (country/region) showing month-over-month changes, averages, and patterns",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "Monthly dataset identifier (must end with '-month', e.g., 'transport-country-month')"
                    },
                    "entity_column": {
                        "type": "string",
                        "description": "Column to filter by (e.g., 'country_name', 'admin1_name')"
                    },
                    "entity_value": {
                        "type": "string",
                        "description": "Entity value to analyze (e.g., 'United States of America')"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year to analyze (default: 2020)",
                        "default": 2020
                    },
                    "value_column": {
                        "type": "string",
                        "description": "Column to measure (default: 'MtCO2')",
                        "default": "MtCO2"
                    }
                },
                "required": ["file_id", "entity_column", "entity_value"]
            }
        ),
        Tool(
            name="detect_seasonal_patterns",
            description="Detect seasonal patterns in emissions data by analyzing multi-year monthly averages and identifying peak/low months",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "Monthly dataset identifier (e.g., 'transport-country-month')"
                    },
                    "entity_column": {
                        "type": "string",
                        "description": "Column to filter by (e.g., 'country_name')"
                    },
                    "entity_value": {
                        "type": "string",
                        "description": "Entity to analyze (e.g., 'Germany')"
                    },
                    "start_year": {
                        "type": "integer",
                        "description": "Start year for analysis (default: 2015)",
                        "default": 2015
                    },
                    "end_year": {
                        "type": "integer",
                        "description": "End year for analysis (default: 2023)",
                        "default": 2023
                    },
                    "value_column": {
                        "type": "string",
                        "description": "Column to measure (default: 'MtCO2')",
                        "default": "MtCO2"
                    }
                },
                "required": ["file_id", "entity_column", "entity_value"]
            }
        ),
        Tool(
            name="get_data_coverage",
            description="Get comprehensive data coverage information for all datasets including available countries, cities, and admin regions",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_column_suggestions",
            description="Get smart suggestions for column values with fuzzy matching support",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "column": {
                        "type": "string",
                        "description": "Column name to get suggestions for"
                    },
                    "query": {
                        "type": "string",
                        "description": "Optional search query for fuzzy matching"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum suggestions to return (default: 10)",
                        "default": 10
                    }
                },
                "required": ["file_id", "column"]
            }
        ),
        Tool(
            name="validate_query",
            description="Validate a query before execution and get helpful suggestions for improvements",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "Dataset identifier"
                    },
                    "select": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Columns to select"
                    },
                    "where": {
                        "type": "object",
                        "description": "Filter conditions"
                    },
                    "group_by": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Columns to group by"
                    },
                    "order_by": {
                        "type": "string",
                        "description": "Column to sort by"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Row limit"
                    }
                },
                "required": ["file_id"]
            }
        ),
        Tool(
            name="aggregate_across_sectors",
            description="Aggregate emissions across multiple sectors for an entity (country/region/city)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity name (e.g., 'Germany', 'California', 'Paris')"
                    },
                    "level": {
                        "type": "string",
                        "enum": ["country", "admin1", "city"],
                        "description": "Geographic level (default: auto-detect)",
                        "default": "country"
                    },
                    "sectors": {
                        "description": "List of sectors or 'all' for all sectors",
                        "oneOf": [
                            {"type": "array", "items": {"type": "string"}},
                            {"type": "string", "enum": ["all"]}
                        ],
                        "default": "all"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year to query (default: 2023)",
                        "default": 2023
                    }
                },
                "required": ["entity"]
            }
        ),
        Tool(
            name="compare_emissions",
            description="Compare emissions between multiple entities (countries/regions/cities)",
            inputSchema={
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of entities to compare (min 2)"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Sector to compare (default: transport)",
                        "default": "transport"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year for comparison (default: 2023)",
                        "default": 2023
                    },
                    "level": {
                        "type": "string",
                        "enum": ["country", "admin1", "city"],
                        "description": "Geographic level (default: country)",
                        "default": "country"
                    }
                },
                "required": ["entities"]
            }
        ),
        Tool(
            name="analyze_emissions_trend",
            description="Analyze emissions trend over a time period with growth rate calculation",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity name (e.g., 'Germany')"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Sector to analyze (default: transport)",
                        "default": "transport"
                    },
                    "start_year": {
                        "type": "integer",
                        "description": "Start year (default: 2000)",
                        "default": 2000
                    },
                    "end_year": {
                        "type": "integer",
                        "description": "End year (default: 2023)",
                        "default": 2023
                    },
                    "level": {
                        "type": "string",
                        "enum": ["country", "admin1", "city"],
                        "description": "Geographic level (default: country)",
                        "default": "country"
                    }
                },
                "required": ["entity"]
            }
        ),
        Tool(
            name="get_top_emitters",
            description="Get top N emitters for a sector and year, ranked by emissions",
            inputSchema={
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "description": "Sector to query (default: transport)",
                        "default": "transport"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year to query (default: 2023)",
                        "default": 2023
                    },
                    "level": {
                        "type": "string",
                        "enum": ["country", "admin1", "city"],
                        "description": "Geographic level (default: country)",
                        "default": "country"
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "Number of top emitters to return (default: 10, max: 50)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="smart_query_emissions",
            description="Intelligent emissions query with auto-normalization, level detection, and fallback. Use this when entity name or level is ambiguous (e.g., 'USA', 'California', 'NYC')",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity name in any format (e.g., 'USA', 'United States', 'California', 'NYC', 'LA')"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Sector to query (default: transport)",
                        "default": "transport"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year to query (default: 2023)",
                        "default": 2023
                    },
                    "grain": {
                        "type": "string",
                        "enum": ["year", "month"],
                        "description": "Temporal granularity (default: year)",
                        "default": "year"
                    },
                    "level": {
                        "type": "string",
                        "enum": ["country", "admin1", "city", "auto"],
                        "description": "Geographic level - use 'auto' for automatic detection (default: auto)",
                        "default": "auto"
                    },
                    "enable_fallback": {
                        "type": "boolean",
                        "description": "Enable fallback to higher levels if no data found (city→admin1→country) (default: true)",
                        "default": true
                    }
                },
                "required": ["entity"]
            }
        ),
        Tool(
            name="top_emitters",
            description="Find top emitters by sector and year. Returns ranked list of countries/states/cities with highest emissions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sector": {
                        "type": "string",
                        "description": "Sector name (transport, power, waste, agriculture, buildings, fuel-exploitation, ind-combustion, ind-processes)",
                        "enum": ["transport", "power", "waste", "agriculture", "buildings", "fuel-exploitation", "ind-combustion", "ind-processes"]
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year to analyze (2000-2024)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of top emitters to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    },
                    "geographic_level": {
                        "type": "string",
                        "enum": ["country", "admin1", "city"],
                        "description": "Geographic level to analyze (default: country)",
                        "default": "country"
                    }
                },
                "required": ["sector", "year"]
            }
        ),
        Tool(
            name="analyze_trend",
            description="Analyze emissions trend over time with growth rates and patterns. Calculates year-over-year growth, CAGR, and identifies patterns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Country, state, or city name"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Sector to analyze",
                        "enum": ["transport", "power", "waste", "agriculture", "buildings", "fuel-exploitation", "ind-combustion", "ind-processes"]
                    },
                    "start_year": {
                        "type": "integer",
                        "description": "Start year (2000-2024)"
                    },
                    "end_year": {
                        "type": "integer",
                        "description": "End year (2000-2024)"
                    }
                },
                "required": ["entity_name", "sector", "start_year", "end_year"]
            }
        ),
        Tool(
            name="compare_sectors",
            description="Compare emissions across multiple sectors for a location. Returns totals, percentages, and rankings.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entity_name": {
                        "type": "string",
                        "description": "Country, state, or city name"
                    },
                    "sectors": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["transport", "power", "waste", "agriculture", "buildings", "fuel-exploitation", "ind-combustion", "ind-processes"]
                        },
                        "description": "List of sectors to compare (at least 2 required)"
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year to analyze (2000-2024)"
                    }
                },
                "required": ["entity_name", "sectors", "year"]
            }
        ),
        Tool(
            name="compare_geographies",
            description="Compare emissions across multiple countries/regions/cities. Returns rankings and percentages.",
            inputSchema={
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of country/state/city names to compare (at least 2 required)"
                    },
                    "sector": {
                        "type": "string",
                        "description": "Sector to analyze",
                        "enum": ["transport", "power", "waste", "agriculture", "buildings", "fuel-exploitation", "ind-combustion", "ind-processes"]
                    },
                    "year": {
                        "type": "integer",
                        "description": "Year to compare (2000-2024)"
                    }
                },
                "required": ["entities", "sector", "year"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    logger.info(f"Tool called: {name}")
    logger.debug(f"Arguments: {json.dumps(arguments, default=str)[:200]}")

    if name == "list_emissions_datasets":
        files = []
        for file in MANIFEST.get("files", []):
            file_id = file.get("file_id", "")
            files.append({
                "file_id": file_id,
                "name": file.get("name", ""),
                "description": file.get("description", ""),
                "sector": file_id.split("-")[0] if "-" in file_id else "",
                "resolution": file.get("resolution", ""),
                "temporal_coverage": file.get("temporal_coverage", "2000-2023"),
                "units": file.get("units", "tonnes CO₂")
            })
        
        return [TextContent(
            type="text",
            text=json.dumps({"datasets": files}, indent=2)
        )]
    
    elif name == "get_dataset_schema":
        file_id = arguments.get("file_id")
        if not file_id:
            return [TextContent(type="text", text=json.dumps({"error": "file_id required"}))]
        
        valid, error = _validate_file_id(file_id)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": error}))]
        
        file_meta = _find_file_meta(file_id)
        if not file_meta:
            available = [f.get("file_id") for f in MANIFEST.get("files", [])[:10]]
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "file_not_found",
                    "file_id": file_id,
                    "available": available
                })
            )]
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "file_id": file_id,
                "name": file_meta.get("name", ""),
                "description": file_meta.get("description", ""),
                "columns": file_meta.get("columns", []),
                "temporal_coverage": file_meta.get("temporal_coverage", ""),
                "resolution": file_meta.get("resolution", ""),
                "source": file_meta.get("source", "")
            }, indent=2)
        )]
    
    elif name == "query_emissions":
        file_id = arguments.get("file_id")
        if not file_id:
            return [TextContent(type="text", text=json.dumps({"error": "file_id required"}))]
        
        valid, error = _validate_file_id(file_id)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": error}))]
        
        file_meta = _find_file_meta(file_id)
        if not file_meta:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "file_not_found",
                    "file_id": file_id
                })
            )]
        
        # Get table name
        table = _get_table_name(file_meta)
        if not table:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "invalid_table_path", "path": file_meta.get("path")})
            )]
        
        # Build query
        select = arguments.get("select")
        where = arguments.get("where") or {}
        group_by = arguments.get("group_by")
        order_by = arguments.get("order_by")
        limit = min(arguments.get("limit", 20), 1000)
        aggregations = arguments.get("aggregations")
        
        try:
            # Build SELECT with validation
            if select:
                select_list = select if isinstance(select, list) else [select]
                # Validate each column name
                for col in select_list:
                    valid, error = _validate_column_name_enhanced(col)
                    if not valid:
                        return [TextContent(type="text", text=json.dumps({"error": f"Invalid select column: {error}"}))]
                select_sql = ", ".join(select_list)
            else:
                select_sql = "*"

            # Handle aggregations with validation
            if aggregations:
                agg_parts = []
                for col, func in aggregations.items():
                    # Validate column name
                    valid, error = _validate_column_name_enhanced(col)
                    if not valid:
                        return [TextContent(type="text", text=json.dumps({"error": f"Invalid aggregation column: {error}"}))]
                    # Validate aggregation function
                    valid, error = _validate_aggregation_function(func)
                    if not valid:
                        return [TextContent(type="text", text=json.dumps({"error": error}))]
                    agg_parts.append(f"{func.upper()}({col}) AS {func}_{col}")
                if group_by:
                    select_sql = ", ".join(group_by) + ", " + ", ".join(agg_parts)
                else:
                    select_sql = ", ".join(agg_parts)

            sql = f"SELECT {select_sql} FROM {table}"

            # WHERE clause
            where_sql, params = _build_where_sql(where)
            sql += where_sql

            # GROUP BY with validation
            if group_by:
                group_list = group_by if isinstance(group_by, list) else [group_by]
                # Validate each group by column
                for col in group_list:
                    valid, error = _validate_column_name_enhanced(col)
                    if not valid:
                        return [TextContent(type="text", text=json.dumps({"error": f"Invalid group_by column: {error}"}))]
                sql += f" GROUP BY {', '.join(group_list)}"

            # ORDER BY with validation
            if order_by:
                # Parse order by to extract column name (handles "column ASC" or "column DESC")
                order_parts = order_by.split()
                order_col = order_parts[0]
                valid, error = _validate_column_name_enhanced(order_col)
                if not valid:
                    return [TextContent(type="text", text=json.dumps({"error": f"Invalid order_by column: {error}"}))]
                # Validate direction if specified
                if len(order_parts) > 1:
                    direction = order_parts[1].upper()
                    if direction not in ("ASC", "DESC"):
                        return [TextContent(type="text", text=json.dumps({"error": "order_by direction must be ASC or DESC"}))]
                sql += f" ORDER BY {order_by}"

            # LIMIT
            sql += f" LIMIT {limit}"

            # Execute query
            with _get_db_connection() as conn:
                # Get column description first
                desc_cursor = conn.execute(sql, params)
                columns = [desc[0] for desc in desc_cursor.description]
                
                # Use cached execution for better performance
                result = execute_cached(conn, sql, params)

                # Convert to dict
                rows = [dict(zip(columns, row)) for row in result]

            return [TextContent(
                type="text",
                text=json.dumps({
                    "rows": rows,
                    "meta": {
                        "file_id": file_id,
                        "row_count": len(rows),
                        "limit": limit
                    }
                }, indent=2, default=str)
            )]
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}")
            error_response = {
                "error": "query_failed",
                "detail": str(e)
            }
            # Only expose SQL in debug mode for security
            if os.getenv("DEBUG") == "true":
                error_response["sql"] = sql if 'sql' in locals() else None
            return [TextContent(
                type="text",
                text=json.dumps(error_response)
            )]
    
    elif name == "calculate_yoy_change":
        file_id = arguments.get("file_id")
        key_column = arguments.get("key_column")
        value_column = arguments.get("value_column", "emissions_tonnes")
        base_year = arguments.get("base_year", 2019)
        compare_year = arguments.get("compare_year", 2020)
        top_n = arguments.get("top_n", 10)
        direction = arguments.get("direction", "drop")

        file_meta = _find_file_meta(file_id)
        if not file_meta:
            return [TextContent(type="text", text=json.dumps({"error": "file_not_found"}))]

        table = _get_table_name(file_meta)
        if not table:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_table"}))]

        # Validate column names (security: prevent SQL injection)
        valid, error = _validate_column_name(key_column, file_meta)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_column", "detail": error}))]

        valid, error = _validate_column_name(value_column, file_meta)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_column", "detail": error}))]

        try:
            # Calculate YoY changes
            sql = f"""
            WITH base AS (
                SELECT {key_column}, {value_column} as base_value
                FROM {table}
                WHERE year = ?
            ),
            compare AS (
                SELECT {key_column}, {value_column} as compare_value
                FROM {table}
                WHERE year = ?
            )
            SELECT
                b.{key_column} as entity,
                b.base_value,
                c.compare_value,
                (c.compare_value - b.base_value) as change,
                ((c.compare_value - b.base_value) / b.base_value * 100) as change_pct
            FROM base b
            JOIN compare c ON b.{key_column} = c.{key_column}
            WHERE b.base_value > 0
            ORDER BY change {'ASC' if direction == 'drop' else 'DESC'}
            LIMIT ?
            """

            with _get_db_connection() as conn:
                cursor = conn.execute(sql, [base_year, compare_year, top_n])
                columns = [desc[0] for desc in cursor.description]
                result = cursor.fetchall()

                rows = [dict(zip(columns, row)) for row in result]

            return [TextContent(
                type="text",
                text=json.dumps({
                    "yoy_changes": rows,
                    "meta": {
                        "base_year": base_year,
                        "compare_year": compare_year,
                        "direction": direction
                    }
                }, indent=2, default=str)
            )]

        except Exception as e:
            logger.error(f"YoY calculation failed: {e}")
            return [TextContent(
                type="text",
                text=json.dumps({"error": "yoy_calculation_failed", "detail": str(e)})
            )]

    elif name == "analyze_monthly_trends":
        file_id = arguments.get("file_id")
        entity_column = arguments.get("entity_column")
        entity_value = arguments.get("entity_value")
        year = arguments.get("year", 2020)
        value_column = arguments.get("value_column", "MtCO2")

        # Validate it's a monthly dataset
        if not file_id.endswith("-month"):
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "invalid_dataset",
                    "detail": "file_id must be a monthly dataset (ending with '-month')",
                    "file_id": file_id
                })
            )]

        file_meta = _find_file_meta(file_id)
        if not file_meta:
            return [TextContent(type="text", text=json.dumps({"error": "file_not_found"}))]

        table = _get_table_name(file_meta)
        if not table:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_table"}))]

        # Validate column names (security: prevent SQL injection)
        valid, error = _validate_column_name(entity_column, file_meta)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_column", "detail": error}))]

        valid, error = _validate_column_name(value_column, file_meta)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_column", "detail": error}))]

        try:
            # Get monthly data
            sql = f"""
            SELECT month, {value_column}
            FROM {table}
            WHERE {entity_column} = ? AND year = ?
            ORDER BY month
            """

            with _get_db_connection() as conn:
                result = conn.execute(sql, [entity_value, year]).fetchall()

            if not result:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "no_data",
                        "detail": f"No data found for {entity_value} in {year}"
                    })
                )]

            # Calculate statistics
            monthly_data = [{"month": row[0], value_column: row[1]} for row in result]
            values = [row[1] for row in result]

            # Calculate month-over-month changes
            mom_changes = []
            for i in range(1, len(values)):
                change = values[i] - values[i-1]
                change_pct = (change / values[i-1] * 100) if values[i-1] > 0 else 0
                mom_changes.append({
                    "from_month": result[i-1][0],
                    "to_month": result[i][0],
                    "change": float(change),
                    "change_pct": float(change_pct)
                })

            # Find extremes
            min_idx = values.index(min(values))
            max_idx = values.index(max(values))

            analysis = {
                "entity": entity_value,
                "year": year,
                "monthly_data": monthly_data,
                "statistics": {
                    "average": float(sum(values) / len(values)),
                    "total": float(sum(values)),
                    "min": {
                        "month": result[min_idx][0],
                        "value": float(values[min_idx])
                    },
                    "max": {
                        "month": result[max_idx][0],
                        "value": float(values[max_idx])
                    },
                    "range": float(max(values) - min(values)),
                    "std_dev": float(sum((x - sum(values)/len(values))**2 for x in values) / len(values)) ** 0.5
                },
                "month_over_month_changes": mom_changes,
                "insights": []
            }

            # Generate insights
            avg = analysis["statistics"]["average"]
            if values[0] > values[-1] * 1.2:
                analysis["insights"].append(f"Significant decline from January to December ({((values[-1]/values[0]-1)*100):.1f}%)")
            elif values[-1] > values[0] * 1.2:
                analysis["insights"].append(f"Significant increase from January to December ({((values[-1]/values[0]-1)*100):.1f}%)")

            # Check for dramatic drops (like COVID)
            for change in mom_changes:
                if change["change_pct"] < -30:
                    analysis["insights"].append(
                        f"Dramatic drop from month {change['from_month']} to {change['to_month']} ({change['change_pct']:.1f}%)"
                    )

            return [TextContent(
                type="text",
                text=json.dumps(analysis, indent=2, default=str)
            )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "analysis_failed", "detail": str(e)})
            )]

    elif name == "detect_seasonal_patterns":
        file_id = arguments.get("file_id")
        entity_column = arguments.get("entity_column")
        entity_value = arguments.get("entity_value")
        start_year = arguments.get("start_year", 2015)
        end_year = arguments.get("end_year", 2023)
        value_column = arguments.get("value_column", "MtCO2")

        if not file_id.endswith("-month"):
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "invalid_dataset",
                    "detail": "file_id must be a monthly dataset"
                })
            )]

        file_meta = _find_file_meta(file_id)
        if not file_meta:
            return [TextContent(type="text", text=json.dumps({"error": "file_not_found"}))]

        table = _get_table_name(file_meta)
        if not table:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_table"}))]

        # Validate column names (security: prevent SQL injection)
        valid, error = _validate_column_name(entity_column, file_meta)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_column", "detail": error}))]

        valid, error = _validate_column_name(value_column, file_meta)
        if not valid:
            return [TextContent(type="text", text=json.dumps({"error": "invalid_column", "detail": error}))]

        try:
            # Calculate average by month across years
            sql = f"""
            SELECT
                month,
                AVG({value_column}) as avg_value,
                MIN({value_column}) as min_value,
                MAX({value_column}) as max_value,
                COUNT(*) as year_count
            FROM {table}
            WHERE {entity_column} = ?
                AND year >= ?
                AND year <= ?
            GROUP BY month
            ORDER BY month
            """

            with _get_db_connection() as conn:
                result = conn.execute(sql, [entity_value, start_year, end_year]).fetchall()

            if not result:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "no_data",
                        "detail": f"No data found for {entity_value} between {start_year}-{end_year}"
                    })
                )]

            # Build monthly patterns
            month_names = list(calendar.month_abbr)[1:]  # Skip empty string at index 0

            patterns = []
            for row in result:
                patterns.append({
                    "month": int(row[0]),
                    "month_name": month_names[int(row[0]) - 1],
                    "average": float(row[1]),
                    "min": float(row[2]),
                    "max": float(row[3]),
                    "years_included": int(row[4])
                })

            # Find peak and low seasons
            averages = [p["average"] for p in patterns]
            overall_avg = sum(averages) / len(averages)

            peak_months = [p for p in patterns if p["average"] > overall_avg * 1.1]
            low_months = [p for p in patterns if p["average"] < overall_avg * 0.9]

            # Calculate seasonality index (coefficient of variation)
            std_dev = (sum((x - overall_avg)**2 for x in averages) / len(averages)) ** 0.5
            seasonality_index = (std_dev / overall_avg) * 100 if overall_avg > 0 else 0

            analysis = {
                "entity": entity_value,
                "period": f"{start_year}-{end_year}",
                "monthly_patterns": patterns,
                "seasonality": {
                    "overall_average": float(overall_avg),
                    "seasonality_index": float(seasonality_index),
                    "interpretation": "High" if seasonality_index > 15 else "Moderate" if seasonality_index > 8 else "Low"
                },
                "peak_months": [{"month": p["month_name"], "average": p["average"]} for p in peak_months],
                "low_months": [{"month": p["month_name"], "average": p["average"]} for p in low_months],
                "insights": []
            }

            # Generate insights
            if peak_months:
                peak_names = ", ".join([p["month_name"] for p in peak_months])
                analysis["insights"].append(f"Peak emissions typically occur in: {peak_names}")

            if low_months:
                low_names = ", ".join([p["month_name"] for p in low_months])
                analysis["insights"].append(f"Lowest emissions typically occur in: {low_names}")

            if seasonality_index > 15:
                analysis["insights"].append("Strong seasonal pattern detected - emissions vary significantly by month")
            elif seasonality_index < 8:
                analysis["insights"].append("Weak seasonal pattern - emissions are relatively consistent year-round")

            return [TextContent(
                type="text",
                text=json.dumps(analysis, indent=2, default=str)
            )]

        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": "seasonal_analysis_failed", "detail": str(e)})
            )]

    elif name == "get_data_coverage":
        try:
            # Build comprehensive coverage index
            coverage_idx = _coverage_index()
            cities_coverage = _get_cities_data_coverage()

            result = {
                "coverage_by_type": {
                    "countries": {
                        "count": len(coverage_idx.get("country", [])),
                        "sample": coverage_idx.get("country", [])[:10]
                    },
                    "admin1_regions": {
                        "count": len(coverage_idx.get("admin1", [])),
                        "sample": coverage_idx.get("admin1", [])[:10]
                    },
                    "cities": {
                        "count": len(coverage_idx.get("city", [])),
                        "sample": coverage_idx.get("city", [])[:10]
                    }
                },
                "city_data_coverage": cities_coverage,
                "datasets": len(MANIFEST.get("files", [])),
                "status": "comprehensive"
            }

            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error getting data coverage: {e}")
            return [TextContent(
                type="text",
                text=json.dumps(_error_response(
                    "coverage_error",
                    f"Failed to retrieve data coverage: {str(e)}"
                ))
            )]

    elif name == "get_column_suggestions":
        file_id = arguments.get("file_id")
        column = arguments.get("column")
        query = arguments.get("query")
        limit = arguments.get("limit", 10)

        if not file_id or not column:
            return [TextContent(
                type="text",
                text=json.dumps(_error_response(
                    "missing_parameters",
                    "file_id and column are required"
                ))
            )]

        # Validate file_id
        valid, error = _validate_file_id(file_id)
        if not valid:
            return [TextContent(
                type="text",
                text=json.dumps(_error_response("invalid_file_id", error))
            )]

        file_meta = _find_file_meta(file_id)
        if not file_meta:
            return [TextContent(
                type="text",
                text=json.dumps(_error_response(
                    "file_not_found",
                    f"Dataset '{file_id}' not found"
                ))
            )]

        try:
            suggestions = _get_suggestions_for_column(file_meta, column, query, limit)
            return [TextContent(
                type="text",
                text=json.dumps(suggestions, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error getting column suggestions: {e}")
            return [TextContent(
                type="text",
                text=json.dumps(_error_response(
                    "suggestions_error",
                    f"Failed to get suggestions: {str(e)}"
                ))
            )]

    elif name == "aggregate_across_sectors":
        entity = arguments.get("entity")
        level = arguments.get("level", "country")
        sectors = arguments.get("sectors", "all")
        year = arguments.get("year", 2023)

        # Smart normalization
        if entity:
            entity = _normalize_entity_name(entity, level)

        # Get all sectors if "all" specified
        all_sectors = ["transport", "power", "waste", "agriculture",
                      "buildings", "fuel-exploitation", "industrial-combustion",
                      "industrial-processes"]

        if sectors == "all":
            sectors_to_query = all_sectors
        elif isinstance(sectors, list):
            sectors_to_query = sectors
        else:
            sectors_to_query = [sectors]

        # Query each sector
        results = []
        total_emissions = 0
        column_name = f"{level}_name" if level != "country" else "country_name"

        for sector in sectors_to_query:
            file_id = f"{sector}-{level}-year"
            file_meta = _find_file_meta(file_id)

            if not file_meta:
                results.append({
                    "sector": sector,
                    "emissions_tonnes": None,
                    "error": "dataset_not_found"
                })
                continue

            try:
                where = {column_name: entity, "year": year}
                data = _duckdb_pushdown(
                    file_meta=file_meta,
                    select=[column_name, "year", "emissions_tonnes"],
                    where=where,
                    group_by=[],
                    order_by=None,
                    limit=10
                )

                if data and len(data) > 0:
                    sector_emissions = data[0].get("emissions_tonnes", 0)
                    total_emissions += sector_emissions
                    results.append({
                        "sector": sector,
                        "emissions_tonnes": float(sector_emissions),
                        "emissions_mtco2": float(sector_emissions / 1e6)
                    })
                else:
                    results.append({
                        "sector": sector,
                        "emissions_tonnes": None,
                        "error": "no_data"
                    })
            except Exception as e:
                logger.warning(f"Could not get data for {sector}: {e}")
                results.append({
                    "sector": sector,
                    "emissions_tonnes": None,
                    "error": str(e)
                })

        response = {
            "entity": entity,
            "level": level,
            "year": year,
            "total_emissions_tonnes": float(total_emissions),
            "total_emissions_mtco2": float(total_emissions / 1e6),
            "breakdown": results,
            "sectors_with_data": len([r for r in results if r.get("emissions_tonnes") is not None]),
            "sectors_queried": len(sectors_to_query)
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]

    elif name == "compare_emissions":
        entities = arguments.get("entities", [])
        sector = arguments.get("sector", "transport")
        year = arguments.get("year", 2023)
        level = arguments.get("level", "country")

        # Smart normalization for all entities
        entities = [_normalize_entity_name(e, level) for e in entities]

        if len(entities) < 2:
            return [TextContent(type="text", text=json.dumps({
                "error": "At least 2 entities required for comparison",
                "provided": len(entities)
            }))]

        column_name = f"{level}_name" if level != "country" else "country_name"
        file_id = f"{sector}-{level}-year"
        file_meta = _find_file_meta(file_id)

        if not file_meta:
            return [TextContent(type="text", text=json.dumps({
                "error": "dataset_not_found",
                "file_id": file_id
            }))]

        # Query each entity
        results = []
        for entity in entities:
            where = {column_name: entity, "year": year}

            try:
                data = _duckdb_pushdown(
                    file_meta=file_meta,
                    select=[column_name, "year", "emissions_tonnes"],
                    where=where,
                    group_by=[],
                    order_by=None,
                    limit=10
                )

                if data and len(data) > 0:
                    emissions = data[0].get("emissions_tonnes", 0)
                    results.append({
                        "entity": entity,
                        "emissions_tonnes": float(emissions),
                        "emissions_mtco2": float(emissions / 1e6)
                    })
                else:
                    results.append({
                        "entity": entity,
                        "emissions_tonnes": None,
                        "error": "no_data"
                    })
            except Exception as e:
                results.append({
                    "entity": entity,
                    "emissions_tonnes": None,
                    "error": str(e)
                })

        # Calculate comparisons
        valid_results = [r for r in results if r.get("emissions_tonnes") is not None]

        if len(valid_results) >= 2:
            # Sort by emissions
            sorted_results = sorted(valid_results, key=lambda x: x["emissions_tonnes"], reverse=True)

            # Calculate differences
            highest = sorted_results[0]
            comparisons = []

            for r in sorted_results[1:]:
                diff = highest["emissions_tonnes"] - r["emissions_tonnes"]
                pct_diff = (diff / r["emissions_tonnes"] * 100) if r["emissions_tonnes"] > 0 else 0

                comparisons.append({
                    "entity": r["entity"],
                    "vs_highest": highest["entity"],
                    "difference_tonnes": float(diff),
                    "difference_mtco2": float(diff / 1e6),
                    "percentage_higher": float(pct_diff)
                })
        else:
            sorted_results = None
            comparisons = None

        response = {
            "comparison": {
                "entities": entities,
                "sector": sector,
                "year": year,
                "level": level
            },
            "results": results,
            "ranking": sorted_results,
            "comparisons": comparisons,
            "summary": {
                "highest_emitter": sorted_results[0]["entity"] if sorted_results else None,
                "lowest_emitter": sorted_results[-1]["entity"] if sorted_results else None,
                "total_emissions_mtco2": sum(r["emissions_mtco2"] for r in valid_results) if valid_results else 0
            }
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]

    elif name == "analyze_emissions_trend":
        entity = arguments.get("entity")
        sector = arguments.get("sector", "transport")
        start_year = arguments.get("start_year", 2000)
        end_year = arguments.get("end_year", 2023)
        level = arguments.get("level", "country")

        # Smart normalization
        if entity:
            entity = _normalize_entity_name(entity, level)

        column_name = f"{level}_name" if level != "country" else "country_name"
        file_id = f"{sector}-{level}-year"
        file_meta = _find_file_meta(file_id)

        if not file_meta:
            return [TextContent(type="text", text=json.dumps({
                "error": "dataset_not_found",
                "file_id": file_id
            }))]

        try:
            where = {
                column_name: entity,
                "year": {"gte": start_year, "lte": end_year}
            }

            data = _duckdb_pushdown(
                file_meta=file_meta,
                select=[column_name, "year", "emissions_tonnes"],
                where=where,
                group_by=[],
                order_by="year ASC",
                limit=100
            )

            if not data or len(data) == 0:
                return [TextContent(type="text", text=json.dumps({
                    "error": "no_data",
                    "entity": entity,
                    "years": f"{start_year}-{end_year}"
                }))]

            # Calculate trend statistics
            years = [row["year"] for row in data]
            values = [row["emissions_tonnes"] for row in data]

            # Calculate year-over-year changes
            yoy_changes = []
            for i in range(1, len(values)):
                change = values[i] - values[i-1]
                pct_change = (change / values[i-1] * 100) if values[i-1] > 0 else 0
                yoy_changes.append({
                    "from_year": years[i-1],
                    "to_year": years[i],
                    "change_tonnes": float(change),
                    "change_percent": float(pct_change)
                })

            # Calculate overall trend
            total_change = values[-1] - values[0]
            total_pct_change = (total_change / values[0] * 100) if values[0] > 0 else 0
            num_years = years[-1] - years[0]
            avg_annual_change = total_change / num_years if num_years > 0 else 0
            avg_annual_pct = total_pct_change / num_years if num_years > 0 else 0

            # Find peak and low
            max_idx = values.index(max(values))
            min_idx = values.index(min(values))

            response = {
                "entity": entity,
                "sector": sector,
                "period": f"{start_year}-{end_year}",
                "level": level,
                "data_points": len(data),
                "yearly_data": [{"year": d["year"], "emissions_tonnes": float(d["emissions_tonnes"]),
                                "emissions_mtco2": float(d["emissions_tonnes"] / 1e6)} for d in data],
                "trend_analysis": {
                    "start_value": float(values[0]),
                    "end_value": float(values[-1]),
                    "total_change_tonnes": float(total_change),
                    "total_change_percent": float(total_pct_change),
                    "avg_annual_change_tonnes": float(avg_annual_change),
                    "avg_annual_change_percent": float(avg_annual_pct),
                    "peak": {
                        "year": years[max_idx],
                        "value": float(values[max_idx])
                    },
                    "low": {
                        "year": years[min_idx],
                        "value": float(values[min_idx])
                    },
                    "trend_direction": "increasing" if total_change > 0 else "decreasing" if total_change < 0 else "stable"
                },
                "year_over_year_changes": yoy_changes
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]

        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return [TextContent(type="text", text=json.dumps({
                "error": "analysis_failed",
                "detail": str(e)
            }))]

    elif name == "get_top_emitters":
        sector = arguments.get("sector", "transport")
        year = arguments.get("year", 2023)
        level = arguments.get("level", "country")
        top_n = min(arguments.get("top_n", 10), 50)

        column_name = f"{level}_name" if level != "country" else "country_name"
        file_id = f"{sector}-{level}-year"
        file_meta = _find_file_meta(file_id)

        if not file_meta:
            return [TextContent(type="text", text=json.dumps({
                "error": "dataset_not_found",
                "file_id": file_id
            }))]

        try:
            where = {"year": year}
            data = _duckdb_pushdown(
                file_meta=file_meta,
                select=[column_name, "year", "emissions_tonnes"],
                where=where,
                group_by=[],
                order_by="emissions_tonnes DESC",
                limit=top_n
            )

            if not data:
                return [TextContent(type="text", text=json.dumps({
                    "error": "no_data",
                    "year": year
                }))]

            # Calculate percentages and rankings
            total_emissions = sum(row["emissions_tonnes"] for row in data)

            ranked_data = []
            for idx, row in enumerate(data, 1):
                emissions = row["emissions_tonnes"]
                ranked_data.append({
                    "rank": idx,
                    "entity": row[column_name],
                    "emissions_tonnes": float(emissions),
                    "emissions_mtco2": float(emissions / 1e6),
                    "percentage_of_top": float((emissions / total_emissions * 100) if total_emissions > 0 else 0)
                })

            response = {
                "sector": sector,
                "year": year,
                "level": level,
                "top_n": len(ranked_data),
                "top_emitters": ranked_data,
                "total_from_top": float(total_emissions),
                "total_from_top_mtco2": float(total_emissions / 1e6)
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]

        except Exception as e:
            logger.error(f"Top emitters query failed: {e}")
            return [TextContent(type="text", text=json.dumps({
                "error": "query_failed",
                "detail": str(e)
            }))]

    elif name == "smart_query_emissions":
        entity = arguments.get("entity")
        sector = arguments.get("sector", "transport")
        year = arguments.get("year", 2023)
        grain = arguments.get("grain", "year")
        level = arguments.get("level", "auto")
        enable_fallback = arguments.get("enable_fallback", True)

        if not entity:
            return [TextContent(type="text", text=json.dumps({
                "error": "missing_entity",
                "detail": "Entity name is required"
            }))]

        # Step 1: Smart entity resolution
        try:
            resolved_entity, detected_level, suggestions = _smart_entity_resolution(
                entity,
                level if level != "auto" else None
            )

            logger.info(f"Smart query: '{entity}' → '{resolved_entity}' ({detected_level})")

        except Exception as e:
            logger.error(f"Entity resolution failed: {e}")
            return [TextContent(type="text", text=json.dumps({
                "error": "resolution_failed",
                "detail": str(e),
                "original_entity": entity
            }))]

        # Step 2: Try to query at detected level with fallback
        levels_to_try = [detected_level]

        if enable_fallback:
            # Add fallback levels
            if detected_level == "city":
                levels_to_try.extend(["admin1", "country"])
            elif detected_level == "admin1":
                levels_to_try.append("country")

        fallback_trace = []
        final_data = None
        final_level = None

        for try_level in levels_to_try:
            column_name = f"{try_level}_name" if try_level != "country" else "country_name"
            file_id = f"{sector}-{try_level}-{grain}"
            file_meta = _find_file_meta(file_id)

            if not file_meta:
                fallback_trace.append({
                    "level": try_level,
                    "status": "dataset_not_found",
                    "file_id": file_id
                })
                continue

            try:
                where = {column_name: resolved_entity, "year": year}

                if grain == "month":
                    select_cols = [column_name, "year", "month", "emissions_tonnes"]
                else:
                    select_cols = [column_name, "year", "emissions_tonnes"]

                data = _duckdb_pushdown(
                    file_meta=file_meta,
                    select=select_cols,
                    where=where,
                    group_by=[],
                    order_by="year ASC" if grain == "year" else "year ASC, month ASC",
                    limit=100
                )

                if data and len(data) > 0:
                    # Success! Found data
                    final_data = data
                    final_level = try_level
                    fallback_trace.append({
                        "level": try_level,
                        "status": "success",
                        "rows_found": len(data)
                    })
                    break
                else:
                    fallback_trace.append({
                        "level": try_level,
                        "status": "no_data",
                        "file_id": file_id
                    })

            except Exception as e:
                fallback_trace.append({
                    "level": try_level,
                    "status": "error",
                    "error": str(e),
                    "file_id": file_id
                })
                logger.warning(f"Query failed at {try_level} level: {e}")
                continue

        # Step 3: Return results or error
        if final_data:
            # Format data with MtCO2
            formatted_data = []
            for row in final_data:
                formatted_row = dict(row)
                if "emissions_tonnes" in formatted_row:
                    formatted_row["emissions_mtco2"] = float(formatted_row["emissions_tonnes"] / 1e6)
                    formatted_row["emissions_tonnes"] = float(formatted_row["emissions_tonnes"])
                formatted_data.append(formatted_row)

            response = {
                "query": {
                    "original_entity": entity,
                    "resolved_entity": resolved_entity,
                    "requested_level": level,
                    "detected_level": detected_level,
                    "actual_level_used": final_level,
                    "sector": sector,
                    "year": year,
                    "grain": grain
                },
                "resolution": {
                    "normalized": resolved_entity,
                    "detected_level": detected_level,
                    "suggestions": suggestions if suggestions else [],
                    "fallback_used": final_level != detected_level
                },
                "data": formatted_data,
                "metadata": {
                    "rows_returned": len(formatted_data),
                    "fallback_trace": fallback_trace,
                    "data_source": f"{sector}-{final_level}-{grain}"
                }
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]

        else:
            # No data found at any level
            response = {
                "error": "no_data_found",
                "query": {
                    "original_entity": entity,
                    "resolved_entity": resolved_entity,
                    "detected_level": detected_level,
                    "sector": sector,
                    "year": year
                },
                "resolution": {
                    "normalized": resolved_entity,
                    "detected_level": detected_level,
                    "suggestions": suggestions if suggestions else []
                },
                "fallback_trace": fallback_trace,
                "suggestions": [
                    f"Try a different entity (suggestions: {', '.join(suggestions[:3])})" if suggestions else "Entity not found in database",
                    f"Try a different year (requested: {year})",
                    f"Try a different sector (requested: {sector})"
                ]
            }

            return [TextContent(type="text", text=json.dumps(response, indent=2, default=str))]

    elif name == "validate_query":
        file_id = arguments.get("file_id")
        select = arguments.get("select", [])
        where = arguments.get("where", {})
        group_by = arguments.get("group_by", [])
        order_by = arguments.get("order_by")
        limit = arguments.get("limit", 20)

        if not file_id:
            return [TextContent(
                type="text",
                text=json.dumps(_error_response("missing_file_id", "file_id is required"))
            )]

        # Validate file_id
        valid, error = _validate_file_id(file_id)
        if not valid:
            return [TextContent(
                type="text",
                text=json.dumps(_error_response("invalid_file_id", error))
            )]

        file_meta = _find_file_meta(file_id)
        if not file_meta:
            return [TextContent(
                type="text",
                text=json.dumps(_error_response("file_not_found", f"Dataset '{file_id}' not found"))
            )]

        validation_result = {
            "valid": True,
            "warnings": [],
            "suggestions": [],
            "query_patterns": {}
        }

        try:
            # Validate query complexity
            valid, complexity_error, limits = _validate_query_complexity(select, where, group_by, order_by)
            if not valid:
                validation_result["valid"] = False
                validation_result["warnings"].append(complexity_error)
                validation_result["limits"] = limits

            # Validate query intent
            intent_valid, intent_warning, suggestions_dict, suggestions_list = _validate_query_intent(
                file_id, where, select, file_meta
            )
            if intent_warning:
                validation_result["warnings"].append(intent_warning)
            if suggestions_list:
                validation_result["suggestions"].extend(suggestions_list)
            if suggestions_dict:
                validation_result["intent_suggestions"] = suggestions_dict

            # Detect query patterns
            patterns = _detect_query_patterns(where, group_by, order_by, limit)
            validation_result["query_patterns"] = patterns

            return [TextContent(
                type="text",
                text=json.dumps(validation_result, indent=2)
            )]
        except Exception as e:
            logger.error(f"Error validating query: {e}")
            return [TextContent(
                type="text",
                text=json.dumps(_error_response(
                    "validation_error",
                    f"Query validation failed: {str(e)}"
                ))
            )]

    elif name == "top_emitters":
        sector = arguments.get("sector")
        year = arguments.get("year")
        limit = arguments.get("limit", 10)
        geographic_level = arguments.get("geographic_level", "country")
        
        if not sector or not year:
            return [TextContent(type="text", text=json.dumps({"error": "sector and year required"}))]
        
        try:
            file_id = f"{sector}-{geographic_level}-year"
            file_meta = _find_file_meta(file_id)
            if not file_meta:
                return [TextContent(type="text", text=json.dumps({"error": "file_not_found", "file_id": file_id}))]
            
            table = _get_table_name(file_meta)
            if not table:
                return [TextContent(type="text", text=json.dumps({"error": "table_not_found"}))]
            
            # Build query based on geographic level
            if geographic_level == "country":
                sql = f"""
                    SELECT
                        country_name,
                        iso3,
                        emissions_tonnes,
                        RANK() OVER (ORDER BY emissions_tonnes DESC) as rank
                    FROM {table}
                    WHERE year = ?
                    ORDER BY emissions_tonnes DESC
                    LIMIT ?
                """
            elif geographic_level == "admin1":
                sql = f"""
                    SELECT
                        country_name,
                        admin1_name,
                        emissions_tonnes,
                        RANK() OVER (ORDER BY emissions_tonnes DESC) as rank
                    FROM {table}
                    WHERE year = ?
                    ORDER BY emissions_tonnes DESC
                    LIMIT ?
                """
            else:  # city
                sql = f"""
                    SELECT
                        country_name,
                        admin1_name,
                        city_name,
                        emissions_tonnes,
                        RANK() OVER (ORDER BY emissions_tonnes DESC) as rank
                    FROM {table}
                    WHERE year = ?
                    ORDER BY emissions_tonnes DESC
                    LIMIT ?
                """
            
            with _get_db_connection() as conn:
                result = conn.execute(sql, [year, limit]).fetchall()
            
            emitters = []
            for row in result:
                if geographic_level == "country":
                    emitters.append({
                        "rank": int(row[3]),
                        "country": row[0],
                        "iso3": row[1],
                        "emissions_tonnes": float(row[2]),
                        "emissions_mtco2": float(row[2]) / 1_000_000
                    })
                elif geographic_level == "admin1":
                    emitters.append({
                        "rank": int(row[3]),
                        "country": row[0],
                        "admin1": row[1],
                        "emissions_tonnes": float(row[2]),
                        "emissions_mtco2": float(row[2]) / 1_000_000
                    })
                else:  # city
                    emitters.append({
                        "rank": int(row[4]),
                        "country": row[0],
                        "admin1": row[1],
                        "city": row[2],
                        "emissions_tonnes": float(row[3]),
                        "emissions_mtco2": float(row[3]) / 1_000_000
                    })
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "sector": sector,
                    "year": year,
                    "geographic_level": geographic_level,
                    "top_emitters": emitters
                }, indent=2, default=str)
            )]
        except Exception as e:
            logger.error(f"Top emitters query failed: {e}")
            return [TextContent(type="text", text=json.dumps({"error": "query_failed", "detail": str(e)}))]
    
    elif name == "analyze_trend":
        entity_name = arguments.get("entity_name")
        sector = arguments.get("sector")
        start_year = arguments.get("start_year")
        end_year = arguments.get("end_year")
        
        if not all([entity_name, sector, start_year, end_year]):
            return [TextContent(type="text", text=json.dumps({"error": "All parameters required"}))]
        
        try:
            # Auto-detect geographic level
            normalized = _normalize_entity_name(entity_name)
            coverage = _coverage_index()
            
            geographic_level = None
            if normalized in coverage.get("city", []):
                geographic_level = "city"
            elif normalized in coverage.get("admin1", []):
                geographic_level = "admin1"
            elif normalized in coverage.get("country", []):
                geographic_level = "country"
            
            if not geographic_level:
                return [TextContent(type="text", text=json.dumps({"error": "entity_not_found", "entity": entity_name}))]
            
            file_id = f"{sector}-{geographic_level}-year"
            file_meta = _find_file_meta(file_id)
            if not file_meta:
                return [TextContent(type="text", text=json.dumps({"error": "file_not_found", "file_id": file_id}))]
            
            table = _get_table_name(file_meta)
            if not table:
                return [TextContent(type="text", text=json.dumps({"error": "table_not_found"}))]
            
            entity_column = f"{geographic_level}_name"
            
            # Query yearly data
            sql = f"""
                SELECT year, emissions_tonnes
                FROM {table}
                WHERE {entity_column} = ? AND year BETWEEN ? AND ?
                ORDER BY year
            """
            
            with _get_db_connection() as conn:
                result = conn.execute(sql, [normalized, start_year, end_year]).fetchall()
            
            if not result:
                return [TextContent(type="text", text=json.dumps({"error": "no_data_found"}))]
            
            # Calculate trend metrics
            years = [row[0] for row in result]
            emissions = [float(row[1]) for row in result]
            
            # Year-over-year growth rates
            yoy_growth = []
            for i in range(1, len(emissions)):
                growth = ((emissions[i] - emissions[i-1]) / emissions[i-1]) * 100 if emissions[i-1] > 0 else 0
                yoy_growth.append({
                    "year": years[i],
                    "growth_pct": round(growth, 2)
                })
            
            # Total change
            total_change_pct = ((emissions[-1] - emissions[0]) / emissions[0]) * 100 if emissions[0] > 0 else 0
            total_change_abs = emissions[-1] - emissions[0]
            
            # Determine pattern
            if total_change_pct > 10:
                pattern = "increasing"
            elif total_change_pct < -10:
                pattern = "decreasing"
            else:
                pattern = "stable"
            
            # Calculate CAGR
            num_years = len(years) - 1
            cagr = (((emissions[-1] / emissions[0]) ** (1 / num_years)) - 1) * 100 if emissions[0] > 0 and num_years > 0 else 0
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "entity": normalized,
                    "sector": sector,
                    "period": f"{start_year}-{end_year}",
                    "pattern": pattern,
                    "total_change_pct": round(total_change_pct, 2),
                    "total_change_tonnes": round(total_change_abs, 2),
                    "cagr_pct": round(cagr, 2),
                    "start_emissions": round(emissions[0], 2),
                    "end_emissions": round(emissions[-1], 2),
                    "yoy_growth": yoy_growth,
                    "yearly_data": [
                        {"year": y, "emissions_tonnes": round(e, 2)}
                        for y, e in zip(years, emissions)
                    ]
                }, indent=2, default=str)
            )]
        except Exception as e:
            logger.error(f"Trend analysis failed: {e}")
            return [TextContent(type="text", text=json.dumps({"error": "analysis_failed", "detail": str(e)}))]
    
    elif name == "compare_sectors":
        entity_name = arguments.get("entity_name")
        sectors = arguments.get("sectors", [])
        year = arguments.get("year")
        
        if not entity_name or not sectors or len(sectors) < 2 or not year:
            return [TextContent(type="text", text=json.dumps({"error": "entity_name, sectors (min 2), and year required"}))]
        
        try:
            normalized = _normalize_entity_name(entity_name)
            coverage = _coverage_index()
            
            geographic_level = None
            if normalized in coverage.get("city", []):
                geographic_level = "city"
            elif normalized in coverage.get("admin1", []):
                geographic_level = "admin1"
            elif normalized in coverage.get("country", []):
                geographic_level = "country"
            
            if not geographic_level:
                return [TextContent(type="text", text=json.dumps({"error": "entity_not_found"}))]
            
            results = []
            total_emissions = 0
            entity_column = f"{geographic_level}_name"
            
            # Query each sector
            for sector in sectors:
                file_id = f"{sector}-{geographic_level}-year"
                file_meta = _find_file_meta(file_id)
                if not file_meta:
                    continue
                
                table = _get_table_name(file_meta)
                if not table:
                    continue
                
                sql = f"SELECT emissions_tonnes FROM {table} WHERE {entity_column} = ? AND year = ?"
                
                with _get_db_connection() as conn:
                    result = conn.execute(sql, [normalized, year]).fetchone()
                
                if result:
                    emissions = float(result[0])
                    results.append({"sector": sector, "emissions": emissions})
                    total_emissions += emissions
            
            if not results:
                return [TextContent(type="text", text=json.dumps({"error": "no_data_found"}))]
            
            # Calculate percentages and rank
            for item in results:
                item["percentage"] = round((item["emissions"] / total_emissions) * 100, 2) if total_emissions > 0 else 0
                item["emissions_mtco2"] = round(item["emissions"] / 1_000_000, 2)
            
            # Sort by emissions descending
            results.sort(key=lambda x: x["emissions"], reverse=True)
            
            # Add rank
            for i, item in enumerate(results, 1):
                item["rank"] = i
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "entity": normalized,
                    "year": year,
                    "total_emissions_tonnes": round(total_emissions, 2),
                    "total_emissions_mtco2": round(total_emissions / 1_000_000, 2),
                    "sectors": results
                }, indent=2, default=str)
            )]
        except Exception as e:
            logger.error(f"Sector comparison failed: {e}")
            return [TextContent(type="text", text=json.dumps({"error": "comparison_failed", "detail": str(e)}))]
    
    elif name == "compare_geographies":
        entities = arguments.get("entities", [])
        sector = arguments.get("sector")
        year = arguments.get("year")
        
        if not entities or len(entities) < 2 or not sector or not year:
            return [TextContent(type="text", text=json.dumps({"error": "entities (min 2), sector, and year required"}))]
        
        try:
            results = []
            total_emissions = 0
            
            for entity in entities:
                normalized = _normalize_entity_name(entity)
                coverage = _coverage_index()
                
                geographic_level = None
                if normalized in coverage.get("city", []):
                    geographic_level = "city"
                elif normalized in coverage.get("admin1", []):
                    geographic_level = "admin1"
                elif normalized in coverage.get("country", []):
                    geographic_level = "country"
                
                if not geographic_level:
                    continue
                
                file_id = f"{sector}-{geographic_level}-year"
                file_meta = _find_file_meta(file_id)
                if not file_meta:
                    continue
                
                table = _get_table_name(file_meta)
                if not table:
                    continue
                
                entity_column = f"{geographic_level}_name"
                sql = f"SELECT emissions_tonnes FROM {table} WHERE {entity_column} = ? AND year = ?"
                
                with _get_db_connection() as conn:
                    result = conn.execute(sql, [normalized, year]).fetchone()
                
                if result:
                    emissions = float(result[0])
                    results.append({
                        "entity": normalized,
                        "geographic_level": geographic_level,
                        "emissions": emissions
                    })
                    total_emissions += emissions
            
            if not results:
                return [TextContent(type="text", text=json.dumps({"error": "no_data_found"}))]
            
            # Calculate percentages
            for item in results:
                item["percentage"] = round((item["emissions"] / total_emissions) * 100, 2) if total_emissions > 0 else 0
                item["emissions_mtco2"] = round(item["emissions"] / 1_000_000, 2)
            
            # Sort and rank
            results.sort(key=lambda x: x["emissions"], reverse=True)
            for i, item in enumerate(results, 1):
                item["rank"] = i
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "sector": sector,
                    "year": year,
                    "comparison": results,
                    "total_emissions_tonnes": round(total_emissions, 2),
                    "total_emissions_mtco2": round(total_emissions / 1_000_000, 2)
                }, indent=2, default=str)
            )]
        except Exception as e:
            logger.error(f"Geography comparison failed: {e}")
            return [TextContent(type="text", text=json.dumps({"error": "comparison_failed", "detail": str(e)}))]
    
    else:
        return [TextContent(
            type="text",
            text=json.dumps({"error": "unknown_tool", "name": name})
        )]


# ========================================
# RESOURCES - Data LLM can access
# ========================================

@app.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="emissions://datasets",
            name="All Emissions Datasets",
            description="List of all available emissions datasets",
            mimeType="application/json"
        )
    ]


@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Handle resource reads"""
    if uri == "emissions://datasets":
        files = [
            {
                "file_id": f.get("file_id", ""),
                "name": f.get("name", ""),
                "description": f.get("description", "")
            }
            for f in MANIFEST.get("files", [])
        ]
        return json.dumps({"datasets": files}, indent=2)
    
    return json.dumps({"error": "resource_not_found", "uri": uri})


# ========================================
# PROMPTS - Pre-defined prompt templates
# ========================================

@app.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """List available prompts"""
    return [
        Prompt(
            name="analyze_emissions",
            description="Analyze emissions trends for a country and sector",
            arguments=[
                PromptArgument(name="country", description="Country name", required=True),
                PromptArgument(name="sector", description="Sector (default: transport)", required=False),
                PromptArgument(name="start_year", description="Start year (default: 2000)", required=False),
                PromptArgument(name="end_year", description="End year (default: 2023)", required=False)
            ]
        ),
        Prompt(
            name="compare_countries",
            description="Compare emissions across multiple countries",
            arguments=[
                PromptArgument(name="countries", description="List of country names", required=True),
                PromptArgument(name="sector", description="Sector (default: transport)", required=False),
                PromptArgument(name="year", description="Year for comparison (default: 2023)", required=False)
            ]
        ),
        Prompt(
            name="analyze_covid_impact",
            description="Analyze COVID-19 pandemic impact on emissions using monthly data",
            arguments=[
                PromptArgument(name="country", description="Country name (default: global analysis)", required=False),
                PromptArgument(name="sector", description="Sector (default: transport)", required=False),
                PromptArgument(name="year", description="Year to analyze (default: 2020)", required=False)
            ]
        )
    ]


@app.get_prompt()
async def handle_get_prompt(name: str, arguments: dict) -> list[PromptMessage]:
    """Handle prompt generation"""
    
    if name == "analyze_emissions":
        country = arguments.get("country", "Unknown")
        sector = arguments.get("sector", "transport")
        start_year = arguments.get("start_year", 2000)
        end_year = arguments.get("end_year", 2023)
        
        return [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"""Analyze {sector} emissions trends for {country} from {start_year} to {end_year}.

Please:
1. Query the emissions data for this country and sector
2. Calculate the total change in emissions
3. Identify the year with highest and lowest emissions
4. Calculate the average annual growth rate
5. Compare to global or regional trends if possible

Provide insights on:
- Main trends (increasing, decreasing, or stable)
- Significant events or changes
- Comparison to climate targets if known
"""
                )
            )
        ]
    
    elif name == "compare_countries":
        countries = arguments.get("countries", [])
        if not isinstance(countries, list):
            countries = [countries]
        countries_str = ", ".join(countries)
        sector = arguments.get("sector", "transport")
        year = arguments.get("year", 2023)
        
        return [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"""Compare {sector} emissions for {countries_str} in {year}.

Please:
1. Query emissions data for each country
2. Rank countries by total emissions
3. Calculate per-capita emissions if possible
4. Show emissions as percentage of global total
5. Identify trends over the past 5 years

Provide insights on:
- Which country is the largest emitter
- Per-capita comparisons (fairness perspective)
- Recent trends (increasing or decreasing)
- Policy implications
"""
                )
            )
        ]

    elif name == "analyze_covid_impact":
        country = arguments.get("country", "")
        sector = arguments.get("sector", "transport")
        year = arguments.get("year", 2020)

        analysis_scope = f"for {country}" if country else "globally"

        return [
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"""Analyze the COVID-19 pandemic impact on {sector} emissions {analysis_scope} in {year}.

Please use the monthly trend analysis and seasonal pattern detection tools to:

1. **Monthly Analysis for {year}:**
   - Retrieve monthly emissions data for {year}
   - Identify the dramatic drop in March-April 2020 (lockdown period)
   - Calculate the magnitude of the drop from pre-COVID levels
   - Track the recovery pattern through the rest of the year

2. **Compare with Previous Years:**
   - Compare {year} monthly patterns to 2019 and earlier years
   - Identify deviations from normal seasonal patterns
   - Calculate total annual emissions reduction

3. **Key Metrics:**
   - Peak drop month and percentage decrease
   - Time to recovery (months)
   - Total annual reduction compared to 2019
   - Which months returned to normal vs. stayed depressed

4. **Insights:**
   - What does this tell us about the relationship between economic activity and emissions?
   - Were there any surprising patterns (e.g., sectors that didn't drop as expected)?
   - What lessons can we learn for emissions reduction policies?
   - Did emissions "rebound" above pre-pandemic levels after recovery?

5. **Regional Differences (if analyzing specific country):**
   - How did {country}'s experience compare to global trends?
   - Were there unique factors affecting {country}'s emissions during the pandemic?
   - What policy responses did {country} implement?

Use the analyze_monthly_trends tool with file_id='{sector}-country-month' for detailed month-by-month analysis, and detect_seasonal_patterns to compare {year} against historical norms.
"""
                )
            )
        ]

    # Note: get_data_coverage, get_column_suggestions, and validate_query
    # have been moved to handle_call_tool() as they are tools, not prompts

    return []


# ========================================
# MAIN - Run MCP server
# ========================================

async def main():
    """Run the MCP server via stdio"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())










