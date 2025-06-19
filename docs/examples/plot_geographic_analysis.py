"""
Geographic Analysis with Census Data
=====================================

This example demonstrates how to work with geographic census data,
including creating maps and performing spatial analysis.
"""

# %%
# Import required libraries
# -------------------------

import pycancensus as pc
import matplotlib.pyplot as plt
import pandas as pd

# Set up the plotting style
plt.style.use('default')
plt.rcParams['figure.figsize'] = (12, 8)

# %%
# Getting Geographic Census Data
# ------------------------------
# 
# Let's retrieve census data with geographic boundaries for mapping.

print("Retrieving geographic census data...")

try:
    # Get population data with geometries for Vancouver CMA
    geo_data = pc.get_census(
        dataset="CA21",
        regions={"CMA": "59933"},  # Vancouver CMA
        vectors=["v_CA21_1", "v_CA21_434"],  # Population and median income
        level="CT",  # Census Tract level for detailed analysis
        geo_format="geopandas"
    )
    
    print(f"Retrieved {len(geo_data)} census tracts")
    print(f"Columns: {list(geo_data.columns)}")
    
except Exception as e:
    print(f"Error retrieving data: {e}")
    print("Creating sample data for demonstration...")
    
    # Create sample data for demonstration when API is not available
    import numpy as np
    from shapely.geometry import Point
    import geopandas as gpd
    
    # Sample coordinates around Vancouver area
    n_points = 50
    np.random.seed(42)
    lons = np.random.uniform(-123.3, -122.9, n_points)
    lats = np.random.uniform(49.15, 49.35, n_points)
    
    geo_data = gpd.GeoDataFrame({
        'GeoUID': [f'59933{i:03d}' for i in range(n_points)],
        'name': [f'Census Tract {i}' for i in range(n_points)],
        'v_CA21_1': np.random.randint(1000, 8000, n_points),  # Population
        'v_CA21_434': np.random.randint(30000, 120000, n_points),  # Median income
        'geometry': [Point(lon, lat) for lon, lat in zip(lons, lats)]
    }, crs='EPSG:4326')
    
    print("Using sample data for demonstration")

# %%
# Creating a Basic Map
# --------------------
# 
# Let's create a simple map showing population distribution.

fig, ax = plt.subplots(1, 1, figsize=(12, 10))

# Create choropleth map of population
if 'v_CA21_1' in geo_data.columns:
    geo_data.plot(
        column='v_CA21_1',
        cmap='YlOrRd',
        legend=True,
        ax=ax,
        legend_kwds={'label': 'Population', 'shrink': 0.8}
    )

ax.set_title('Population Distribution by Census Tract\nVancouver CMA, 2021', 
             fontsize=16, pad=20)
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')

# Remove axes ticks for cleaner look  
ax.tick_params(labelsize=10)
plt.tight_layout()
plt.show()

# %%
# Multi-variable Analysis
# -----------------------
# 
# Let's compare two variables: population and median income.

if 'v_CA21_1' in geo_data.columns and 'v_CA21_434' in geo_data.columns:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Population map
    geo_data.plot(
        column='v_CA21_1',
        cmap='YlOrRd',
        legend=True,
        ax=ax1,
        legend_kwds={'label': 'Population', 'shrink': 0.8}
    )
    ax1.set_title('Population by Census Tract')
    ax1.axis('off')
    
    # Median income map
    geo_data.plot(
        column='v_CA21_434',
        cmap='YlGnBu', 
        legend=True,
        ax=ax2,
        legend_kwds={'label': 'Median Income ($)', 'shrink': 0.8}
    )
    ax2.set_title('Median Income by Census Tract')
    ax2.axis('off')
    
    plt.suptitle('Vancouver CMA: Population vs Income Distribution', 
                 fontsize=16, y=1.02)
    plt.tight_layout()
    plt.show()

# %%
# Statistical Analysis
# --------------------
# 
# Let's perform some basic statistical analysis on our geographic data.

