# ClimateGPT

[![CI Pipeline](https://github.com/DharmpratapSingh/Team-1B-Fusion/actions/workflows/ci.yml/badge.svg)](https://github.com/DharmpratapSingh/Team-1B-Fusion/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-0.2.0-green.svg)](pyproject.toml)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.20.0+-orange.svg)](https://modelcontextprotocol.io)

AI-powered emissions data analysis system for EDGAR v2024 datasets. Query historical CO₂ emissions data through a conversational interface powered by an LLM and MCP (Model Context Protocol) server.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker Deployment](#docker-deployment)
- [Example Queries](#example-queries)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Configuration](#configuration)
  - [Environment Variables](#environment-variables)
- [Testing](#testing)
- [Data Sources](#data-sources)
- [Usage Notes](#usage-notes)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [Development](#development)
- [License](#license)
- [Contributing](#contributing)
- [Support](#support)

## Features

- **Multi-sector emissions data**: Transport, Power Industry, and other EDGAR sectors
- **Geographic granularity**: Country, admin-1 (state/province), and city-level data
- **Temporal analysis**: Monthly and annual data from 2000-2024
- **Conversational interface**: Natural language queries powered by LLM
- **MCP server**: Standardized data access via Model Context Protocol
- **Interactive UI**: Streamlit-based chat interface with persona modes
- **Smart Entity Resolution**: Automatic handling of country/city aliases (USA→United States, NYC→New York, etc.), fuzzy matching for typos, and intelligent geographic level detection
- **Enterprise Security**: SQL injection prevention, input validation, CORS restrictions, and secure credential management
- **High Performance**: Optimized query execution, connection pooling, and 50% reduction in database load

## Quick Start

### Prerequisites

- **Python 3.11** (specifically required - not 3.10 or 3.12)
  - Why 3.11? This version provides the optimal balance of performance and compatibility with our dependencies (DuckDB, GeoPandas, NumPy 2.x)
- **[uv](https://docs.astral.sh/uv/)** - Fast Python package manager and resolver
  - Installation: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Docker** (optional, for containerized deployment)
- **OpenAI API Key** (or compatible LLM endpoint) for conversational interface

### Local Development

1. **Start the MCP bridge + MCP stdio server** (port 8010):

```bash
make serve
```

2. **In a second terminal, start the UI** (port 8501):

```bash
make ui
```

3. Open http://localhost:8501 in your browser

### Docker Deployment

```bash
docker compose up --build
```

This will start both services:
- **server**: HTTP bridge (FastAPI) + true MCP stdio server on port 8010
- **ui**: Streamlit interface on port 8501

## Example Queries

Once the system is running, you can ask questions like:

**Simple Queries:**
- "What were the CO2 emissions from transport in Germany in 2023?"
- "Show me power industry emissions in California for 2022"
- "What are the transport emissions for Paris in 2020?"

**Temporal Analysis:**
- "How have transport emissions in the United States changed from 2000 to 2023?"
- "Compare monthly transport emissions in Beijing between 2022 and 2023"
- "What were the peak emissions months for power industry in Texas in 2023?"

**Comparative Queries:**
- "Compare transport emissions between France and Germany in 2023"
- "Which US state had the highest power industry emissions in 2022?"
- "Compare emissions from transport and power industry in China in 2023"

**Complex Multi-Sector:**
- "Analyze transport and power industry emissions trends in India from 2015 to 2023"
- "What sectors contribute most to emissions in California?"

**Smart Entity Resolution (NEW!):**
The system now intelligently handles various name formats and aliases:
- **Country aliases**: "USA", "US", "America" → "United States of America"
- **State abbreviations**: "CA", "TX", "NY" → "California", "Texas", "New York"
- **City nicknames**: "NYC" → "New York", "LA" → "Los Angeles"
- **Typo correction**: "Califronia" → "California" (fuzzy matching at 80%+ similarity)
- **Auto-level detection**: Automatically determines if you're querying a country, state, or city
- **Intelligent fallback**: If city data unavailable, tries state → country automatically

**Notes:**
- You can now use common aliases like "USA", "UK", "NYC" - the system normalizes them automatically!
- Emissions are in tonnes CO₂ (displayed as MtCO₂ for large values)
- Data covers 2000-2024 with monthly resolution
- Available sectors: transport, power-industry, waste, agriculture, buildings, fuel-exploitation, industrial-combustion, industrial-processes

## Architecture

### MCP Server Stack (`mcp_http_bridge.py` + `mcp_server_stdio.py`)

- `mcp_http_bridge.py`: FastAPI bridge that exposes the legacy HTTP REST surface (`/query`, `/list_files`, etc.) while proxying every request to the real MCP stdio server. Includes CORS security restrictions and configurable origin whitelisting.
- `mcp_server_stdio.py`: The fully featured MCP implementation that speaks the Model Context Protocol over stdio and executes all DuckDB queries. Features include:
  - **Smart Entity Resolution**: Normalizes location names, handles aliases, performs fuzzy matching, and auto-detects geographic levels
  - **Security**: Comprehensive SQL injection prevention with input validation, column name sanitization, and parameterized queries
  - **Performance**: Connection pooling, optimized query execution (no redundant queries), and efficient cursor management
  - **MCP Tools**: 15+ tools including `smart_query_emissions`, `query_emissions`, `calculate_yoy_change`, `get_file_info`, and more

The bridge automatically spawns `mcp_server_stdio.py` on startup and relays JSON-RPC traffic between HTTP clients (UI, automation) and the MCP server. This keeps existing HTTP integrations working while using the canonical MCP runtime under the hood.

### UI (`enhanced_climategpt_with_personas.py`)

Streamlit chat interface with:
- Multiple persona modes (Analyst, Technical, Policy Advisor)
- Chat-first layout with inline controls
- CSV export of query results
- Status indicators and error handling
- Secure credential management (no hardcoded defaults)

## API Reference

The HTTP bridge exposes the following RESTful endpoints on port 8010:

### Query Endpoint

**POST** `/query`

Execute a natural language query against the emissions database.

```bash
curl -X POST http://localhost:8010/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What were transport emissions in Germany in 2023?",
    "assist_mode": "smart",
    "proxy_strategy": "spatial"
  }'
```

**Request Body:**
```json
{
  "question": "string (required)",
  "assist_mode": "smart|lite|off (default: smart)",
  "proxy_strategy": "spatial|random|off (default: spatial)",
  "proxy_max_k": 10,
  "proxy_radius_km": 100
}
```

**Response:**
```json
{
  "answer": "Natural language summary",
  "data": [...],
  "metadata": {
    "intent": {...},
    "datasets_used": [...],
    "query_time_ms": 123
  }
}
```

### List Files Endpoint

**GET** `/list_files`

List all available datasets in the manifest.

```bash
curl http://localhost:8010/list_files
```

**Response:**
```json
{
  "files": [
    {
      "name": "transport_admin0_yearly",
      "description": "Country-level transport emissions (yearly)",
      "path": "data/warehouse/climategpt.duckdb",
      "table_name": "transport_admin0_yearly"
    }
  ]
}
```

### Health Check

**GET** `/health`

Check server status.

```bash
curl http://localhost:8010/health
```

**Response:**
```json
{
  "status": "healthy",
  "mcp_server": "running",
  "version": "0.2.0"
}
```

## Configuration

### Environment Variables

Configure the system using environment variables. Create a `.env` file or export them in your shell:

#### MCP Server Configuration

```bash
# Required
export MCP_MANIFEST_PATH=data/curated-2/manifest_mcp_duckdb.json

# Optional
export PORT=8010                          # HTTP server port (default: 8010)
export MCP_RATE_CAP=60                    # Rate limit: requests per 5 minutes per IP
export MCP_LOG_LEVEL=INFO                 # Logging level: DEBUG|INFO|WARNING|ERROR
```

#### LLM Configuration

```bash
# Required for conversational interface
# IMPORTANT: Must be in "username:password" format for authentication
export OPENAI_API_KEY=username:password   # Your API credentials in username:password format

# Optional
export OPENAI_BASE_URL=https://api.openai.com/v1  # LLM endpoint
export MODEL=gpt-4                        # Model name (gpt-4, gpt-3.5-turbo, etc.)
```

**Security Note:** The system no longer accepts hardcoded credentials. The `OPENAI_API_KEY` environment variable is required and must be in `username:password` format. The application will fail fast with a clear error if credentials are missing or incorrectly formatted.

#### Query Behavior Defaults

```bash
# Assist Mode: how the LLM assists with query interpretation
export ASSIST_DEFAULT=smart               # smart|lite|off (default: smart)
  # smart: Full LLM-powered query understanding
  # lite: Basic query parsing
  # off: Direct SQL only

# Proxy Strategy: how to handle missing admin-1/city data
export PROXY_DEFAULT=spatial              # spatial|random|off (default: spatial)
  # spatial: Find nearby locations with data
  # random: Use random sampling
  # off: No proxy fallback

export PROXY_MAX_K=10                     # Max proxy results to return
export PROXY_RADIUS_KM=100                # Search radius for spatial proxy (km)
```

#### Streamlit UI Configuration

```bash
export STREAMLIT_SERVER_PORT=8501         # UI port (default: 8501)
export STREAMLIT_SERVER_ADDRESS=0.0.0.0   # Bind address
```

#### Security Configuration

```bash
# CORS Origins (comma-separated list of allowed origins)
export ALLOWED_ORIGINS=http://localhost:8501,http://localhost:3000

# Default allows localhost origins only for security
# Add your production domains as needed:
# export ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

**Security Best Practice:** Never use `*` for allowed origins in production. The system now enforces explicit origin whitelisting to prevent unauthorized cross-origin requests.

#### Development & Debugging

```bash
export DEBUG=true                         # Enable debug mode
export LOG_QUERIES=true                   # Log all SQL queries
```

See `docker-compose.yml` for container-specific configuration examples.

## Testing

### Unit & Integration Tests

Run the test suite:

```bash
make test
```

Or with pytest directly:

```bash
uv run pytest -v
```

### LLM Comparative Testing

The system has been tested with multiple LLM backends. Key findings:
- **Default LLM**: 100% success rate, 5.7s average response time (recommended for production)
- **Llama Q5_K_M**: 80% success rate, 10.4s average response time (viable for development/testing)
- All tool calls and natural language summarization working correctly

See `docs/TESTING_RESULTS.md` for detailed comparison results.

For automated LLM testing tools, see the `testing/` directory which includes:
- Test harness with 50 question bank covering all sectors and query types
- Analysis and visualization scripts
- LM Studio setup guides

## Data Sources

This project uses EDGAR (Emissions Database for Global Atmospheric Research) v2024 datasets:
- CO₂ emissions by sector (transport, power industry, etc.)
- Global coverage with spatial resolution
- Monthly temporal resolution (2000-2024)

## Usage Notes

- Use exact country names (e.g., "United States of America" not "USA")
- All emissions values are in tonnes CO₂; large numbers displayed as MtCO₂
- No forecasts or per-capita metrics (by design)
- Queries are limited by rate limiting to prevent abuse

## Troubleshooting

### Common Issues

#### Server Won't Start

**Problem:** `ModuleNotFoundError` or import errors

**Solution:**
```bash
# Ensure dependencies are installed
uv sync

# Or with pip
pip install -r requirements.txt

# Verify Python version
python --version  # Should be 3.11.x
```

**Problem:** Port 8010 already in use

**Solution:**
```bash
# Find and kill the process using port 8010
lsof -ti:8010 | xargs kill -9

# Or change the port
export PORT=8011
make serve
```

#### UI Connection Issues

**Problem:** UI can't connect to MCP server

**Solution:**
```bash
# Verify server is running
curl http://localhost:8010/health

# Check server logs for errors
# Make sure both server and UI are running in separate terminals

# Terminal 1
make serve

# Terminal 2
make ui
```

#### Database Errors

**Problem:** `DuckDB: IO Error: No such file or directory`

**Solution:**
```bash
# Verify database exists
ls -lh data/warehouse/climategpt.duckdb

# Check manifest path
export MCP_MANIFEST_PATH=data/curated-2/manifest_mcp_duckdb.json

# Verify manifest is valid
python -c "import json; print(json.load(open('data/curated-2/manifest_mcp_duckdb.json')))"
```

#### LLM/OpenAI Errors

**Problem:** `AuthenticationError` or `Invalid API key`

**Solution:**
```bash
# Set your API key
export OPENAI_API_KEY=sk-your-actual-key-here

# Or create a .env file
echo "OPENAI_API_KEY=sk-your-key" > .env
```

**Problem:** Rate limit errors from OpenAI

**Solution:**
- Wait a few minutes and retry
- Switch to a different model with higher limits
- Consider using a local LLM (see `testing/LM_STUDIO_SETUP.md`)

#### Docker Issues

**Problem:** Docker build fails

**Solution:**
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker compose build --no-cache

# Check Docker resources (need at least 4GB RAM)
docker stats
```

**Problem:** Container exits immediately

**Solution:**
```bash
# Check container logs
docker compose logs server
docker compose logs ui

# Verify environment variables in docker-compose.yml
```

#### Query Returns No Results

**Problem:** Valid question returns empty data

**Possible causes:**
1. **Country name mismatch**: Use "United States of America" not "USA"
2. **Data not available**: Not all locations have city/admin-1 level data
3. **Time range**: Data is limited to 2000-2024
4. **Sector name**: Use exact sector names (e.g., "power-industry" not "power")

**Solution:**
```bash
# Check available datasets
curl http://localhost:8010/list_files

# Try a simpler query first
curl -X POST http://localhost:8010/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What were transport emissions in Germany in 2023?"}'
```

#### Performance Issues

**Problem:** Slow query responses

**Solution:**
- Check system resources (CPU, RAM, disk I/O)
- Reduce `PROXY_MAX_K` for faster spatial queries
- Use yearly data instead of monthly for large time ranges
- Consider optimizing DuckDB with `PRAGMA threads=4`

### Getting Help

If you encounter issues not covered here:

1. Check the logs in the terminal where you ran `make serve`
2. Enable debug logging: `export MCP_LOG_LEVEL=DEBUG`
3. Review the full documentation in `docs/`
4. Check existing issues on GitHub
5. Create a new issue with:
   - Error message
   - Steps to reproduce
   - Python version (`python --version`)
   - OS and version

## Documentation

Additional documentation is available in the `docs/` folder:
- `docs/QUICK_START.md` - Detailed setup guide
- `docs/SYSTEM_REFERENCE.md` - System architecture and quick reference
- `docs/TESTING_GUIDE.md` - Testing procedures and methodology
- `docs/TESTING_RESULTS.md` - Testing results and LLM comparison findings
- `docs/CI_CD_SETUP_GUIDE.md` - CI/CD deployment
- `docs/README_MCP.md` - MCP protocol details

For automated testing tools and scripts, see the `testing/` directory.

### Recent Improvements Documentation

The following reports document recent enhancements and security improvements:
- `CODE_REVIEW_REPORT.md` - Comprehensive code review and analysis (1,213 lines)
- `SMART_QUERY_GUIDE.md` - Smart entity resolution system user guide
- `FINAL_STATUS.md` - Final status report of all implemented improvements
- `IMPROVEMENTS_SUMMARY.md` - Summary of all fixes and enhancements
- `UNNECESSARY_FILES.md` - Repository cleanup recommendations

**Latest Updates (v0.2.0):**
- ✅ Smart entity resolution with alias normalization and fuzzy matching
- ✅ All P0+P1 security issues resolved (hardcoded credentials removed, CORS hardened)
- ✅ Performance optimizations (50% reduction in database load)
- ✅ Comprehensive SQL injection prevention
- ✅ Enhanced input validation across all query endpoints

## Development

### Project Structure

```
.
├── mcp_http_bridge.py                     # HTTP bridge that wraps the MCP stdio server
├── mcp_server_stdio.py                    # MCP stdio protocol server (source of truth)
├── enhanced_climategpt_with_personas.py   # Streamlit UI
├── run_llm.py                             # LLM integration harness
├── src/
│   └── utils/                             # Core utilities
│       ├── router.py                      # Intent to dataset routing
│       ├── intent.py                      # Intent extraction
│       ├── answer.py                      # Response formatting
│       ├── fallbacks.py                   # Query fallback logic
│       └── http.py                        # HTTP utilities
├── data/
│   ├── curated-2/                         # Processed datasets
│   │   └── manifest_mcp_duckdb.json       # Dataset manifest
│   ├── warehouse/                         # DuckDB databases
│   └── geo/                               # Geographic data
├── testing/                               # LLM testing infrastructure
│   ├── test_harness.py                    # Automated test runner
│   ├── analyze_results.py                 # Results analysis
│   ├── test_question_bank.json            # 50 test questions
│   └── test_results/                      # Test outputs
├── tests/                                 # Unit/integration tests
├── docs/                                  # Documentation
│   ├── QUICK_START.md                     # Setup guide
│   ├── SYSTEM_REFERENCE.md                # Architecture reference
│   ├── TESTING_GUIDE.md                   # Testing procedures
│   └── TESTING_RESULTS.md                 # LLM comparison results
├── Dockerfile.server                      # Server container
├── Dockerfile.ui                          # UI container
├── docker-compose.yml                     # Multi-container setup
├── Makefile                               # Development commands
├── pyproject.toml                         # Dependencies
└── uv.lock                                # Locked dependencies
```

### Dependencies

Managed via `pyproject.toml` with pinned versions for reproducibility:
- FastAPI + Uvicorn (API server)
- Streamlit (UI)
- DuckDB (analytical database)
- OpenAI (LLM integration)
- Pandas, NumPy (data processing)
- GeoPandas, Shapely (spatial operations)

Install all dependencies:

```bash
uv sync
```

## License

This project is currently in development. License information will be added soon.

For questions about licensing, please contact the project maintainers or open an issue on GitHub.

## Contributing

We welcome contributions! To contribute:

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Team-1B-Fusion.git
   cd Team-1B-Fusion
   ```
3. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development Workflow

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Make your changes**:
   - Write clean, documented code
   - Follow the existing code style
   - Add tests for new functionality

3. **Run tests and linting**:
   ```bash
   # Run tests
   make test

   # Run linting
   uv run ruff check .
   uv run black --check .

   # Auto-format code
   uv run black .
   uv run ruff check --fix .
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

   Use conventional commit messages:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `test:` for tests
   - `refactor:` for refactoring
   - `chore:` for maintenance

5. **Push and create a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Quality Standards

- **Python 3.11** compatibility required
- **Type hints** encouraged for new code
- **Docstrings** for all public functions/classes
- **Test coverage** for new features
- **No breaking changes** without discussion

### Areas for Contribution

- 🐛 Bug fixes
- 📚 Documentation improvements
- ✨ New data sources or sectors
- 🔧 Performance optimizations
- 🧪 Additional test coverage
- 🌍 Geographic data expansion
- 🎨 UI/UX improvements

### Code Review Process

1. All PRs require at least one approval
2. CI/CD pipeline must pass (linting, tests, security checks)
3. Documentation must be updated for user-facing changes
4. Maintainers will review within 1-2 weeks

## Support

### Getting Help

- 📖 **Documentation**: Check the `docs/` folder for detailed guides
- 💬 **Issues**: [Open an issue](https://github.com/DharmpratapSingh/Team-1B-Fusion/issues) on GitHub
- 🐛 **Bug Reports**: Use the issue template and include reproduction steps
- 💡 **Feature Requests**: Describe your use case and proposed solution

### Reporting Security Issues

If you discover a security vulnerability, please **DO NOT** open a public issue. Instead, email the maintainers directly or use GitHub's private security reporting feature.

### Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Provide constructive feedback
- Follow the code of conduct (coming soon)

---

**Built with:** Python 3.11 | FastAPI | Streamlit | DuckDB | MCP Protocol

**Data Source:** [EDGAR v2024](https://edgar.jrc.ec.europa.eu/) - Emissions Database for Global Atmospheric Research

**Version:** 0.2.0 | **Status:** Active Development 🚧
