#!/usr/bin/env python3
"""
HTTP-to-MCP Bridge Server

This bridge allows HTTP clients (like the Streamlit UI) to communicate
with the TRUE MCP protocol server (mcp_server_stdio.py) which uses stdio.

Architecture:
  HTTP Client (Streamlit) → FastAPI Bridge → MCP Server (stdio) → DuckDB
"""

import asyncio
import json
import logging
import os
import sys
from typing import Any, Literal
from collections.abc import Callable
from pathlib import Path
import uuid
import time
from collections import defaultdict
import threading

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="ClimateGPT MCP Bridge",
    description="HTTP-to-MCP protocol bridge for ClimateGPT",
    version="1.0.0"
)

# CORS middleware - Configure allowed origins via environment variable
# SECURITY: Fail closed - require explicit configuration
# For development: ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8501"
# For production: Set to your actual frontend domains
ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS")
if not ALLOWED_ORIGINS_ENV:
    # Only allow localhost in development mode
    if os.getenv("ENVIRONMENT", "production") == "development":
        ALLOWED_ORIGINS = ["http://localhost:8501", "http://localhost:3000"]
        logger.warning("Using default localhost CORS origins in development mode")
    else:
        logger.error("ALLOWED_ORIGINS environment variable not set in production!")
        raise ValueError(
            "ALLOWED_ORIGINS environment variable is required in production. "
            "Set it to a comma-separated list of allowed origins. "
            "Example: ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com"
        )
