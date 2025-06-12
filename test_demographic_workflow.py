#!/usr/bin/env python3
"""
Test the demographic embeddings workflow to identify issues
"""

import numpy as np
import pandas as pd
import pycancensus as pc

# Test vectors (subset for faster testing)
visible_minority_2016 = {
    'v_CA16_3954': 'Total_Population_VM',
    'v_CA16_3957': 'South_Asian',
    'v_CA16_3960': 'Chinese', 
    'v_CA16_3963': 'Black',
}

visible_minority_2021 = {
    'v_CA21_4872': 'Total_Population_VM',
    'v_CA21_4875': 'South_Asian',
    'v_CA21_4878': 'Chinese',
    'v_CA21_4881': 'Black', 
}

population_vectors = {
    2016: 'v_CA16_1',
    2021: 'v_CA21_1'
}

def collect_census_data(year, vectors, population_vector, min_population=50000):
    """
    Collect census data for Canadian cities above minimum population threshold
    """
    print(f"Collecting {year} Census data...")
    
    # Use subset of provinces for testing
    test_provinces = ['35', '24', '48']  # Ontario, Quebec, Alberta
    
    data = pc.get_census(
        dataset=f'CA{str(year)[2:]}',
        regions={'PR': test_provinces},
        vectors=list(vectors.keys()) + [population_vector],
        level='CSD',
        use_cache=True
    )
    
    print(f"Raw data shape: {data.shape}")
    
    # Handle column name variations
    if 'Population ' in data.columns:
        data.rename(columns={'Population ': 'pop'}, inplace=True)
    elif 'Population' in data.columns:
        data.rename(columns={'Population': 'pop'}, inplace=True)
    
    # Filter for minimum population
    data = data[data['pop'] >= min_population].copy()
    print(f"After population filter: {data.shape}")
    
    # Calculate proportions
    print("Calculating proportions...")
    proportion_count = 0
    for vector_code, group_name in vectors.items():
        matching_cols = [col for col in data.columns if col.startswith(vector_code)]
        
        if matching_cols:
            actual_col = matching_cols[0]
            prop_col_name = f'{group_name}_prop'
            data[prop_col_name] = data[actual_col] / data['pop']
            proportion_count += 1
            print(f"  Created {prop_col_name}")
        else:
            print(f"  WARNING: Vector {vector_code} ({group_name}) not found")
    
    print(f"Created {proportion_count} proportion columns")
    
    # Add year identifier
    data['year'] = year
    
    # Show proportion columns
    prop_cols = [col for col in data.columns if col.endswith('_prop')]
    print(f"Proportion columns: {prop_cols}")
    
    return data

def harmonize_data(data_2016, data_2021):
    """
    Harmonize datasets and filter to cities present in both years
    """
    print("\n" + "="*50)
    print("HARMONIZATION DEBUG")
    print("="*50)
    
    print(f"2016 data shape: {data_2016.shape}")
    print(f"2021 data shape: {data_2021.shape}")
    
    # Get proportion columns
    prop_cols_2016 = [col for col in data_2016.columns if col.endswith('_prop')]
    prop_cols_2021 = [col for col in data_2021.columns if col.endswith('_prop')]
    
    print(f"2016 proportion columns: {prop_cols_2016}")
    print(f"2021 proportion columns: {prop_cols_2021}")
    
    # Find common proportion columns
    common_prop_cols = set(prop_cols_2016) & set(prop_cols_2021)
    prop_cols = list(common_prop_cols)
    
    print(f"Common proportion columns: {prop_cols}")
    
    if not prop_cols:
        print("ERROR: No common proportion columns found!")
        return None, []
    
    # Key columns to keep
    keep_cols = ['GeoUID', 'Region Name', 'pop', 'year'] + prop_cols
    
    # Subset both datasets
    df_2016 = data_2016[keep_cols].copy()
    df_2021 = data_2021[keep_cols].copy()
    
    # Find cities present in both years
    common_cities = set(df_2016['GeoUID']) & set(df_2021['GeoUID'])
    print(f"Cities in both years: {len(common_cities)}")
    
    # Filter to common cities
    df_2016 = df_2016[df_2016['GeoUID'].isin(common_cities)]
    df_2021 = df_2021[df_2021['GeoUID'].isin(common_cities)]
    
    # Combine datasets
    combined_data = pd.concat([df_2016, df_2021], ignore_index=True)
    
    print(f"Combined dataset shape: {combined_data.shape}")
    print(f"SUCCESS: Harmonization complete")
    
    return combined_data, prop_cols

def main():
    print("TESTING DEMOGRAPHIC EMBEDDINGS WORKFLOW")
    print("="*60)
    
    # Collect data
    data_2016 = collect_census_data(2016, visible_minority_2016, population_vectors[2016])
    data_2021 = collect_census_data(2021, visible_minority_2021, population_vectors[2021])
    
    # Harmonize
    combined_data, demographic_cols = harmonize_data(data_2016, data_2021)
    
    # Test feature preparation
    if combined_data is not None and demographic_cols:
        print(f"\n✅ SUCCESS: Ready for embedding")
        print(f"   Combined data shape: {combined_data.shape}")
        print(f"   Demographic columns: {demographic_cols}")
        print(f"   Feature matrix would be: ({len(combined_data)}, {len(demographic_cols)})")
    else:
        print(f"\n❌ FAILURE: Cannot proceed to embedding")
        print(f"   combined_data is None: {combined_data is None}")
        print(f"   demographic_cols empty: {not demographic_cols}")

if __name__ == "__main__":
    main()