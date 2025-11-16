# ClimateGPT Architecture Documentation

**Version:** 1.0.0
**Last Updated:** 2025-11-16
**Status:** Production Ready

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagrams](#architecture-diagrams)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Performance Characteristics](#performance-characteristics)
7. [Security Architecture](#security-architecture)
8. [Deployment Architecture](#deployment-architecture)

---

## System Overview

ClimateGPT is a production-grade AI-powered emissions data analysis system that provides natural language access to 19.7M rows of EDGAR v2024 climate data through a conversational interface.

**Key Capabilities:**
- Natural language queries via LLM
- Real-time emissions data retrieval
- Multi-sector, multi-geography, multi-temporal analysis
- High-performance database queries (sub-millisecond)
- Enterprise-grade security and observability

---

## Architecture Diagrams

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ClimateGPT System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐         ┌──────────────┐      ┌──────────────┐  │
│  │              │         │              │      │              │  │
│  │  Streamlit   │────────>│ MCP HTTP     │─────>│  MCP stdio   │  │
│  │     UI       │  HTTP   │   Bridge     │ IPC  │    Server    │  │
│  │ (Port 8501)  │<────────│ (Port 8010)  │<─────│   (stdio)    │  │
│  │              │         │              │      │              │  │
│  └──────────────┘         └──────────────┘      └──────┬───────┘  │
│       │                         │                       │          │
│       │                         │                       │          │
│       │                         v                       v          │
│       │                   ┌──────────┐          ┌─────────────┐   │
│       │                   │   Rate   │          │   DuckDB    │   │
│       │                   │  Limiter │          │  Database   │   │
│       │                   └──────────┘          │  (0.86 GB)  │   │
│       │                         │               │ 19.7M rows  │   │
│       │                         │               └─────────────┘   │
│       │                         │                                 │
│       └─────────────────────────┴─────────────────────────────────┘
│                                 │                                   │
│                                 v                                   │
│                         ┌──────────────┐                            │
│                         │   LLM API    │                            │
│                         │  (OpenAI-    │                            │
│                         │ compatible)  │                            │
│                         └──────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Component Breakdown                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Presentation Layer                           │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  enhanced_climategpt_with_personas.py                        │  │   │
│  │  │  - Streamlit UI                                              │  │   │
│  │  │  - Persona-based chat interface                              │  │   │
│  │  │  - Session management                                        │  │   │
│  │  │  - Response rendering                                        │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     │ HTTP REST                             │
│                                     v                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      API Gateway Layer                              │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  mcp_http_bridge.py                                          │  │   │
│  │  │  - FastAPI server                                            │  │   │
│  │  │  - MCP-to-HTTP bridge                                        │  │   │
│  │  │  - Rate limiting middleware                                  │  │   │
│  │  │  - CORS enforcement                                          │  │   │
│  │  │  - Request ID tracking                                       │  │   │
│  │  │  - Error sanitization                                        │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     │ stdio (IPC)                           │
│                                     v                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    Business Logic Layer                            │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  mcp_server_stdio.py                                         │  │   │
│  │  │  - MCP tool definitions (19 tools)                          │  │   │
│  │  │  - Entity normalization                                     │  │   │
│  │  │  - Query building                                           │  │   │
│  │  │  - Query caching (LRU, TTL)                                 │  │   │
│  │  │  - Circuit breaker                                          │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  │                                                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  Shared Modules                                              │  │   │
│  │  │  - shared/entity_normalization.py                           │  │   │
│  │  │  - models/schemas.py (Pydantic)                             │  │   │
│  │  │  - middleware/request_tracking.py                           │  │   │
│  │  │  - utils/config.py                                          │  │   │
│  │  │  - utils/error_handling.py                                  │  │   │
│  │  │  - utils/serialization.py                                   │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                     │                                       │
│                                     │ SQL                                   │
│                                     v                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Data Layer                                     │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  DuckDB Database                                             │  │   │
│  │  │  - 48 tables (8 sectors × 6 table types)                    │  │   │
│  │  │  - 19.7M rows                                                │  │   │
│  │  │  - 83 indexes (sub-ms queries)                               │  │   │
│  │  │  - 2 materialized views                                     │  │   │
│  │  │  - Connection pooling                                       │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
┌──────────┐
│   User   │
└────┬─────┘
     │ "What were USA's transport emissions in 2023?"
     v
┌─────────────────────────────────────────────────────────────┐
│ Streamlit UI (enhanced_climategpt_with_personas.py)         │
│ - Receives user query                                       │
│ - Sends to LLM with tool definitions                        │
└────┬────────────────────────────────────────────────────────┘
     │ HTTP POST /query
     v
┌─────────────────────────────────────────────────────────────┐
│ MCP HTTP Bridge (mcp_http_bridge.py)                        │
│ 1. Rate limiting check                                      │
│ 2. CORS validation                                          │
│ 3. Generate request ID                                      │
│ 4. Forward to MCP stdio                                     │
└────┬────────────────────────────────────────────────────────┘
     │ stdio (IPC)
     v
┌─────────────────────────────────────────────────────────────┐
│ MCP Server (mcp_server_stdio.py)                            │
│ 1. Pydantic validation                                      │
│ 2. Entity normalization: "USA" → "United States of America" │
│ 3. Get ISO3 code: "USA"                                     │
│ 4. Build SQL query                                          │
│ 5. Check query cache                                        │
└────┬────────────────────────────────────────────────────────┘
     │ Cache miss
     │ SQL: SELECT * FROM transport_country_year WHERE iso3='USA' AND year=2023
     v
┌─────────────────────────────────────────────────────────────┐
│ DuckDB Database                                              │
│ 1. Index lookup on (iso3, year)                             │
│ 2. Return result in 0.17ms                                  │
└────┬────────────────────────────────────────────────────────┘
     │ Result: [{emissions_tonnes: 1234567890, ...}]
     v
┌─────────────────────────────────────────────────────────────┐
│ MCP Server (Response Processing)                            │
│ 1. Cache result (TTL: 5 min)                                │
│ 2. Format response                                          │
│ 3. Log with request ID                                      │
└────┬────────────────────────────────────────────────────────┘
     │ JSON response
     v
┌─────────────────────────────────────────────────────────────┐
│ MCP HTTP Bridge (Response)                                  │
│ 1. Add request ID to headers                                │
│ 2. Compress if >1MB                                         │
│ 3. Paginate if >10K rows                                    │
└────┬────────────────────────────────────────────────────────┘
     │ HTTP 200 with data
     v
┌─────────────────────────────────────────────────────────────┐
│ LLM (OpenAI-compatible)                                      │
│ 1. Receives tool call result                                │
│ 2. Generates natural language summary                       │
│ 3. "In 2023, USA's transport emissions were 1.23 GtCO₂"     │
└────┬────────────────────────────────────────────────────────┘
     │ Natural language response
     v
┌──────────┐
│   User   │ Sees formatted answer in chat
└──────────┘
```

### Database Schema Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Database Structure                              │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  8 Sectors                                                             │
│  ├── transport                                                         │
│  ├── power                                                             │
│  ├── waste                                                             │
│  ├── agriculture                                                       │
│  ├── buildings                                                         │
│  ├── fuel_exploitation                                                 │
│  ├── ind_combustion                                                    │
│  └── ind_processes                                                     │
│                                                                        │
│  Each sector has 6 tables:                                             │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │ {sector}_country_month    - Country-level monthly data          │ │
│  │ {sector}_country_year     - Country-level yearly data           │ │
│  │ {sector}_admin1_month     - State/province monthly data         │ │
│  │ {sector}_admin1_year      - State/province yearly data          │ │
│  │ {sector}_city_month       - City-level monthly data             │ │
│  │ {sector}_city_year        - City-level yearly data              │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  Total: 48 tables × 19.7M rows = 0.86 GB                              │
│                                                                        │
│  Indexes (83 total):                                                   │
│  - (iso3, year)           - Fast country lookups (4x faster)           │
│  - (country_name, year)   - Name-based lookups                         │
│  - (admin1_name, year)    - State lookups                              │
│  - (city_name, year)      - City lookups                               │
│  - (year, month)          - Temporal queries                           │
│                                                                        │
│  Materialized Views (2):                                               │
│  - mv_country_total_yearly     - All sectors combined (6,204 rows)     │
│  - mv_top20_countries_yearly   - Top 20 emitters by year (500 rows)   │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Streamlit UI (`enhanced_climategpt_with_personas.py`)

**Purpose:** User-facing chat interface with persona-based responses

**Key Features:**
- Multi-persona support (Scientist, Activist, Analyst, Educator)
- Session state management
- Streaming responses
- Chat history
- Error handling and user feedback

**Dependencies:**
- Streamlit
- requests (HTTP client for MCP bridge)
- LLM client (OpenAI-compatible)

**Port:** 8501

---

### 2. MCP HTTP Bridge (`mcp_http_bridge.py`)

**Purpose:** HTTP REST API gateway that bridges HTTP to MCP stdio protocol

**Key Features:**
- FastAPI server with OpenAPI docs
- Rate limiting (100 req/60s default)
- CORS enforcement (fail-closed)
- Request ID tracking
- Error sanitization
- Response compression
- Health check endpoint

**Endpoints:**
- `GET /health` - Health check
- `POST /tools/{tool_name}` - Execute MCP tool
- `GET /tools` - List available tools

**Port:** 8010

---

### 3. MCP stdio Server (`mcp_server_stdio.py`)

**Purpose:** Core business logic and MCP protocol implementation

**Key Features:**
- 19 MCP tools for data access
- Entity normalization (100+ aliases)
- Query caching (LRU, 5-min TTL)
- Circuit breaker pattern
- ISO3 optimization (4x faster)
- Pydantic validation
- Connection pooling

**Tools:**
- `query_emissions` - Basic emissions query
- `smart_query_emissions` - Auto-resolution query
- `top_emitters` - Ranking queries
- `analyze_trend` - Trend analysis
- `compare_sectors` - Sector comparison
- `compare_geographies` - Geographic comparison
- ...and 13 more

---

### 4. DuckDB Database

**Purpose:** High-performance analytical database

**Specifications:**
- **Size:** 0.86 GB (554 MB data + 364 MB indexes)
- **Rows:** 19,768,748
- **Tables:** 48
- **Indexes:** 83
- **Query Time:** 0.17-1.17ms (average)

**Optimization:**
- Column-store format (fast analytics)
- Connection pooling (10 connections default)
- Indexed lookups (no full table scans)
- Materialized views for common queries

---

## Technology Stack

### Backend
- **Python:** 3.11 (optimal compatibility)
- **FastAPI:** Modern async web framework
- **DuckDB:** High-performance analytical database
- **Pydantic:** Schema validation (v2)
- **MCP SDK:** Model Context Protocol

### Frontend
- **Streamlit:** Interactive UI framework
- **OpenAI SDK:** LLM client (compatible with any OpenAI-like API)

### Infrastructure
- **Docker:** Containerization
- **Docker Compose:** Multi-container orchestration
- **uv:** Fast Python package manager

### Development
- **mypy:** Static type checking
- **pytest:** Testing framework
- **GitHub Actions:** CI/CD

---

## Performance Characteristics

### Query Performance

| Operation | Before Optimization | After Optimization | Improvement |
|-----------|--------------------|--------------------|-------------|
| Country-year lookup | 200-1000ms | 0.17-1.17ms | **20-200x faster** |
| City-month lookup | 500-2000ms | 0.5-2ms | **100-1000x faster** |
| Large result set (10K rows) | 5000ms | 500ms (with streaming) | **10x faster** |
| Compressed response | N/A | 83% size reduction | **N/A** |

### Caching

- **Cache Hit Rate:** 50%+ (typical workload)
- **Cache Size:** 1000 entries (configurable)
- **TTL:** 300 seconds / 5 minutes
- **Storage:** In-memory LRU

### Scalability

- **Concurrent Users:** 100+ (with default settings)
- **Requests/Second:** 50+ (rate limited to prevent abuse)
- **Database Connections:** 10-20 (configurable pool)
- **LLM Concurrency:** 10 (configurable)

---

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────┐
│                  Security Layers                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer 1: Network Security                              │
│  ├── CORS whitelisting (fail-closed)                    │
│  ├── Rate limiting (100 req/60s)                        │
│  └── HTTPS enforcement (production)                     │
│                                                         │
│  Layer 2: Authentication                                │
│  ├── API key validation (username:password format)     │
│  ├── No hardcoded credentials                          │
│  └── Environment variable enforcement                   │
│                                                         │
│  Layer 3: Input Validation                              │
│  ├── Pydantic schema validation                        │
│  ├── SQL injection prevention                          │
│  ├── Parameter sanitization                            │
│  └── Type checking                                     │
│                                                         │
│  Layer 4: Error Handling                                │
│  ├── Production-safe error messages                    │
│  ├── No SQL query exposure                             │
│  ├── No stack trace exposure                           │
│  └── Request ID for tracing                            │
│                                                         │
│  Layer 5: Observability                                 │
│  ├── Request ID tracking                               │
│  ├── Comprehensive logging                             │
│  ├── Error monitoring                                  │
│  └── Audit trail                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Security Controls

| Control | Implementation | Status |
|---------|----------------|--------|
| **SQL Injection** | Parameterized queries, column validation | ✅ Implemented |
| **Code Injection** | No eval(), pandas.eval() only | ✅ Implemented |
| **CORS** | Explicit origin whitelist, no wildcards | ✅ Implemented |
| **Rate Limiting** | 100 req/60s per IP | ✅ Implemented |
| **Error Messages** | Sanitized in production | ✅ Implemented |
| **Credentials** | Environment variables only | ✅ Implemented |
| **Circuit Breaker** | Thread-safe implementation | ✅ Implemented |
| **Input Validation** | Pydantic models | ✅ Implemented |

---

## Deployment Architecture

### Docker Compose Deployment

```
┌─────────────────────────────────────────────────────────┐
│              Docker Compose Setup                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Container: climategpt-server                   │   │
│  │  Image: python:3.11                             │   │
│  │  Ports: 8010:8010                               │   │
│  │  Services:                                      │   │
│  │  - MCP HTTP Bridge (FastAPI)                    │   │
│  │  - MCP stdio Server                             │   │
│  │  Volumes:                                       │   │
│  │  - ./data:/app/data (database)                  │   │
│  │  Environment:                                   │   │
│  │  - OPENAI_API_KEY                               │   │
│  │  - ALLOWED_ORIGINS                              │   │
│  │  - DB_POOL_SIZE=15                              │   │
│  └─────────────────────────────────────────────────┘   │
│                           │                             │
│                           │ Network: climategpt-network │
│                           │                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Container: climategpt-ui                       │   │
│  │  Image: python:3.11                             │   │
│  │  Ports: 8501:8501                               │   │
│  │  Services:                                      │   │
│  │  - Streamlit UI                                 │   │
│  │  Environment:                                   │   │
│  │  - MCP_BRIDGE_URL=http://server:8010           │   │
│  │  - OPENAI_API_KEY                               │   │
│  │  Depends on: climategpt-server                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Production Deployment (Kubernetes - Recommended)

```
┌─────────────────────────────────────────────────────────┐
│           Kubernetes Deployment                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Ingress Controller                             │   │
│  │  - HTTPS termination                            │   │
│  │  - Load balancing                               │   │
│  │  - Rate limiting                                │   │
│  └────────┬────────────────────────────────────────┘   │
│           │                                             │
│           v                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Service: climategpt-server                     │   │
│  │  Type: ClusterIP                                │   │
│  │  Port: 8010                                     │   │
│  └────────┬────────────────────────────────────────┘   │
│           │                                             │
│           v                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Deployment: climategpt-server                  │   │
│  │  Replicas: 3                                    │   │
│  │  Resources:                                     │   │
│  │  - CPU: 1000m                                   │   │
│  │  - Memory: 2Gi                                  │   │
│  │  PVC: climategpt-db-pvc (10Gi)                  │   │
│  │  ConfigMap: climategpt-config                   │   │
│  │  Secrets: climategpt-secrets                    │   │
│  └─────────────────────────────────────────────────┘   │
│           │                                             │
│           v                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Service: climategpt-ui                         │   │
│  │  Type: ClusterIP                                │   │
│  │  Port: 8501                                     │   │
│  └────────┬────────────────────────────────────────┘   │
│           │                                             │
│           v                                             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Deployment: climategpt-ui                      │   │
│  │  Replicas: 2                                    │   │
│  │  Resources:                                     │   │
│  │  - CPU: 500m                                    │   │
│  │  - Memory: 1Gi                                  │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Monitoring and Observability

### Request Tracing

```
User Request → [Request ID: a3d4f567-...] → All logs tagged
├── [a3d4f567] Streamlit: Received user query
├── [a3d4f567] HTTP Bridge: Rate limit check PASS
├── [a3d4f567] HTTP Bridge: CORS validation PASS
├── [a3d4f567] MCP Server: Entity normalization: USA → United States of America
├── [a3d4f567] MCP Server: Cache MISS for query
├── [a3d4f567] MCP Server: Database query executed in 0.17ms
├── [a3d4f567] MCP Server: Result cached
└── [a3d4f567] HTTP Bridge: Response sent (compressed)
```

### Logging Levels

- **DEBUG:** Entity normalization, cache hits/misses, SQL queries
- **INFO:** Request lifecycle, configuration, performance metrics
- **WARNING:** Rate limit approaches, cache evictions, slow queries
- **ERROR:** Validation failures, database errors, LLM failures
- **CRITICAL:** Configuration failures, startup errors

---

## Scalability Considerations

### Horizontal Scaling

**Can scale:**
- ✅ MCP HTTP Bridge (stateless, multiple replicas)
- ✅ Streamlit UI (stateless, multiple replicas)
- ⚠️ MCP stdio Server (stateful cache, needs distributed cache for multi-instance)

**Cannot easily scale:**
- ❌ DuckDB (single-file database, read replicas possible)

### Performance Tuning

**Database:**
- Increase `DB_POOL_SIZE` for more concurrent queries
- Add more indexes for specific query patterns
- Create materialized views for frequent aggregations

**Application:**
- Increase `LLM_CONCURRENCY_LIMIT` for better throughput
- Increase `CACHE_SIZE` for better hit rates
- Tune `CACHE_TTL_SECONDS` based on data freshness requirements

**Infrastructure:**
- Use load balancer for HTTP Bridge
- Add CDN for static assets
- Implement distributed caching (Redis)

---

## Future Architecture Enhancements

### Phase 6 (Planned)
- Distributed caching (Redis/Memcached)
- Read replicas for database
- Metrics export (Prometheus)
- Distributed tracing (OpenTelemetry)
- GraphQL API

### Phase 7 (Planned)
- Event streaming (Kafka)
- Real-time data updates
- ML-based query optimization
- Multi-tenancy support

---

## References

- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [DuckDB Documentation](https://duckdb.org)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Pydantic Documentation](https://docs.pydantic.dev)

---

**Document Version:** 1.0.0
**Maintained By:** ClimateGPT Team
**Last Review:** 2025-11-16