else:
    ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",")]
    logger.info(f"CORS allowed origins: {ALLOWED_ORIGINS}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# MCP Server Process
mcp_process: asyncio.subprocess.Process | None = None
request_counter: int = 0


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Simple in-memory rate limiter with sliding window"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60) -> None:
        self.max_requests: int = max_requests
        self.window_seconds: int = window_seconds
        self.requests: dict[str, list[float]] = defaultdict(list)
        self.lock: threading.Lock = threading.Lock()

    def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed for this client"""
        with self.lock:
            now = time.time()
            # Remove old requests outside the window
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id]
                if now - req_time < self.window_seconds
            ]

            # Check if under limit
            if len(self.requests[client_id]) < self.max_requests:
                self.requests[client_id].append(now)
                return True

            return False

    def get_retry_after(self, client_id: str) -> int:
        """Get seconds until next request is allowed"""
        with self.lock:
            if not self.requests[client_id]:
                return 0
            oldest_request = min(self.requests[client_id])
            return max(0, int(self.window_seconds - (time.time() - oldest_request)))

# Initialize rate limiter
# Default: 100 requests per 60 seconds (configurable via env)
MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))
WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
rate_limiter = RateLimiter(max_requests=MAX_REQUESTS, window_seconds=WINDOW_SECONDS)


# ============================================================================
# Query Caching (Optimization)
# ============================================================================

class QueryCache:
    """Simple in-memory cache for query results with TTL"""

    def __init__(self, ttl_seconds: int = 3600) -> None:
        self.ttl_seconds: int = ttl_seconds  # Default 1 hour
        self.cache: dict[str, tuple[Any, float]] = {}
        self.lock: threading.Lock = threading.Lock()
        self.stats = {"hits": 0, "misses": 0}

    def get_key(self, method: str, params: dict[str, Any]) -> str:
        """Generate cache key from method and params"""
        # Sort params to ensure consistency
        params_str = json.dumps(params, sort_keys=True)
        return f"{method}:{params_str}"

    def get(self, key: str) -> Any | None:
        """Retrieve cached value if not expired"""
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None

            value, timestamp = self.cache[key]
            if time.time() - timestamp > self.ttl_seconds:
                # Cache expired, remove it
                del self.cache[key]
                self.stats["misses"] += 1
                return None

            self.stats["hits"] += 1
            return value

    def set(self, key: str, value: Any) -> None:
        """Store value in cache"""
        with self.lock:
            self.cache[key] = (value, time.time())

    def clear(self) -> None:
        """Clear all cache entries"""
        with self.lock:
            self.cache.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
            return {
                "hits": self.stats["hits"],
                "misses": self.stats["misses"],
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 2),
                "cached_queries": len(self.cache),
                "ttl_seconds": self.ttl_seconds
            }


# Initialize query cache
# Default: 1 hour TTL (configurable via env)
CACHE_TTL_SECONDS = int(os.getenv("QUERY_CACHE_TTL_SECONDS", "3600"))
ENABLE_CACHE = os.getenv("ENABLE_QUERY_CACHE", "true").lower() == "true"
query_cache = QueryCache(ttl_seconds=CACHE_TTL_SECONDS) if ENABLE_CACHE else None

logger.info(f"Query cache: {'ENABLED' if query_cache else 'DISABLED'} (TTL: {CACHE_TTL_SECONDS}s)")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable[[Request], Any]) -> Any:
    """Apply rate limiting to all requests"""
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    # Get client identifier (IP address)
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    if not rate_limiter.is_allowed(client_ip):
        retry_after = rate_limiter.get_retry_after(client_ip)
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limit_exceeded",
                "message": f"Too many requests. Please try again in {retry_after} seconds.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )

    return await call_next(request)


# ============================================================================
# JSON parsing helpers
# ============================================================================

def _safe_json_loads(payload: str) -> Any:
    """
    Load JSON with resilience to stray characters or multiple objects.
    Falls back to extracting the first valid JSON object/array.
    """
    if payload is None:
        return {}

    text = payload.strip()
    if not text:
        return {}

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt to locate the first JSON object or array
        for opener, closer in (("{", "}"), ("[", "]")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end != -1 and end > start:
                candidate = text[start : end + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

        # Attempt to parse line by line (NDJSON style)
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue

        # Log the actual payload for debugging
        try:
            snippet = text[:200] if len(text) > 200 else text
        except Exception as e:
            snippet = f"<error getting snippet: {e}>"
        logger.error(f"Unparseable JSON payload snippet: {snippet}")
        logger.error(f"Payload type: {type(text)}, length: {len(text) if hasattr(text, '__len__') else 'N/A'}")
        raise json.JSONDecodeError("Unable to parse JSON from MCP response", text[:100] if isinstance(text, str) else str(text)[:100], 0)


# ============================================================================
# MCP Protocol Communication
# ============================================================================

async def send_mcp_request(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Send a JSON-RPC 2.0 request to MCP server via stdio"""
    global request_counter, mcp_process

    if not mcp_process:
        raise HTTPException(status_code=503, detail="MCP server not initialized")

    request_counter += 1
    request_id = f"http-bridge-{request_counter}"

    # Build JSON-RPC 2.0 request
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params
    }

    # Send request to MCP server stdin
    request_json = json.dumps(jsonrpc_request) + "\n"
    logger.info(f"→ MCP Request: {method} (id={request_id})")
    logger.debug(f"Request payload: {request_json.strip()}")

    try:
        mcp_process.stdin.write(request_json.encode())
        await mcp_process.stdin.drain()
    except Exception as e:
        logger.error(f"Failed to send request to MCP server: {e}")
        raise HTTPException(status_code=503, detail=f"MCP communication error: {e}")

    # Read response from MCP server stdout
    try:
        response_line = await asyncio.wait_for(
            mcp_process.stdout.readline(),
            timeout=30.0
        )
        response_json = response_line.decode().strip()

        if not response_json:
            raise HTTPException(status_code=503, detail="Empty response from MCP server")

        logger.debug(f"← MCP Response: {response_json}")
        response = json.loads(response_json)

        # Check for JSON-RPC error
        if "error" in response:
            error = response["error"]
            logger.error(f"MCP server error: {error}")
            raise HTTPException(
                status_code=400,
                detail=error.get("message", "MCP server error")
            )

        # Return the result
        return response.get("result", {})

    except asyncio.TimeoutError:
        logger.error("MCP server response timeout")
        raise HTTPException(status_code=504, detail="MCP server timeout")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from MCP server: {e}")
        raise HTTPException(status_code=502, detail="Invalid response from MCP server")


# ============================================================================
# HTTP Endpoints (REST API compatibility with existing ClimateGPT UI)
# ============================================================================

