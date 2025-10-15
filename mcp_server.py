import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import lru_cache

import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from dotenv import load_dotenv
import duckdb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------
# Robust .env loading (from the same folder as this file)
# ---------------------------------------------------------------------
ENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=ENV_PATH)

OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("MODEL")

# Not strictly required for the API to run, but warn if missing
_missing = [k for k, v in {
    "OPENAI_BASE_URL": OPENAI_BASE_URL,
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "MODEL": MODEL
}.items() if not v]
if _missing:
    print(f"[mcp_server] Warning: missing env vars in {ENV_PATH.name}: {', '.join(_missing)}")

# ---------------------------------------------------------------------
# App and manifest
# ---------------------------------------------------------------------
app = FastAPI(title="ClimateGPT MCP Server", version="0.2.0")

# CORS for local dev (frontend / notebooks)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:*",
        "http://127.0.0.1",
        "http://127.0.0.1:*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load manifest (defensive)
manifest_path = Path("data/curated/manifest_mcp_duckdb.json")
if not manifest_path.exists():
    raise FileNotFoundError(f"Manifest not found at {manifest_path}")
with open(manifest_path, "r") as f:
    MANIFEST = json.load(f)

# ---------------------------------------------------------------------
# Legacy -> expanded aliases (so old IDs still work)
# ---------------------------------------------------------------------
ALIASES = {
    "transport_country_year": "transport_country_year.expanded",
    "transport_country_month": "transport_country_month.expanded",
    "transport_admin1_year": "transport_admin1_year.expanded",
    "transport_admin1_month": "transport_admin1_month.expanded",
    "transport_city_year": "transport_city_year.expanded",
    "transport_city_month": "transport_city_month.expanded",
}

def _resolve_file_id(fid: str) -> str:
    return ALIASES.get(fid, fid)


# Columns that can be aggregated
AGG_COLUMNS = ["emissions_tonnes", "MtCO2"]


# ---------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------
class QueryRequest(BaseModel):
    file_id: str
    select: List[str] = []
    where: Dict[str, Any] = {}
    group_by: List[str] = []
    order_by: Optional[str] = None
    limit: Optional[int] = 20


class DeltaRequest(BaseModel):
    file_id: str
    where: Dict[str, Any] = {}
    key_col: str = "admin1_name"
    value_col: str = "emissions_tonnes"
    base_year: int = 2019
    compare_year: int = 2020
    top_n: int = 10
    direction: str = "drop"  # "drop" or "rise"


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
@lru_cache(maxsize=16)
def _load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path)

# ---------------------------------------------------------------------
# Table loader: supports DuckDB or CSV
# ---------------------------------------------------------------------
def _load_table(file_meta: Dict[str, Any]) -> pd.DataFrame:
    """
    Load a table according to the manifest entry.
    Supported:
      - DuckDB URI: duckdb://<absolute_or_relative_db_path>#<table_or_view>
      - CSV path (default)
    """
    engine = file_meta.get("engine")
    if engine == "duckdb":
        uri = file_meta.get("path")
        if not uri:
            raise ValueError("Missing 'path' field in manifest for DuckDB entry")
        if not isinstance(uri, str) or not uri.startswith("duckdb://"):
            raise ValueError(f"Invalid DuckDB URI in manifest: {uri}")
        # parse duckdb://<db>#<table>
        db_path, sep, table = uri[len("duckdb://"):].partition("#")
        if not sep or not db_path or not table:
            raise ValueError(f"DuckDB URI must be duckdb://<db_path>#<table>, got: {uri}")
        con = duckdb.connect(db_path, read_only=True)
        try:
            return con.execute(f"SELECT * FROM {table}").df()
        finally:
            con.close()
    # default: CSV
    path = file_meta.get("path")
    if not path:
        raise ValueError("Missing 'path' field in manifest")
    return _load_csv(path)


def _get_file_meta(file_id: str) -> Optional[Dict[str, Any]]:
    return next((f for f in MANIFEST["files"] if f["file_id"] == file_id), None)


def _apply_filter(df: pd.DataFrame, col: str, val: Any) -> pd.DataFrame:
    if col not in df.columns:
        return df
    if isinstance(val, dict):
        if "in" in val:
            return df[df[col].isin(val["in"])]
        if "between" in val:
            lo, hi = val["between"]
            return df[df[col].between(lo, hi, inclusive="both")]
        if "gte" in val:
            return df[df[col] >= val["gte"]]
        if "lte" in val:
            return df[df[col] <= val["lte"]]
        if "contains" in val:
            return df[df[col].astype(str).str.contains(str(val["contains"]), case=False, na=False, regex=False)]
    # default equality
    return df[df[col] == val]


def _coerce_numeric(df: pd.DataFrame, cols: List[str]) -> None:
    for c in cols:
        if c in df.columns and not is_numeric_dtype(df[c]):
            conv = pd.to_numeric(df[c], errors="coerce")
            if conv.notna().mean() > 0.8 or c in AGG_COLUMNS:
                df[c] = conv


