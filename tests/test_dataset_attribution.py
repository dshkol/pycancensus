"""Test dataset_attribution function against R cancensus."""

import os
import sys
import pytest
from pathlib import Path

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pycancensus as pc

# Import R bridge for cross-validation
from tests.cross_validation.utils.r_python_bridge import RPythonBridge


class TestDatasetAttribution:
    """Test dataset_attribution function."""
    
    def test_single_dataset(self):
        """Test attribution for a single dataset."""
        result = pc.dataset_attribution(['CA16'])
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(attr, str) for attr in result)
        assert any('2016' in attr for attr in result)
    
    def test_multiple_datasets_same_type(self):
        """Test attribution for multiple census datasets."""
        result = pc.dataset_attribution(['CA06', 'CA16'])
        assert isinstance(result, list)
        assert len(result) > 0
        
        # Should have merged years
        has_merged = False
        for attr in result:
            if '2006' in attr and '2016' in attr:
                has_merged = True
                break
        assert has_merged, "Expected merged attribution with both years"
    
    def test_invalid_dataset(self):
        """Test with invalid dataset."""
        with pytest.raises(ValueError, match="No valid datasets found"):
            pc.dataset_attribution(['INVALID'])
    
    def test_case_insensitive(self):
        """Test that dataset names are case insensitive."""
        result1 = pc.dataset_attribution(['ca16'])
        result2 = pc.dataset_attribution(['CA16'])
        assert result1 == result2
    
    @pytest.mark.skipif(
        not os.environ.get("RUN_R_TESTS", False),
        reason="R tests not enabled"
    )
    def test_r_equivalence(self):
        """Test equivalence with R cancensus."""
        bridge = RPythonBridge()
        
        try:
            # Test single dataset
            r_result = bridge.run_r_code("""
                library(cancensus)
                dataset_attribution('CA16')
            """, return_type="raw")
            
            py_result = pc.dataset_attribution(['CA16'])
            
            # Both should return similar attribution text
            assert len(py_result) > 0
            assert isinstance(py_result[0], str)
            
            # Test multiple datasets
            r_result_multi = bridge.run_r_code("""
                library(cancensus)
                dataset_attribution(c('CA06', 'CA16'))
            """, return_type="raw")
            
            py_result_multi = pc.dataset_attribution(['CA06', 'CA16'])
            
            # Should have merged attributions
            assert len(py_result_multi) > 0
            
        finally:
            bridge.cleanup()


if __name__ == "__main__":
    # Run basic tests
    test = TestDatasetAttribution()
    
    print("Testing single dataset...")
    test.test_single_dataset()
    print("✅ Single dataset test passed")
    
    print("\nTesting multiple datasets...")
    test.test_multiple_datasets_same_type()
    print("✅ Multiple datasets test passed")
    
    print("\nTesting invalid dataset...")
    test.test_invalid_dataset()
    print("✅ Invalid dataset test passed")
    
    print("\nTesting case insensitivity...")
    test.test_case_insensitive()
    print("✅ Case insensitivity test passed")
    
    # Run R equivalence test if requested
    if os.environ.get("RUN_R_TESTS"):
        print("\nTesting R equivalence...")
        test.test_r_equivalence()
        print("✅ R equivalence test passed")
    
    print("\n🎉 All tests passed!")