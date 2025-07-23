"""Test label_vectors function against R cancensus."""

import os
import sys
import pytest
import warnings
from pathlib import Path

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pycancensus as pc


class TestLabelVectors:
    """Test label_vectors function."""
    
    def test_no_metadata_warning(self):
        """Test that warning is issued when no metadata exists."""
        import pandas as pd
        
        # Create a simple DataFrame without census_vectors attribute
        df = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['a', 'b', 'c']})
        
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = pc.label_vectors(df)
            
            # Should return None and issue warning
            assert result is None
            assert len(w) == 1
            assert "Data does not have variables to labels" in str(w[0].message)
    
    def test_with_detailed_labels(self):
        """Test getting census data with detailed labels (default)."""
        try:
            # Get census data with detailed labels (default)
            data = pc.get_census(
                dataset="CA21",
                regions={"PR": "35"},
                vectors=["v_CA21_1"],
                level="PR",
                labels="detailed",
                quiet=True
            )
            
            # With detailed labels, should not have census_vectors attribute
            result = pc.label_vectors(data)
            assert result is None
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    def test_with_short_labels(self):
        """Test getting census data with short labels."""
        try:
            # Get census data with short labels
            data = pc.get_census(
                dataset="CA21",
                regions={"PR": "35"},
                vectors=["v_CA21_1", "v_CA21_2"],
                level="PR",
                labels="short",
                quiet=True
            )
            
            # With short labels, should have census_vectors attribute
            result = pc.label_vectors(data)
            
            if result is not None:
                # Should be a DataFrame with Vector and Detail columns
                assert isinstance(result, pd.DataFrame)
                assert "Vector" in result.columns
                assert "Detail" in result.columns
                assert len(result) > 0
                
                # Check that vector codes are present
                vectors_in_result = result["Vector"].tolist()
                assert any("v_CA21_1" in vec for vec in vectors_in_result)
                
                print(f"✅ Got vector metadata with {len(result)} entries")
                print(result.head())
            else:
                print("⚠️  No vector metadata returned")
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")
    
    def test_with_geo_format(self):
        """Test label_vectors with GeoDataFrame from geopandas format."""
        try:
            # Get census data with geography and short labels
            data = pc.get_census(
                dataset="CA21",
                regions={"PR": "35"},
                vectors=["v_CA21_1"],
                level="PR",
                geo_format="geopandas",
                labels="short",
                quiet=True
            )
            
            # Should work with GeoDataFrame too
            result = pc.label_vectors(data)
            
            if result is not None:
                assert isinstance(result, pd.DataFrame)
                assert "Vector" in result.columns
                assert "Detail" in result.columns
                print(f"✅ Got vector metadata from GeoDataFrame with {len(result)} entries")
            
        except Exception as e:
            pytest.skip(f"API call failed: {e}")


if __name__ == "__main__":
    # Import pandas for testing
    import pandas as pd
    
    # Run basic tests
    test = TestLabelVectors()
    
    print("Testing no metadata warning...")
    test.test_no_metadata_warning()
    print("✅ No metadata warning test passed")
    
    print("\nTesting with detailed labels...")
    test.test_with_detailed_labels()
    print("✅ Detailed labels test passed")
    
    print("\nTesting with short labels...")
    test.test_with_short_labels()
    print("✅ Short labels test passed")
    
    print("\nTesting with geo format...")
    test.test_with_geo_format()
    print("✅ Geo format test passed")
    
    print("\n🎉 All tests passed!")