def _response(df: pd.DataFrame, file_id: str, limit: Optional[int]) -> Dict[str, Any]:
    lim = 100 if limit is None else int(limit)
    lim = max(1, min(lim, 1000))
    out = df.head(lim).replace({np.nan: None})
    return {
        "rows": out.to_dict(orient="records"),
        "row_count": int(len(df)),
        "meta": {
            "units": _get_file_meta(file_id).get("semantics", {}).get("units", ["tonnes CO2"]),
            "source": _get_file_meta(file_id).get("semantics", {}).get("source", "EDGAR v2024 transport"),
            "table_id": file_id,
            "spatial_resolution": _get_file_meta(file_id).get("semantics", {}).get("spatial_resolution"),
            "temporal_resolution": _get_file_meta(file_id).get("semantics", {}).get("temporal_resolution"),
        }
    }


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}
@app.get("/list_files")
def list_files():
    """Enumerate available tables with basic descriptors."""
    return MANIFEST["files"]


@app.get("/get_schema/{file_id}")
def get_schema(file_id: str):
    """Return full schema/metadata for a file."""
    meta = _get_file_meta(file_id)
    return meta if meta else {"error": "file not found"}

@app.post("/query")
def query(req: QueryRequest):
    """Filter/aggregate a file by common dimensions."""
    fid = _resolve_file_id(req.file_id)
    file_meta = _get_file_meta(fid)
    if not file_meta:
        return {"error": "file not found"}

    try:
        df = _load_table(file_meta).copy()
    except Exception as e:
        return {"error": "read_failed", "detail": str(e), "path": file_meta.get("path", "unknown")}

    # Explicit typing
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "month" in df.columns:
        df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    for c in ["emissions_tonnes", "MtCO2"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Validate select/group_by columns
    valid_cols = set(df.columns)
    bad_select = [c for c in req.select if c not in valid_cols]
    bad_group  = [c for c in req.group_by if c not in valid_cols]
    if bad_select or bad_group:
        return {"error": "invalid columns", "select": bad_select, "group_by": bad_group}

    # Filters
    for k, v in req.where.items():
        df = _apply_filter(df, k, v)

    # Projection
    if req.select:
        keep = [c for c in req.select if c in df.columns]
        df = df[keep] if keep else df

        # Grouping + aggregations
    if req.group_by:
        agg_map = {c: "sum" for c in AGG_COLUMNS if c in df.columns}
        if agg_map:
            df = df.groupby(req.group_by, dropna=False).agg(agg_map).reset_index()

        # Ordering
    if req.order_by:
        parts = req.order_by.split()
        col = parts[0]
        ascending = not (len(parts) > 1 and parts[1].upper() == "DESC")
        if col not in df.columns:
            return {"error": "invalid order_by", "order_by": req.order_by}
        df = df.sort_values(col, ascending=ascending)

    return _response(df, fid, req.limit)

@app.post("/metrics/yoy")
def yoy(req: DeltaRequest):
    """
    Convenience endpoint to compute year-over-year deltas
    (e.g., biggest drop from base_year to compare_year).
    """
    fid = _resolve_file_id(req.file_id)
    file_meta = _get_file_meta(fid)
    if not file_meta:
        return {"error": "file not found"}

    try:
        df = _load_table(file_meta).copy()
    except Exception as e:
        return {"error": "read_failed", "detail": str(e), "path": file_meta["path"]}
    # Explicit typing
    if "year" in df.columns:
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    if "month" in df.columns:
        df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    for c in ["emissions_tonnes", "MtCO2"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Apply provided filters, but enforce year IN [base, compare]
    filters = dict(req.where)
    filters["year"] = {"in": [req.base_year, req.compare_year]}
    for k, v in filters.items():
        df = _apply_filter(df, k, v)

    # Keep only needed columns
    needed = [req.key_col, "year", req.value_col]
    df = df[[c for c in needed if c in df.columns]]

    # Build pivot per key
    by_key: Dict[str, Dict[int, float]] = {}
    for _, r in df.iterrows():
        key = r[req.key_col]
        yr = int(r["year"])
        val = float(r[req.value_col])
        by_key.setdefault(key, {})[yr] = val

    rows = []
    for k, years in by_key.items():
        b = years.get(req.base_year)
        c = years.get(req.compare_year)
        if b is None or c is None:
            continue
        delta = b - c
        pct = (delta / b) * 100.0 if b else None
        rows.append({"key": k, "base": b, "compare": c, "delta": delta, "pct": pct})

    # Sort by requested direction
    rows.sort(key=lambda x: x["delta"], reverse=(req.direction == "drop"))

    # Shape response similar to /query
    return {
        "rows": rows[: req.top_n],
        "row_count": len(rows),
        "base_year": req.base_year,
        "compare_year": req.compare_year,
        "meta": {
            "units": _get_file_meta(fid).get("semantics", {}).get("units", ["tonnes CO2"]),
            "source": "EDGAR v2024 transport",
            "table_id": fid,
            "spatial_resolution": _get_file_meta(fid).get("semantics", {}).get("spatial_resolution"),
            "temporal_resolution": _get_file_meta(fid).get("semantics", {}).get("temporal_resolution")
        }
    }

@app.get("/tools")
def tools():
    return [{
        "type": "function",
        "function": {
            "name": "query",
            "description": "Filter/aggregate EDGAR transport emissions",
            "parameters": QueryRequest.model_json_schema()
        }
    },{
        "type": "function",
        "function": {
            "name": "metrics.yoy",
            "description": "Compute YoY deltas",
            "parameters": DeltaRequest.model_json_schema()
        }
    }]

# ---------------------------------------------------------------------
# Local runner (so: uv run python mcp_server.py works)
# ---------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8010"))
    uvicorn.run("mcp_server:app", host="127.0.0.1", port=port, reload=True)