@app.get("/health", response_model=None)
async def health_check() -> dict[str, Any] | JSONResponse:
    """Health check endpoint with system stats"""
    health = {
        "status": "healthy" if (mcp_process and mcp_process.returncode is None) else "unhealthy",
        "mcp_server": "running" if (mcp_process and mcp_process.returncode is None) else "not running",
        "cache": query_cache.get_stats() if query_cache else None,
        "rate_limiter": {
            "enabled": True,
            "max_requests_per_window": MAX_REQUESTS,
            "window_seconds": WINDOW_SECONDS
        }
    }

    if mcp_process and mcp_process.returncode is None:
        return health

    return JSONResponse(status_code=503, content=health)


@app.get("/cache/stats")
async def cache_stats() -> dict[str, Any]:
    """Get cache statistics"""
    if not query_cache:
        return {"status": "cache_disabled"}
    return {
        "status": "cache_enabled",
        "stats": query_cache.get_stats()
    }


@app.delete("/cache/clear")
async def cache_clear() -> dict[str, Any]:
    """Clear all cached queries"""
    if not query_cache:
        return {"status": "cache_disabled"}

    stats_before = query_cache.get_stats()
    query_cache.clear()
    return {
        "status": "cleared",
        "entries_cleared": stats_before["cached_queries"]
    }


@app.get("/list_files")
async def list_files() -> dict[str, Any]:
    """List available datasets via MCP list_emissions_datasets tool"""
    try:
        result = await send_mcp_request("tools/call", {
            "name": "list_emissions_datasets",
            "arguments": {}
        })

        # Parse the result content
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "{}")
                try:
                    return _safe_json_loads(text_content)
                except json.JSONDecodeError as exc:
                    logger.error(f"Failed to parse list_files payload: {exc}")
                    raise HTTPException(status_code=500, detail=f"Invalid MCP response: {exc}") from exc

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/get_schema/{file_id}")
async def get_schema(file_id: str) -> dict[str, Any]:
    """Get schema for a specific dataset via MCP get_dataset_schema tool"""
    try:
        result = await send_mcp_request("tools/call", {
            "name": "get_dataset_schema",
            "arguments": {"file_id": file_id}
        })

        # Parse the result content
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                # Extract text from content
                text_content = content[0].get("text", "{}")
                try:
                    return _safe_json_loads(text_content)
                except json.JSONDecodeError as exc:
                    logger.error(f"Failed to parse get_schema payload: {exc}")
                    raise HTTPException(status_code=500, detail=f"Invalid MCP response: {exc}") from exc

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schema: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class QueryRequest(BaseModel):
    file_id: str
    select: list[str] | None = None
    where: dict[str, Any] | None = None
    group_by: list[str] | None = None
    order_by: str | None = None
    limit: int | None = None


@app.post("/query")
async def query_data(request: QueryRequest) -> dict[str, Any]:
    """Query dataset via MCP query_emissions tool with caching"""
    try:
        # Get request arguments and remove problematic "assist" parameter
        # (workaround for MCP library bug with boolean values)
        arguments = request.dict(exclude_none=True)
        arguments.pop("assist", None)  # Remove assist if present

        # Check cache first (if enabled)
        cache_key = None
        if query_cache:
            cache_key = query_cache.get_key("query_emissions", arguments)
            cached_result = query_cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache HIT for query: {cache_key[:50]}...")
                return cached_result

        result = await send_mcp_request("tools/call", {
            "name": "query_emissions",
            "arguments": arguments
        })

        # Parse the result content
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "{}")
                logger.debug(f"MCP response text_content type: {type(text_content)}")
                logger.debug(f"MCP response text_content: {text_content[:500] if isinstance(text_content, str) else str(text_content)[:500]}")
                try:
                    parsed_result = _safe_json_loads(text_content)
                    # Cache the successful result
                    if query_cache and cache_key:
                        query_cache.set(cache_key, parsed_result)
                        logger.info(f"Cache SET for query: {cache_key[:50]}...")
                    return parsed_result
                except Exception as exc:
                    logger.error(f"Failed to parse query payload: {exc}")
                    logger.error(f"Problematic content: {text_content[:500] if isinstance(text_content, str) else str(text_content)[:500]}")
                    raise HTTPException(status_code=500, detail=f"Invalid MCP response: {exc}") from exc

        # Cache the result if it's successful
        if query_cache and cache_key:
            query_cache.set(cache_key, result)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class YoYMetricsRequest(BaseModel):
    file_id: str
    key_column: str
    value_column: str
    base_year: int
    compare_year: int
    top_n: int | None = 10
    direction: str | None = "rise"


