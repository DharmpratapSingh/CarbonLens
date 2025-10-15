# ClimateGPT - Multi-Sector Emissions Analysis System

A comprehensive AI-powered system for analyzing global CO₂ emissions across transport and power industry sectors using EDGAR v2024 data.

## 🌍 Overview

ClimateGPT is an advanced analytical system that provides natural language querying capabilities for global emissions data. It combines Large Language Models (LLMs) with a high-performance DuckDB database to deliver fast, accurate insights into CO₂ emissions patterns across different sectors, countries, and time periods.

### Key Features

- **Multi-Sector Analysis**: Transport and Power Industry emissions data
- **Natural Language Queries**: Ask questions in plain English
- **High-Performance Database**: DuckDB backend for 10-100x faster queries
- **Multiple Geographic Levels**: Country, Admin1 (state/province), and City analysis
- **Temporal Analysis**: Annual and monthly data from 2000-2023
- **Interactive Web Interface**: Streamlit-based UI with visualizations
- **RESTful API**: MCP server for programmatic access

## 📊 Data Sources

### EDGAR v2024 Datasets
- **Transport Sector**: Road, rail, ship, and aviation emissions
- **Power Industry**: Power and heat generation plant emissions
- **Spatial Resolution**: 0.1° grid cells
- **Temporal Coverage**: 2000-2023 (24 years)
- **Geographic Coverage**: Global (206 countries, 7,160+ cities)

### Data Quality
- **100% Quality Pass Rate**: All datasets pass comprehensive quality checks
- **Clean ISO3 Codes**: Standardized 3-letter country codes
- **Validated Names**: Proper country, admin1, and city names
- **No Missing Values**: Complete dataset with no null entries
- **Optimized Schema**: Clean, consistent data structure

## 🏗️ System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Streamlit UI  │    │   MCP Server    │    │   DuckDB        │
│                 │◄──►│   (FastAPI)     │◄──►│   Database      │
│ • Chat Interface│    │                 │    │                 │
│ • Visualizations│    │ • REST API      │    │ • 9 Tables      │
│ • Query Builder │    │ • Query Engine  │    │ • 2.9M+ Rows    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   LLM Backend   │
                    │                 │
                    │ • OpenAI API    │
                    │ • Tool Calling  │
                    │ • Response Gen  │
                    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- OpenAI API key (for LLM functionality)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd DataSets_ClimateGPT
   ```

2. **Install dependencies using uv**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your OpenAI API key
   ```

4. **Start the system**
   ```bash
   # Terminal 1: Start MCP Server
   uv run python mcp_server.py
   
   # Terminal 2: Start Streamlit UI
   uv run streamlit run climategpt_streamlit_app.py --server.port 8501
   ```

5. **Access the application**
   - Open http://localhost:8501 in your browser
   - Start asking questions about emissions data!

## 📁 Project Structure

```
DataSets_ClimateGPT/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project configuration
├── .env.example                       # Environment variables template
├── docker-compose.yml                 # Docker configuration
├── Dockerfile                         # Docker image definition
│
├── data/                              # Data directory
│   ├── curated/                       # Processed datasets
│   │   ├── country-year/              # Country-level annual data
│   │   ├── admin1-year/               # Admin1-level annual data
│   │   ├── city-year/                 # City-level annual data
│   │   ├── power-country-year/        # Power industry country data
│   │   ├── power-admin1-year/         # Power industry admin1 data
│   │   ├── power-city-year/           # Power industry city data
│   │   ├── power-monthly/             # Power industry monthly data
│   │   └── manifest_mcp_duckdb.json   # Database manifest
│   ├── geo/                           # Geographic boundary files
│   │   ├── ne_10m_admin_0_countries/  # Country boundaries
│   │   ├── ne_10m_admin_1_states_provinces/ # Admin1 boundaries
│   │   └── GHS_UCDB_GLOBE_R2024A_V1_1/ # City boundaries
│   └── warehouse/                     # Database files
│       └── climategpt.duckdb          # Main DuckDB database
│
├── src/                               # Source code
│   ├── cli.py                         # Command-line interface
│   └── pipelines/                     # Data processing pipelines
│
├── mcp_server.py                      # MCP server (FastAPI)
├── climategpt_streamlit_app.py        # Streamlit web interface
├── aggregate_power_industry.py        # Power industry data aggregation
├── create_power_monthly.py            # Monthly data generation
├── add_expanded_datasets.py           # Dataset expansion utilities
└── run_llm.py                         # LLM runner script
```

