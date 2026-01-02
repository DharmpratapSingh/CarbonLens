# ClimateGPT Codebase Structure Analysis

## Overview
ClimateGPT is a comprehensive emissions data analysis system built on the EDGAR v2024 dataset, featuring MCP (Model Context Protocol) server implementation, LLM integration, and interactive Streamlit UI.

---

## 1. MCP SERVER IMPLEMENTATION

### Primary Files

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/mcp_server_stdio.py`
**Purpose**: TRUE MCP Protocol server implementation using stdio-based communication
**Key Features**:
- Implements MCP (Model Context Protocol) server communicating via stdin/stdout
- Provides tools for querying climate emissions data from DuckDB
- Handles entity resolution, normalization, and caching
- Structured logging with JSON format for production
- Tools exposed:
  - `list_emissions_datasets`: Lists available datasets
  - `get_dataset_schema`: Gets schema for specific dataset
  - `query_emissions`: Query emissions data with filters
  - `calculate_yoy_change`: Year-over-year metrics
  - `top_emitters`: Identifies top emitting countries/regions
  - `analyze_trend`: Analyzes emission trends
  - `compare_sectors`: Compares across sectors
  - `compare_geographies`: Compares geographic regions
- Uses LRU cache for query optimization
- Handles JSON-RPC 2.0 protocol

**Key Components**:
- Logging setup (JSON/text format)
- MCP Server initialization
- Tool registration and execution
- DuckDB connection management
- Entity normalization functions
- Cache management

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/mcp_http_bridge.py`
**Purpose**: HTTP-to-MCP bridge enabling REST API clients (like Streamlit) to communicate with stdio MCP server
**Key Features**:
- FastAPI-based HTTP server bridging HTTP requests to MCP protocol
- Rate limiting (100 requests per 60 seconds by default)
- Query result caching with TTL (1 hour default)
- CORS middleware configuration
- Health check and monitoring endpoints
- Handles MCP server process lifecycle (startup/shutdown)
- Robust JSON parsing with fallback mechanisms

**Endpoints**:
- `GET /health` - Health check with system stats
- `GET /cache/stats` - Cache statistics
- `DELETE /cache/clear` - Clear cache
- `GET /list_files` - List datasets via MCP
- `GET /get_schema/{file_id}` - Get dataset schema
- `POST /query` - Query emissions data
- `POST /metrics/yoy` - Year-over-year metrics
- `POST /batch/query` - Batch query execution

**Configuration** (via environment variables):
- `PORT`: Server port (default: 8010)
- `ALLOWED_ORIGINS`: CORS allowed origins
- `RATE_LIMIT_MAX_REQUESTS`: Rate limit (default: 100)
- `RATE_LIMIT_WINDOW_SECONDS`: Rate limit window (default: 60)
- `QUERY_CACHE_TTL_SECONDS`: Cache TTL (default: 3600)
- `ENABLE_QUERY_CACHE`: Enable/disable caching (default: true)
- `ENVIRONMENT`: Environment mode (development/production)

---

## 2. LLM RUNNER

### Primary File

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/run_llm.py`
**Purpose**: Main LLM inference orchestration for ClimateGPT Q&A
**Key Features**:
- Integrates with OpenAI API or compatible endpoints (e.g., Erasmus AI)
- Loads system prompt from `system_prompt.txt`
- Implements tool routing optimization flow:
  - Single entity lookups → query tool
  - Comparisons → query tool with multiple calls
  - Top/Highest/Lowest → query with order_by + limit
  - Year-over-year change → metrics.yoy tool
  - Seasonal patterns → query with month grain
  - Multi-sector totals → multiple query calls
- Persona framework caching (BaselineContextProvider)
- Baseline knowledge augmentation (policy, sector strategy, educational context)

**Configuration** (via environment variables):
- `OPENAI_BASE_URL`: Custom LLM endpoint
- `MODEL`: Model identifier (default: /cache/climategpt_8b_test)
- `OPENAI_API_KEY`: Authentication (format: username:password)
- `PORT`: MCP Bridge port (default: 8010)

**Tool Integration**:
- Calls MCP bridge at `http://127.0.0.1:{PORT}`
- Supports JSON-based tool calls
- Returns only JSON responses (no prose)

