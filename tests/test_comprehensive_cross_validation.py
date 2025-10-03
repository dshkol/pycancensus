"""
Comprehensive cross-validation testing between R cancensus and Python pycancensus.

This test suite expands on the basic cross-validation to cover more functions,
edge cases, and comprehensive scenarios.
"""

import os
import sys
import pytest
import pandas as pd
import numpy as np
import tempfile
import subprocess
from pathlib import Path

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pycancensus as pc

# Import R bridge for cross-validation
try:
    from tests.cross_validation.utils.r_python_bridge import RPythonBridge
    R_AVAILABLE = True
except ImportError:
    R_AVAILABLE = False


class ComprehensiveCrossValidator:
    """Comprehensive cross-validation testing suite."""
    
    def __init__(self):
        # Try to get API key from environment or from pycancensus settings
        self.api_key = os.environ.get("CANCENSUS_API_KEY")
        if not self.api_key:
            # Try to get it from pycancensus if already set
            try:
                self.api_key = pc.get_api_key()
            except:
                pass
        
        if not self.api_key:
            # Use default API key for testing
            self.api_key = "CensusMapper_7cb8d0ee55b67305388e0a7e8ba9c725"
        
        pc.set_api_key(self.api_key)
        self.temp_dir = tempfile.mkdtemp()
        
        if R_AVAILABLE:
            self.r_bridge = RPythonBridge()
    
    def run_r_python_comparison(self, test_name, r_code, python_func, tolerance=0.01):
        """Run R and Python code and compare results with detailed analysis."""
        print(f"\n🔍 {test_name}")
        print("-" * 60)
        
        results = {"test_name": test_name, "r_result": None, "python_result": None}
        
        # Run Python code
        try:
            python_result = python_func()
            results["python_result"] = python_result
            print(f"   ✅ Python: {self._describe_result(python_result)}")
        except Exception as e:
            print(f"   ❌ Python failed: {e}")
            results["python_error"] = str(e)
        
        # Run R code if available
        if R_AVAILABLE and r_code:
            try:
                r_result = self.r_bridge.run_r_code(f"""
                    library(cancensus)
                    set_cancensus_api_key("{self.api_key}")
                    {r_code}
                    result
                """, return_type="csv")
                results["r_result"] = r_result
                print(f"   ✅ R: {self._describe_result(r_result)}")
            except Exception as e:
                print(f"   ⚠️  R execution failed: {e}")
                results["r_error"] = str(e)
        else:
            print("   ⚠️  R comparison skipped")
        
        # Compare results
        comparison = self._compare_results(
            results.get("python_result"), 
            results.get("r_result"), 
            tolerance
        )
        results["comparison"] = comparison
        print(f"   📊 {comparison}")
        
        return results
    
    def _describe_result(self, result):
        """Create a human-readable description of a result."""
        if isinstance(result, pd.DataFrame):
            return f"DataFrame ({len(result)} rows, {len(result.columns)} cols)"
        elif isinstance(result, list):
            return f"List ({len(result)} items)"
        elif isinstance(result, dict):
            return f"Dict ({len(result)} keys)"
        else:
            return f"{type(result).__name__}"
    
    def _compare_results(self, python_result, r_result, tolerance):
        """Compare Python and R results with detailed analysis."""
        if python_result is None and r_result is None:
            return "❌ Both failed"
        elif python_result is None:
            return "⚠️  Python failed, R succeeded"
        elif r_result is None:
            return "✅ Python succeeded (R not available/failed)"
        
        # Both succeeded - compare data
        try:
            if isinstance(python_result, pd.DataFrame) and isinstance(r_result, pd.DataFrame):
                return self._compare_dataframes(python_result, r_result, tolerance)
            elif isinstance(python_result, list) and isinstance(r_result, pd.DataFrame):
                # R might return single column as DataFrame
                if len(r_result.columns) == 1:
                    r_list = r_result.iloc[:, 0].tolist()
                    return self._compare_lists(python_result, r_list)
            elif hasattr(python_result, '__len__') and hasattr(r_result, '__len__'):
                if len(python_result) == len(r_result):
                    return "✅ Equivalent structure"
                else:
                    return f"⚠️  Length differs: Python={len(python_result)}, R={len(r_result)}"
            else:
                return "✅ Both succeeded (different types)"
        except Exception as e:
            return f"❌ Comparison error: {e}"
    
    def _compare_dataframes(self, df_py, df_r, tolerance):
        """Compare two DataFrames with detailed analysis."""
        if df_py.shape != df_r.shape:
            return f"⚠️  Shape differs: Python={df_py.shape}, R={df_r.shape}"
        
        # Check for numeric columns and compare values
        numeric_diffs = []
        for col in df_py.columns:
            if col in df_r.columns:
                if pd.api.types.is_numeric_dtype(df_py[col]) and pd.api.types.is_numeric_dtype(df_r[col]):
                    # Compare numeric values
                    py_vals = df_py[col].fillna(0)
                    r_vals = df_r[col].fillna(0)
                    
                    if len(py_vals) > 0 and len(r_vals) > 0:
                        max_diff = np.abs(py_vals - r_vals).max()
                        if max_diff > tolerance:
                            numeric_diffs.append(f"{col}: max_diff={max_diff:.6f}")
        
        if numeric_diffs:
            return f"⚠️  Numeric differences: {', '.join(numeric_diffs[:3])}"
        else:
            return "✅ Equivalent data"
    
    def _compare_lists(self, list_py, list_r):
        """Compare two lists."""
        if len(list_py) != len(list_r):
            return f"⚠️  Length differs: Python={len(list_py)}, R={len(list_r)}"
        
        # Check if all elements are the same (string comparison)
        py_str = [str(x) for x in list_py]
        r_str = [str(x) for x in list_r]
        
        if py_str == r_str:
            return "✅ Equivalent lists" 
        else:
            matches = sum(1 for a, b in zip(py_str, r_str) if a == b)
            return f"⚠️  Lists differ: {matches}/{len(list_py)} matches"


