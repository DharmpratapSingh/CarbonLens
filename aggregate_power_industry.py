"""
Power Industry Data Aggregation
==============================

This script aggregates the combined Power Industry NetCDF data into country, state, and city levels
following the same structure as the transport data.

Based on: Transport data aggregation patterns
Sector: Power Industry - Power and heat generation plants
"""

import xarray as xr
import pandas as pd
import numpy as np
from pathlib import Path
import geopandas as gpd
from shapely.geometry import Point
import time

# ------------ config ------------
CURATED_DIR = Path("data/curated")
POWER_NC = CURATED_DIR / "edgar_power_industry_2000_2024_rawcombined.nc"
GEO_DIR = Path("data/geo")

# Output directories
COUNTRY_DIR = CURATED_DIR / "power-country-year"
ADMIN1_DIR = CURATED_DIR / "power-admin1-year"
CITY_DIR = CURATED_DIR / "power-city-year"

for dir_path in [COUNTRY_DIR, ADMIN1_DIR, CITY_DIR]:
    dir_path.mkdir(exist_ok=True)

def section_timer():
    t = {"last": time.time(), "start": None}
    def tick(label):
        now = time.time()
        if t["start"] is None:
            t["start"] = now
            t["last"] = now
            print(f"[{label}] start")
        else:
            print(f"[{label}] +{now - t['last']:.2f}s (elapsed {now - t['start']:.2f}s)")
            t["last"] = now
    return tick

tick = section_timer()

# ------------ load power industry data ------------
tick("load_power_data")
print("Loading Power Industry NetCDF data...")
ds = xr.open_dataset(POWER_NC, engine="netcdf4")
print(f"Power Industry data: {dict(ds.sizes)}")
print(f"Data variables: {list(ds.data_vars)}")

# ------------ load geographic data ------------
tick("load_geo_data")
print("Loading geographic boundary data...")

# Countries
countries_gdf = gpd.read_file(GEO_DIR / "ne_10m_admin_0_countries" / "ne_10m_admin_0_countries.shp")
print(f"Countries: {len(countries_gdf)}")

# Admin1 (states/provinces)
admin1_gdf = gpd.read_file(GEO_DIR / "ne_10m_admin_1_states_provinces" / "ne_10m_admin_1_states_provinces.shp")
print(f"Admin1 regions: {len(admin1_gdf)}")

# Cities (UCDB) - use the general characteristics layer and reproject to WGS84
cities_gdf = gpd.read_file(GEO_DIR / "GHS_UCDB_GLOBE_R2024A_V1_1" / "GHS_UCDB_GLOBE_R2024A.gpkg", 
                          layer="GHS_UCDB_THEME_GENERAL_CHARACTERISTICS_GLOBE_R2024A")
cities_gdf = cities_gdf.to_crs('EPSG:4326')  # Reproject to WGS84
# Clean column names (remove BOM characters)
cities_gdf.columns = [col.strip('\ufeff') for col in cities_gdf.columns]
print(f"Cities: {len(cities_gdf)}")

# ------------ create grid points ------------
tick("create_grid")
print("Creating grid point geometries...")
lats = ds.lat.values
lons = ds.lon.values

# Create all grid points
grid_points = []
for lat in lats:
    for lon in lons:
        grid_points.append(Point(lon, lat))

grid_gdf = gpd.GeoDataFrame(
    {'geometry': grid_points},
    crs='EPSG:4326'
)
print(f"Grid points: {len(grid_gdf)}")

# ------------ country aggregation ------------
tick("country_aggregation")
print("Aggregating to country level...")

# Spatial join: grid points to countries
grid_countries = gpd.sjoin(grid_gdf, countries_gdf, how='left', predicate='within')
print(f"Grid points with country assignment: {grid_countries['ADM0_A3'].notna().sum()}")

# Create country mapping
country_mapping = {}
for idx, row in grid_countries.iterrows():
    if pd.notna(row['ADM0_A3']):
        lat_idx = idx // len(lons)
        lon_idx = idx % len(lons)
        country_mapping[(lat_idx, lon_idx)] = {
            'iso3': row['ADM0_A3'],
            'country_name': row['NAME']
        }