---

## 3. MAIN APPLICATION

### Primary Files

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/streamlit_app.py`
**Purpose**: Interactive web UI for ClimateGPT using Streamlit
**Key Features**:
- Question input with Streamlit interface
- Subprocess execution of run_llm.py for LLM inference
- Custom CSS styling with header, Q&A sections
- Response display with error handling
- Integrates with MCP HTTP bridge backend

**Configuration**:
- Uses .env for loading environment variables
- Connects to MCP bridge via HTTP

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/location_resolver.py`
**Purpose**: Intelligently identifies location types (city, state, country) and returns correct database file/column
**Key Features**:
- Resolves location names to their type
- Returns optimal query parameters
- Caching of location lookups
- DuckDB integration for dynamic lookup
- Supports hierarchy: city > admin1 > country

**Return Fields**:
- `location_type`: "city", "admin1", or "country"
- `column_name`: Column to query
- `file_suffix`: File identifier suffix
- `normalized_name`: Normalized location name
- `confidence`: HIGH, MEDIUM, or LOW

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/router.py`
**Purpose**: Route user intent to correct MCP tool and file_id
**Key Functions**:
- `level_to_segment()`: Maps level to segment (city/admin1/country)
- `grain_to_segment()`: Maps grain to temporal segment (month/year)
- `sector_to_prefix()`: Formats sector for file_id
- `route_file_id()`: Creates file_id from intent (e.g., transport-country-year)

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/answer.py`
**Purpose**: Response formatting and summarization
**Key Functions**:
- `ensure_mtco2()`: Converts tonnes to MtCO2 units
- `deterministic_summary()`: Generates deterministic text summary from MCP data

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/baseline_context.py`
**Purpose**: Enriches MCP responses with baseline climate knowledge
**Key Classes**:
- `BaselineContextProvider`: Provides baseline context knowledge
- `PolicyContextAugmenter`: Adds policy context
- `SectorStrategyAugmenter`: Adds sector-specific strategy
- `EducationalContextAugmenter`: Adds educational content

**Features**:
- Enriches MCP data with knowledge-grounded context
- Persona-specific responses (Climate Analyst, Research Scientist, etc.)
- Question element extraction
- Narrative generation combining data + context

#### Additional Utilities
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/intent.py` - Intent parsing
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/fallbacks.py` - Fallback strategies
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/logging.py` - Logging utilities
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/http.py` - HTTP utilities
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/utils/serialization.py` - JSON serialization

---

## 4. TESTING SETUP & TEST FILES

### Test Framework Configuration

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/pytest.ini`
**Configuration**:
```ini
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers --disable-warnings --color=yes --durations=10
markers:
  unit: Unit tests
  integration: Integration tests
  e2e: End-to-end tests
  slow: Slow tests
  network: Network-dependent tests
  database: Database-dependent tests
```

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/pyproject.toml`
**Project Configuration**:
- Name: climategpt
- Version: 0.2.0
- Python: >=3.11, <3.12
- Build backend: hatchling

**Dependencies** (selected):
- mcp>=1.20.0 (Model Context Protocol)
- duckdb>=1.4.1 (Database)
- fastapi==0.117.1 (HTTP)
- streamlit==1.50.0 (UI)
- openai>=2.2.0 (LLM)
- pandas, numpy, geopandas, xarray (Data)

**Dev Dependencies**:
- pytest==8.3.3
- ruff==0.6.9
- black==24.8.0

### Unit Tests Directory

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/tests/test_new_tools.py`
**Purpose**: Tests for Phase 3 MCP tools (entity resolution, caching, etc.)
**Test Coverage**:
- `test_entity_resolution()`: Tests entity normalization and ISO3 code lookup
- `test_cache()`: Tests query cache implementation

**Imported Functions**:
- `_normalize_entity_name()`: Normalizes country/region names
- `_get_iso3_code()`: Looks up ISO3 codes
- `query_cache`: LRU cache object

### Comprehensive Testing Suite

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/testing/test_harness.py`
**Purpose**: Automated test harness for comparative LLM testing
**Features**:
- Tests ClimateGPT against baseline LLMs (e.g., Llama via LM Studio)
- Comprehensive question bank testing
- Configurable test execution
- Result tracking and analysis
- Test result CSV export

