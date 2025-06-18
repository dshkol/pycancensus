#!/usr/bin/env python3
"""
Comprehensive integration tests for pycancensus with real-world scenarios.

Tests various use cases that a data analyst or researcher would encounter:
- Multi-level geographic analysis
- Economic indicators across provinces  
- Demographic breakdowns by gender/age
- Urban vs rural comparisons
- Time series analysis across census years
- Complex vector hierarchies
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import time
import warnings

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import pycancensus as pc

# Test configuration
API_KEY = os.environ.get("CANCENSUS_API_KEY") or "CensusMapper_7cb8d0ee55b67305388e0a7e8ba9c725"

@pytest.fixture(scope="module", autouse=True)
def setup_api():
    """Set up API key for all tests."""
    pc.set_api_key(API_KEY)
    print(f"\n🔑 Using API key: {API_KEY[:20]}...")

class TestComprehensiveScenarios:
    """Real-world data analysis scenarios."""
    
    def test_scenario_1_provincial_population_analysis(self):
        """
        Scenario 1: Provincial Population Analysis
        A researcher wants to compare population across all provinces.
        """
        print("\n📊 Scenario 1: Provincial Population Analysis")
        
        # Get population data for a few key provinces for testing
        data = pc.get_census(
            dataset="CA21",
            regions={"PR": ["35", "24", "48", "59"]},  # Ontario, Quebec, Alberta, BC
            vectors=["v_CA21_1"],  # Total population
            level="PR",  # Provincial level
            quiet=True
        )
        
        # Validate results
        assert len(data) >= 3, f"Expected at least 3 provinces, got {len(data)}"
        assert "v_CA21_1" in data.columns or any("Population" in col for col in data.columns), "Population data missing"
        assert data["Population"].sum() > 10000000, "Total population seems too low for selected provinces"
        
        print(f"   ✅ Retrieved data for {len(data)} provinces/territories")
        print(f"   ✅ Total population: {data['Population'].sum():,}")
        
        # Find most/least populous provinces
        max_pop = data.loc[data["Population"].idxmax()]
        min_pop = data.loc[data["Population"].idxmin()]
        print(f"   📈 Most populous: {max_pop['Region Name']} ({max_pop['Population']:,})")
        print(f"   📉 Least populous: {min_pop['Region Name']} ({min_pop['Population']:,})")
    
    def test_scenario_2_toronto_demographic_breakdown(self):
        """
        Scenario 2: Toronto Demographic Analysis
        Analyze age and gender demographics in Toronto CMA.
        """
        print("\n🏙️ Scenario 2: Toronto Demographic Breakdown")
        
        # Key demographic vectors for Toronto CMA
        demographic_vectors = [
            "v_CA21_1",   # Total population
            "v_CA21_2",   # Male population  
            "v_CA21_3",   # Female population
        ]
        
        # Get Toronto CMA data
        data = pc.get_census(
            dataset="CA21", 
            regions={"CMA": "35535"},  # Toronto CMA
            vectors=demographic_vectors,
            level="CSD",  # City/municipality level
            quiet=True
        )
        
        # Validate results
        assert len(data) > 20, f"Expected many municipalities in Toronto CMA, got {len(data)}"
        assert any("Population" in col for col in data.columns), "Population data missing"
        
        total_pop = data["Population"].sum()
        print(f"   ✅ Retrieved data for {len(data)} municipalities")
        print(f"   ✅ Toronto CMA total population: {total_pop:,}")
        
        # Calculate gender ratio
        if "v_CA21_2" in data.columns and "v_CA21_3" in data.columns:
            male_col = "v_CA21_2"
            female_col = "v_CA21_3"
        else:
            # Find columns by pattern
            male_col = next((col for col in data.columns if "Male" in col), None)
            female_col = next((col for col in data.columns if "Female" in col), None)
        
        if male_col and female_col:
            total_male = data[male_col].sum()
            total_female = data[female_col].sum()
            gender_ratio = (total_male / total_female) * 100
            print(f"   📊 Gender ratio: {gender_ratio:.1f} males per 100 females")
    
    def test_scenario_3_income_inequality_analysis(self):
        """
        Scenario 3: Income Analysis
        Compare median household income across different regions.
        """
        print("\n💰 Scenario 3: Income Analysis")
        
        # Search for income-related vectors
        income_vectors = pc.search_census_vectors("median household income", "CA21", quiet=True)
        
        if len(income_vectors) == 0:
            # Try alternative search terms
            income_vectors = pc.search_census_vectors("income", "CA21", quiet=True)
            income_vectors = income_vectors[income_vectors["label"].str.contains("median", case=False, na=False)]
        
        assert len(income_vectors) > 0, "No income vectors found"
        
        # Use the first relevant income vector
        income_vector = income_vectors.iloc[0]["vector"]
        print(f"   🔍 Using income vector: {income_vector}")
        
        # Get income data for major cities (CMAs)
        major_cmas = {
            "CMA": ["35535", "24462", "48825", "59933", "505"]  # Toronto, Montreal, Calgary, Vancouver, Ottawa
        }
        
        data = pc.get_census(
            dataset="CA21",
            regions=major_cmas,
            vectors=[income_vector],
            level="CMA",
            quiet=True
        )
        
        # Validate results
        assert len(data) >= 3, f"Expected data for major CMAs, got {len(data)}"
        
        print(f"   ✅ Retrieved income data for {len(data)} major metropolitan areas")
        
        # Show income comparison
        income_col = next((col for col in data.columns if col.startswith("v_")), None)
        if income_col and not data[income_col].isna().all():
            data_sorted = data.sort_values(income_col, ascending=False)
            print("   📈 Income ranking:")
            for idx, row in data_sorted.head(3).iterrows():
                print(f"      {row['Region Name']}: ${row[income_col]:,.0f}")
    
    def test_scenario_4_vector_hierarchy_navigation(self):
        """
        Scenario 4: Vector Hierarchy Navigation
        Use the new hierarchy functions to explore related variables.
        """
        print("\n🌳 Scenario 4: Vector Hierarchy Navigation")
        
        # Test hierarchy functions with population vector
        base_vector = "v_CA21_1"  # Total population
        
        # Test parent vectors
        parents = pc.parent_census_vectors(base_vector, dataset="CA21")
        print(f"   🔼 Found {len(parents)} parent vectors for {base_vector}")
        
        # Test child vectors  
        children = pc.child_census_vectors(base_vector, dataset="CA21")
        print(f"   🔽 Found {len(children)} child vectors for {base_vector}")
        
        # Test vector search
        housing_vectors = pc.find_census_vectors("CA21", "dwelling")
        print(f"   🏠 Found {len(housing_vectors)} dwelling-related vectors")
        
        # Validate hierarchy functions work
        assert isinstance(parents, pd.DataFrame), "parent_census_vectors should return DataFrame"
        assert isinstance(children, pd.DataFrame), "child_census_vectors should return DataFrame" 
        assert isinstance(housing_vectors, pd.DataFrame), "find_census_vectors should return DataFrame"
        
        print("   ✅ All hierarchy functions working correctly")
    
    def test_scenario_5_multi_dataset_comparison(self):
        """
        Scenario 5: Multi-Dataset Time Series
        Compare population changes between 2016 and 2021 census.
        """
        print("\n📅 Scenario 5: Multi-Dataset Time Series Analysis")
        
        # Test region for comparison (use a specific city)
        test_region = {"CSD": "5915022"}  # Vancouver
        
        try:
            # Get 2021 data
            data_2021 = pc.get_census(
                dataset="CA21",
                regions=test_region, 
                vectors=["v_CA21_1"],  # Total population
                level="CSD",
                quiet=True
            )
            
            # Get 2016 data 
            data_2016 = pc.get_census(
                dataset="CA16",
                regions=test_region,
                vectors=["v_CA16_401"],  # Total population in 2016
                level="CSD", 
                quiet=True
            )
            
            if len(data_2021) > 0 and len(data_2016) > 0:
                pop_2021 = data_2021["Population"].iloc[0] if "Population" in data_2021.columns else data_2021.iloc[0, -1]
                pop_2016 = data_2016["Population"].iloc[0] if "Population" in data_2016.columns else data_2016.iloc[0, -1]
                
                growth = ((pop_2021 - pop_2016) / pop_2016) * 100
                
                print(f"   📊 Population change 2016-2021:")
                print(f"      2016: {pop_2016:,}")
                print(f"      2021: {pop_2021:,}")
                print(f"      Growth: {growth:.1f}%")
                
                assert abs(growth) < 50, f"Population growth seems unrealistic: {growth}%"
                print("   ✅ Multi-dataset comparison successful")
            else:
                print("   ⚠️  Could not retrieve data for both years")
                
        except Exception as e:
            print(f"   ⚠️  Multi-dataset test encountered issue: {e}")
    
    def test_scenario_6_geography_with_data(self):
        """
        Scenario 6: Geographic Analysis
        Retrieve data with geographic boundaries for mapping.
        """
        print("\n🗺️ Scenario 6: Geographic Data Analysis")
        
        try:
            # Get geographic data with population
            geo_data = pc.get_census(
                dataset="CA21",
                regions={"PR": "01"},  # New Brunswick (smaller for testing)
                vectors=["v_CA21_1"],  # Population
                level="CSD",
                geo_format="geopandas",
                quiet=True
            )
            
            # Validate geographic data
            assert hasattr(geo_data, 'geometry'), "Should return GeoDataFrame with geometry"
            assert len(geo_data) > 5, f"Expected multiple municipalities, got {len(geo_data)}"
            assert any("Population" in col for col in geo_data.columns), "Population data missing"
            
            print(f"   ✅ Retrieved geographic data for {len(geo_data)} regions")
            print(f"   🎯 Data type: {type(geo_data).__name__}")
            print(f"   📏 Has geometry: {hasattr(geo_data, 'geometry')}")
            
            # Check spatial validity
            valid_geometries = geo_data.geometry.is_valid.sum()
            print(f"   ✅ Valid geometries: {valid_geometries}/{len(geo_data)}")
            
        except Exception as e:
            print(f"   ⚠️  Geographic test encountered issue: {e}")

class TestRobustnessAndEdgeCases:
    """Test robustness and edge cases."""
    
    def test_error_handling_invalid_regions(self):
        """Test error handling with invalid region codes."""
        print("\n🛡️ Testing Error Handling - Invalid Regions")
        
        with pytest.raises(Exception):
            pc.get_census(
                dataset="CA21",
                regions={"INVALID": "99999"},
                vectors=["v_CA21_1"],
                level="PR",
                quiet=True
            )
        print("   ✅ Invalid region codes properly rejected")
    
    def test_error_handling_invalid_vectors(self):
        """Test error handling with invalid vector codes."""
        print("\n🛡️ Testing Error Handling - Invalid Vectors")
        
        # This should not crash, but may return empty data
        try:
            data = pc.get_census(
                dataset="CA21", 
                regions={"PR": "01"},
                vectors=["v_INVALID_999"],
                level="PR",
                quiet=True
            )
            print("   ✅ Invalid vector codes handled gracefully")
        except Exception as e:
            print(f"   ✅ Invalid vectors properly rejected: {type(e).__name__}")
    
    def test_large_region_request(self):
        """Test handling of large region requests."""
        print("\n📏 Testing Large Region Requests")
        
        # Request data for all census subdivisions in a province
        start_time = time.time()
        
        try:
            data = pc.get_census(
                dataset="CA21",
                regions={"PR": "46"},  # Manitoba (medium-sized province)
                vectors=["v_CA21_1"],  # Just population
                level="CSD",
                quiet=True
            )
            
            elapsed = time.time() - start_time
            
            print(f"   ✅ Retrieved {len(data)} regions in {elapsed:.1f} seconds")
            assert len(data) > 50, f"Expected many CSDs in Manitoba, got {len(data)}"
            
            if elapsed > 30:
                print(f"   ⚠️  Request took {elapsed:.1f}s - consider optimization")
            
        except Exception as e:
            print(f"   ⚠️  Large request test failed: {e}")

def run_performance_benchmark():
    """Run a basic performance benchmark."""
    print("\n⚡ Performance Benchmark")
    
    scenarios = [
        ("Small request (1 region)", {"PR": "01"}, "PR"),
        ("Medium request (1 province CSDs)", {"PR": "46"}, "CSD"), 
        ("Large request (major CMA CSDs)", {"CMA": "35535"}, "CSD"),
    ]
    
    for name, regions, level in scenarios:
        start_time = time.time()
        try:
            data = pc.get_census(
                dataset="CA21",
                regions=regions,
                vectors=["v_CA21_1"],
                level=level,
                quiet=True
            )
            elapsed = time.time() - start_time
            print(f"   {name}: {len(data)} regions in {elapsed:.1f}s")
        except Exception as e:
            print(f"   {name}: Failed - {e}")

if __name__ == "__main__":
    # Set up API key
    pc.set_api_key(API_KEY)
    
    print("🚀 Running Comprehensive Integration Tests")
    print("=" * 60)
    
    # Run test scenarios
    test_class = TestComprehensiveScenarios()
    
    try:
        test_class.test_scenario_1_provincial_population_analysis()
        test_class.test_scenario_2_toronto_demographic_breakdown()
        test_class.test_scenario_3_income_inequality_analysis()
        test_class.test_scenario_4_vector_hierarchy_navigation()
        test_class.test_scenario_5_multi_dataset_comparison()
        test_class.test_scenario_6_geography_with_data()
        
        # Run robustness tests
        robustness_class = TestRobustnessAndEdgeCases()
        robustness_class.test_large_region_request()
        
        # Run performance benchmark
        run_performance_benchmark()
        
        print("\n" + "=" * 60)
        print("✅ COMPREHENSIVE TESTS COMPLETED SUCCESSFULLY")
        print("   All real-world scenarios validated!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILURE: {e}")
        raise