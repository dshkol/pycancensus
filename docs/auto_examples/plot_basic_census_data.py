"""
Basic Census Data Access
=========================

This example demonstrates how to access Canadian Census data using pycancensus,
covering the essential functions for getting started with census data analysis.
"""

# %%
# Setting up pycancensus
# ----------------------
# 
# First, we need to import pycancensus and set up our API key.
# You can get a free API key at: https://censusmapper.ca/users/sign_up

import pycancensus as pc
import pandas as pd

# Set your API key (you'll need to replace this with your actual key)
import os
api_key = os.environ.get('CANCENSUS_API_KEY')
if api_key:
    pc.set_api_key(api_key)
    print("API key configured")
else:
    print("No API key - examples will show code structure")
    print("Get your API key at: https://censusmapper.ca/users/sign_up")

# %%
# Exploring Available Datasets
# -----------------------------
# 
# Let's start by exploring what Census datasets are available.

print("Available Census Datasets:")
try:
    datasets = pc.list_census_datasets()
    print(datasets)
except Exception as e:
    print(f"Error accessing datasets: {e}")
    print("Make sure you have set your API key!")

# %%
# Finding Census Regions
# -----------------------
# 
# Next, let's explore the geographic regions available in the Census.

print("\nExploring Census Regions:")
try:
    # Get regions for the 2021 Census
    regions = pc.list_census_regions("CA21")
    print(f"Found {len(regions)} regions in CA21 dataset")
    print("\nSample regions:")
    print(regions.head())
    
    # Search for specific regions (Vancouver)
    print("\nSearching for Vancouver regions:")
    vancouver_regions = pc.search_census_regions("Vancouver", "CA21")
    print(vancouver_regions[["region", "name", "level", "pop"]].head())
    
except Exception as e:
    print(f"Error accessing regions: {e}")

# %%
# Discovering Census Variables
# ----------------------------
# 
# Census data is organized into vectors (variables). Let's explore what's available.

print("\nExploring Census Variables:")
try:
    # List available vectors
    vectors = pc.list_census_vectors("CA21")
    print(f"Found {len(vectors)} vectors in CA21 dataset")
    print("\nSample vectors:")
    print(vectors[["vector", "label", "type"]].head())
    
    # Search for population-related vectors
    print("\nSearching for population vectors:")
    pop_vectors = pc.search_census_vectors("population", "CA21")
    print(pop_vectors[["vector", "label", "type"]].head())
    
except Exception as e:
    print(f"Error accessing vectors: {e}")

# %%
# Getting Census Data
# -------------------
# 
# Now let's retrieve actual census data for analysis.

print("\nRetrieving Census Data:")
try:
    # Get population data for Vancouver CMA
    data = pc.get_census(
        dataset="CA21",
        regions={"CMA": "59933"},  # Vancouver CMA
        vectors=["v_CA21_1", "v_CA21_2"],  # Population vectors
        level="CSD"  # Census Subdivision level
    )
    
    print(f"Retrieved data shape: {data.shape}")
    print("\nSample data:")
    print(data.head())
    
    # Basic analysis
    if not data.empty and 'v_CA21_1' in data.columns:
        total_pop = data['v_CA21_1'].sum()
        print(f"\nTotal population in Vancouver CMA: {total_pop:,}")
        
except Exception as e:
    print(f"Error retrieving census data: {e}")

# %%
# Working with Geographic Data
# ----------------------------
# 
# pycancensus can also retrieve geographic boundaries along with the data.

print("\nRetrieving Geographic Data:")
try:
    # Get census data with geographic boundaries
    geo_data = pc.get_census(
        dataset="CA21",
        regions={"CMA": "59933"},  # Vancouver CMA
        vectors=["v_CA21_1"],  # Population
        level="CSD",
        geo_format="geopandas"
    )
    
    print(f"GeoDataFrame shape: {geo_data.shape}")
    print(f"Columns: {list(geo_data.columns)}")
    if hasattr(geo_data, 'crs'):
        print(f"Coordinate Reference System: {geo_data.crs}")
    
    # Just the geometries
    geometries = pc.get_census_geometry(
        dataset="CA21",
        regions={"CMA": "59933"},
        level="CSD"
    )
    print(f"\nGeometries-only shape: {geometries.shape}")
    
except Exception as e:
    print(f"Error retrieving geographic data: {e}")

# %%
# Vector Hierarchy Navigation
# ---------------------------
# 
# pycancensus provides tools to navigate the hierarchical structure of census variables.

print("\nVector Hierarchy Navigation:")
try:
    # Find vectors using enhanced search
    income_vectors = pc.find_census_vectors("CA21", "income")
    print(f"Found {len(income_vectors)} income-related vectors")
    
    # Navigate vector hierarchies using household income as example
    # This demonstrates a real hierarchy: main category -> income brackets -> sub-brackets
    income_parent = "v_CA21_923"  # Household total income groups in 2020
    high_income_bracket = "v_CA21_939"  # $100,000 and over bracket
    
    # Find children of main income vector (all income brackets)
    income_brackets = pc.child_census_vectors(income_parent, dataset="CA21")
    print(f"Income brackets under '{income_parent}': {len(income_brackets)} categories")
    
    # Find grandchildren (sub-categories of high income bracket)  
    high_income_subcats = pc.child_census_vectors(high_income_bracket, dataset="CA21")
    print(f"High-income sub-categories: {len(high_income_subcats)} levels")
    
    # Find parent relationship (child -> parent navigation)
    parent_of_bracket = pc.parent_census_vectors(high_income_bracket, dataset="CA21")
    if not parent_of_bracket.empty:
        print(f"Parent of '{high_income_bracket}': {parent_of_bracket['vector'].iloc[0]}")
    
except Exception as e:
    print(f"Error with vector operations: {e}")

# %%
# Summary
# -------
# 
# This example covered the basic workflow for accessing Canadian Census data:
# 
# 1. **Setup**: Import pycancensus and set your API key
# 2. **Explore**: Discover available datasets, regions, and variables
# 3. **Retrieve**: Get census data for your areas and variables of interest
# 4. **Analyze**: Work with the data using pandas/geopandas workflows
# 
# For more advanced examples, see the other gallery examples and tutorials.

print("\n" + "="*50)
print("Basic Census Data Access Example Complete")
print("="*50)
print("\nNext steps:")
print("1. Get your free API key at: https://censusmapper.ca/users/sign_up")
print("2. Set your API key: pc.set_api_key('your_key_here')")  
print("3. Try running this example with real data!")
print("4. Explore the other examples in the gallery")