**Usage**:
```bash
python test_harness.py                    # Test both systems
python test_harness.py --climategpt-only  # Test only ClimateGPT
python test_harness.py --pilot            # First 10 questions
python test_harness.py --questions 1,2,3  # Specific questions
```

**Configuration**:
- `test_config.json`: Test configuration
- `test_question_bank.json`: 22,155 test questions
- `test_question_bank.csv`: CSV version of question bank
- Test results saved to `test_results/` directory

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/testing/test_10_questions.py`
**Purpose**: Quick smoke test with 10 questions
**Features**:
- Rapid validation of system
- Used for CI/CD pipelines

#### Testing Utilities
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/testing/verify_setup.py` - Verifies system setup
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/testing/extract_ground_truth.py` - Extracts ground truth data
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/testing/analyze_results.py` - Analyzes test results

#### Testing Documentation
- `COMPARATIVE_TESTING_GUIDE.md` - Guide for comparative testing
- `TEST_HARNESS_USAGE.md` - Detailed test harness usage
- `QUESTION_BANK_SUMMARY.md` - Question bank documentation
- `LM_STUDIO_SETUP.md` - LM Studio configuration
- `QUICKSTART.md` - Quick start guide
- `requirements_testing.txt` - Testing dependencies

#### Additional Test Files in docs/
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/docs/test_run_llm_baseline.py` - Baseline LLM tests
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/docs/test_baseline_usage.py` - Baseline usage tests
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/docs/test_mcp_quality.py` - MCP quality tests
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/docs/test_enhanced_mcp.py` - Enhanced MCP tests
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/docs/direct_baseline_test.py` - Direct baseline tests

---

## 5. DATABASE CONFIGURATION

### Database Configuration File

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/utils/config.py`
**Purpose**: Centralized configuration management for ClimateGPT
**Key Configuration Classes**:
- `Config`: Main configuration class

**Configuration Parameters**:

**Environment**:
- `ENVIRONMENT`: production/development (default: production)
- `IS_PRODUCTION`, `IS_DEVELOPMENT`: Boolean flags

**Database**:
- `DB_PATH`: DuckDB file path (default: data/warehouse/climategpt.duckdb)
- `DB_POOL_SIZE`: Connection pool size (default: 10)
- `DB_MAX_CONNECTIONS`: Max connections (default: 20)

**LLM**:
- `LLM_CONCURRENCY_LIMIT`: Max concurrent requests (default: 10)
- `OPENAI_API_KEY`: API authentication (username:password format)
- `MODEL`: Model identifier (default: /cache/climategpt_8b_test)

**Rate Limiting**:
- `RATE_LIMIT_MAX_REQUESTS`: Requests per window (default: 100)
- `RATE_LIMIT_WINDOW_SECONDS`: Time window (default: 60)

**CORS**:
- `ALLOWED_ORIGINS_ENV`: Comma-separated allowed origins
- Auto-defaults to localhost:8501, localhost:3000 in development

**Cache**:
- `CACHE_SIZE`: Max cache entries (default: 1000)
- `CACHE_TTL_SECONDS`: Cache TTL (default: 300)

**Server**:
- `HTTP_HOST`: Server host (default: 0.0.0.0)
- `HTTP_PORT`: Server port (default: 8010)

**Validation**:
- `validate()`: Validates all configuration on import
- Raises errors in production, warnings in development

