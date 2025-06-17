"""Test API equivalence between cancensus and pycancensus."""

import os
import sys
from pathlib import Path
import pandas as pd
import pytest
import json
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import pycancensus as pc
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.r_python_bridge import RPythonBridge
from utils.data_comparison import DataComparator

# Test configuration
API_KEY = os.environ.get("CANCENSUS_API_KEY")

@pytest.fixture(scope="module")
def r_bridge():
    """Create R-Python bridge for tests."""
    bridge = RPythonBridge()
    yield bridge
    bridge.cleanup()

@pytest.fixture(scope="module")
def comparator():
    """Create data comparator for tests."""
    return DataComparator()

@pytest.fixture(autouse=True)
def setup_api_key():
    """Ensure API key is set for all tests."""
    if API_KEY:
        pc.set_api_key(API_KEY)
    else:
        pytest.skip("CANCENSUS_API_KEY not set")

class TestAPIEquivalence:
    """Test that both libraries produce equivalent API calls and results."""
    
    def test_basic_census_retrieval(self, r_bridge, comparator):
        """Test basic census data retrieval produces same results."""
        # Test parameters
        dataset = "CA16"
        regions = {"CSD": "5915022"}  # Vancouver
        vectors = ["v_CA16_408", "v_CA16_409", "v_CA16_410"]
        level = "CSD"
        
        # Get data from Python implementation
        py_data = pc.get_census(
            dataset=dataset,
            regions=regions,
            vectors=vectors,
            level=level
        )
        
        # Get data from R implementation
        r_code = f"""
        library(cancensus)
        set_cancensus_api_key("{API_KEY}")
        
        data <- get_census(
            dataset = "{dataset}",
            regions = list(CSD = "{regions['CSD']}"),
            vectors = c({','.join(f'"{v}"' for v in vectors)}),
            level = "{level}",
            geo_format = NA
        )
        
        # Convert to standard format
        as.data.frame(data)
        """
        
        r_data = r_bridge.run_r_code(r_code, return_type="csv")
        
        # Compare results
        comparison = comparator.compare_census_data(
            py_data, r_data, "test_basic_census_retrieval"
        )
        
        assert comparison["summary"]["match"], (
            f"Data mismatch: {comparison['summary']}"
        )
    
    def test_multiple_regions(self, r_bridge, comparator):
        """Test retrieval with multiple regions."""
        dataset = "CA21"
        regions = {"CSD": ["5915022", "3520005"]}  # Vancouver, Toronto
        vectors = ["v_CA21_1", "v_CA21_8"]
        level = "CSD"
        
        # Python implementation
        py_data = pc.get_census(
            dataset=dataset,
            regions=regions,
            vectors=vectors,
            level=level
        )
        
        # R implementation
        r_code = f"""
        library(cancensus)
        set_cancensus_api_key("{API_KEY}")
        
        data <- get_census(
            dataset = "{dataset}",
            regions = list(CSD = c({','.join(f'"{r}"' for r in regions['CSD'])})),
            vectors = c({','.join(f'"{v}"' for v in vectors)}),
            level = "{level}",
            geo_format = NA
        )
        
        as.data.frame(data)
        """
        
        r_data = r_bridge.run_r_code(r_code, return_type="csv")
        
        # Compare
        comparison = comparator.compare_census_data(
            py_data, r_data, "test_multiple_regions"
        )
        
        assert comparison["summary"]["match"], (
            f"Data mismatch: {comparison['summary']}"
        )
    
    def test_different_levels(self, r_bridge, comparator):
        """Test retrieval at different geographic levels."""
        dataset = "CA16"
        regions = {"CMA": "59933"}  # Vancouver CMA
        vectors = ["v_CA16_1"]
        
        levels_to_test = ["CSD", "CT", "DA"]
        
        for level in levels_to_test:
            # Python
            py_data = pc.get_census(
                dataset=dataset,
                regions=regions,
                vectors=vectors,
                level=level
            )
            
            # R
            r_code = f"""
            library(cancensus)
            set_cancensus_api_key("{API_KEY}")
            
            data <- get_census(
                dataset = "{dataset}",
                regions = list(CMA = "{regions['CMA']}"),
                vectors = "{vectors[0]}",
                level = "{level}",
                geo_format = NA
            )
            
            as.data.frame(data)
            """
            
            r_data = r_bridge.run_r_code(r_code, return_type="csv")
            
            # Compare
            comparison = comparator.compare_census_data(
                py_data, r_data, f"test_different_levels_{level}"
            )
            
            assert comparison["summary"]["match"], (
                f"Data mismatch for level {level}: {comparison['summary']}"
            )
    
    def test_dataset_list(self, r_bridge, comparator):
        """Test that both libraries return same dataset list."""
        # Python
        py_datasets = pc.list_census_datasets()
        
        # R
        r_code = """
        library(cancensus)
        set_cancensus_api_key("{API_KEY}")
        
        datasets <- list_census_datasets()
        as.data.frame(datasets)
        """
        
        r_datasets = r_bridge.run_r_code(r_code, return_type="csv")
        
        # Compare dataset codes
        py_codes = set(py_datasets["dataset"].values)
        r_codes = set(r_datasets["dataset"].values)
        
        assert py_codes == r_codes, (
            f"Dataset mismatch. Python only: {py_codes - r_codes}, "
            f"R only: {r_codes - py_codes}"
        )
    
    def test_vector_list(self, r_bridge, comparator):
        """Test that both libraries return same vector lists."""
        dataset = "CA16"
        
        # Python
        py_vectors = pc.list_census_vectors(dataset)
        
        # R
        r_code = f"""
        library(cancensus)
        set_cancensus_api_key("{API_KEY}")
        
        vectors <- list_census_vectors("{dataset}")
        as.data.frame(vectors)
        """
        
        r_vectors = r_bridge.run_r_code(r_code, return_type="csv")
        
        # Compare vector counts and basic properties
        assert len(py_vectors) == len(r_vectors), (
            f"Vector count mismatch: Python {len(py_vectors)}, R {len(r_vectors)}"
        )
        
        # Compare vector IDs
        py_ids = set(py_vectors["vector"].values)
        r_ids = set(r_vectors["vector"].values)
        
        assert py_ids == r_ids, (
            f"Vector ID mismatch. Count difference: {len(py_ids ^ r_ids)}"
        )
    
    def test_region_list(self, r_bridge, comparator):
        """Test that both libraries return same region lists."""
        dataset = "CA21"
        
        # Test for different region levels
        levels = ["PR", "CMA", "CD", "CSD"]
        
        for level in levels:
            # Python
            py_regions = pc.list_census_regions(dataset, level=level)
            
            # R
            r_code = f"""
            library(cancensus)
            set_cancensus_api_key("{API_KEY}")
            
            regions <- list_census_regions("{dataset}", levels = "{level}")
            as.data.frame(regions)
            """
            
            r_regions = r_bridge.run_r_code(r_code, return_type="csv")
            
            # Compare region counts
            assert len(py_regions) == len(r_regions), (
                f"Region count mismatch for {level}: "
                f"Python {len(py_regions)}, R {len(r_regions)}"
            )

if __name__ == "__main__":
    pytest.main([__file__, "-v"])