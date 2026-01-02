"""
EDA Visualizations for ClimateGPT - PNG Output Version
Generates matplotlib/plotly static PNG charts for data exploration
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['font.size'] = 10

# Connect to DuckDB
DB_PATH = Path(".") / "data" / "warehouse" / "climategpt.duckdb"
conn = duckdb.connect(str(DB_PATH), read_only=True)

print("=" * 80)
print("ClimateGPT - EDA VISUALIZATIONS (PNG OUTPUT)")
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

fig, ax = plt.subplots(figsize=(12, 7))
bars = ax.barh(df_top_countries['country_name'], df_top_countries['total_emissions'] / 1e9)

# Color gradient
colors = plt.cm.Reds(np.linspace(0.4, 0.8, len(bars)))
for bar, color in zip(bars, colors):
    bar.set_color(color)

ax.set_xlabel('Total Emissions (Billion tonnes CO2e)', fontsize=12, fontweight='bold')
ax.set_ylabel('Country', fontsize=12, fontweight='bold')
ax.set_title('Top 10 Countries by Total Emissions (2000-2023)', fontsize=14, fontweight='bold')
ax.invert_yaxis()

# Add value labels
for i, v in enumerate(df_top_countries['total_emissions'] / 1e9):
    ax.text(v + 0.1, i, f'{v:.2f}B', va='center', fontweight='bold')

plt.tight_layout()
plt.savefig('01_top_10_countries.png', dpi=300, bbox_inches='tight')
print("✅ Saved: 01_top_10_countries.png")
plt.close()

# ============================================================================
# 2. SECTOR DISTRIBUTION (ALL SECTORS COMBINED)
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
            sector_emissions.append(result)
    except:
        pass

if sector_emissions:
    df_sectors = pd.concat(sector_emissions, ignore_index=True)

    fig, ax = plt.subplots(figsize=(10, 8))
    colors = plt.cm.Set3(np.linspace(0, 1, len(df_sectors)))
    wedges, texts, autotexts = ax.pie(
        df_sectors['total_emissions'],
        labels=df_sectors['sector'].str.replace('_', ' ').str.title(),
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 10, 'weight': 'bold'}
    )

    ax.set_title('Emissions Distribution by Sector (2000-2023)', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig('02_sector_distribution.png', dpi=300, bbox_inches='tight')
    print("✅ Saved: 02_sector_distribution.png")
    plt.close()

# ============================================================================
# 3. GLOBAL EMISSIONS TREND OVER TIME (POWER SECTOR)
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

fig, ax = plt.subplots(figsize=(14, 7))
ax.plot(df_trends['year'], df_trends['total_emissions'] / 1e9,
        color='#FF6B6B', linewidth=3, marker='o', markersize=6, label='Global Emissions')
ax.fill_between(df_trends['year'], df_trends['total_emissions'] / 1e9,
                alpha=0.3, color='#FF6B6B')

# Highlight COVID-19
covid_idx = df_trends[df_trends['year'] == 2020].index[0] if 2020 in df_trends['year'].values else None
if covid_idx is not None:
    covid_val = df_trends.loc[covid_idx, 'total_emissions'] / 1e9
    ax.annotate('COVID-19\nImpact', xy=(2020, covid_val), xytext=(2018, covid_val + 0.5),
                arrowprops=dict(arrowstyle='->', color='red', lw=2),
                fontsize=11, fontweight='bold', color='red')

ax.set_xlabel('Year', fontsize=12, fontweight='bold')
ax.set_ylabel('Total Emissions (Billion tonnes CO2e)', fontsize=12, fontweight='bold')
ax.set_title('Global Emissions Trend - Power Sector (2000-2023)', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3)
ax.legend(fontsize=11)

plt.tight_layout()
plt.savefig('03_global_emissions_trend.png', dpi=300, bbox_inches='tight')
print("✅ Saved: 03_global_emissions_trend.png")
plt.close()

# ============================================================================
# 4. DATA COMPLETENESS BY YEAR
# ============================================================================
print("[4/6] Generating Data Completeness chart...")

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

fig, ax = plt.subplots(figsize=(14, 7))
colors_map = ['#d73027' if x < 50 else '#fee090' if x < 80 else '#91bfdb' if x < 95 else '#1a9850'
              for x in df_completeness['completeness_pct']]
bars = ax.bar(df_completeness['year'], df_completeness['completeness_pct'], color=colors_map, edgecolor='black', linewidth=0.5)

ax.set_xlabel('Year', fontsize=12, fontweight='bold')
ax.set_ylabel('Completeness (%)', fontsize=12, fontweight='bold')
ax.set_title('Data Completeness by Year (% of Countries with Data)', fontsize=14, fontweight='bold')
ax.set_ylim(0, 105)

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{height:.0f}%', ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()
plt.savefig('04_data_completeness.png', dpi=300, bbox_inches='tight')
print("✅ Saved: 04_data_completeness.png")
plt.close()

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

fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Linear scale
axes[0].hist(df_distribution['emissions_tonnes'] / 1e6, bins=50, color='#45B7D1', edgecolor='black', alpha=0.7)
axes[0].set_xlabel('Emissions (Million tonnes CO2e)', fontsize=11, fontweight='bold')
axes[0].set_ylabel('Frequency', fontsize=11, fontweight='bold')
axes[0].set_title('Distribution of Emissions (Linear Scale)', fontsize=12, fontweight='bold')
axes[0].grid(True, alpha=0.3)

# Log scale
axes[1].hist(np.log10(df_distribution['emissions_tonnes'] + 1), bins=50, color='#90EE90', edgecolor='black', alpha=0.7)
axes[1].set_xlabel('Log10(Emissions + 1)', fontsize=11, fontweight='bold')
axes[1].set_ylabel('Frequency', fontsize=11, fontweight='bold')
axes[1].set_title('Distribution of Emissions (Log Scale)', fontsize=12, fontweight='bold')
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('05_emissions_distribution.png', dpi=300, bbox_inches='tight')
print("✅ Saved: 05_emissions_distribution.png")
plt.close()

# ============================================================================
# 6. TOP 20 COUNTRIES - VERTICAL BAR CHART
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

fig, ax = plt.subplots(figsize=(14, 8))
colors = plt.cm.Reds(np.linspace(0.4, 0.9, len(df_top_20)))
bars = ax.bar(range(len(df_top_20)), df_top_20['total_emissions'] / 1e9, color=colors, edgecolor='black', linewidth=0.5)

ax.set_xticks(range(len(df_top_20)))
ax.set_xticklabels(df_top_20['country_name'], rotation=45, ha='right', fontweight='bold')
ax.set_ylabel('Total Emissions (Billion tonnes CO2e)', fontsize=12, fontweight='bold')
ax.set_title('Top 20 Countries by Total Emissions (2000-2023)', fontsize=14, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

# Add value labels
for i, (bar, val) in enumerate(zip(bars, df_top_20['total_emissions'] / 1e9)):
    ax.text(bar.get_x() + bar.get_width()/2., val, f'{val:.2f}B',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig('06_top_20_countries_vertical.png', dpi=300, bbox_inches='tight')
print("✅ Saved: 06_top_20_countries_vertical.png")
plt.close()

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
print(f"  Years: {df_summary['years'].values[0]} ({int(df_summary['min_year'].values[0])}-{int(df_summary['max_year'].values[0])})")
print(f"  Avg Emissions: {df_summary['avg_emissions'].values[0]:,.0f} tonnes")
print(f"  Min Emissions: {df_summary['min_emissions'].values[0]:,.0f} tonnes")
print(f"  Max Emissions: {df_summary['max_emissions'].values[0]:,.0f} tonnes")

if not df_sectors.empty:
    print(f"\nAll Sectors Combined:")
    print(f"  Total Sectors: {len(df_sectors)}")
    print(f"  Total Records: {df_sectors['record_count'].sum():,}")

print("\n" + "=" * 80)
print("✅ All PNG visualizations generated successfully!")
print("=" * 80)
print("\nGenerated PNG files:")
print("  1. 01_top_10_countries.png")
print("  2. 02_sector_distribution.png")
print("  3. 03_global_emissions_trend.png")
print("  4. 04_data_completeness.png")
print("  5. 05_emissions_distribution.png")
print("  6. 06_top_20_countries_vertical.png")
print("\n✅ Ready for PowerPoint/Google Slides insertion!")

conn.close()
