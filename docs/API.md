# ClimateGPT API Documentation

**Version:** 0.3.0
**Base URL:** `http://localhost:8010` (development) or `https://your-domain.com/api` (production)
**Protocol:** REST + MCP (Model Context Protocol)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Rate Limiting](#rate-limiting)
4. [Error Handling](#error-handling)
5. [Core Endpoints](#core-endpoints)
6. [MCP Tools](#mcp-tools)
7. [Request/Response Examples](#requestresponse-examples)
8. [SDKs and Client Libraries](#sdks-and-client-libraries)

---

## Overview

ClimateGPT provides two API interfaces:

1. **HTTP REST API** (`mcp_http_bridge.py`) - For HTTP clients
2. **MCP stdio Protocol** (`mcp_server_stdio.py`) - For MCP-compatible LLM clients

### API Features

- ✅ **19 MCP Tools** for emissions data access
- ✅ **Automatic input validation** (Pydantic schemas)
- ✅ **Request ID tracking** for debugging
- ✅ **Sub-millisecond query performance**
- ✅ **Smart entity resolution** (handles aliases, typos)
- ✅ **Rate limiting** (100 req/60s default)
- ✅ **CORS support** (configurable)
- ✅ **Compression** for large responses

---

## Authentication

### API Key Authentication

Currently uses Basic Auth with username:password format.

**Header:**
```
Authorization: Basic base64(username:password)
```

**Environment Variable:**
```bash
export OPENAI_API_KEY=username:password
```

**Note:** For production, use proper OAuth2 or API key management.

---

## Rate Limiting

### Default Limits

- **Max Requests:** 100 per 60 seconds per IP
- **Window:** Sliding window (not fixed)
- **Response Code:** 429 Too Many Requests

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1234567890
Retry-After: 42
```

### Configure Limits

```bash
export RATE_LIMIT_MAX_REQUESTS=500
export RATE_LIMIT_WINDOW_SECONDS=60
```

---

## Error Handling

### Error Response Format

```json
{
  "error": "Error message",
  "error_code": "VALIDATION_ERROR",
  "request_id": "a3d4f567-8901-2345-6789-abcdef012345",
  "details": {
    "field": "year",
    "message": "Year must be between 2000 and 2024"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| **200** | OK | Request successful |
| **400** | Bad Request | Invalid input parameters |
| **429** | Too Many Requests | Rate limit exceeded |
| **500** | Internal Server Error | Server error (check logs with request_id) |
| **503** | Service Unavailable | Database connection failed |

### Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `ENTITY_NOT_FOUND` | Country/city not found in database |
| `DATABASE_ERROR` | Database query failed |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Unexpected server error |

---

## Core Endpoints

### Health Check

**GET** `/health`

Check API health and status.

**Response:**
```json
{
  "status": "healthy",
  "version": "0.3.0",
  "uptime": 3600,
  "database": "connected",
  "cache_size": 432,
  "cache_hit_rate": 0.67
}
```

### List Tools

**GET** `/tools`

List all available MCP tools.

**Response:**
```json
{
  "tools": [
    {
      "name": "query_emissions",
      "description": "Query emissions data by sector, year, location",
      "parameters": {
        "sector": "string (required)",
        "year": "integer 2000-2024 (required)",
        "country_name": "string (optional)"
      }
    },
    ...
  ]
}
```

### Execute Tool

**POST** `/tools/{tool_name}`

Execute a specific MCP tool.

**Path Parameters:**
- `tool_name` - Name of the tool to execute

**Request Body:**
```json
{
  "sector": "transport",
  "year": 2023,
  "country_name": "USA"
}
```

**Response:**
```json
{
  "data": [...],
  "total_rows": 12,
  "query_time_ms": 0.42
}
```

---

## MCP Tools

### 1. query_emissions

Basic emissions query with explicit parameters.

**Parameters:**
```typescript
{
  sector: "transport" | "power" | "waste" | "agriculture" | "buildings" | "fuel_exploitation" | "ind_combustion" | "ind_processes",
  year: number,  // 2000-2024
  month?: number,  // 1-12 (optional)
  country_name?: string,
  admin1_name?: string,  // State/province
  city_name?: string,
  max_rows?: number  // Default: 10000
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8010/tools/query_emissions \
  -H "Content-Type: application/json" \
  -d '{
    "sector": "transport",
    "year": 2023,
    "country_name": "United States of America"
  }'
```

**Example Response:**
```json
{
  "data": [
    {
      "year": 2023,
      "month": null,
      "emissions_tonnes": 1567890123.45,
      "country_name": "United States of America",
      "iso3": "USA"
    }
  ],
  "total_rows": 1,
  "truncated": false,
  "query_time_ms": 0.17
}
```

---

### 2. smart_query_emissions

Intelligent query with automatic entity resolution and fallback.

**Parameters:**
```typescript
{
  sector: string,
  year: number,
  month?: number,
  entity_name: string  // Auto-resolves country/state/city
}
```

**Features:**
- Handles aliases: "USA" → "United States of America"
- Fuzzy matching: "Califrnia" → "California"
- Auto-level detection: Determines if country/state/city
- Intelligent fallback: City → State → Country

**Example:**
```bash
curl -X POST http://localhost:8010/tools/smart_query_emissions \
  -H "Content-Type: application/json" \
  -d '{
    "sector": "transport",
    "year": 2023,
    "entity_name": "NYC"
  }'
```

---

### 3. top_emitters

Find top N emitters by sector and year.

**Parameters:**
```typescript
{
  sector: string,
  year: number,
  limit?: number,  // 1-50, default: 10
  geographic_level?: "country" | "admin1" | "city"  // Default: "country"
}
```

**Example:**
```bash
curl -X POST http://localhost:8010/tools/top_emitters \
  -H "Content-Type: application/json" \
  -d '{
    "sector": "transport",
    "year": 2023,
    "limit": 5,
    "geographic_level": "country"
  }'
```

**Response:**
```json
{
  "sector": "transport",
  "year": 2023,
  "geographic_level": "country",
  "emitters": [
    {
      "rank": 1,
      "country": "China",
      "iso3": "CHN",
      "emissions_tonnes": 2345678901.23,
      "emissions_mtco2": 2345.68
    },
    {
      "rank": 2,
      "country": "United States of America",
      "iso3": "USA",
      "emissions_tonnes": 1567890123.45,
      "emissions_mtco2": 1567.89
    },
    ...
  ]
}
```

---

### 4. analyze_trend

Analyze emissions trends over time with growth rates.

**Parameters:**
```typescript
{
  entity_name: string,
  sector: string,
  start_year: number,
  end_year: number
}
```

**Example:**
```bash
curl -X POST http://localhost:8010/tools/analyze_trend \
  -H "Content-Type: application/json" \
  -d '{
    "entity_name": "China",
    "sector": "transport",
    "start_year": 2018,
    "end_year": 2023
  }'
```

**Response:**
```json
{
  "entity": "China",
  "sector": "transport",
  "period": "2018-2023",
  "pattern": "increasing",
  "total_change_pct": 23.5,
  "total_change_tonnes": 450000000.0,
  "cagr_pct": 4.3,
  "start_emissions": 1900000000.0,
  "end_emissions": 2350000000.0,
  "yoy_growth": [
    {"year": 2019, "growth_pct": 4.2},
    {"year": 2020, "growth_pct": -5.1},
    {"year": 2021, "growth_pct": 8.7},
    {"year": 2022, "growth_pct": 3.9},
    {"year": 2023, "growth_pct": 4.5}
  ],
  "yearly_data": [...]
}
```

---

### 5. compare_sectors

Compare emissions across multiple sectors for a location.

**Parameters:**
```typescript
{
  entity_name: string,
  sectors: string[],  // 2-8 sectors
  year: number
}
```

**Example:**
```bash
curl -X POST http://localhost:8010/tools/compare_sectors \
  -H "Content-Type: application/json" \
  -d '{
    "entity_name": "Germany",
    "sectors": ["transport", "power", "waste"],
    "year": 2023
  }'
```

**Response:**
```json
{
  "entity": "Germany",
  "year": 2023,
  "total_emissions_tonnes": 500000000.0,
  "total_emissions_mtco2": 500.0,
  "sectors": [
    {
      "sector": "power",
      "rank": 1,
      "emissions_tonnes": 250000000.0,
      "emissions_mtco2": 250.0,
      "percentage": 50.0
    },
    {
      "sector": "transport",
      "rank": 2,
      "emissions_tonnes": 180000000.0,
      "emissions_mtco2": 180.0,
      "percentage": 36.0
    },
    {
      "sector": "waste",
      "rank": 3,
      "emissions_tonnes": 70000000.0,
      "emissions_mtco2": 70.0,
      "percentage": 14.0
    }
  ]
}
```

---

### 6. compare_geographies

Compare emissions across multiple countries/regions.

**Parameters:**
```typescript
{
  entities: string[],  // 2-20 entities
  sector: string,
  year: number
}
```

**Example:**
```bash
curl -X POST http://localhost:8010/tools/compare_geographies \
  -H "Content-Type: application/json" \
  -d '{
    "entities": ["USA", "China", "India"],
    "sector": "transport",
    "year": 2023
  }'
```

**Response:**
```json
{
  "sector": "transport",
  "year": 2023,
  "total_emissions_tonnes": 5000000000.0,
  "total_emissions_mtco2": 5000.0,
  "comparison": [
    {
      "entity": "China",
      "geographic_level": "country",
      "rank": 1,
      "emissions_tonnes": 2350000000.0,
      "emissions_mtco2": 2350.0,
      "percentage": 47.0
    },
    {
      "entity": "United States of America",
      "geographic_level": "country",
      "rank": 2,
      "emissions_tonnes": 1570000000.0,
      "emissions_mtco2": 1570.0,
      "percentage": 31.4
    },
    {
      "entity": "India",
      "geographic_level": "country",
      "rank": 3,
      "emissions_tonnes": 1080000000.0,
      "emissions_mtco2": 1080.0,
      "percentage": 21.6
    }
  ]
}
```

---

## Additional Tools

### 7-19. Other MCP Tools

For complete list of all 19 tools, use:

```bash
curl http://localhost:8010/tools
```

Additional tools include:
- `list_countries` - Get all available countries
- `list_sectors` - Get all available sectors
- `list_years` - Get available year range
- `get_coverage` - Get geographic coverage for sector
- ...and 11 more

---

## Request/Response Examples

### Pagination

For large datasets (>1000 rows):

**Request:**
```bash
curl -X POST http://localhost:8010/tools/query_emissions \
  -H "Content-Type: application/json" \
  -d '{
    "sector": "transport",
    "year": 2023,
    "max_rows": 100
  }'
```

**Response:**
```json
{
  "data": [...],  // First 100 rows
  "total_rows": 100,
  "truncated": true,
  "pagination": {
    "page": 1,
    "page_size": 100,
    "total_pages": 150,
    "has_next": true
  }
}
```

### Compression

For responses >1MB, request gzip compression:

**Request:**
```bash
curl -X POST http://localhost:8010/tools/query_emissions \
  -H "Content-Type: application/json" \
  -H "Accept-Encoding: gzip" \
  -d '{...}'
```

**Response Headers:**
```
Content-Encoding: gzip
Content-Length: 12345  # Compressed size
X-Original-Size: 98765  # Original size
```

---

## SDKs and Client Libraries

### Python

```python
import requests

class ClimateGPTClient:
    def __init__(self, base_url="http://localhost:8010"):
        self.base_url = base_url
        self.session = requests.Session()

    def query_emissions(self, sector, year, country_name=None):
        """Query emissions data"""
        response = self.session.post(
            f"{self.base_url}/tools/query_emissions",
            json={
                "sector": sector,
                "year": year,
                "country_name": country_name
            }
        )
        response.raise_for_status()
        return response.json()

    def top_emitters(self, sector, year, limit=10):
        """Get top emitters"""
        response = self.session.post(
            f"{self.base_url}/tools/top_emitters",
            json={
                "sector": sector,
                "year": year,
                "limit": limit
            }
        )
        response.raise_for_status()
        return response.json()

# Usage
client = ClimateGPTClient()
result = client.query_emissions("transport", 2023, "USA")
print(result)
```

### JavaScript/TypeScript

```typescript
class ClimateGPTClient {
  private baseUrl: string;

  constructor(baseUrl: string = "http://localhost:8010") {
    this.baseUrl = baseUrl;
  }

  async queryEmissions(params: {
    sector: string;
    year: number;
    country_name?: string;
  }) {
    const response = await fetch(`${this.baseUrl}/tools/query_emissions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  }

  async topEmitters(params: {
    sector: string;
    year: number;
    limit?: number;
  }) {
    const response = await fetch(`${this.baseUrl}/tools/top_emitters`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(params),
    });

    return await response.json();
  }
}

// Usage
const client = new ClimateGPTClient();
const result = await client.queryEmissions({
  sector: "transport",
  year: 2023,
  country_name: "USA",
});
console.log(result);
```

### cURL Examples

See individual tool documentation above for cURL examples.

---

## OpenAPI/Swagger Documentation

Interactive API documentation available at:

**URL:** `http://localhost:8010/docs`

Features:
- Try out endpoints in browser
- View request/response schemas
- Download OpenAPI spec (JSON)

**Alternative:** ReDoc documentation at `http://localhost:8010/redoc`

---

## Best Practices

### Performance

1. **Use ISO3 codes when possible** (4x faster):
   ```json
   {"country_name": "USA"}  // Faster than "United States of America"
   ```

2. **Query yearly tables when month not needed** (12x fewer rows):
   ```json
   {"year": 2023}  // Not {"year": 2023, "month": null}
   ```

3. **Limit result sets:**
   ```json
   {"max_rows": 1000}  // Don't fetch all data at once
   ```

4. **Use smart tools for better UX:**
   ```json
   {"tool": "smart_query_emissions"}  // Handles aliases automatically
   ```

### Error Handling

1. **Always check status code:**
   ```python
   response.raise_for_status()  # Raises exception on 4xx/5xx
   ```

2. **Use request_id for debugging:**
   ```python
   if response.status_code != 200:
       request_id = response.json().get("request_id")
       print(f"Error - Request ID: {request_id}")
   ```

3. **Implement retry logic with backoff:**
   ```python
   from tenacity import retry, wait_exponential, stop_after_attempt

   @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
   def query_with_retry(client, ...):
       return client.query_emissions(...)
   ```

### Security

1. **Use HTTPS in production**
2. **Store API keys securely** (not in code)
3. **Validate input on client side** (faster feedback)
4. **Implement rate limiting on client** (prevent 429 errors)

---

## Changelog

### v0.3.0 (2025-11-16)

- ✅ Added Pydantic validation for all tools
- ✅ Added request ID tracking
- ✅ Added compression for large responses
- ✅ Added pagination support
- ✅ Improved error messages

### v0.2.0 (2025-01-16)

- ✅ Added 4 new analytical tools (top_emitters, analyze_trend, etc.)
- ✅ Added query caching (5-min TTL)
- ✅ Added materialized views
- ✅ Improved entity resolution

### v0.1.0 (2025-01-10)

- ✅ Initial release
- ✅ 15 MCP tools
- ✅ Basic HTTP bridge
- ✅ Rate limiting

---

## Support

- **Documentation:** https://github.com/DharmpratapSingh/Team-1B-Fusion/tree/main/docs
- **Issues:** https://github.com/DharmpratapSingh/Team-1B-Fusion/issues
- **API Status:** http://localhost:8010/health

---

**Document Version:** 1.0.0
**API Version:** 0.3.0
**Last Updated:** 2025-11-16
