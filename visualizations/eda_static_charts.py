"""
EDA Visualizations - Static PNG Export using Plotly
Generates high-quality PNG charts with console output
"""

import duckdb
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from pathlib import Path

# Connect to DuckDB
DB_PATH = Path(".") / "data" / "warehouse" / "climategpt.duckdb"
conn = duckdb.connect(str(DB_PATH), read_only=True)

print("=" * 80)
print("ClimateGPT - EDA VISUALIZATIONS (Static PNG Export)")
print("=" * 80)

# ============================================================================
# 1. TOP 10 COUNTRIES BY EMISSIONS
# ============================================================================
print("\n[1/6] Generating Top 10 Countries chart...")

query_top_countries = """
SELECT
    country_name,
    SUM(emissions_tonnes) as total_emissions
FROM power_country_year
WHERE country_name IS NOT NULL
GROUP BY country_name
ORDER BY total_emissions DESC
LIMIT 10
"""

df_top_countries = conn.execute(query_top_countries).fetch_df()

fig = px.bar(
    df_top_countries.sort_values('total_emissions'),
    x='total_emissions',
    y='country_name',
    orientation='h',
    title='Top 10 Countries by Total Emissions (2000-2023)',
    labels={'country_name': 'Country', 'total_emissions': 'Total Emissions (tonnes CO2e)'},
    color='total_emissions',
    color_continuous_scale='Reds'
)

fig.update_layout(
    height=600,
    showlegend=False,
    template='plotly_white',
    font=dict(size=11),
    xaxis_title='Total Emissions (tonnes CO2e)',
    yaxis_title=''
)

try:
    fig.write_image('01_top_10_countries.png', width=1200, height=600, scale=2)
    print("✅ Saved: 01_top_10_countries.png")
except:
    print("⚠️  Kaleido not available, saving as HTML alternative")
    fig.write_html('01_top_10_countries.html')

# ============================================================================
# 2. SECTOR DISTRIBUTION
# ============================================================================
print("[2/6] Generating Sector Distribution chart...")

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
sector_stats = []
for sector_name, table_name in sector_tables.items():
    query = f"""
    SELECT
        '{sector_name}' as sector,
        SUM(emissions_tonnes) as total_emissions,
        COUNT(*) as record_count
    FROM {table_name}
    """
    try:
        result = conn.execute(query).fetch_df()
        if not result.empty:
            sector_emissions.append(result[['sector', 'total_emissions']])
            sector_stats.append(result)
    except:
        pass

if sector_emissions:
    df_sectors = pd.concat(sector_emissions, ignore_index=True)

    fig = px.pie(
        df_sectors,
        values='total_emissions',
        names='sector',
        title='Emissions Distribution by Sector (2000-2023)',
        color_discrete_sequence=px.colors.qualitative.Set3
    )

    fig.update_layout(
        height=600,
        template='plotly_white',
        font=dict(size=11)
    )

    try:
        fig.write_image('02_sector_distribution.png', width=900, height=600, scale=2)
        print("✅ Saved: 02_sector_distribution.png")
    except:
        print("⚠️  Kaleido not available, saving as HTML alternative")
        fig.write_html('02_sector_distribution.html')

# ============================================================================
# 3. GLOBAL EMISSIONS TREND
# ============================================================================
print("[3/6] Generating Global Emissions Trend chart...")

query_trends = """
SELECT
    year,
    SUM(emissions_tonnes) as total_emissions
FROM power_country_year
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year ASC
"""

df_trends = conn.execute(query_trends).fetch_df()

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_trends['year'],
    y=df_trends['total_emissions'] / 1e9,
    mode='lines+markers',
    name='Global Emissions',
    line=dict(color='#FF6B6B', width=3),
    marker=dict(size=8),
    fill='tozeroy',
    fillcolor='rgba(255, 107, 107, 0.2)'
))

# Add COVID annotation
covid_year = 2020
covid_val = df_trends[df_trends['year'] == covid_year]['total_emissions'].values[0] / 1e9
fig.add_annotation(
    x=covid_year,
    y=covid_val,
    text='COVID-19<br>Impact',
    showarrow=True,
    arrowhead=2,
    arrowwidth=2,
    arrowcolor='red',
    ax=50,
    ay=-50
)

fig.update_layout(
    title='Global Emissions Trend - Power Sector (2000-2023)',
    xaxis_title='Year',
    yaxis_title='Total Emissions (Billion tonnes CO2e)',
    height=600,
    template='plotly_white',
    font=dict(size=11),
    showlegend=False,
    hovermode='x unified'
)

try:
    fig.write_image('03_global_emissions_trend.png', width=1200, height=600, scale=2)
    print("✅ Saved: 03_global_emissions_trend.png")
except:
    print("⚠️  Kaleido not available, saving as HTML alternative")
    fig.write_html('03_global_emissions_trend.html')

# ============================================================================
# 4. DATA COMPLETENESS
# ============================================================================
print("[4/6] Generating Data Completeness chart...")

query_completeness = """
SELECT
    year,
    COUNT(DISTINCT country_name) as countries_with_data,
    (COUNT(DISTINCT country_name)::FLOAT / 305.0 * 100) as completeness_pct
FROM power_country_year
WHERE year IS NOT NULL
GROUP BY year
ORDER BY year ASC
"""

