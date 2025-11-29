# ClimateGPT Quick Reference Guide

## File Location Summary Table

| Component | File Path | Purpose |
|-----------|-----------|---------|
| **MCP SERVER** | `/src/mcp_server_stdio.py` | TRUE MCP protocol server (stdio) |
| | `/src/mcp_http_bridge.py` | HTTP-to-MCP bridge (FastAPI) |
| **LLM RUNNER** | `/src/run_llm.py` | LLM inference orchestrator |
| **UI** | `/src/streamlit_app.py` | Interactive web interface |
| **LOCATION RESOLUTION** | `/src/location_resolver.py` | City/state/country detection |
| **ROUTING** | `/src/utils/router.py` | Intent-to-tool routing |
| **RESPONSE FORMATTING** | `/src/utils/answer.py` | Summary & unit conversion |
| **CONTEXT ENRICHMENT** | `/src/utils/baseline_context.py` | Knowledge augmentation |
| **DATABASE CONFIG** | `/utils/config.py` | Centralized configuration |
| **DATABASE ANALYSIS** | `/src/analyze_db.py` | DB inspection tool |
| **PYTEST CONFIG** | `/pytest.ini` | Test framework setup |
| **PROJECT CONFIG** | `/pyproject.toml` | Build & dependencies |
| **UNIT TESTS** | `/tests/test_new_tools.py` | Entity resolution & cache tests |
| **TEST HARNESS** | `/testing/test_harness.py` | Comparative LLM testing |
| **SMOKE TEST** | `/testing/test_10_questions.py` | Quick validation |
| **TEST UTILITIES** | `/testing/verify_setup.py` | System setup verification |
| | `/testing/extract_ground_truth.py` | Ground truth extraction |
| | `/testing/analyze_results.py` | Test result analysis |
| **CLI ENTRY** | `/src/cli.py` | Command-line interface |

## Port Assignments

| Service | Port | Environment Variable |
|---------|------|----------------------|
| MCP HTTP Bridge | 8010 | `PORT` |
| Streamlit UI | 8501 | Default Streamlit |
| LM Studio (local) | 1234 | Test config |

## Environment Variables Quick Setup

```bash
# Required
export OPENAI_API_KEY="username:password"
export OPENAI_BASE_URL="https://erasmus.ai/models/climategpt_8b_test/v1"
export MODEL="/cache/climategpt_8b_test"

# Database
export DB_PATH="data/warehouse/climategpt.duckdb"

# Server
export PORT="8010"
export HTTP_HOST="0.0.0.0"
export HTTP_PORT="8010"

# Environment
export ENVIRONMENT="development"  # or "production"
export ALLOWED_ORIGINS="http://localhost:8501,http://localhost:3000"

# Rate Limiting
export RATE_LIMIT_MAX_REQUESTS="100"
export RATE_LIMIT_WINDOW_SECONDS="60"

# Caching
export ENABLE_QUERY_CACHE="true"
export QUERY_CACHE_TTL_SECONDS="3600"
export CACHE_SIZE="1000"
export CACHE_TTL_SECONDS="300"

# Logging
export LOG_LEVEL="INFO"
export LOG_FORMAT="json"
```

## Key Command Patterns

### Start MCP Server
```bash
python src/mcp_server_stdio.py
```

### Start HTTP Bridge
```bash
python src/mcp_http_bridge.py
```

### Start Streamlit UI
```bash
streamlit run src/streamlit_app.py
```

### Run Tests
```bash
# Unit tests
pytest tests/test_new_tools.py -v

# Full test harness
python testing/test_harness.py

# Quick smoke test
python testing/test_10_questions.py

# Specific questions
python testing/test_harness.py --questions 1,2,3

# ClimateGPT only
python testing/test_harness.py --climategpt-only
```

### Verify Setup
```bash
python testing/verify_setup.py
```

## Tool Categories (from MCP Server)

### Data Query Tools
- `list_emissions_datasets` - List available datasets
- `get_dataset_schema` - Get schema for dataset
- `query_emissions` - Query with filters (where, select, limit)

### Analytical Tools
- `calculate_yoy_change` - Year-over-year metrics
- `top_emitters` - Top countries/regions
- `analyze_trend` - Trend analysis
- `compare_sectors` - Sector comparison
- `compare_geographies` - Geographic comparison

## MCP HTTP Bridge Endpoints

### Health & Monitoring
- `GET /health` - Health check + stats
- `GET /cache/stats` - Cache statistics
- `DELETE /cache/clear` - Clear cache

### Data Access
- `GET /list_files` - List datasets
- `GET /get_schema/{file_id}` - Get schema
- `POST /query` - Query data
- `POST /metrics/yoy` - Year-over-year metrics
- `POST /batch/query` - Batch queries

## Database Tables Pattern

```
[SECTOR]-[GRANULE]-[TEMPORAL]

Sectors: transport, energy, industrial, agriculture, waste, ...
Granules: country, admin1, city
Temporal: year, month

Examples:
- transport-country-year
- energy-admin1-month
- agriculture-city-year
```

## Testing Questions Available

- Location: `/testing/test_question_bank.json` (22,155+ questions)
- Format: Category, Sector, Level (country/admin1/city), Grain (year/month), Difficulty

## Configuration Validation

Config is auto-validated on import at `/utils/config.py`:
- Production mode: raises errors if invalid
- Development mode: logs warnings

Key validations:
- `DB_POOL_SIZE`: 1-100
- `LLM_CONCURRENCY_LIMIT`: 1-50
- `OPENAI_API_KEY`: required, format username:password
- `ALLOWED_ORIGINS`: required in production

## Key Classes

| Class | File | Purpose |
|-------|------|---------|
| `BaselineContextProvider` | `utils/baseline_context.py` | Context enrichment |
| `LocationResolver` | `location_resolver.py` | Location type detection |
| `RateLimiter` | `mcp_http_bridge.py` | Request rate limiting |
| `QueryCache` | `mcp_http_bridge.py` | Query result caching |
| `Config` | `utils/config.py` | Config management |
| `TestConfig` | `testing/test_harness.py` | Test configuration |
| `TestResult` | `testing/test_harness.py` | Test result tracking |

## Personas Supported

- Climate Analyst
- Research Scientist
- Policy Maker
- Educator
- Business Executive

(Defined in `BaselineContextProvider`)

## Dependencies Overview

**Critical for MCP**: mcp>=1.20.0
**Critical for Data**: duckdb>=1.4.1, pandas, numpy
**Critical for API**: fastapi==0.117.1, pydantic==2.11.9
**Critical for LLM**: openai>=2.2.0
**UI**: streamlit==1.50.0
**Testing**: pytest==8.3.3

Total: ~30+ dependencies (see pyproject.toml for full list)
