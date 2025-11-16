"""
Pydantic models for request/response validation.
Uses Pydantic v2 syntax.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Literal, Any


class QueryEmissionsRequest(BaseModel):
    """Request model for query_emissions tool"""
    sector: Literal['transport', 'power', 'waste', 'agriculture', 'buildings', 'fuel_exploitation', 'ind_combustion', 'ind_processes']
    year: int = Field(ge=2000, le=2024, description="Year between 2000-2024")
    month: int | None = Field(None, ge=1, le=12, description="Optional month 1-12")
    country_name: str | None = None
    admin1_name: str | None = None
    city_name: str | None = None
    max_rows: int = Field(10000, ge=1, le=100000, description="Maximum rows to return")

    @field_validator('sector')
    @classmethod
    def validate_sector(cls, v: str) -> str:
        valid_sectors = {'transport', 'power', 'waste', 'agriculture', 'buildings',
                        'fuel_exploitation', 'ind_combustion', 'ind_processes'}
        if v not in valid_sectors:
            raise ValueError(f"Invalid sector. Must be one of {valid_sectors}")
        return v


class TopEmittersRequest(BaseModel):
    """Request model for top_emitters tool"""
    sector: Literal['transport', 'power', 'waste', 'agriculture', 'buildings', 'fuel_exploitation', 'ind_combustion', 'ind_processes']
    year: int = Field(ge=2000, le=2024)
    limit: int = Field(10, ge=1, le=50, description="Number of results 1-50")
    geographic_level: Literal['country', 'admin1', 'city'] = 'country'


class TrendAnalysisRequest(BaseModel):
    """Request model for analyze_trend tool"""
    entity_name: str = Field(min_length=1)
    sector: Literal['transport', 'power', 'waste', 'agriculture', 'buildings', 'fuel_exploitation', 'ind_combustion', 'ind_processes']
    start_year: int = Field(ge=2000, le=2024)
    end_year: int = Field(ge=2000, le=2024)

    @field_validator('end_year')
    @classmethod
    def validate_year_range(cls, v: int, info) -> int:
        if 'start_year' in info.data and v < info.data['start_year']:
            raise ValueError("end_year must be >= start_year")
        return v


class CompareSectorsRequest(BaseModel):
    """Request model for compare_sectors tool"""
    entity_name: str = Field(min_length=1)
    sectors: list[str] = Field(min_length=2, max_length=8)
    year: int = Field(ge=2000, le=2024)

    @field_validator('sectors')
    @classmethod
    def validate_sectors(cls, v: list[str]) -> list[str]:
        valid_sectors = {'transport', 'power', 'waste', 'agriculture', 'buildings',
                        'fuel_exploitation', 'ind_combustion', 'ind_processes'}
        for sector in v:
            if sector not in valid_sectors:
                raise ValueError(f"Invalid sector '{sector}'. Must be one of {valid_sectors}")
        return v


class CompareGeographiesRequest(BaseModel):
    """Request model for compare_geographies tool"""
    entities: list[str] = Field(min_length=2, max_length=20)
    sector: Literal['transport', 'power', 'waste', 'agriculture', 'buildings', 'fuel_exploitation', 'ind_combustion', 'ind_processes']
    year: int = Field(ge=2000, le=2024)


class EmissionsDataPoint(BaseModel):
    """Single emissions data point"""
    year: int
    month: int | None = None
    emissions_tonnes: float
    country_name: str | None = None
    admin1_name: str | None = None
    city_name: str | None = None
    iso3: str | None = None


class QueryEmissionsResponse(BaseModel):
    """Response model for query_emissions tool"""
    data: list[EmissionsDataPoint]
    total_rows: int
    truncated: bool = False
    query_time_ms: float | None = None


class TopEmitterEntry(BaseModel):
    """Single entry in top emitters list"""
    rank: int
    country: str | None = None
    admin1: str | None = None
    city: str | None = None
    iso3: str | None = None
    emissions_tonnes: float
    emissions_mtco2: float


class TopEmittersResponse(BaseModel):
    """Response model for top_emitters tool"""
    sector: str
    year: int
    geographic_level: str
    emitters: list[TopEmitterEntry]


class TrendDataPoint(BaseModel):
    """Single data point in trend analysis"""
    year: int
    emissions_tonnes: float
    growth_pct: float | None = None


class TrendAnalysisResponse(BaseModel):
    """Response model for analyze_trend tool"""
    entity: str
    sector: str
    period: str
    pattern: Literal['increasing', 'decreasing', 'stable']
    total_change_pct: float
    total_change_tonnes: float
    cagr_pct: float  # Compound Annual Growth Rate
    start_emissions: float
    end_emissions: float
    yoy_growth: list[dict[str, Any]]
    yearly_data: list[TrendDataPoint]


class SectorComparisonEntry(BaseModel):
    """Single sector in comparison"""
    sector: str
    rank: int
    emissions_tonnes: float
    emissions_mtco2: float
    percentage: float


class SectorComparisonResponse(BaseModel):
    """Response model for compare_sectors tool"""
    entity: str
    year: int
    total_emissions_tonnes: float
    total_emissions_mtco2: float
    sectors: list[SectorComparisonEntry]


class GeographyComparisonEntry(BaseModel):
    """Single geography in comparison"""
    entity: str
    geographic_level: str
    rank: int
    emissions_tonnes: float
    emissions_mtco2: float
    percentage: float


class GeographyComparisonResponse(BaseModel):
    """Response model for compare_geographies tool"""
    sector: str
    year: int
    total_emissions_tonnes: float
    total_emissions_mtco2: float
    comparison: list[GeographyComparisonEntry]


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    error_code: str | None = None
    request_id: str | None = None
    details: dict[str, Any] | None = None
