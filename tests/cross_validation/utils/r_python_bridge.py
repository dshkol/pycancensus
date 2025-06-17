"""Utilities for running R code from Python and comparing results."""

import subprocess
import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import tempfile
import os

class RPythonBridge:
    """Bridge for running R code and comparing results with Python."""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def run_r_code(self, r_code: str, return_type: str = "json") -> Any:
        """
        Run R code and return results.
        
        Parameters:
        -----------
        r_code : str
            R code to execute
        return_type : str
            Type of return value: 'json', 'csv', 'raw'
            
        Returns:
        --------
        Any
            Results from R execution
        """
        # Create temporary R script
        r_script_path = Path(self.temp_dir) / "temp_script.R"
        output_path = Path(self.temp_dir) / f"output.{return_type}"
        
        # Wrap R code to save output
        wrapped_code = self._wrap_r_code(r_code, output_path, return_type)
        
        with open(r_script_path, 'w') as f:
            f.write(wrapped_code)
        
        # Run R script
        try:
            result = subprocess.run(
                ['Rscript', str(r_script_path)],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse output based on type
            if return_type == "json" and output_path.exists():
                with open(output_path, 'r') as f:
                    return json.load(f)
            elif return_type == "csv" and output_path.exists():
                return pd.read_csv(output_path)
            else:
                return result.stdout
                
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"R execution failed: {e.stderr}")
        finally:
            # Cleanup
            if r_script_path.exists():
                r_script_path.unlink()
            if output_path.exists():
                output_path.unlink()
    
    def _wrap_r_code(self, r_code: str, output_path: Path, return_type: str) -> str:
        """Wrap R code to save output in specified format."""
        if return_type == "json":
            wrapper = f"""
library(jsonlite)
result <- {{
{r_code}
}}
write_json(result, "{output_path}", auto_unbox = TRUE, pretty = TRUE)
"""
        elif return_type == "csv":
            wrapper = f"""
result <- {{
{r_code}
}}
write.csv(result, "{output_path}", row.names = FALSE)
"""
        else:
            wrapper = r_code
            
        return wrapper
    
    def compare_dataframes(self, df_python: pd.DataFrame, df_r: pd.DataFrame, 
                          tolerance: float = 1e-6) -> Dict[str, Any]:
        """
        Compare dataframes from Python and R.
        
        Parameters:
        -----------
        df_python : pd.DataFrame
            DataFrame from Python
        df_r : pd.DataFrame
            DataFrame from R
        tolerance : float
            Numerical tolerance for comparison
            
        Returns:
        --------
        Dict[str, Any]
            Comparison results
        """
        results = {
            "shapes_match": df_python.shape == df_r.shape,
            "python_shape": df_python.shape,
            "r_shape": df_r.shape,
            "columns_match": set(df_python.columns) == set(df_r.columns),
            "python_columns": list(df_python.columns),
            "r_columns": list(df_r.columns),
            "differences": []
        }
        
        if not results["shapes_match"] or not results["columns_match"]:
            return results
        
        # Compare values column by column
        for col in df_python.columns:
            if col not in df_r.columns:
                continue
                
            py_vals = df_python[col]
            r_vals = df_r[col]
            
            # Handle numeric columns
            if pd.api.types.is_numeric_dtype(py_vals) and pd.api.types.is_numeric_dtype(r_vals):
                # Check for NaN alignment
                nan_match = (py_vals.isna() == r_vals.isna()).all()
                if not nan_match:
                    results["differences"].append({
                        "column": col,
                        "type": "nan_mismatch",
                        "python_nan_count": py_vals.isna().sum(),
                        "r_nan_count": r_vals.isna().sum()
                    })
                
                # Compare non-NaN values
                mask = ~(py_vals.isna() | r_vals.isna())
                if mask.any():
                    max_diff = np.abs(py_vals[mask] - r_vals[mask]).max()
                    if max_diff > tolerance:
                        results["differences"].append({
                            "column": col,
                            "type": "numeric_difference",
                            "max_difference": float(max_diff),
                            "tolerance": tolerance
                        })
            
            # Handle string columns
            elif pd.api.types.is_string_dtype(py_vals) or pd.api.types.is_string_dtype(r_vals):
                # Convert to string for comparison
                py_str = py_vals.astype(str)
                r_str = r_vals.astype(str)
                
                mismatches = (py_str != r_str).sum()
                if mismatches > 0:
                    results["differences"].append({
                        "column": col,
                        "type": "string_mismatch",
                        "mismatch_count": int(mismatches),
                        "total_rows": len(py_vals)
                    })
        
        results["match"] = len(results["differences"]) == 0
        return results
    
    def run_cancensus_function(self, function_name: str, **kwargs) -> Any:
        """
        Run a cancensus function with given parameters.
        
        Parameters:
        -----------
        function_name : str
            Name of cancensus function to run
        **kwargs : dict
            Arguments to pass to the function
            
        Returns:
        --------
        Any
            Function results
        """
        # Convert Python arguments to R format
        r_args = self._python_to_r_args(kwargs)
        
        # Build R code
        r_code = f"""
library(cancensus)
library(sf)

# Set API key if provided
if (Sys.getenv("CANCENSUS_API_KEY") != "") {{
    set_cancensus_api_key(Sys.getenv("CANCENSUS_API_KEY"))
}}

# Call function
result <- {function_name}({r_args})

# Convert to appropriate format
if ("sf" %in% class(result)) {{
    # Convert sf object to list with data and geometry
    list(
        data = st_drop_geometry(result),
        geometry = st_as_text(st_geometry(result))
    )
}} else {{
    result
}}
"""
        
        return self.run_r_code(r_code, return_type="json")
    
    def _python_to_r_args(self, kwargs: Dict[str, Any]) -> str:
        """Convert Python arguments to R function call format."""
        args = []
        
        for key, value in kwargs.items():
            if isinstance(value, str):
                args.append(f'{key} = "{value}"')
            elif isinstance(value, list):
                if all(isinstance(v, str) for v in value):
                    r_vec = 'c(' + ', '.join(f'"{v}"' for v in value) + ')'
                else:
                    r_vec = 'c(' + ', '.join(str(v) for v in value) + ')'
                args.append(f'{key} = {r_vec}')
            elif isinstance(value, dict):
                # Handle region specification
                r_list_items = []
                for k, v in value.items():
                    if isinstance(v, str):
                        r_list_items.append(f'{k} = "{v}"')
                    else:
                        r_list_items.append(f'{k} = {v}')
                r_list = 'list(' + ', '.join(r_list_items) + ')'
                args.append(f'{key} = {r_list}')
            elif value is None:
                args.append(f'{key} = NULL')
            elif isinstance(value, bool):
                args.append(f'{key} = {str(value).upper()}')
            else:
                args.append(f'{key} = {value}')
        
        return ', '.join(args)
    
    def cleanup(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)