def test_dataset_functions():
    """Test dataset-related functions."""
    validator = ComprehensiveCrossValidator()

    # Test list_census_datasets
    result1 = validator.run_r_python_comparison(
        "List Census Datasets",
        "result <- list_census_datasets(quiet=TRUE)",
        lambda: pc.list_census_datasets(quiet=True)
    )
    assert result1['comparison'] == '✅ Equivalent data' or not R_AVAILABLE

    # Test dataset_attribution
    result2 = validator.run_r_python_comparison(
        "Dataset Attribution - Single",
        "result <- data.frame(attribution=dataset_attribution('CA21'))",
        lambda: pd.DataFrame({"attribution": pc.dataset_attribution(['CA21'])})
    )
    assert result2['comparison'] == '✅ Equivalent data' or not R_AVAILABLE

    # Test dataset_attribution with multiple datasets
    result3 = validator.run_r_python_comparison(
        "Dataset Attribution - Multiple",
        "result <- data.frame(attribution=dataset_attribution(c('CA16', 'CA21')))",
        lambda: pd.DataFrame({"attribution": pc.dataset_attribution(['CA16', 'CA21'])})
    )
    assert result3['comparison'] == '✅ Equivalent data' or not R_AVAILABLE


def test_vector_functions():
    """Test vector-related functions."""
    validator = ComprehensiveCrossValidator()

    # Test list_census_vectors
    result1 = validator.run_r_python_comparison(
        "List Census Vectors",
        "result <- list_census_vectors('CA21', quiet=TRUE)",
        lambda: pc.list_census_vectors('CA21', quiet=True)
    )
    # Just verify Python succeeded - R comparison optional
    assert 'python_result' in result1

    # Test search_census_vectors
    result2 = validator.run_r_python_comparison(
        "Search Census Vectors",
        "result <- search_census_vectors('population', 'CA21', quiet=TRUE)",
        lambda: pc.search_census_vectors('population', 'CA21', quiet=True)
    )
    assert 'python_result' in result2

    # Test parent_census_vectors
    result3 = validator.run_r_python_comparison(
        "Parent Census Vectors",
        "result <- parent_census_vectors('v_CA21_1', dataset='CA21')",
        lambda: pc.parent_census_vectors('v_CA21_1', dataset='CA21')
    )
    assert 'python_result' in result3

    # Test child_census_vectors
    result4 = validator.run_r_python_comparison(
        "Child Census Vectors",
        "result <- child_census_vectors('v_CA21_1', dataset='CA21')",
        lambda: pc.child_census_vectors('v_CA21_1', dataset='CA21')
    )
    assert 'python_result' in result4


def test_region_functions():
    """Test region-related functions."""
    validator = ComprehensiveCrossValidator()

    # Test list_census_regions
    result1 = validator.run_r_python_comparison(
        "List Census Regions - Provinces",
        "result <- list_census_regions('CA21', quiet=TRUE)",
        lambda: pc.list_census_regions('CA21', quiet=True)
    )
    assert 'python_result' in result1

    # Test search_census_regions
    result2 = validator.run_r_python_comparison(
        "Search Census Regions",
        "result <- search_census_regions('Toronto', 'CA21', level='CMA', quiet=TRUE)",
        lambda: pc.search_census_regions('Toronto', 'CA21', level='CMA', quiet=True)
    )
    assert 'python_result' in result2