## 🗄️ Database Schema

### Tables Overview

| Table | Description | Rows | Columns |
|-------|-------------|------|---------|
| `transport_country_year` | Transport emissions by country (annual) | 5,371 | 5 |
| `transport_admin1_year` | Transport emissions by admin1 (annual) | 57,696 | 7 |
| `transport_city_year` | Transport emissions by city (annual) | 244,847 | 8 |
| `power_country_year` | Power industry emissions by country (annual) | 4,802 | 5 |
| `power_admin1_year` | Power industry emissions by admin1 (annual) | 49,793 | 7 |
| `power_city_year` | Power industry emissions by city (annual) | 147,082 | 8 |
| `power_country_month` | Power industry emissions by country (monthly) | 57,624 | 6 |
| `power_admin1_month` | Power industry emissions by admin1 (monthly) | 597,516 | 8 |
| `power_city_month` | Power industry emissions by city (monthly) | 1,764,984 | 9 |

### Common Schema

**Country Level:**
- `iso3`: 3-letter country code
- `country_name`: Full country name
- `year`: Year (2000-2023)
- `emissions_tonnes`: Emissions in tonnes CO₂
- `MtCO2`: Emissions in megatonnes CO₂

**Admin1 Level:**
- All country fields plus:
- `admin1_geoid`: Admin1 geographic ID
- `admin1_name`: Admin1 name (state/province)

**City Level:**
- All admin1 fields plus:
- `city_id`: City identifier
- `city_name`: City name

**Monthly Data:**
- All annual fields plus:
- `month`: Month (1-12)

## 🔧 API Reference

### MCP Server Endpoints

#### `GET /list_files`
Returns available datasets and their metadata.

**Response:**
```json
[
  {
    "file_id": "transport-country-year",
    "name": "Transport Emissions by Country (Annual)",
    "description": "Annual transport sector CO2 emissions by country",
    "engine": "duckdb",
    "path": "duckdb://data/warehouse/climategpt.duckdb#transport_country_year",
    "semantics": {
      "source": "EDGAR v2024 transport",
      "units": ["tonnes CO2"],
      "spatial_resolution": "country",
      "temporal_resolution": "annual"
    }
  }
]
```

#### `POST /query`
Query datasets with filtering, sorting, and aggregation.

**Request:**
```json
{
  "file_id": "transport-country-year",
  "select": ["country_name", "year", "MtCO2"],
  "where": {"year": 2020},
  "order_by": "MtCO2 DESC",
  "limit": 10
}
```

**Response:**
```json
{
  "rows": [
    {
      "country_name": "United States of America",
      "year": 2020,
      "MtCO2": 1481.68
    }
  ],
  "row_count": 1,
  "meta": {
    "units": ["tonnes CO2"],
    "source": "EDGAR v2024 transport",
    "table_id": "transport-country-year"
  }
}
```

#### `GET /get_schema/{file_id}`
Get detailed schema information for a dataset.

#### `POST /metrics/yoy`
Calculate year-over-year growth metrics.

## 💬 Example Queries

### Natural Language Examples

**Transport Sector:**
- "What are the top 10 countries by transport emissions in 2020?"
- "Show me transport emissions trends for China from 2015 to 2023"
- "Which US states have the highest transport emissions?"

**Power Industry:**
- "Compare power industry emissions between China and the US"
- "What are the monthly power emissions patterns for India?"
- "Which cities have the highest power plant emissions?"

**Multi-Sector Analysis:**
- "Compare transport vs power emissions globally"
- "Which sector contributes more to total emissions in Europe?"
- "Show me the correlation between transport and power emissions by country"

### SQL Examples