### Database Analysis Tools

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/analyze_db.py`
**Purpose**: Analyzes DuckDB database structure and contents
**Features**:
- Lists all tables
- Shows row counts per table
- For country_year tables: shows year range and country count
- Quick database health check

### Database Structure

**Expected Tables** (from EDGAR v2024 dataset):
- transport-country-year
- transport-admin1-year
- transport-city-year
- transport-country-month
- transport-admin1-month
- transport-city-month
- (Similar tables for other sectors: energy, industrial, agriculture, waste, etc.)

**Supported Granularities**:
- Geographic: country, admin1 (state/province), city
- Temporal: year, month

---

## 6. ADDITIONAL KEY COMPONENTS

### Pipeline and Processing

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/pipelines/viirs.py`
**Purpose**: VIIRS satellite data processing pipeline

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/process_edgar_complete.py`
**Purpose**: EDGAR dataset processing

### CLI Entry Point

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/src/cli.py`
**Purpose**: Command-line interface for ClimateGPT tasks
**Commands**:
- `viirs_etl`: VIIRS ETL pipeline
- `mcp_viirs`: Start MCP server for VIIRS data

### Configuration Files

#### Sector Configuration
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/scripts/preprocessing/sector_config.py` - Sector definitions
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/scripts/preprocessing/edgar_config.py` - EDGAR configuration

### Middleware

#### `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/middleware/request_tracking.py`
**Purpose**: Request tracking middleware for monitoring

---

## 7. ENVIRONMENT SETUP

### Environment Variables (.env)
```
OPENAI_API_KEY=username:password
OPENAI_BASE_URL=https://erasmus.ai/models/climategpt_8b_test/v1
MODEL=/cache/climategpt_8b_test
PORT=8010
DB_PATH=data/warehouse/climategpt.duckdb
ENVIRONMENT=production
ALLOWED_ORIGINS=http://localhost:8501,http://localhost:3000
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
QUERY_CACHE_TTL_SECONDS=3600
ENABLE_QUERY_CACHE=true
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Startup Scripts
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/run_mcp_server.sh` - MCP server startup
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/run_mcp_dev.sh` - MCP development mode
- `/Users/dharmpratapsingh/Downloads/DataSets_ClimateGPT/start_climategpt.sh` - Full system startup

---

## 8. ARCHITECTURE FLOW

```
User Question (Streamlit UI)
    ↓
Streamlit App (streamlit_app.py)
    ↓
LLM Runner (run_llm.py)
    ├─ Intent Parsing (utils/intent.py)
    ├─ Baseline Context (utils/baseline_context.py)
    └─ Tool Routing (utils/router.py)
    ↓
OpenAI API / Custom LLM
    ↓
Returns JSON Tool Calls
    ↓
HTTP Bridge (mcp_http_bridge.py)
    ├─ Rate Limiting
    ├─ Query Cache
    └─ CORS Middleware
    ↓
MCP Server (mcp_server_stdio.py)
    ├─ Tool Execution
    ├─ Entity Resolution
    ├─ Query Caching
    └─ Manifest Loading
    ↓
DuckDB Database
    └─ EDGAR v2024 Emissions Data
    ↓
Response Data
    ↓
Answer Formatting (utils/answer.py)
    ↓
Response to User
```

---

## 9. KEY DEPENDENCIES

### Core Dependencies
- **mcp** >= 1.20.0: Model Context Protocol implementation
- **duckdb** >= 1.4.1: Embedded database
- **fastapi** == 0.117.1: HTTP framework
- **pydantic** == 2.11.9: Data validation
- **streamlit** == 1.50.0: UI framework
- **openai** >= 2.2.0: LLM API
- **uvicorn[standard]** == 0.37.0: ASGI server

### Data Processing
- **pandas** == 2.3.2: Data manipulation
- **numpy** == 2.3.3: Numerical computing
- **geopandas** == 1.1.1: Geospatial data
- **xarray** == 2025.9.0: Multi-dimensional arrays
- **pyarrow** == 21.0.0: Data format support

---

## Summary

ClimateGPT is a sophisticated climate data Q&A system with:
1. **MCP Server Layer**: TRUE MCP protocol via stdio + HTTP bridge for REST compatibility
2. **LLM Integration**: Tool-based inference with prompt optimization
3. **Web UI**: Streamlit frontend for user interaction
4. **Robust Testing**: Comprehensive test harness for comparative evaluation
5. **Production Configuration**: Centralized config with environment variables
6. **Scalable Database**: DuckDB-based EDGAR emissions warehouse

All components are modular, well-tested, and configured for both development and production environments.
