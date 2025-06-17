"""Integration tests for pycancensus compatibility with cancensus R library."""

import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import tempfile
import shutil

import sys
from pathlib import Path

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pycancensus as pc


class TestCancensusCompatibility:
    """Test pycancensus compatibility with cancensus R library results."""
    
    @pytest.fixture(autouse=True)
    def setup_test_env(self):
        """Setup test environment."""
        # Use test API key or skip if not available
        test_api_key = os.environ.get("CANCENSUS_API_KEY")
        if test_api_key:
            pc.set_api_key(test_api_key)
        else:
            pytest.skip("CANCENSUS_API_KEY not set")
        
        # Setup temporary cache directory
        self.temp_cache = tempfile.mkdtemp()
        pc.set_cache_path(self.temp_cache)
        
        yield
        
        # Cleanup
        if os.path.exists(self.temp_cache):
            shutil.rmtree(self.temp_cache)
    
    def test_get_census_basic_functionality(self):
        """Test basic get_census functionality matches expected patterns."""
        # This test uses a small, fast query
        data = pc.get_census(
            dataset="CA21",
            regions={"PR": "59"},  # British Columbia
            vectors=["v_CA21_1"],  # Total population
            level="PR"
        )
        
        # Verify structure matches expected cancensus format
        assert isinstance(data, pd.DataFrame)
        assert "GeoUID" in data.columns
        assert "Type" in data.columns
        assert "Region Name" in data.columns
        assert "v_CA21_1" in data.columns
        
        # Verify data types are appropriate
        assert pd.api.types.is_integer_dtype(data["v_CA21_1"])
        assert isinstance(data["GeoUID"].iloc[0], str)
        
        # Verify basic data integrity
        assert len(data) > 0
        assert not data["v_CA21_1"].isna().all()
    
    def test_get_census_with_geometry(self):
        """Test geometry retrieval functionality."""
        data = pc.get_census(
            dataset="CA21",
            regions={"CSD": "5915022"},  # Vancouver
            vectors=["v_CA21_1"],
            level="CSD",
            geo_format="geopandas"
        )
        
        # Verify geometry is included
        assert hasattr(data, 'geometry')
        assert not data.geometry.isna().all()
        
        # Verify it's a proper GeoDataFrame
        try:
            import geopandas as gpd
            assert isinstance(data, gpd.GeoDataFrame)
        except ImportError:
            pytest.skip("geopandas not available")
    
    def test_list_functions_compatibility(self):
        """Test list functions return expected formats."""
        # Test datasets
        datasets = pc.list_census_datasets()
        assert isinstance(datasets, pd.DataFrame)
        assert "dataset" in datasets.columns
        assert "description" in datasets.columns
        assert len(datasets) > 0
        
        # Test vectors
        vectors = pc.list_census_vectors("CA21")
        assert isinstance(vectors, pd.DataFrame)
        assert "vector" in vectors.columns
        assert "type" in vectors.columns
        assert "label" in vectors.columns
        assert len(vectors) > 0
        
        # Test regions
        regions = pc.list_census_regions("CA21")
        assert isinstance(regions, pd.DataFrame)
        assert "region" in regions.columns
        assert "name" in regions.columns
        assert len(regions) > 0
    
    def test_search_functions(self):
        """Test search functionality."""
        # Search vectors
        vectors = pc.search_census_vectors("CA21", "population")
        assert isinstance(vectors, pd.DataFrame)
        assert len(vectors) > 0
        
        # Search regions
        regions = pc.search_census_regions("CA21", "Vancouver")
        assert isinstance(regions, pd.DataFrame)
        assert len(regions) > 0
    
    def test_error_handling(self):
        """Test error handling matches expected patterns."""
        # Invalid dataset
        with pytest.raises((ValueError, Exception)):
            pc.get_census(
                dataset="INVALID",
                regions={"PR": "59"},
                vectors=["v_CA21_1"],
                level="PR"
            )
        
        # Invalid region
        with pytest.raises((ValueError, Exception)):
            pc.get_census(
                dataset="CA21",
                regions={"PR": "99999"},  # Non-existent region
                vectors=["v_CA21_1"],
                level="PR"
            )
        
        # Invalid vector
        with pytest.raises((ValueError, Exception)):
            pc.get_census(
                dataset="CA21",
                regions={"PR": "59"},
                vectors=["v_INVALID_999"],
                level="PR"
            )
    
    def test_caching_functionality(self):
        """Test caching works as expected."""
        # Clear cache first
        pc.clear_cache()
        
        # Make request
        data1 = pc.get_census(
            dataset="CA21",
            regions={"PR": "59"},
            vectors=["v_CA21_1"],
            level="PR"
        )
        
        # Check cache was created
        cache_list = pc.list_cache()
        assert len(cache_list) > 0
        
        # Make same request again
        data2 = pc.get_census(
            dataset="CA21",
            regions={"PR": "59"},
            vectors=["v_CA21_1"],
            level="PR"
        )
        
        # Data should be identical
        pd.testing.assert_frame_equal(data1, data2)
    
    def test_data_type_consistency(self):
        """Test that data types are consistent with cancensus expectations."""
        data = pc.get_census(
            dataset="CA21",
            regions={"CSD": "5915022"},  # Vancouver
            vectors=["v_CA21_1", "v_CA21_8", "v_CA21_434"],  # Mix of data types
            level="CSD"
        )
        
        # Population counts should be integers or floats
        assert pd.api.types.is_numeric_dtype(data["v_CA21_1"])
        
        # Geographic identifiers should be strings
        assert pd.api.types.is_string_dtype(data["GeoUID"]) or pd.api.types.is_object_dtype(data["GeoUID"])
        
        # Check for proper handling of NA values
        # Should not have string representations of NA
        for col in data.columns:
            if data[col].dtype == 'object' or pd.api.types.is_string_dtype(data[col]):
                assert not any(data[col].astype(str).str.contains(r'^(x|X|F|\.\.\.)$', na=False))
    
    def test_multiple_regions_functionality(self):
        """Test handling of multiple regions."""
        data = pc.get_census(
            dataset="CA21",
            regions={"CSD": ["5915022", "3520005"]},  # Vancouver, Toronto
            vectors=["v_CA21_1"],
            level="CSD"
        )
        
        assert len(data) == 2  # Should have data for both cities
        assert "5915022" in data["GeoUID"].values
        assert "3520005" in data["GeoUID"].values
    
    def test_hierarchical_region_retrieval(self):
        """Test retrieving data at different hierarchical levels."""
        # Get CT data for Vancouver CMA
        data = pc.get_census(
            dataset="CA21",
            regions={"CMA": "59933"},  # Vancouver CMA
            vectors=["v_CA21_1"],
            level="CT"
        )
        
        # Should have multiple census tracts
        assert len(data) > 100  # Vancouver CMA has many CTs
        assert all(data["GeoUID"].str.len() == 10)  # CT GeoUIDs are 10 digits
        
    @pytest.mark.slow
    def test_large_dataset_handling(self):
        """Test handling of larger datasets."""
        # This test might be slow, so mark it as such
        data = pc.get_census(
            dataset="CA21",
            regions={"PR": "59"},  # BC
            vectors=["v_CA21_1", "v_CA21_2", "v_CA21_3"],
            level="DA"  # Dissemination Areas - lots of records
        )
        
        # Should handle large datasets without issues
        assert len(data) > 10000  # BC has many DAs
        assert not data.empty
        assert data["v_CA21_1"].sum() > 0  # Total population should be positive


