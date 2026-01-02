"""
EDA Visualizations for ClimateGPT Emissions Database
Generates interactive Plotly charts for data exploration
"""

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path

# Connect to DuckDB
DB_PATH = Path(__file__).parent / "data" / "warehouse" / "climategpt.duckdb"
conn = duckdb.connect(str(DB_PATH), read_only=True)

print("=" * 80)
print("ClimateGPT - EDA VISUALIZATIONS")
print("=" * 80)

# ============================================================================
# 1. TOP 10 COUNTRIES BY EMISSIONS
# ============================================================================
print("\n[1/6] Generating Top 10 Countries chart...")

query_top_countries = """
SELECT
    country_name,
    SUM(emissions_tonnes) as total_emissions,
    COUNT(*) as record_count
FROM power_country_year
WHERE country_name IS NOT NULL
GROUP BY country_name
ORDER BY total_emissions DESC
LIMIT 10
"""

df_top_countries = conn.execute(query_top_countries).fetch_df()

fig_top_countries = px.bar(
    df_top_countries,
    x='country_name',
    y='total_emissions',
    title='Top 10 Countries by Total Emissions (2000-2023)',
    labels={'country_name': 'Country', 'total_emissions': 'Total Emissions (tonnes CO2e)'},
    color='total_emissions',
    color_continuous_scale='Reds'
)

fig_top_countries.update_layout(
    xaxis_tickangle=-45,
    height=500,
    showlegend=False,
    hovermode='x unified',
    template='plotly_white'
)

fig_top_countries.update_traces(
    hovertemplate='<b>%{x}</b><br>Emissions: %{y:,.0f} tonnes<extra></extra>'
)

fig_top_countries.write_html('01_top_10_countries.html')
print("✅ Saved: 01_top_10_countries.html")

# ============================================================================
# 2. SECTOR DISTRIBUTION (ALL SECTORS COMBINED)
# ============================================================================
print("[2/6] Generating Sector Distribution chart...")

# Get all sector tables - with correct table names
sector_tables = {
    'power': 'power_country_year',
    'industrial_combustion': 'ind_combustion_country_year',
    'industrial_processes': 'ind_processes_country_year',
    'transport': 'transport_country_year',
    'buildings': 'buildings_country_year',
    'agriculture': 'agriculture_country_year',
    'waste': 'waste_country_year',
    'fuel_exploitation': 'fuel_exploitation_country_year'
}
sector_emissions = []

for sector_name, table_name in sector_tables.items():
    query = f"""
    SELECT
        '{sector_name}' as sector,
        SUM(emissions_tonnes) as total_emissions,
        COUNT(*) as record_count,
        COUNT(DISTINCT country_name) as countries
    FROM {table_name}
    """
    try:
        result = conn.execute(query).fetch_df()
        if not result.empty:
            sector_emissions.append(result)
    except Exception as e:
        print(f"  Note: {sector_name} table not available")