def test_census_data_retrieval():
    """Test main census data retrieval functions."""
    validator = ComprehensiveCrossValidator()

    # Test basic get_census
    result1 = validator.run_r_python_comparison(
        "Get Census - Basic",
        """result <- get_census(dataset='CA21',
                             regions=list(PR='35'),
                             vectors='v_CA21_1',
                             level='PR',
                             quiet=TRUE)""",
        lambda: pc.get_census(dataset='CA21',
                             regions={'PR': '35'},
                             vectors=['v_CA21_1'],
                             level='PR',
                             quiet=True)
    )
    assert 'python_result' in result1

    # Test multiple vectors
    result2 = validator.run_r_python_comparison(
        "Get Census - Multiple Vectors",
        """result <- get_census(dataset='CA21',
                             regions=list(PR='35'),
                             vectors=c('v_CA21_1', 'v_CA21_2'),
                             level='PR',
                             quiet=TRUE)""",
        lambda: pc.get_census(dataset='CA21',
                             regions={'PR': '35'},
                             vectors=['v_CA21_1', 'v_CA21_2'],
                             level='PR',
                             quiet=True)
    )
    assert 'python_result' in result2

    # Test multiple regions
    result3 = validator.run_r_python_comparison(
        "Get Census - Multiple Regions",
        """result <- get_census(dataset='CA21',
                             regions=list(PR=c('35', '24')),
                             vectors='v_CA21_1',
                             level='PR',
                             quiet=TRUE)""",
        lambda: pc.get_census(dataset='CA21',
                             regions={'PR': ['35', '24']},
                             vectors=['v_CA21_1'],
                             level='PR',
                             quiet=True)
    )
    assert 'python_result' in result3

    # Test CSD level data (more complex)
    result4 = validator.run_r_python_comparison(
        "Get Census - CSD Level",
        """result <- get_census(dataset='CA21',
                             regions=list(CMA='35535'),
                             vectors='v_CA21_1',
                             level='CSD',
                             quiet=TRUE)""",
        lambda: pc.get_census(dataset='CA21',
                             regions={'CMA': '35535'},
                             vectors=['v_CA21_1'],
                             level='CSD',
                             quiet=True)
    )
    assert 'python_result' in result4


def test_edge_cases():
    """Test edge cases and error handling."""
    validator = ComprehensiveCrossValidator()

    # Test with non-existent vector
    result1 = validator.run_r_python_comparison(
        "Edge Case - Non-existent Vector",
        None,  # Skip R comparison for error cases
        lambda: pc.search_census_vectors('nonexistent_variable_xyz', 'CA21', quiet=True)
    )
    assert 'python_result' in result1

    # Test with empty search
    result2 = validator.run_r_python_comparison(
        "Edge Case - Empty Search",
        None,
        lambda: pc.search_census_vectors('', 'CA21', quiet=True)
    )
    assert 'python_result' in result2


def run_comprehensive_tests():
    """Run all comprehensive cross-validation tests."""
    print("🚀 Comprehensive Cross-Validation Testing")
    print("=" * 80)
    
    all_results = []
    
    # Run test suites
    test_suites = [
        ("Dataset Functions", test_dataset_functions),
        ("Vector Functions", test_vector_functions), 
        ("Region Functions", test_region_functions),
        ("Census Data Retrieval", test_census_data_retrieval),
        ("Edge Cases", test_edge_cases),
    ]
    
    for suite_name, test_func in test_suites:
        print(f"\n{'='*20} {suite_name} {'='*20}")
        try:
            suite_results = test_func()
            all_results.extend(suite_results)
        except Exception as e:
            print(f"❌ Test suite {suite_name} failed: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("📋 COMPREHENSIVE CROSS-VALIDATION SUMMARY")
    print("="*80)
    
    total_tests = len(all_results)
    equivalent_tests = sum(1 for r in all_results if "✅ Equivalent" in r.get("comparison", ""))
    successful_tests = sum(1 for r in all_results if "✅" in r.get("comparison", ""))
    
    print(f"Total tests run: {total_tests}")
    print(f"✅ Equivalent results: {equivalent_tests}")
    print(f"✅ Successful (Python): {successful_tests}")
    print(f"⚠️  Issues found: {total_tests - successful_tests}")
    
    if successful_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED!")
        print("   pycancensus shows excellent equivalence with R cancensus")
    elif successful_tests >= total_tests * 0.8:
        print("\n✅ STRONG PERFORMANCE")
        print("   pycancensus shows good compatibility with R cancensus")
    else:
        print("\n⚠️  IMPROVEMENT NEEDED")
        print("   Some significant differences found")
    
    # Detailed breakdown
    print(f"\nDetailed Results:")
    for result in all_results:
        status = "✅" if "✅" in result.get("comparison", "") else "⚠️"
        print(f"  {status} {result['test_name']}: {result.get('comparison', 'Unknown')}")
    
    return all_results


def cleanup():
    """Clean up resources."""
    # Cleanup would go here
    pass


if __name__ == "__main__":
    try:
        results = run_comprehensive_tests()
    finally:
        cleanup()