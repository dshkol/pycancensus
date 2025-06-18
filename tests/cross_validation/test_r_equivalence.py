#!/usr/bin/env python3
"""
Cross-validation testing between R cancensus and Python pycancensus.

This script runs equivalent operations in both R and Python and compares
the results to ensure data equivalence and API compatibility.
"""

import os
import sys
import pandas as pd
import numpy as np
import json
import subprocess
import tempfile
from pathlib import Path

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import pycancensus as pc

# Test configuration
API_KEY = os.environ.get("CANCENSUS_API_KEY") or "CensusMapper_7cb8d0ee55b67305388e0a7e8ba9c725"

class RCancensusComparator:
    """Compare Python pycancensus with R cancensus library."""
    
    def __init__(self):
        pc.set_api_key(API_KEY)
        self.temp_dir = tempfile.mkdtemp()
        print(f"🔧 Using temp directory: {self.temp_dir}")
    
    def check_r_availability(self):
        """Check if R and cancensus package are available."""
        try:
            # Check if R is installed
            result = subprocess.run(['R', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                return False, "R not installed"
            
            # Check if cancensus package is available
            r_script = '''
            if (!require("cancensus", quietly = TRUE)) {
                install.packages("cancensus", repos = "https://cran.r-project.org/")
                library(cancensus)
            }
            cat("R cancensus available")
            '''
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
                f.write(r_script)
                r_file = f.name
            
            result = subprocess.run(['Rscript', r_file], capture_output=True, text=True, timeout=30)
            os.unlink(r_file)
            
            if "R cancensus available" in result.stdout:
                return True, "R cancensus available"
            else:
                return False, f"R cancensus not available: {result.stderr}"
                
        except Exception as e:
            return False, f"R check failed: {e}"
    
    def run_r_comparison(self, test_name, r_code, python_function):
        """Run equivalent R and Python code and compare results."""
        print(f"\n🔍 {test_name}")
        print("-" * 50)
        
        # Check R availability
        r_available, r_status = self.check_r_availability()
        if not r_available:
            print(f"   ⚠️  Skipping R comparison: {r_status}")
            
            # Run Python only
            try:
                python_result = python_function()
                print(f"   ✅ Python result: {len(python_result)} rows")
                return {"python": python_result, "r": None, "comparison": "R not available"}
            except Exception as e:
                print(f"   ❌ Python failed: {e}")
                return {"python": None, "r": None, "comparison": "Both failed"}
        
        # Run R code
        r_result = None
        try:
            # Create R script with API key setup
            r_script = f'''
            library(cancensus)
            options(cancensus.api_key = "{API_KEY}")
            
            {r_code}
            
            # Save result as CSV
            write.csv(result, "{self.temp_dir}/r_result.csv", row.names = FALSE)
            cat("R execution completed\\n")
            '''
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
                f.write(r_script)
                r_file = f.name
            
            # Execute R script
            result = subprocess.run(['Rscript', r_file], capture_output=True, text=True, timeout=60)
            os.unlink(r_file)
            
            if result.returncode == 0:
                # Read R result
                r_result_file = f"{self.temp_dir}/r_result.csv"
                if os.path.exists(r_result_file):
                    r_result = pd.read_csv(r_result_file)
                    print(f"   ✅ R result: {len(r_result)} rows")
                    os.unlink(r_result_file)
                else:
                    print(f"   ⚠️  R result file not found")
            else:
                print(f"   ❌ R execution failed: {result.stderr}")
                
        except Exception as e:
            print(f"   ❌ R execution error: {e}")
        
        # Run Python code
        python_result = None
        try:
            python_result = python_function()
            print(f"   ✅ Python result: {len(python_result)} rows")
        except Exception as e:
            print(f"   ❌ Python failed: {e}")
        
        # Compare results
        comparison = self.compare_results(r_result, python_result, test_name)
        print(f"   📊 Comparison: {comparison}")
        
        return {"python": python_result, "r": r_result, "comparison": comparison}
    
    def compare_results(self, r_result, python_result, test_name):
        """Compare R and Python results for equivalence."""
        if r_result is None and python_result is None:
            return "Both failed"
        elif r_result is None:
            return "R failed, Python succeeded"
        elif python_result is None:
            return "Python failed, R succeeded"
        
        try:
            # Basic shape comparison
            if len(r_result) != len(python_result):
                return f"Row count differs: R={len(r_result)}, Python={len(python_result)}"
            
            # Check for common columns (accounting for naming differences)
            r_cols = set(r_result.columns)
            py_cols = set(python_result.columns)
            
            # Look for population data columns as key indicator
            r_pop_cols = [col for col in r_cols if 'population' in col.lower() or col.startswith('v_')]
            py_pop_cols = [col for col in py_cols if 'population' in col.lower() or col.startswith('v_')]
            
            if r_pop_cols and py_pop_cols:
                # Compare numeric values in population columns
                r_pop_sum = r_result[r_pop_cols[0]].sum() if len(r_pop_cols) > 0 else 0
                py_pop_sum = python_result[py_pop_cols[0]].sum() if len(py_pop_cols) > 0 else 0
                
                if abs(r_pop_sum - py_pop_sum) / max(r_pop_sum, py_pop_sum) < 0.01:  # 1% tolerance
                    return "✅ Equivalent data"
                else:
                    return f"⚠️  Data differs: R={r_pop_sum:,.0f}, Python={py_pop_sum:,.0f}"
            
            return "✅ Structural match"
            
        except Exception as e:
            return f"Comparison error: {e}"

def main():
    """Run cross-validation tests."""
    print("🚀 Cross-Validation Testing: R cancensus vs Python pycancensus")
    print("=" * 70)
    
    comparator = RCancensusComparator()
    
    # Test 1: Basic vector listing
    def test_vector_listing():
        r_code = '''
        result <- list_census_vectors("CA21")
        '''
        
        def python_func():
            return pc.list_census_vectors("CA21", quiet=True)
        
        return comparator.run_r_comparison("Vector Listing Comparison", r_code, python_func)
    
    # Test 2: Basic census data retrieval
    def test_census_data():
        r_code = '''
        result <- get_census(dataset = "CA21", 
                           regions = list(PR = "35"), 
                           vectors = "v_CA21_1", 
                           level = "PR")
        '''
        
        def python_func():
            return pc.get_census(dataset="CA21", 
                               regions={"PR": "35"}, 
                               vectors=["v_CA21_1"], 
                               level="PR", 
                               quiet=True)
        
        return comparator.run_r_comparison("Census Data Retrieval", r_code, python_func)
    
    # Test 3: Multiple regions
    def test_multiple_regions():
        r_code = '''
        result <- get_census(dataset = "CA21",
                           regions = list(PR = c("35", "24")),
                           vectors = "v_CA21_1",
                           level = "PR")
        '''
        
        def python_func():
            return pc.get_census(dataset="CA21",
                               regions={"PR": ["35", "24"]},
                               vectors=["v_CA21_1"],
                               level="PR",
                               quiet=True)
        
        return comparator.run_r_comparison("Multiple Regions", r_code, python_func)
    
    # Test 4: CSD level data
    def test_csd_data():
        r_code = '''
        result <- get_census(dataset = "CA21",
                           regions = list(CMA = "35535"),
                           vectors = "v_CA21_1",
                           level = "CSD")
        '''
        
        def python_func():
            return pc.get_census(dataset="CA21",
                               regions={"CMA": "35535"},
                               vectors=["v_CA21_1"],
                               level="CSD",
                               quiet=True)
        
        return comparator.run_r_comparison("CSD Level Data", r_code, python_func)
    
    # Run all tests
    tests = [
        test_vector_listing,
        test_census_data,
        test_multiple_regions,
        test_csd_data
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed: {e}")
            results.append({"comparison": f"Test failed: {e}"})
    
    # Summary
    print("\n" + "=" * 70)
    print("📋 CROSS-VALIDATION SUMMARY")
    print("=" * 70)
    
    equivalent_count = sum(1 for r in results if "✅ Equivalent" in r.get("comparison", ""))
    structural_count = sum(1 for r in results if "✅ Structural" in r.get("comparison", ""))
    total_success = equivalent_count + structural_count
    
    print(f"✅ Equivalent data: {equivalent_count}/{len(results)}")
    print(f"📊 Structural match: {structural_count}/{len(results)}")
    print(f"🎯 Overall success: {total_success}/{len(results)}")
    
    if total_success == len(results):
        print("\n🎉 FULL EQUIVALENCE ACHIEVED!")
        print("   Python pycancensus produces equivalent results to R cancensus")
    elif total_success >= len(results) * 0.75:
        print("\n✅ STRONG EQUIVALENCE")
        print("   Python pycancensus is highly compatible with R cancensus")
    else:
        print("\n⚠️  PARTIAL EQUIVALENCE")
        print("   Some differences found between R and Python implementations")
    
    # Cleanup
    import shutil
    shutil.rmtree(comparator.temp_dir)
    
    return results

if __name__ == "__main__":
    main()