if 'v_CA21_1' in geo_data.columns and 'v_CA21_434' in geo_data.columns:
    print("\nStatistical Summary:")
    print("="*50)
    
    # Population statistics
    pop_stats = geo_data['v_CA21_1'].describe()
    print("Population Statistics:")
    print(f"  Mean: {pop_stats['mean']:.0f}")
    print(f"  Median: {pop_stats['50%']:.0f}")
    print(f"  Std Dev: {pop_stats['std']:.0f}")
    print(f"  Range: {pop_stats['min']:.0f} - {pop_stats['max']:.0f}")
    
    # Income statistics
    income_stats = geo_data['v_CA21_434'].describe()
    print(f"\nMedian Income Statistics:")
    print(f"  Mean: ${income_stats['mean']:,.0f}")
    print(f"  Median: ${income_stats['50%']:,.0f}")
    print(f"  Std Dev: ${income_stats['std']:,.0f}")
    print(f"  Range: ${income_stats['min']:,.0f} - ${income_stats['max']:,.0f}")
    
    # Correlation analysis
    correlation = geo_data['v_CA21_1'].corr(geo_data['v_CA21_434'])
    print(f"\nCorrelation between Population and Income: {correlation:.3f}")

# %%
# Scatter Plot Analysis
# ---------------------
# 
# Let's visualize the relationship between population and income.

if 'v_CA21_1' in geo_data.columns and 'v_CA21_434' in geo_data.columns:
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    
    scatter = ax.scatter(
        geo_data['v_CA21_1'], 
        geo_data['v_CA21_434'],
        c=geo_data['v_CA21_1'],
        cmap='viridis',
        alpha=0.7,
        s=60
    )
    
    ax.set_xlabel('Population')
    ax.set_ylabel('Median Income ($)')
    ax.set_title('Population vs Median Income\nVancouver CMA Census Tracts')
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Population')
    
    # Add trend line
    z = np.polyfit(geo_data['v_CA21_1'], geo_data['v_CA21_434'], 1)
    p = np.poly1d(z)
    ax.plot(geo_data['v_CA21_1'], p(geo_data['v_CA21_1']), 
            "r--", alpha=0.8, linewidth=2)
    
    plt.tight_layout()
    plt.show()

# %%
# Working with Different Geography Levels
# ---------------------------------------
# 
# Census data is available at different geographic levels. Let's compare a few.

print("\nComparing Geographic Levels:")
print("="*40)

levels_to_try = ["CMA", "CSD", "CT"]
level_names = ["Metro Area", "Municipality", "Census Tract"]

for level, name in zip(levels_to_try, level_names):
    try:
        # Get count of regions at each level
        regions = pc.list_census_regions("CA21", level=level)
        print(f"{name} ({level}): {len(regions)} regions")
    except:
        print(f"{name} ({level}): Unable to retrieve")

# %%
# Advanced Mapping with Folium
# -----------------------------
# 
# For interactive maps, we can use folium (when available).

try:
    import folium
    from folium import plugins
    
    print("\nCreating interactive map with Folium...")
    
    # Create base map centered on Vancouver
    center_lat = geo_data.geometry.centroid.y.mean()
    center_lon = geo_data.geometry.centroid.x.mean()
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles='OpenStreetMap'
    )
    
    # Add choropleth layer
    if 'v_CA21_1' in geo_data.columns:
        folium.Choropleth(
            geo_data=geo_data,
            data=geo_data,
            columns=['GeoUID', 'v_CA21_1'],
            key_on='feature.properties.GeoUID',
            fill_color='YlOrRd',
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name='Population'
        ).add_to(m)
    
    print("Interactive map created successfully!")
    print("(Map object created but not displayed in static documentation)")
    
except ImportError:
    print("Folium not available - install with: pip install folium")
except Exception as e:
    print(f"Error creating interactive map: {e}")

# %%
# Summary and Next Steps
# ----------------------
# 
# This example demonstrated key geographic analysis capabilities:

print("\n" + "="*60)
print("Geographic Analysis Example Complete")
print("="*60)

print("\nWhat we covered:")
print("• Retrieving census data with geographic boundaries")
print("• Creating choropleth maps with matplotlib")
print("• Multi-variable geographic visualization")
print("• Statistical analysis of spatial data")
print("• Scatter plot analysis of geographic variables")
print("• Working with different geographic levels")
print("• Interactive mapping with Folium")

print("\nNext steps for your analysis:")
print("1. Experiment with different census variables")
print("2. Try different geographic levels (CMA, CSD, CT, DA)")
print("3. Combine multiple datasets for temporal analysis")
print("4. Use spatial analysis tools from geopandas")
print("5. Create interactive dashboards with your maps")

# %%
# Additional Resources
# --------------------
# 
# For more advanced geographic analysis, consider exploring:
# 
# - **geopandas**: Advanced spatial operations and analysis
# - **folium**: Interactive web maps
# - **plotly**: Interactive plotting and dashboards  
# - **contextily**: Adding basemaps to static plots
# - **rasterio**: Working with raster data
# - **pysal**: Spatial analysis library