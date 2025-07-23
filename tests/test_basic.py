#!/usr/bin/env python3
"""
Basic tests for pycancensus.
"""

import pytest
import pandas as pd
import geopandas as gpd
from unittest.mock import patch, MagicMock

import pycancensus as pc


class TestSettings:
    """Test settings functionality."""
    
    def test_set_get_api_key(self):
        """Test setting and getting API key."""
        test_key = "test_api_key_123"
        pc.set_api_key(test_key)
        assert pc.get_api_key() == test_key
    
    def test_set_get_cache_path(self):
        """Test setting and getting cache path."""
        import tempfile
        import os
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pc.set_cache_path(temp_dir)
            # Resolve both paths to handle symlinks on macOS
            expected_path = str(Path(temp_dir).resolve())
            actual_path = str(Path(pc.get_cache_path()).resolve())
            assert actual_path == expected_path
            assert os.path.exists(temp_dir)
    
    def test_persistent_api_key_storage(self):
        """Test persistent API key storage."""
        import tempfile
        import json
        from pathlib import Path
        from unittest.mock import patch
        
        test_key = "test_persistent_key_456"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the config directory to use temp directory
            with patch('pycancensus.settings._get_config_path') as mock_config_path:
                config_file = Path(temp_dir) / "config.json"
                mock_config_path.return_value = config_file
                
                # Clear any existing session variables
                import pycancensus.settings as settings
                settings._API_KEY = None
                
                # Set API key with persistence
                pc.set_api_key(test_key, install=True)
                
                # Verify config file was created
                assert config_file.exists()
                
                # Verify config file contains the key
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    assert config["api_key"] == test_key
                
                # Clear session variable and test that key is still retrieved
                settings._API_KEY = None
                retrieved_key = pc.get_api_key()
                assert retrieved_key == test_key
                
                # Test removal
                pc.remove_api_key()
                assert pc.get_api_key() is None
                
                # Verify config file was updated
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    assert "api_key" not in config


class TestUtils:
    """Test utility functions."""
    
    def test_validate_dataset(self):
        """Test dataset validation."""
        from pycancensus.utils import validate_dataset
        
        # Valid datasets
        assert validate_dataset("CA16") == "CA16"
        assert validate_dataset("ca21") == "CA21"
        assert validate_dataset(" CA11 ") == "CA11"
        
        # Invalid datasets
        with pytest.raises(ValueError):
            validate_dataset("invalid")
        with pytest.raises(ValueError):
            validate_dataset("CA")
        with pytest.raises(ValueError):
            validate_dataset(123)
    
    def test_validate_level(self):
        """Test level validation."""
        from pycancensus.utils import validate_level
        
        # Valid levels
        valid_levels = ["Regions", "PR", "CMA", "CD", "CSD", "CT", "DA", "EA", "DB"]
        for level in valid_levels:
            assert validate_level(level) == level
        
        # Invalid level
        with pytest.raises(ValueError):
            validate_level("invalid")
    
    def test_process_regions(self):
        """Test region processing."""
        from pycancensus.utils import process_regions
        
        # Valid regions
        regions = {"CMA": "59933", "PR": ["35", "48"]}
        processed = process_regions(regions)
        assert processed["CMA"] == "59933"
        assert processed["PR"] == ["35", "48"]
        
        # Invalid regions
        with pytest.raises(ValueError):
            process_regions({})
        with pytest.raises(ValueError):
            process_regions({"invalid": "123"})