class TestDataQuality:
    """Test data quality and consistency."""
    
    @pytest.fixture(autouse=True)
    def setup_test_env(self):
        """Setup test environment."""
        test_api_key = os.environ.get("CANCENSUS_API_KEY")
        if test_api_key:
            pc.set_api_key(test_api_key)
        else:
            pytest.skip("CANCENSUS_API_KEY not set")
    
    def test_data_consistency_across_levels(self):
        """Test that data is consistent across geographic levels."""
        # Get CMA-level data
        cma_data = pc.get_census(
            dataset="CA21",
            regions={"CMA": "59933"},  # Vancouver CMA
            vectors=["v_CA21_1"],  # Total population
            level="CMA"
        )
        
        # Get CSD-level data for same region
        csd_data = pc.get_census(
            dataset="CA21",
            regions={"CMA": "59933"},
            vectors=["v_CA21_1"],
            level="CSD"
        )
        
        # Sum of CSDs should approximately equal CMA total
        cma_pop = cma_data["v_CA21_1"].iloc[0]
        csd_pop_sum = csd_data["v_CA21_1"].sum()
        
        # Allow for small rounding differences
        assert abs(cma_pop - csd_pop_sum) / cma_pop < 0.01, (
            f"Population inconsistency: CMA={cma_pop}, CSD sum={csd_pop_sum}"
        )
    
    def test_geographic_identifier_format(self):
        """Test that geographic identifiers follow expected formats."""
        test_cases = [
            ("PR", "CA21", 2),     # Province: 2 digits
            ("CMA", "CA21", 3),    # CMA: 3 digits
            ("CD", "CA21", 4),     # CD: 4 digits
            ("CSD", "CA21", 7),    # CSD: 7 digits
            ("CT", "CA21", 10),    # CT: 10 digits
        ]
        
        for level, dataset, expected_length in test_cases:
            data = pc.get_census(
                dataset=dataset,
                regions={"PR": "59"},  # BC
                vectors=["v_CA21_1"],
                level=level
            )
            
            # Check GeoUID format
            assert all(data["GeoUID"].str.len() == expected_length), (
                f"GeoUID length mismatch for {level}: expected {expected_length}"
            )
            
            # Check GeoUID is numeric
            assert all(data["GeoUID"].str.isdigit()), (
                f"Non-numeric GeoUID found for {level}"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])