# Aggregate emissions by country and year
country_emissions = {}
for year in range(2000, 2024):
    year_data = ds.sel(time=ds.time.dt.year == year)
    if len(year_data.time) == 0:
        continue
    
    # Sum across months for annual total
    annual_emissions = year_data.emissions.sum(dim='time')
    
    for (lat_idx, lon_idx), country_info in country_mapping.items():
        iso3 = country_info['iso3']
        country_name = country_info['country_name']
        
        if iso3 not in country_emissions:
            country_emissions[iso3] = {
                'country_name': country_name,
                'emissions_by_year': {}
            }
        
        emission_value = float(annual_emissions.isel(lat=lat_idx, lon=lon_idx).values)
        if pd.notna(emission_value) and emission_value > 0:
            if year not in country_emissions[iso3]['emissions_by_year']:
                country_emissions[iso3]['emissions_by_year'][year] = 0
            country_emissions[iso3]['emissions_by_year'][year] += emission_value

# Convert to DataFrame
country_data = []
for iso3, data in country_emissions.items():
    for year, emissions in data['emissions_by_year'].items():
        country_data.append({
            'iso3': iso3,
            'country_name': data['country_name'],
            'year': year,
            'emissions_tonnes': emissions,
            'MtCO2': emissions / 1e6,
            'units': 'tonnes CO2',
            'source': 'EDGAR v2024 power industry',
            'spatial_res': '0.1°',
            'temporal_res': 'annual'
        })

country_df = pd.DataFrame(country_data)
country_df = country_df.sort_values(['year', 'emissions_tonnes'], ascending=[True, False])

# Save country data
country_csv = COUNTRY_DIR / "power_country_year.csv"
country_df.to_csv(country_csv, index=False)
print(f"Saved country data: {country_csv} ({len(country_df)} rows)")

# ------------ admin1 aggregation ------------
tick("admin1_aggregation")
print("Aggregating to admin1 (state/province) level...")

# Spatial join: grid points to admin1
grid_admin1 = gpd.sjoin(grid_gdf, admin1_gdf, how='left', predicate='within')
print(f"Grid points with admin1 assignment: {grid_admin1['adm1_code'].notna().sum()}")

# Create country name mapping from countries shapefile
country_name_map = {}
for _, country_row in countries_gdf.iterrows():
    country_name_map[country_row['ADM0_A3']] = country_row['NAME']

# Create admin1 mapping
admin1_mapping = {}
for idx, row in grid_admin1.iterrows():
    if pd.notna(row['adm1_code']):
        lat_idx = idx // len(lons)
        lon_idx = idx % len(lons)
        # Use proper country name from mapping instead of corrupted adm0_label
        country_name = country_name_map.get(row['adm0_a3'], 'Unknown')
        admin1_mapping[(lat_idx, lon_idx)] = {
            'admin1_geoid': row['adm1_code'],
            'admin1_name': row['name'],
            'country_name': country_name,
            'iso3': row['adm0_a3']
        }

# Aggregate emissions by admin1 and year
admin1_emissions = {}
for year in range(2000, 2024):
    year_data = ds.sel(time=ds.time.dt.year == year)
    if len(year_data.time) == 0:
        continue
    
    annual_emissions = year_data.emissions.sum(dim='time')
    
    for (lat_idx, lon_idx), admin1_info in admin1_mapping.items():
        geoid = admin1_info['admin1_geoid']
        
        if geoid not in admin1_emissions:
            admin1_emissions[geoid] = {
                'admin1_name': admin1_info['admin1_name'],
                'country_name': admin1_info['country_name'],
                'iso3': admin1_info['iso3'],
                'emissions_by_year': {}
            }
        
        emission_value = float(annual_emissions.isel(lat=lat_idx, lon=lon_idx).values)
        if pd.notna(emission_value) and emission_value > 0:
            if year not in admin1_emissions[geoid]['emissions_by_year']:
                admin1_emissions[geoid]['emissions_by_year'][year] = 0
            admin1_emissions[geoid]['emissions_by_year'][year] += emission_value

# Convert to DataFrame
admin1_data = []
for geoid, data in admin1_emissions.items():
    for year, emissions in data['emissions_by_year'].items():
        admin1_data.append({
            'admin1_geoid': geoid,
            'admin1_name': data['admin1_name'],
            'country_name': data['country_name'],
            'iso3': data['iso3'],
            'year': year,
            'emissions_tonnes': emissions,
            'MtCO2': emissions / 1e6,
            'units': 'tonnes CO2',
            'source': 'EDGAR v2024 power industry',
            'spatial_res': '0.1°',
            'temporal_res': 'annual'
        })

admin1_df = pd.DataFrame(admin1_data)
admin1_df = admin1_df.sort_values(['year', 'emissions_tonnes'], ascending=[True, False])

# Save admin1 data
admin1_csv = ADMIN1_DIR / "power_admin1_year.csv"
admin1_df.to_csv(admin1_csv, index=False)
print(f"Saved admin1 data: {admin1_csv} ({len(admin1_df)} rows)")