if sector_emissions:
    df_sectors = pd.concat(sector_emissions, ignore_index=True)

    fig_sector_dist = go.Figure(data=[
        go.Pie(
            labels=df_sectors['sector'].str.replace('_', ' ').str.title(),
            values=df_sectors['total_emissions'],
            hole=0.4,
            hovertemplate='<b>%{label}</b><br>Emissions: %{value:,.0f} tonnes<br>%{percent}<extra></extra>',
            marker=dict(colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2'])
        )
    ])

    fig_sector_dist.update_layout(
        title='Emissions Distribution by Sector (2000-2023)',
        height=500,
        template='plotly_white'
    )

    fig_sector_dist.write_html('02_sector_distribution.html')
    print("✅ Saved: 02_sector_distribution.html")

# ============================================================================
# 3. GLOBAL EMISSIONS TREND OVER TIME (POWER SECTOR)
# ============================================================================
print("[3/6] Generating Global Emissions Trend chart...")

query_trends = """
SELECT
    year,
    SUM(emissions_tonnes) as total_emissions,
    COUNT(*) as record_count
FROM power_country_year
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year ASC
"""

df_trends = conn.execute(query_trends).fetch_df()

fig_trends = go.Figure()

fig_trends.add_trace(go.Scatter(
    x=df_trends['year'],
    y=df_trends['total_emissions'],
    mode='lines+markers',
    name='Global Emissions',
    line=dict(color='#FF6B6B', width=3),
    marker=dict(size=8),
    fill='tozeroy',
    fillcolor='rgba(255, 107, 107, 0.2)',
    hovertemplate='<b>Year: %{x}</b><br>Emissions: %{y:,.0f} tonnes<extra></extra>'
))

fig_trends.update_layout(
    title='Global Emissions Trend - Power Sector (2000-2023)',
    xaxis_title='Year',
    yaxis_title='Total Emissions (tonnes CO2e)',
    height=500,
    hovermode='x unified',
    template='plotly_white',
    showlegend=False
)

# Add COVID annotation
covid_year = 2020
fig_trends.add_annotation(
    x=covid_year,
    y=df_trends[df_trends['year'] == covid_year]['total_emissions'].values[0],
    text='COVID-19<br>Impact',
    showarrow=True,
    arrowhead=2,
    arrowsize=1,
    arrowwidth=2,
    arrowcolor='red',
    ax=40,
    ay=-60,
    bgcolor='yellow',
    opacity=0.8
)

fig_trends.write_html('03_global_emissions_trend.html')
print("✅ Saved: 03_global_emissions_trend.html")

# ============================================================================
# 4. EMISSIONS BY YEAR - HEAT MAP
# ============================================================================
print("[4/6] Generating Year-wise Data Completeness chart...")

query_completeness = """
SELECT
    year,
    COUNT(DISTINCT country_name) as countries_with_data,
    COUNT(*) as total_records,
    (COUNT(DISTINCT country_name)::FLOAT / 305.0 * 100) as completeness_pct
FROM power_country_year
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year ASC
"""

df_completeness = conn.execute(query_completeness).fetch_df()

fig_completeness = go.Figure(data=[
    go.Bar(
        x=df_completeness['year'],
        y=df_completeness['completeness_pct'],
        marker=dict(
            color=df_completeness['completeness_pct'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title='Completeness %')
        ),
        hovertemplate='<b>Year: %{x}</b><br>Completeness: %{y:.1f}%<extra></extra>',
        showlegend=False
    )
])

fig_completeness.update_layout(
    title='Data Completeness by Year (% of Countries with Data)',
    xaxis_title='Year',
    yaxis_title='Completeness (%)',
    height=500,
    template='plotly_white'
)

fig_completeness.write_html('04_data_completeness.html')
print("✅ Saved: 04_data_completeness.html")

# ============================================================================
# 5. EMISSIONS DISTRIBUTION (BOX PLOT)
# ============================================================================
print("[5/6] Generating Emissions Distribution chart...")

query_distribution = """
SELECT
    emissions_tonnes,
    year
FROM power_country_year
WHERE emissions_tonnes > 0
LIMIT 50000
"""

df_distribution = conn.execute(query_distribution).fetch_df()

fig_distribution = go.Figure()

fig_distribution.add_trace(go.Box(
    y=np.log10(df_distribution['emissions_tonnes'] + 1),
    name='Emissions (log scale)',
    boxmean='sd',
    marker=dict(color='#45B7D1'),
    hovertemplate='Log Emissions: %{y:.2f}<extra></extra>'
))

fig_distribution.update_layout(
    title='Distribution of Emissions Values (Log Scale)',
    yaxis_title='Log10(Emissions in tonnes CO2e)',
    height=500,
    template='plotly_white',
    showlegend=False
)

fig_distribution.write_html('05_emissions_distribution.html')
print("✅ Saved: 05_emissions_distribution.html")

# ============================================================================
# 6. GEOGRAPHIC DISTRIBUTION - CHOROPLETH
# ============================================================================
print("[6/6] Generating Geographic Distribution chart...")

query_geo = """
SELECT
    country_name,
    SUM(emissions_tonnes) as total_emissions
FROM power_country_year
WHERE country_name IS NOT NULL
GROUP BY country_name
ORDER BY total_emissions DESC
"""

df_geo = conn.execute(query_geo).fetch_df()

# Create ISO code mapping (simplified)
iso_mapping = {
    'China': 'CHN',
    'United States': 'USA',
    'India': 'IND',
    'Russia': 'RUS',
    'Japan': 'JPN',
    'Germany': 'DEU',
    'Brazil': 'BRA',
    'Indonesia': 'IDN',
    'Iran': 'IRN',
    'Mexico': 'MEX'
}

# Add ISO codes for top countries
df_geo['iso_alpha'] = df_geo['country_name'].map(iso_mapping)
df_geo_top = df_geo[df_geo['iso_alpha'].notna()].head(10)

fig_geo = px.choropleth(
    df_geo_top,
    locations='iso_alpha',
    color='total_emissions',
    hover_name='country_name',
    title='Top 10 Countries - Emissions Magnitude',
    color_continuous_scale='Reds',
    labels={'total_emissions': 'Total Emissions'},
)

fig_geo.update_layout(
    geo=dict(projection_type='natural earth'),
    height=500,
    template='plotly_white'
)

fig_geo.write_html('06_geographic_distribution.html')
print("✅ Saved: 06_geographic_distribution.html")

# ============================================================================
# SUMMARY STATISTICS
# ============================================================================
print("\n" + "=" * 80)
print("DATA SUMMARY")
print("=" * 80)

query_summary = """
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT country_name) as countries,
    COUNT(DISTINCT year) as years,
    MIN(year) as min_year,
    MAX(year) as max_year,
    ROUND(AVG(emissions_tonnes), 2) as avg_emissions,
    ROUND(MIN(emissions_tonnes), 2) as min_emissions,
    ROUND(MAX(emissions_tonnes), 2) as max_emissions
FROM power_country_year
"""

df_summary = conn.execute(query_summary).fetch_df()
print(f"\nPower Sector Statistics:")
print(f"  Total Records: {df_summary['total_records'].values[0]:,}")
print(f"  Countries: {df_summary['countries'].values[0]}")
print(f"  Years: {df_summary['years'].values[0]} ({df_summary['min_year'].values[0]}-{df_summary['max_year'].values[0]})")
print(f"  Avg Emissions: {df_summary['avg_emissions'].values[0]:,.0f} tonnes")
print(f"  Min Emissions: {df_summary['min_emissions'].values[0]:,.0f} tonnes")
print(f"  Max Emissions: {df_summary['max_emissions'].values[0]:,.0f} tonnes")

if not df_sectors.empty:
    print(f"\nAll Sectors Combined:")
    print(f"  Total Sectors: {len(df_sectors)}")
    print(f"  Total Records: {df_sectors['record_count'].sum():,}")
    print(f"  Total Countries: {df_sectors['countries'].sum()}")

print("\n" + "=" * 80)
print("✅ All visualizations generated successfully!")
print("=" * 80)
print("\nGenerated files:")
print("  1. 01_top_10_countries.html")
print("  2. 02_sector_distribution.html")
print("  3. 03_global_emissions_trend.html")
print("  4. 04_data_completeness.html")
print("  5. 05_emissions_distribution.html")
print("  6. 06_geographic_distribution.html")
print("\nOpen these HTML files in your browser to view the interactive charts!")

conn.close()