```sql
-- Top countries by transport emissions 2020
SELECT country_name, MtCO2 
FROM transport_country_year 
WHERE year = 2020 
ORDER BY MtCO2 DESC 
LIMIT 10;

-- Multi-sector comparison
SELECT 
  t.country_name,
  t.MtCO2 as transport_MtCO2,
  p.MtCO2 as power_MtCO2,
  (t.MtCO2 + p.MtCO2) as total_MtCO2
FROM transport_country_year t
JOIN power_country_year p ON t.iso3 = p.iso3 AND t.year = p.year
WHERE t.year = 2020
ORDER BY total_MtCO2 DESC
LIMIT 10;
```

## 🎨 Web Interface Features

### Streamlit App Capabilities

- **Chat Interface**: Natural language conversation with ClimateGPT
- **Query Builder**: Visual interface for constructing queries
- **Data Visualization**: Interactive charts and graphs
- **Export Functionality**: Download results as CSV/JSON
- **Conversation History**: Save and manage chat sessions
- **Example Queries**: Pre-built queries for common analyses

### Visualization Types

- **Line Charts**: Time series trends
- **Bar Charts**: Country/region comparisons
- **Area Charts**: Cumulative emissions
- **Pie Charts**: Sector contributions
- **Heatmaps**: Geographic patterns

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# OpenAI Configuration
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_api_key_here
MODEL=gpt-4o-mini

# Server Configuration
MCP_SERVER_URL=http://127.0.0.1:8010
STREAMLIT_PORT=8501

# Database Configuration
DUCKDB_PATH=data/warehouse/climategpt.duckdb
```

### Database Configuration

The system uses DuckDB for optimal analytical performance:

- **File Location**: `data/warehouse/climategpt.duckdb`
- **Size**: ~122 MB
- **Indexes**: Optimized for common query patterns
- **Connection**: Read-only for API, read-write for updates

## 🚀 Performance

### Query Performance

- **DuckDB Backend**: 10-100x faster than CSV queries
- **Optimized Indexes**: Fast lookups on key columns
- **Memory Efficient**: Streaming queries for large datasets
- **Concurrent Access**: Multiple users supported

### System Requirements

- **Minimum RAM**: 4 GB
- **Recommended RAM**: 8 GB+
- **Storage**: 2 GB for data + 1 GB for system
- **CPU**: Multi-core recommended for concurrent users

## 🛠️ Development

### Adding New Datasets

1. **Prepare Data**: Ensure CSV format with proper schema
2. **Update Manifest**: Add entry to `manifest_mcp_duckdb.json`
3. **Import to Database**: Use DuckDB import utilities
4. **Test Queries**: Verify API endpoints work correctly

### Extending Functionality

- **New Query Types**: Add to MCP server endpoints
- **Visualization Types**: Extend Streamlit chart library
- **Data Sources**: Integrate additional EDGAR sectors
- **Geographic Levels**: Add new administrative boundaries

## 📈 Data Processing Pipeline

### Raw Data Processing

1. **NetCDF Files**: EDGAR v2024 raw data
2. **Geographic Joins**: Spatial aggregation to boundaries
3. **Quality Checks**: Validation and cleaning
4. **Database Import**: DuckDB optimization

### Monthly Data Generation

- **Annual to Monthly**: Even distribution across 12 months
- **Seasonal Patterns**: Future enhancement for realistic patterns
- **Validation**: Consistency checks with annual totals

## 🔍 Troubleshooting

### Common Issues

**Server Won't Start:**
- Check if port 8010 is available
- Verify database file exists
- Check environment variables

**Query Errors:**
- Verify file_id exists in manifest
- Check column names in select clause
- Ensure proper data types in where clause

**Performance Issues:**
- Check database indexes
- Monitor memory usage
- Consider query optimization

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
uv run python mcp_server.py
```

## 📚 Additional Resources

### Documentation
- [EDGAR v2024 Documentation](https://edgar.jrc.ec.europa.eu/)
- [DuckDB Documentation](https://duckdb.org/docs/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Data Sources
- **EDGAR**: Emissions Database for Global Atmospheric Research
- **Natural Earth**: Geographic boundary data
- **GHS-UCDB**: Global Human Settlement Urban Centres Database

## 📄 License

This project uses data from EDGAR v2024 under CC-BY 4.0 license. Please refer to EDGAR terms and conditions for data usage.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the API documentation

---

**ClimateGPT** - Making emissions data accessible through natural language queries.