# ------------ city aggregation ------------
tick("city_aggregation")
print("Aggregating to city level...")

# Spatial join: grid points to cities
grid_cities = gpd.sjoin(grid_gdf, cities_gdf, how='left', predicate='within')
print(f"Grid points with city assignment: {grid_cities['ID_UC_G0'].notna().sum()}")

# Create city mapping with proper admin1 names
city_mapping = {}
for idx, row in grid_cities.iterrows():
    if pd.notna(row['ID_UC_G0']):
        lat_idx = idx // len(lons)
        lon_idx = idx % len(lons)
        # Clean city name and country name (remove Unicode BOM and extra spaces)
        city_name = str(row['GC_UCN_MAI_2025']).strip().replace('\ufeff', '') if pd.notna(row['GC_UCN_MAI_2025']) else 'Unknown'
        country_name_raw = str(row['GC_CNT_GAD_2025']).strip().replace('\ufeff', '') if pd.notna(row['GC_CNT_GAD_2025']) else 'Unknown'
        # Clean ISO3 code (remove Unicode BOM and extra spaces)
        iso3_raw = str(row['GC_CNT_UNN_2025']).strip().replace('\ufeff', '') if pd.notna(row['GC_CNT_UNN_2025']) else 'Unknown'
        # Use proper country name from mapping if available
        country_name = country_name_map.get(iso3_raw, country_name_raw) if pd.notna(iso3_raw) and iso3_raw != 'Unknown' else country_name_raw
        
        # Get admin1 information from the admin1 mapping
        admin1_info = admin1_mapping.get((lat_idx, lon_idx), {})
        admin1_name = admin1_info.get('admin1_name', 'Unknown')
        
        city_mapping[(lat_idx, lon_idx)] = {
            'city_id': row['ID_UC_G0'],
            'city_name': city_name,
            'admin1_name': admin1_name,  # Now using proper admin1 name
            'country_name': country_name,
            'iso3': iso3_raw
        }

# Aggregate emissions by city and year
city_emissions = {}
for year in range(2000, 2024):
    year_data = ds.sel(time=ds.time.dt.year == year)
    if len(year_data.time) == 0:
        continue
    
    annual_emissions = year_data.emissions.sum(dim='time')
    
    for (lat_idx, lon_idx), city_info in city_mapping.items():
        city_id = city_info['city_id']
        
        if city_id not in city_emissions:
            city_emissions[city_id] = {
                'city_name': city_info['city_name'],
                'admin1_name': city_info['admin1_name'],
                'country_name': city_info['country_name'],
                'iso3': city_info['iso3'],
                'emissions_by_year': {}
            }
        
        emission_value = float(annual_emissions.isel(lat=lat_idx, lon=lon_idx).values)
        if pd.notna(emission_value) and emission_value > 0:
            if year not in city_emissions[city_id]['emissions_by_year']:
                city_emissions[city_id]['emissions_by_year'][year] = 0
            city_emissions[city_id]['emissions_by_year'][year] += emission_value

# Convert to DataFrame
city_data = []
for city_id, data in city_emissions.items():
    for year, emissions in data['emissions_by_year'].items():
        city_data.append({
            'city_id': city_id,
            'city_name': data['city_name'],
            'admin1_name': data['admin1_name'],
            'country_name': data['country_name'],
            'iso3': data['iso3'],
            'year': year,
            'emissions_tonnes': emissions,
            'MtCO2': emissions / 1e6,
            'units': 'tonnes CO2',
            'source': 'EDGAR v2024 power industry',
            'spatial_res': '0.1°',
            'temporal_res': 'annual'
        })

city_df = pd.DataFrame(city_data)
city_df = city_df.sort_values(['year', 'emissions_tonnes'], ascending=[True, False])

# Save city data
city_csv = CITY_DIR / "power_city_year.csv"
city_df.to_csv(city_csv, index=False)
print(f"Saved city data: {city_csv} ({len(city_df)} rows)")

tick("done")

# ------------ summary ------------
print("\n[SUMMARY]")
print(f"✅ Power Industry data aggregated successfully!")
print(f"📊 Country level: {len(country_df)} rows")
print(f"📊 Admin1 level: {len(admin1_df)} rows") 
print(f"📊 City level: {len(city_df)} rows")
print(f"📁 Output directories:")
print(f"   - {COUNTRY_DIR}")
print(f"   - {ADMIN1_DIR}")
print(f"   - {CITY_DIR}")
print(f"\n🎯 Next step: Add Power Industry datasets to MCP server manifest")
