#!/usr/bin/env python3
"""
Debug script for housing analysis - converted from Jupyter notebook.
This script tests the pycancensus package functionality for debugging.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Import pycancensus
import pycancensus as pc

def main():
    print("🚀 Starting housing analysis debug script...")
    print("=" * 60)
    
    # Check API key status
    api_key_status = pc.get_api_key()
    print(f"🔑 API key status: {'✅ Set' if api_key_status else '❌ Not set'}")
    
    if not api_key_status:
        print("❌ No API key found. Please set with pc.set_api_key('your_key')")
        return
    
    # Define analysis parameters
    VANCOUVER_CMA = '59933'  # Vancouver CMA region code
    
    # Define our analysis vectors (variables of interest)
    housing_vectors_2016 = [
        'v_CA16_408',  # Total occupied private dwellings by structural type
        'v_CA16_409',  # Single-detached house
        'v_CA16_410',  # Apartment building, five or more storeys
        'v_CA16_411',  # Semi-detached house
        'v_CA16_412',  # Row house
        'v_CA16_413',  # Apartment, duplex
        'v_CA16_414',  # Apartment building, fewer than five storeys
    ]
    
    demographic_vectors_2016 = [
        'v_CA16_1',    # Total population
        'v_CA16_6',    # Population aged 0-14
        'v_CA16_11',   # Population aged 15-64
        'v_CA16_16',   # Population aged 65+
    ]
    
    all_vectors_2016 = housing_vectors_2016 + demographic_vectors_2016
    
    print(f"📊 Testing data collection for {len(all_vectors_2016)} variables...")
    print(f"Housing variables: {len(housing_vectors_2016)}")
    print(f"Demographic variables: {len(demographic_vectors_2016)}")
    
    try:
        # Test 1: Basic data collection without geography
        print("\n🔄 Test 1: Fetching basic 2016 Census data (no geography)...")
        vancouver_basic = pc.get_census(
            dataset='CA16',
            regions={'CMA': VANCOUVER_CMA},
            vectors=all_vectors_2016[:3],  # Just test first 3 vectors
            level='CSD',
            quiet=False
        )
        
        print(f"✅ Basic data loaded: {vancouver_basic.shape[0]} regions, {vancouver_basic.shape[1]} columns")
        print(f"📋 Column names: {list(vancouver_basic.columns)}")
        print(f"📊 Data types:")
        for col, dtype in vancouver_basic.dtypes.items():
            print(f"   {col}: {dtype}")
        
        # Test population column specifically
        if 'Population ' in vancouver_basic.columns:
            pop_col = 'Population '
        elif 'Population' in vancouver_basic.columns:
            pop_col = 'Population'
        elif 'pop' in vancouver_basic.columns:
            pop_col = 'pop'
        else:
            pop_col = None
            
        if pop_col:
            print(f"\n📈 Population column analysis:")
            print(f"   Column name: '{pop_col}'")
            print(f"   Data type: {vancouver_basic[pop_col].dtype}")
            print(f"   Total population: {vancouver_basic[pop_col].sum()}")
            print(f"   Sample values: {vancouver_basic[pop_col].head(3).tolist()}")
        else:
            print("❌ No population column found!")
            
        # Test area column
        area_cols = [col for col in vancouver_basic.columns if 'Area' in col or 'a' == col]
        if area_cols:
            area_col = area_cols[0]
            print(f"\n📏 Area column analysis:")
            print(f"   Column name: '{area_col}'")
            print(f"   Data type: {vancouver_basic[area_col].dtype}")
            print(f"   Total area: {vancouver_basic[area_col].sum()}")
        
    except Exception as e:
        print(f"❌ Test 1 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Test 2: Data collection with geography
        print("\n🔄 Test 2: Fetching 2016 Census data with geography...")
        vancouver_geo = pc.get_census(
            dataset='CA16',
            regions={'CMA': VANCOUVER_CMA},
            vectors=all_vectors_2016[:3],  # Just test first 3 vectors
            level='CSD',
            geo_format='geopandas',
            quiet=False
        )
        
        print(f"✅ Geographic data loaded: {vancouver_geo.shape[0]} regions, {vancouver_geo.shape[1]} columns")
        print(f"📍 CRS: {vancouver_geo.crs if vancouver_geo.crs else 'No CRS specified'}")
        print(f"🗺️  Has geometry: {'geometry' in vancouver_geo.columns}")
        
        # Test region names
        if 'name' in vancouver_geo.columns:
            print(f"🏘️  Sample regions: {vancouver_geo['name'].head(3).tolist()}")
        elif 'Region Name' in vancouver_geo.columns:
            print(f"🏘️  Sample regions: {vancouver_geo['Region Name'].head(3).tolist()}")
            
    except Exception as e:
        print(f"❌ Test 2 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Test 3: Data exploration
        print("\n🔄 Test 3: Data exploration and cleaning...")
        df = vancouver_basic.copy()
        
        # Test column renaming and calculations
        column_mapping = {
            'name': 'Region_Name',
            'pop': 'Population_2016',
            'a': 'Area_sqkm',
            'dw': 'Dwellings',
            'hh': 'Households'
        }
        
        # Find actual column names (handle trailing spaces)
        actual_mapping = {}
        for expected, new_name in column_mapping.items():
            # Look for exact match first
            if expected in df.columns:
                actual_mapping[expected] = new_name
            else:
                # Look for match with trailing/leading spaces
                for col in df.columns:
                    if col.strip() == expected:
                        actual_mapping[col] = new_name
                        break
        
        print(f"📋 Column mapping found: {actual_mapping}")
        df = df.rename(columns=actual_mapping)
        
        # Calculate population density if possible
        if 'Population_2016' in df.columns and 'Area_sqkm' in df.columns:
            df['pop_density'] = df['Population_2016'] / df['Area_sqkm']
            df = df.replace([np.inf, -np.inf], np.nan)
            print(f"📊 Population density calculated:")
            print(f"   Average: {df['pop_density'].mean():.1f} people/sq km")
            print(f"   Median: {df['pop_density'].median():.1f} people/sq km")
        else:
            print("❌ Cannot calculate population density - missing columns")
            
        # Summary statistics
        print(f"\n📈 Summary Statistics:")
        if 'Population_2016' in df.columns:
            print(f"   Total population: {df['Population_2016'].sum():,}")
        if 'Area_sqkm' in df.columns:
            print(f"   Total area: {df['Area_sqkm'].sum():.1f} sq km")
        print(f"   Number of regions: {len(df)}")
        
    except Exception as e:
        print(f"❌ Test 3 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # Test 4: Vector columns analysis
        print("\n🔄 Test 4: Analyzing vector columns...")
        vector_columns = [col for col in df.columns if col.startswith('v_')]
        print(f"📊 Found {len(vector_columns)} vector columns:")
        
        for col in vector_columns:
            dtype = df[col].dtype
            sample_vals = df[col].dropna().head(3).tolist()
            print(f"   {col}: {dtype} - samples: {sample_vals}")
            
        # Check if numeric conversion worked
        numeric_vectors = [col for col in vector_columns if pd.api.types.is_numeric_dtype(df[col])]
        string_vectors = [col for col in vector_columns if not pd.api.types.is_numeric_dtype(df[col])]
        
        print(f"✅ Numeric vector columns: {len(numeric_vectors)}")
        print(f"❌ String vector columns: {len(string_vectors)}")
        
        if string_vectors:
            print(f"   String vectors that should be numeric: {string_vectors}")
            
    except Exception as e:
        print(f"❌ Test 4 failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n🎯 DEBUG SUMMARY:")
    print("=" * 60)
    print("✅ Basic API functionality working")
    if pop_col and pd.api.types.is_numeric_dtype(vancouver_basic[pop_col]):
        print("✅ Population column is numeric")
    else:
        print("❌ Population column data type issue")
    
    if len(numeric_vectors) > 0:
        print("✅ Some vector columns are numeric")
    else:
        print("❌ Vector columns not converting to numeric")
        
    print(f"📊 Ready for full analysis with {len(df)} regions")
    print("\n🚀 Debug script completed!")

if __name__ == "__main__":
    main()