class TestMockedAPI:
    """Test API functions with mocked responses."""
    
    @patch('pycancensus.datasets.requests.get')
    def test_list_datasets(self, mock_get):
        """Test listing datasets with mocked API."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "datasets": [
                {"dataset": "CA16", "description": "2016 Census"},
                {"dataset": "CA21", "description": "2021 Census"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Set API key
        pc.set_api_key("test_key")
        
        # Test function
        datasets = pc.list_census_datasets(use_cache=False)
        
        assert isinstance(datasets, pd.DataFrame)
        assert len(datasets) == 2
        assert "CA16" in datasets["dataset"].values
        assert "CA21" in datasets["dataset"].values
    
    @patch('pycancensus.regions.requests.get')
    def test_list_regions(self, mock_get):
        """Test listing regions with mocked API."""
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "regions": [
                {"region": "59933", "name": "Vancouver", "level": "CMA", "pop": 2463431},
                {"region": "35535", "name": "Toronto", "level": "CMA", "pop": 5928040}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Set API key
        pc.set_api_key("test_key")
        
        # Test function
        regions = pc.list_census_regions("CA16", use_cache=False)
        
        assert isinstance(regions, pd.DataFrame)
        assert len(regions) == 2
        assert "Vancouver" in regions["name"].values
        assert "Toronto" in regions["name"].values
    
    @patch('pycancensus.vectors.requests.get')
    def test_list_vectors(self, mock_get):
        """Test listing vectors with mocked API."""
        # Mock CSV response (new format)
        csv_response = """vector,label,type,units,add,parent,details
v_CA16_1,Total population,Total,Number,additive,,Total population for region
v_CA16_2,Total population Male,Male,Number,additive,v_CA16_1,Male population for region"""
        
        mock_response = MagicMock()
        mock_response.text = csv_response
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Set API key
        pc.set_api_key("test_key")
        
        # Test function
        vectors = pc.list_census_vectors("CA16", use_cache=False)
        
        assert isinstance(vectors, pd.DataFrame)
        assert len(vectors) == 2
        assert "v_CA16_1" in vectors["vector"].values
        assert "v_CA16_2" in vectors["vector"].values


class TestDataProcessing:
    """Test data processing functionality."""
    
    def test_column_name_handling_with_spaces(self):
        """Test that column names with trailing spaces are handled correctly."""
        from pycancensus.core import _process_csv_response
        
        # Mock CSV data with trailing spaces in column names (as returned by API)
        csv_data = """GeoUID,Type,Region Name,Population ,Households ,Dwellings ,Area (sq km),v_CA16_1
5915001,CSD,Test Region,12345,5000,5200,100.5,12345
5915002,CSD,Another Region,67890,25000,26000,200.8,67890"""
        
        # Process the CSV
        result_df = _process_csv_response(csv_data, ['v_CA16_1'], 'detailed')
        
        # Check that columns with trailing spaces are trimmed and converted to numeric
        assert 'Population' in result_df.columns  # Trimmed, no trailing space
        assert pd.api.types.is_numeric_dtype(result_df['Population'])
        assert result_df['Population'].iloc[0] == 12345
        
        assert 'Households' in result_df.columns  # Trimmed, no trailing space
        assert pd.api.types.is_numeric_dtype(result_df['Households'])
        
        assert 'Dwellings' in result_df.columns  # Trimmed, no trailing space
        assert pd.api.types.is_numeric_dtype(result_df['Dwellings'])
        
        # Check that Area column (no trailing space) still works
        assert 'Area (sq km)' in result_df.columns
        assert pd.api.types.is_numeric_dtype(result_df['Area (sq km)'])
        
        # Check that vector columns are converted to numeric
        assert 'v_CA16_1' in result_df.columns
        assert pd.api.types.is_numeric_dtype(result_df['v_CA16_1'])
        
        # Check that categorical columns are properly set
        assert result_df['Type'].dtype.name == 'category'
        assert result_df['Region Name'].dtype.name == 'category'


class TestCache:
    """Test caching functionality."""
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as temp_dir:
            pc.set_cache_path(temp_dir)
            
            # Test caching data
            test_data = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
            
            from pycancensus.cache import cache_data, get_cached_data
            
            # Cache data
            cache_data("test_key", test_data)
            
            # Retrieve cached data
            retrieved_data = get_cached_data("test_key")
            
            assert retrieved_data is not None
            pd.testing.assert_frame_equal(test_data, retrieved_data)
            
            # Test non-existent cache key
            non_existent = get_cached_data("non_existent_key")
            assert non_existent is None


if __name__ == "__main__":
    pytest.main([__file__])