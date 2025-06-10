#!/usr/bin/env python3
"""
Notebook debug script - test the exact same call that would be used in the housing analysis notebook.
This specifically tests the geo_format='geopandas' scenario that the notebook uses.
"""

import sys
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

def main():
    print("🔬 NOTEBOOK DEBUG - Testing exact notebook scenario")
    print("=" * 60)
    
    # Fresh import and cache clear (simulate notebook restart)
    print("🔄 Step 1: Fresh import and cache clear...")
    import pycancensus as pc
    
    try:
        pc.clear_cache()
        print("✅ Cache cleared")
    except Exception as e:
        print(f"⚠️  Cache clear issue: {e}")
    
    # Check API key
    api_key_status = pc.get_api_key()
    print(f"🔑 API key status: {'✅ Set' if api_key_status else '❌ Not set'}")
    
    if not api_key_status:
        print("❌ No API key found. Please set with pc.set_api_key('your_key')")
        return
    
    # Test the EXACT scenario from the notebook
    print("\n🔄 Step 2: Testing notebook scenario - geo_format='geopandas'...")
    
    # Define the exact parameters from the notebook
    VANCOUVER_CMA = '59933'
    
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
    
    try:
        # This is the EXACT call from the notebook that was failing
        print("📍 Making the exact API call from the notebook...")
        vancouver_2016 = pc.get_census(
            dataset='CA16',
            regions={'CMA': VANCOUVER_CMA},
            vectors=all_vectors_2016,
            level='CSD',  # Census Subdivision level
            geo_format='geopandas'  # THIS is what the notebook uses!
        )
        
        print(f"✅ Data loaded: {vancouver_2016.shape[0]} regions, {vancouver_2016.shape[1]} columns")
        
        # Debug the column names and types
        print(f"\n📋 Column Analysis:")
        print(f"All columns: {list(vancouver_2016.columns)}")
        
        print(f"\n📊 Data Types:")
        for col, dtype in vancouver_2016.dtypes.items():
            print(f"   {col}: {dtype}")
        
        # Test the specific operations that were failing in the notebook
        print(f"\n🧪 Testing notebook operations...")
        
        # 1. Test population column access
        pop_columns = [col for col in vancouver_2016.columns if 'pop' in col.lower()]
        print(f"Population-related columns: {pop_columns}")
        
        # Test different possible pop column names
        pop_col = None
        for possible_name in ['pop', 'Population', 'Population ']:
            if possible_name in vancouver_2016.columns:
                pop_col = possible_name
                break
        
        if pop_col:
            print(f"   Found population column: '{pop_col}' (type: {vancouver_2016[pop_col].dtype})")
            
            # Test the exact operation from the notebook
            try:
                total_pop = vancouver_2016[pop_col].sum()
                print(f"   ✅ vancouver_2016['{pop_col}'].sum() = {total_pop:,}")
                
                # Test if it's numeric
                if pd.api.types.is_numeric_dtype(vancouver_2016[pop_col]):
                    print(f"   ✅ Population column is properly numeric")
                else:
                    print(f"   ❌ Population column is NOT numeric: {vancouver_2016[pop_col].dtype}")
                    print(f"   Sample values: {vancouver_2016[pop_col].head(3).tolist()}")
                    
            except Exception as e:
                print(f"   ❌ vancouver_2016['{pop_col}'].sum() FAILED: {e}")
                print(f"   Sample values: {vancouver_2016[pop_col].head(3).tolist()}")
        else:
            print("   ❌ No population column found!")
        
        # 2. Test area column
        area_columns = [col for col in vancouver_2016.columns if 'a' == col or 'Area' in col]
        print(f"\n📏 Area columns: {area_columns}")
        
        if area_columns:
            area_col = area_columns[0]
            try:
                total_area = vancouver_2016[area_col].sum()
                print(f"   ✅ vancouver_2016['{area_col}'].sum() = {total_area:.1f}")
            except Exception as e:
                print(f"   ❌ Area sum failed: {e}")
        
        # 3. Test vector columns
        vector_columns = [col for col in vancouver_2016.columns if col.startswith('v_')]
        print(f"\n📊 Vector columns ({len(vector_columns)} found):")
        
        numeric_vectors = 0
        string_vectors = 0
        
        for col in vector_columns[:3]:  # Test first 3
            dtype = vancouver_2016[col].dtype
            if pd.api.types.is_numeric_dtype(vancouver_2016[col]):
                numeric_vectors += 1
                status = "✅ numeric"
            else:
                string_vectors += 1
                status = "❌ string"
            print(f"   {col[:50]}... : {dtype} ({status})")
        
        print(f"\n📈 Vector Summary:")
        print(f"   Total vector columns: {len(vector_columns)}")
        print(f"   Numeric: {numeric_vectors} ✅")
        print(f"   String: {string_vectors} {'❌' if string_vectors > 0 else '✅'}")
        
        # 4. Test geography
        print(f"\n🗺️  Geography:")
        print(f"   Has geometry column: {'geometry' in vancouver_2016.columns}")
        print(f"   CRS: {vancouver_2016.crs if vancouver_2016.crs else 'None specified'}")
        
        # 5. Final assessment
        print(f"\n🎯 FINAL ASSESSMENT:")
        if pop_col and pd.api.types.is_numeric_dtype(vancouver_2016[pop_col]):
            print("✅ Population column working correctly")
        else:
            print("❌ Population column issue persists")
            
        if len(vector_columns) > 0 and numeric_vectors > 0:
            print("✅ Vector columns present and numeric")
        else:
            print("❌ Vector column issues")
            
        if 'geometry' in vancouver_2016.columns:
            print("✅ Geographic data present")
        else:
            print("❌ Geographic data missing")
            
        # Test the exact notebook operation that was failing
        print(f"\n🔥 TESTING EXACT NOTEBOOK FAILURE SCENARIO:")
        try:
            # This is likely what was failing in the notebook
            total_pop = vancouver_2016['pop'].sum()
            print(f"✅ vancouver_2016['pop'].sum() = {total_pop:,}")
            print("🎉 NOTEBOOK ISSUE RESOLVED!")
        except KeyError:
            print("❌ 'pop' column not found - checking alternatives...")
            for alt_col in ['Population', 'Population ']:
                if alt_col in vancouver_2016.columns:
                    try:
                        total_pop = vancouver_2016[alt_col].sum()
                        print(f"✅ vancouver_2016['{alt_col}'].sum() = {total_pop:,}")
                        print(f"💡 Use '{alt_col}' instead of 'pop' in notebook")
                        break
                    except Exception as e:
                        print(f"❌ vancouver_2016['{alt_col}'].sum() failed: {e}")
        except Exception as e:
            print(f"❌ vancouver_2016['pop'].sum() failed: {e}")
            
    except Exception as e:
        print(f"❌ API call failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "=" * 60)
    print("🔬 Notebook debug completed!")

if __name__ == "__main__":
    main()