df_completeness = conn.execute(query_completeness).fetch_df()

fig = go.Figure(data=[
    go.Bar(
        x=df_completeness['year'],
        y=df_completeness['completeness_pct'],
        marker=dict(
            color=df_completeness['completeness_pct'],
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title='Completeness %')
        )
    )
])

fig.update_layout(
    title='Data Completeness by Year (% of Countries with Data)',
    xaxis_title='Year',
    yaxis_title='Completeness (%)',
    height=600,
    template='plotly_white',
    font=dict(size=11),
    showlegend=False
)

try:
    fig.write_image('04_data_completeness.png', width=1200, height=600, scale=2)
    print("✅ Saved: 04_data_completeness.png")
except:
    print("⚠️  Kaleido not available, saving as HTML alternative")
    fig.write_html('04_data_completeness.html')

# ============================================================================
# 5. EMISSIONS DISTRIBUTION (HISTOGRAM)
# ============================================================================
print("[5/6] Generating Emissions Distribution chart...")

query_distribution = """
SELECT
    emissions_tonnes
FROM power_country_year
WHERE emissions_tonnes > 0
LIMIT 50000
"""

df_distribution = conn.execute(query_distribution).fetch_df()

fig = go.Figure(data=[
    go.Histogram(
        x=np.log10(df_distribution['emissions_tonnes'] + 1),
        nbinsx=50,
        marker=dict(color='#45B7D1', line=dict(color='black', width=0.5))
    )
])

fig.update_layout(
    title='Distribution of Emissions (Log Scale)',
    xaxis_title='Log10(Emissions in tonnes CO2e)',
    yaxis_title='Frequency',
    height=600,
    template='plotly_white',
    font=dict(size=11),
    showlegend=False
)

try:
    fig.write_image('05_emissions_distribution.png', width=1200, height=600, scale=2)
    print("✅ Saved: 05_emissions_distribution.png")
except:
    print("⚠️  Kaleido not available, saving as HTML alternative")
    fig.write_html('05_emissions_distribution.html')

# ============================================================================
# 6. TOP 20 COUNTRIES - VERTICAL
# ============================================================================
print("[6/6] Generating Top 20 Countries (Vertical) chart...")

query_top_20 = """
SELECT
    country_name,
    SUM(emissions_tonnes) as total_emissions
FROM power_country_year
WHERE country_name IS NOT NULL
GROUP BY country_name
ORDER BY total_emissions DESC
LIMIT 20
"""

df_top_20 = conn.execute(query_top_20).fetch_df()

fig = px.bar(
    df_top_20,
    x='country_name',
    y='total_emissions',
    title='Top 20 Countries by Total Emissions (2000-2023)',
    labels={'country_name': 'Country', 'total_emissions': 'Total Emissions (tonnes CO2e)'},
    color='total_emissions',
    color_continuous_scale='Reds'
)

fig.update_layout(
    height=600,
    showlegend=False,
    template='plotly_white',
    font=dict(size=10),
    xaxis_tickangle=-45,
    yaxis_title='Total Emissions (tonnes CO2e)',
    xaxis_title=''
)

try:
    fig.write_image('06_top_20_countries_vertical.png', width=1200, height=600, scale=2)
    print("✅ Saved: 06_top_20_countries_vertical.png")
except:
    print("⚠️  Kaleido not available, saving as HTML alternative")
    fig.write_html('06_top_20_countries_vertical.html')

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

print(f"\n📊 POWER SECTOR STATISTICS:")
print(f"{'─' * 60}")
print(f"  Total Records:        {df_summary['total_records'].values[0]:>20,}")
print(f"  Countries:            {df_summary['countries'].values[0]:>20}")
print(f"  Years:                {df_summary['years'].values[0]:>20} ({int(df_summary['min_year'].values[0])}-{int(df_summary['max_year'].values[0])})")
print(f"  Average Emissions:    {df_summary['avg_emissions'].values[0]:>20,.0f} tonnes")
print(f"  Minimum Emissions:    {df_summary['min_emissions'].values[0]:>20,.0f} tonnes")
print(f"  Maximum Emissions:    {df_summary['max_emissions'].values[0]:>20,.0f} tonnes")

if not sector_stats:
    print(f"\n⚠️  Could not retrieve all sector data")
else:
    df_all_sectors = pd.concat(sector_stats, ignore_index=True)
    print(f"\n📊 ALL SECTORS COMBINED:")
    print(f"{'─' * 60}")
    print(f"  Total Sectors:        {len(df_all_sectors):>20}")
    print(f"  Total Records:        {df_all_sectors['record_count'].sum():>20,}")

print("\n" + "=" * 80)
print("✅ VISUALIZATION GENERATION COMPLETE!")
print("=" * 80)
print("\n📁 Generated files:")
print("   1. 01_top_10_countries.png")
print("   2. 02_sector_distribution.png")
print("   3. 03_global_emissions_trend.png")
print("   4. 04_data_completeness.png")
print("   5. 05_emissions_distribution.png")
print("   6. 06_top_20_countries_vertical.png")
print("\n✅ Ready to insert into PowerPoint/Google Slides!")

conn.close()
