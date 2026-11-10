#!/usr/bin/env python3
"""
Basic usage examples for pycancensus.

This script demonstrates how to use the main functions of pycancensus
to access Canadian Census data and geography.
"""

import pycancensus as pc


def main():
    """Run basic usage examples."""
    
    # Set API key (replace with your actual key)
    # You can get a free key at: https://censusmapper.ca/users/sign_up
    # pc.set_api_key("your_api_key_here")
    
    print("=== pycancensus Basic Usage Examples ===\n")
    
    # Example 1: List available datasets
    print("1. Available Census datasets:")
    try:
        datasets = pc.list_census_datasets()
        print(datasets)
        print()
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure you have set your API key with pc.set_api_key()")
        return
    
    # Example 2: List regions for 2016 Census
    print("2. Sample regions from 2016 Census:")
    try:
        regions = pc.list_census_regions("CA16")
        print(regions.head())
        print(f"Total regions: {len(regions)}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 3: Search for Vancouver regions
    print("3. Searching for Vancouver regions:")
    try:
        vancouver_regions = pc.search_census_regions("Vancouver", "CA16")
        print(vancouver_regions[["region", "name", "level", "pop"]])
        print()
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 4: List some census vectors
    print("4. Sample census vectors from 2016 Census:")
    try:
        vectors = pc.list_census_vectors("CA16")
        print(vectors.head())
        print(f"Total vectors: {len(vectors)}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 5: Search for population vectors
    print("5. Searching for population vectors:")
    try:
        pop_vectors = pc.search_census_vectors("population", "CA16")
        print(pop_vectors[["vector", "label", "type"]].head())
        print()
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 5a: Vector search and hierarchy navigation
    print("5a. Vector search and hierarchy navigation:")
    try:
        # Query first, then dataset (same order as R cancensus)
        income_vectors = pc.find_census_vectors("income", "CA16", query_type="keyword")
        print(f"Found {len(income_vectors)} income-related vectors")
        
        # Navigate vector hierarchies  
        base_vector = "v_CA16_2510"  # Low-income status total
        parents = pc.parent_census_vectors(base_vector, dataset="CA16")
        children = pc.child_census_vectors(base_vector, dataset="CA16") 
        print(f"Vector {base_vector}: {len(parents)} parents, {len(children)} children")
        print()
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 6: Get census data (no geometry)
    print("6. Getting census data for Vancouver CMA:")
    try:
        data = pc.get_census(
            dataset="CA21",  # Updated to latest census
            regions={"CMA": "59933"},  # Vancouver CMA
            vectors=["v_CA21_1", "v_CA21_2"],  # Population 2021 and 2016
            level="CSD",  # Census Subdivision level
            labels="detailed",  # column names include the variable label
        )
        print(data.head())
        print(f"Data shape: {data.shape}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 7: Get census data with geometry
    print("7. Getting census data with geometry:")
    try:
        geo_data = pc.get_census(
            dataset="CA21",  # Updated to latest census
            regions={"CMA": "59933"},  # Vancouver CMA  
            vectors=["v_CA21_1"],  # Total population
            level="CSD",
            geo_format="geopandas",
            labels="short",  # vector columns named by code, e.g. v_CA21_1
        )
        print(f"GeoDataFrame shape: {geo_data.shape}")
        print(f"Columns: {list(geo_data.columns)}")
        print(f"CRS: {geo_data.crs}")
        print()
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 8: Get just geometry
    print("8. Getting census geometries only:")
    try:
        geometries = pc.get_census_geometry(
            dataset="CA21",  # Updated to latest census
            regions={"CMA": "59933"},
            level="CSD"
        )
        print(f"Geometries shape: {geometries.shape}")
        print(f"Columns: {list(geometries.columns)}")
        print()
    except Exception as e:
        print(f"Error: {e}\n")
    
    # Example 9: labelled columns, French labels and named vectors (0.3.0)
    print("9. Labelled columns, French labels and named vectors:")
    try:
        labelled = pc.get_census(
            dataset="CA21",
            regions={"CMA": "59933"},
            vectors={"pop": "v_CA21_1", "median_hh_income": "v_CA21_906"},
            level="CSD",
            labels="labelled",  # standard column names, labels in attrs
            language="fr",
        )
        print(f"Columns: {list(labelled.columns)}")
        labels = labelled.attrs["column_labels"]
        print(f"Label of median_hh_income: {labels['median_hh_income']}")
        print()
    except Exception as e:
        print(f"Error: {e}\n")

    print("=== Examples complete ===")
    print("\nNew in 0.3.0:")
    print("- French labels (language='fr') and labels='labelled'")
    print("- Named vectors, e.g. vectors={'pop': 'v_CA21_1'}")
    print("- All CensusMapper datasets, including TX2018 and CA16xSD")
    print("\nTo run these examples with real data:")
    print("1. Get a free API key at: https://censusmapper.ca/users/sign_up")
    print("2. Set your API key: pc.set_api_key('your_key_here')")
    print("3. Run this script again")


if __name__ == "__main__":
    main()