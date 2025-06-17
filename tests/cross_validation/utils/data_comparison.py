"""Utilities for comparing data between R and Python implementations."""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple, Optional
import json
from deepdiff import DeepDiff
from pathlib import Path
import hashlib

class DataComparator:
    """Compare data structures between R and Python implementations."""
    
    def __init__(self, tolerance: float = 1e-6):
        self.tolerance = tolerance
        self.comparison_results = []
    
    def compare_census_data(self, py_data: pd.DataFrame, r_data: pd.DataFrame,
                           test_name: str) -> Dict[str, Any]:
        """
        Compare census data from Python and R implementations.
        
        Parameters:
        -----------
        py_data : pd.DataFrame
            Data from pycancensus
        r_data : pd.DataFrame
            Data from cancensus
        test_name : str
            Name of the test for logging
            
        Returns:
        --------
        Dict[str, Any]
            Detailed comparison results
        """
        results = {
            "test_name": test_name,
            "timestamp": pd.Timestamp.now().isoformat(),
            "basic_match": {
                "shape": py_data.shape == r_data.shape,
                "columns": set(py_data.columns) == set(r_data.columns)
            },
            "shape_details": {
                "python": py_data.shape,
                "r": r_data.shape
            },
            "column_details": {
                "python_only": list(set(py_data.columns) - set(r_data.columns)),
                "r_only": list(set(r_data.columns) - set(py_data.columns)),
                "common": list(set(py_data.columns) & set(r_data.columns))
            },
            "data_comparison": {},
            "summary": {}
        }
        
        # If shapes or columns don't match, return early
        if not results["basic_match"]["shape"] or not results["basic_match"]["columns"]:
            results["summary"]["match"] = False
            results["summary"]["reason"] = "Shape or column mismatch"
            self.comparison_results.append(results)
            return results
        
        # Sort both dataframes by GeoUID for consistent comparison
        if "GeoUID" in py_data.columns:
            py_data = py_data.sort_values("GeoUID").reset_index(drop=True)
            r_data = r_data.sort_values("GeoUID").reset_index(drop=True)
        
        # Compare each column
        column_comparisons = {}
        all_match = True
        
        for col in results["column_details"]["common"]:
            col_result = self._compare_column(py_data[col], r_data[col], col)
            column_comparisons[col] = col_result
            if not col_result["match"]:
                all_match = False
        
        results["data_comparison"] = column_comparisons
        results["summary"]["match"] = all_match
        results["summary"]["mismatched_columns"] = [
            col for col, res in column_comparisons.items() if not res["match"]
        ]
        
        self.comparison_results.append(results)
        return results
    
    def _compare_column(self, py_col: pd.Series, r_col: pd.Series, 
                       col_name: str) -> Dict[str, Any]:
        """Compare individual columns between Python and R data."""
        result = {
            "column_name": col_name,
            "dtype_python": str(py_col.dtype),
            "dtype_r": str(r_col.dtype),
            "match": True,
            "differences": []
        }
        
        # Check for missing values
        py_na = py_col.isna()
        r_na = r_col.isna()
        
        if not (py_na == r_na).all():
            result["match"] = False
            result["differences"].append({
                "type": "missing_values",
                "python_na_count": int(py_na.sum()),
                "r_na_count": int(r_na.sum()),
                "mismatched_positions": int((py_na != r_na).sum())
            })
        
        # Compare non-missing values
        valid_mask = ~(py_na | r_na)
        
        if valid_mask.any():
            if pd.api.types.is_numeric_dtype(py_col):
                # Numeric comparison
                py_valid = py_col[valid_mask].values
                r_valid = r_col[valid_mask].values
                
                if not np.allclose(py_valid, r_valid, rtol=self.tolerance, atol=self.tolerance):
                    max_diff = np.max(np.abs(py_valid - r_valid))
                    result["match"] = False
                    result["differences"].append({
                        "type": "numeric",
                        "max_absolute_difference": float(max_diff),
                        "tolerance": self.tolerance,
                        "mismatched_count": int(np.sum(np.abs(py_valid - r_valid) > self.tolerance))
                    })
            else:
                # String/categorical comparison
                py_valid = py_col[valid_mask].astype(str)
                r_valid = r_col[valid_mask].astype(str)
                
                mismatches = py_valid != r_valid
                if mismatches.any():
                    result["match"] = False
                    result["differences"].append({
                        "type": "string",
                        "mismatched_count": int(mismatches.sum()),
                        "examples": self._get_mismatch_examples(
                            py_valid[mismatches], 
                            r_valid[mismatches], 
                            limit=5
                        )
                    })
        
        return result
    
    def _get_mismatch_examples(self, py_values: pd.Series, r_values: pd.Series,
                               limit: int = 5) -> List[Dict[str, str]]:
        """Get examples of mismatched values."""
        examples = []
        for i, (py_val, r_val) in enumerate(zip(py_values.head(limit), r_values.head(limit))):
            examples.append({
                "index": int(py_values.index[i]),
                "python": str(py_val),
                "r": str(r_val)
            })
        return examples
    
    def compare_api_responses(self, py_response: Dict[str, Any], 
                            r_response: Dict[str, Any],
                            test_name: str) -> Dict[str, Any]:
        """Compare raw API responses between Python and R."""
        result = {
            "test_name": test_name,
            "timestamp": pd.Timestamp.now().isoformat(),
            "deep_diff": {},
            "summary": {}
        }
        
        # Use DeepDiff for detailed comparison
        diff = DeepDiff(py_response, r_response, ignore_order=True, 
                       significant_digits=6)
        
        if diff:
            result["deep_diff"] = diff.to_dict()
            result["summary"]["match"] = False
            result["summary"]["difference_types"] = list(diff.keys())
        else:
            result["summary"]["match"] = True
            result["summary"]["difference_types"] = []
        
        self.comparison_results.append(result)
        return result
    
    def compare_geometries(self, py_geom: Any, r_geom: Any,
                          test_name: str) -> Dict[str, Any]:
        """Compare geometric data between Python and R."""
        result = {
            "test_name": test_name,
            "timestamp": pd.Timestamp.now().isoformat(),
            "geometry_comparison": {},
            "summary": {}
        }
        
        # TODO: Implement detailed geometry comparison
        # For now, just check if both have geometry
        has_py_geom = hasattr(py_geom, 'geometry') or 'geometry' in py_geom.columns
        has_r_geom = r_geom is not None and 'geometry' in str(type(r_geom)).lower()
        
        result["geometry_comparison"]["python_has_geometry"] = has_py_geom
        result["geometry_comparison"]["r_has_geometry"] = has_r_geom
        result["summary"]["match"] = has_py_geom == has_r_geom
        
        self.comparison_results.append(result)
        return result
    
    def save_results(self, output_dir: Path):
        """Save all comparison results to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save detailed results as JSON
        with open(output_dir / "detailed_comparison_results.json", "w") as f:
            json.dump(self.comparison_results, f, indent=2, default=str)
        
        # Create summary report
        summary = self._create_summary_report()
        with open(output_dir / "comparison_summary.md", "w") as f:
            f.write(summary)
    
    def _create_summary_report(self) -> str:
        """Create a markdown summary of all comparisons."""
        report = ["# Data Comparison Summary\n"]
        report.append(f"Generated: {pd.Timestamp.now()}\n")
        
        # Overall statistics
        total_tests = len(self.comparison_results)
        passed_tests = sum(1 for r in self.comparison_results 
                          if r.get("summary", {}).get("match", False))
        
        report.append(f"## Overall Results: {passed_tests}/{total_tests} tests passed\n")
        
        # Detailed results by test
        report.append("## Test Details\n")
        
        for result in self.comparison_results:
            test_name = result.get("test_name", "Unknown")
            match = result.get("summary", {}).get("match", False)
            status = "✅ PASS" if match else "❌ FAIL"
            
            report.append(f"### {test_name}: {status}\n")
            
            if not match:
                # Add failure details
                if "reason" in result.get("summary", {}):
                    report.append(f"- Reason: {result['summary']['reason']}\n")
                
                if "mismatched_columns" in result.get("summary", {}):
                    cols = result["summary"]["mismatched_columns"]
                    report.append(f"- Mismatched columns: {', '.join(cols)}\n")
                
                if "difference_types" in result.get("summary", {}):
                    types = result["summary"]["difference_types"]
                    report.append(f"- Difference types: {', '.join(types)}\n")
            
            report.append("\n")
        
        return "".join(report)
    
    def generate_hash(self, data: pd.DataFrame) -> str:
        """Generate a hash of dataframe for quick comparison."""
        # Sort by columns and index for consistent hashing
        sorted_data = data.sort_index(axis=1).sort_index(axis=0)
        
        # Convert to string representation
        data_str = sorted_data.to_json(orient='records', date_format='iso')
        
        # Generate hash
        return hashlib.sha256(data_str.encode()).hexdigest()