@app.post("/metrics/yoy")
async def yoy_metrics(request: YoYMetricsRequest) -> dict[str, Any]:
    """Year-over-year metrics via MCP calculate_yoy_change tool"""
    try:
        result = await send_mcp_request("tools/call", {
            "name": "calculate_yoy_change",
            "arguments": request.dict(exclude_none=True)
        })

        # Parse the result content
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get("text", "{}")
                try:
                    return _safe_json_loads(text_content)
                except json.JSONDecodeError as exc:
                    logger.error(f"Failed to parse yearly metrics payload: {exc}")
                    raise HTTPException(status_code=500, detail=f"Invalid MCP response: {exc}") from exc

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating YoY metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BatchQueryRequest(BaseModel):
    queries: list[dict[str, Any]]


@app.post("/batch/query")
async def batch_query(request: BatchQueryRequest) -> dict[str, Any]:
    """Batch query - executes multiple queries via MCP and aggregates results"""
    try:
        results = []

        # Execute each query separately via MCP
        for query in request.queries:
            try:
                result = await send_mcp_request("tools/call", {
                    "name": "query_emissions",
                    "arguments": query
                })

                # Parse the result content
                data = {}
                if isinstance(result, dict) and "content" in result:
                    content = result["content"]
                    if isinstance(content, list) and len(content) > 0:
                        text_content = content[0].get("text", "{}")
                        try:
                            data = _safe_json_loads(text_content)
                        except json.JSONDecodeError as exc:
                            logger.error(f"Failed to parse batch query payload: {exc}")
                            raise HTTPException(status_code=500, detail=f"Invalid MCP response: {exc}") from exc

                results.append({
                    "status": "success",
                    "data": data
                })

            except Exception as e:
                logger.error(f"Batch query item failed: {e}")
                results.append({
                    "status": "error",
                    "error": str(e)
                })

        return {"results": results}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# MCP Server Lifecycle Management
# ============================================================================

@app.on_event("startup")
async def startup_event() -> None:
    """Start the MCP server process on bridge startup"""
    global mcp_process

    logger.info("🚀 Starting MCP Bridge Server...")

    # Find the mcp_server_stdio.py script
    mcp_script = Path(__file__).parent / "mcp_server_stdio.py"

    if not mcp_script.exists():
        logger.error(f"MCP server script not found: {mcp_script}")
        raise RuntimeError("MCP server script not found")

    # Start MCP server as subprocess
    try:
        logger.info(f"📡 Starting MCP server: {mcp_script}")
        mcp_process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(mcp_script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONUNBUFFERED": "1"}
        )

        # Wait a bit for initialization
        await asyncio.sleep(2)

        # Check if process is still running
        if mcp_process.returncode is not None:
            stderr = await mcp_process.stderr.read()
            logger.error(f"MCP server failed to start: {stderr.decode()}")
            raise RuntimeError("MCP server failed to start")

        logger.info("✅ MCP server started successfully")

        # Initialize MCP protocol
        await send_mcp_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "climategpt-http-bridge",
                "version": "1.0.0"
            }
        })

        logger.info("✅ MCP protocol initialized")

    except Exception as e:
        logger.error(f"Failed to start MCP server: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Stop the MCP server process on bridge shutdown"""
    global mcp_process

    if mcp_process:
        logger.info("🛑 Stopping MCP server...")
        try:
            mcp_process.terminate()
            await asyncio.wait_for(mcp_process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("MCP server did not terminate gracefully, killing...")
            mcp_process.kill()
            await mcp_process.wait()

        logger.info("✅ MCP server stopped")


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8010"))

    logger.info(f"🌍 Starting ClimateGPT MCP Bridge on port {port}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
