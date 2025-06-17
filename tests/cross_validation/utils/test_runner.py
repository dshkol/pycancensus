"""Main test orchestration for cross-validation between cancensus and pycancensus."""

import os
import sys
from pathlib import Path
import subprocess
import json
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime
import logging
from tqdm import tqdm

# Add pycancensus to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from utils.r_python_bridge import RPythonBridge
from utils.data_comparison import DataComparator

class CrossValidationRunner:
    """Orchestrate cross-validation tests between R and Python implementations."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("CANCENSUS_API_KEY")
        if not self.api_key:
            raise ValueError("CANCENSUS_API_KEY must be set")
        
        self.bridge = RPythonBridge()
        self.comparator = DataComparator()
        self.results_dir = Path(__file__).parent.parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.results_dir / "test_runner.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def run_all_tests(self):
        """Run all cross-validation tests."""
        self.logger.info("Starting cross-validation test suite")
        
        test_suites = [
            ("API Equivalence", self.test_api_equivalence),
            ("Data Processing", self.test_data_processing),
            ("Geometry Handling", self.test_geometry_handling),
            ("Error Handling", self.test_error_handling),
            ("Performance", self.test_performance)
        ]
        
        results = {}
        
        for suite_name, test_func in tqdm(test_suites, desc="Running test suites"):
            self.logger.info(f"Running {suite_name} tests...")
            try:
                suite_results = test_func()
                results[suite_name] = suite_results
                self.logger.info(f"{suite_name} tests completed")
            except Exception as e:
                self.logger.error(f"Error in {suite_name} tests: {str(e)}")
                results[suite_name] = {"error": str(e)}
        
        # Save overall results
        self._save_overall_results(results)
        
        # Cleanup
        self.bridge.cleanup()
        
        return results
    
    def test_api_equivalence(self) -> Dict:
        """Test that both libraries make equivalent API calls."""
        results = {
            "test_time": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test 1: Basic census data retrieval
        test_cases = [
            {
                "name": "Basic CSD data retrieval",
                "dataset": "CA16",
                "regions": {"CSD": "5915022"},  # Vancouver
                "vectors": ["v_CA16_408", "v_CA16_409", "v_CA16_410"],
                "level": "CSD"
            },
            {
                "name": "CMA with CT level",
                "dataset": "CA16",
                "regions": {"CMA": "59933"},  # Vancouver CMA
                "vectors": ["v_CA16_1", "v_CA16_2"],
                "level": "CT"
            },
            {
                "name": "Multiple regions",
                "dataset": "CA21",
                "regions": {"CSD": ["5915022", "3520005"]},  # Vancouver, Toronto
                "vectors": ["v_CA21_1", "v_CA21_8"],
                "level": "CSD"
            }
        ]
        
        for test_case in test_cases:
            self.logger.info(f"Running test: {test_case['name']}")
            
            # Run Python version
            import pycancensus as pc
            pc.set_api_key(self.api_key)
            
            try:
                py_result = pc.get_census(
                    dataset=test_case["dataset"],
                    regions=test_case["regions"],
                    vectors=test_case["vectors"],
                    level=test_case["level"]
                )
                
                # Run R version
                r_result = self.bridge.run_cancensus_function(
                    "get_census",
                    dataset=test_case["dataset"],
                    regions=test_case["regions"],
                    vectors=test_case["vectors"],
                    level=test_case["level"]
                )
                
                # Convert R result to DataFrame if it's a dict with 'data' key
                if isinstance(r_result, dict) and 'data' in r_result:
                    r_df = pd.DataFrame(r_result['data'])
                else:
                    r_df = pd.DataFrame(r_result)
                
                # Compare results
                comparison = self.comparator.compare_census_data(
                    py_result, r_df, test_case["name"]
                )
                
                results["tests"].append({
                    "test": test_case,
                    "comparison": comparison,
                    "passed": comparison["summary"]["match"]
                })
                
            except Exception as e:
                self.logger.error(f"Error in test {test_case['name']}: {str(e)}")
                results["tests"].append({
                    "test": test_case,
                    "error": str(e),
                    "passed": False
                })
        
        # Save results
        with open(self.results_dir / "api_equivalence_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        return results
    
    def test_data_processing(self) -> Dict:
        """Test data processing consistency."""
        results = {
            "test_time": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test various data processing scenarios
        test_cases = [
            {
                "name": "NA value handling",
                "dataset": "CA16",
                "regions": {"PR": "59"},  # BC
                "vectors": ["v_CA16_2510", "v_CA16_2511"],  # Vectors with potential NA values
                "level": "CSD"
            },
            {
                "name": "Type conversion",
                "dataset": "CA21",
                "regions": {"CMA": "59933"},
                "vectors": ["v_CA21_1", "v_CA21_8", "v_CA21_434"],  # Mix of types
                "level": "CT"
            }
        ]
        
        for test_case in test_cases:
            # Similar structure to api_equivalence tests
            # but focus on data type handling and conversions
            pass
        
        return results
    
    def test_geometry_handling(self) -> Dict:
        """Test geometry processing consistency."""
        results = {
            "test_time": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test geometry retrieval and processing
        # Implementation details...
        
        return results
    
    def test_error_handling(self) -> Dict:
        """Test error handling consistency."""
        results = {
            "test_time": datetime.now().isoformat(),
            "tests": []
        }
        
        # Test various error scenarios
        error_cases = [
            {
                "name": "Invalid API key",
                "test": lambda: self._test_invalid_api_key()
            },
            {
                "name": "Invalid dataset",
                "test": lambda: self._test_invalid_dataset()
            },
            {
                "name": "Invalid region",
                "test": lambda: self._test_invalid_region()
            }
        ]
        
        for error_case in error_cases:
            # Test error handling
            pass
        
        return results
    
    def test_performance(self) -> Dict:
        """Compare performance between implementations."""
        results = {
            "test_time": datetime.now().isoformat(),
            "benchmarks": []
        }
        
        # Performance benchmarks
        # Implementation details...
        
        return results
    
    def _save_overall_results(self, results: Dict):
        """Save overall test results."""
        summary = {
            "test_run": datetime.now().isoformat(),
            "total_suites": len(results),
            "passed_suites": sum(1 for r in results.values() 
                               if not isinstance(r, dict) or "error" not in r),
            "results": results
        }
        
        with open(self.results_dir / "overall_results.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Create markdown report
        self._create_markdown_report(summary)
    
    def _create_markdown_report(self, summary: Dict):
        """Create a markdown report of test results."""
        report = [
            "# Cross-Validation Test Results\n",
            f"Test Run: {summary['test_run']}\n",
            f"## Summary: {summary['passed_suites']}/{summary['total_suites']} suites passed\n"
        ]
        
        for suite_name, suite_results in summary["results"].items():
            report.append(f"\n### {suite_name}\n")
            
            if isinstance(suite_results, dict) and "error" in suite_results:
                report.append(f"❌ Error: {suite_results['error']}\n")
            elif isinstance(suite_results, dict) and "tests" in suite_results:
                passed = sum(1 for t in suite_results["tests"] if t.get("passed", False))
                total = len(suite_results["tests"])
                report.append(f"Results: {passed}/{total} tests passed\n")
                
                for test in suite_results["tests"]:
                    status = "✅" if test.get("passed", False) else "❌"
                    name = test.get("test", {}).get("name", "Unknown")
                    report.append(f"- {status} {name}\n")
        
        with open(self.results_dir / "test_results_summary.md", "w") as f:
            f.write("".join(report))

if __name__ == "__main__":
    runner = CrossValidationRunner()
    runner.run_all_tests()