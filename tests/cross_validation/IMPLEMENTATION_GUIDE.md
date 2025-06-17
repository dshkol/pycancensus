# pycancensus Implementation Guide

**Next Steps for Improving pycancensus**

Based on the comprehensive analysis, this guide provides concrete steps to implement the recommended improvements while ensuring equivalence with the cancensus R library.

## Quick Start: Running the Analysis

### 1. Run Cross-Validation Tests

```bash
# Set up environment
export CANCENSUS_API_KEY="your_api_key_here"

# Navigate to cross-validation directory
cd /Users/dmitryshkolnik/Projects/pycancensus/cross_validation

# Install dependencies
Rscript install_r_deps.R
pip install -r requirements.txt

# Run all tests
./run_all_tests.sh
```

### 2. Run Basic Integration Tests

```bash
# From pycancensus root directory
python -m pytest tests/integration/test_cancensus_compatibility.py -v
```

## Priority Implementation Tasks

### Task 1: Fix API Request Format (HIGH PRIORITY)

**Problem**: Region parameters not always sent as arrays in JSON requests.

**Location**: `pycancensus/core.py` in `_make_api_request()` function

**Current Issue**:
```python
# Current implementation may send:
{"regions": {"CSD": "5915022"}}

# Should always send:
{"regions": {"CSD": ["5915022"]}}
```

**Fix**:
```python
def _prepare_regions_for_api(regions):
    """Ensure all region values are arrays for API consistency."""
    formatted_regions = {}
    for level, codes in regions.items():
        if isinstance(codes, str):
            formatted_regions[level] = [codes]
        elif isinstance(codes, list):
            formatted_regions[level] = codes
        else:
            formatted_regions[level] = [str(codes)]
    return formatted_regions
```

### Task 2: Add Missing Vector Hierarchy Functions (HIGH PRIORITY)

**Create new file**: `pycancensus/hierarchy.py`

```python
"""Vector hierarchy navigation functions."""

import pandas as pd
from typing import List, Dict, Optional
from .utils import make_api_request

def parent_census_vectors(vectors: List[str], dataset: str = None) -> pd.DataFrame:
    """
    Get parent vectors for given child vectors.
    
    Parameters:
    -----------
    vectors : List[str]
        List of vector IDs to find parents for
    dataset : str, optional
        Dataset to search in. If None, inferred from vectors
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with parent vector information
    """
    if dataset is None:
        # Infer dataset from first vector
        dataset = vectors[0].split('_')[1] if vectors else None
        if not dataset:
            raise ValueError("Dataset must be specified or inferable from vectors")
    
    # API call to get vector hierarchy
    url = "https://censusmapper.ca/api/v1/vector_hierarchy"
    params = {
        "vectors": vectors,
        "dataset": dataset,
        "direction": "parent"
    }
    
    response = make_api_request(url, params)
    return pd.DataFrame(response.get("vectors", []))

def child_census_vectors(vectors: List[str], dataset: str = None) -> pd.DataFrame:
    """
    Get child vectors for given parent vectors.
    
    Parameters:
    -----------
    vectors : List[str]
        List of parent vector IDs
    dataset : str, optional
        Dataset to search in
        
    Returns:
    --------
    pd.DataFrame
        DataFrame with child vector information
    """
    if dataset is None:
        dataset = vectors[0].split('_')[1] if vectors else None
        if not dataset:
            raise ValueError("Dataset must be specified or inferable from vectors")
    
    url = "https://censusmapper.ca/api/v1/vector_hierarchy"
    params = {
        "vectors": vectors,
        "dataset": dataset,
        "direction": "child"
    }
    
    response = make_api_request(url, params)
    return pd.DataFrame(response.get("vectors", []))

def find_census_vectors(dataset: str, query: str, 
                       search_type: str = "semantic") -> pd.DataFrame:
    """
    Enhanced vector search with semantic and fuzzy matching.
    
    Parameters:
    -----------
    dataset : str
        Dataset to search in
    query : str
        Search query
    search_type : str
        Type of search: "semantic", "fuzzy", "exact", "keyword"
        
    Returns:
    --------
    pd.DataFrame
        Matching vectors with relevance scores
    """
    url = "https://censusmapper.ca/api/v1/vector_search"
    params = {
        "dataset": dataset,
        "query": query,
        "type": search_type
    }
    
    response = make_api_request(url, params)
    return pd.DataFrame(response.get("vectors", []))
```

### Task 3: Implement Retry Logic (HIGH PRIORITY)

**Create**: `pycancensus/request_handler.py`

```python
"""Enhanced request handling with retry logic."""

import time
import requests
from typing import Dict, Any, Optional
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for retrying failed API requests."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    last_exception = e
                    if attempt < max_retries:
                        wait_time = backoff_factor * (2 ** attempt)
                        logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")
                        
            raise last_exception
        return wrapper
    return decorator

class EnhancedAPIClient:
    """Enhanced API client with connection pooling and retry logic."""
    
    def __init__(self):
        self.session = requests.Session()
        # Connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=0  # We handle retries manually
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
    
    @retry_on_failure(max_retries=3, backoff_factor=1.0)
    def make_request(self, url: str, params: Dict[str, Any], 
                    method: str = "GET") -> requests.Response:
        """Make API request with retry logic."""
        if method.upper() == "GET":
            response = self.session.get(url, params=params, timeout=30)
        elif method.upper() == "POST":
            response = self.session.post(url, json=params, timeout=60)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        response.raise_for_status()
        return response
    
    def __del__(self):
        """Clean up session on deletion."""
        if hasattr(self, 'session'):
            self.session.close()

# Global client instance
_api_client = EnhancedAPIClient()

def make_enhanced_api_request(url: str, params: Dict[str, Any], 
                            method: str = "GET") -> Dict[str, Any]:
    """Make API request using the enhanced client."""
    response = _api_client.make_request(url, params, method)
    return response.json()
```

### Task 4: Add Progress Indicators (MEDIUM PRIORITY)

**Update**: `pycancensus/core.py`

```python
from tqdm import tqdm

def get_census(dataset, regions, vectors=None, level="Regions", 
              geo_format=None, use_cache=True, quiet=False, 
              show_progress=True, **kwargs):
    """Enhanced get_census with progress indicators."""
    
    # ... existing code ...
    
    if show_progress and not quiet:
        # Calculate total work units
        total_regions = sum(len(v) if isinstance(v, list) else 1 
                          for v in regions.values())
        
        with tqdm(total=total_regions, desc="Fetching census data", 
                 disable=quiet) as pbar:
            
            # Process regions with progress updates
            for region_type, region_codes in regions.items():
                if isinstance(region_codes, str):
                    region_codes = [region_codes]
                
                for code in region_codes:
                    # Fetch data for region
                    # ... processing code ...
                    pbar.update(1)
    
    # ... rest of function ...
```

### Task 5: Improve Error Handling (MEDIUM PRIORITY)

**Create**: `pycancensus/exceptions.py`

```python
"""Custom exceptions for pycancensus."""

class PyCancensusError(Exception):
    """Base exception for pycancensus."""
    pass

class APIError(PyCancensusError):
    """API-related errors."""
    def __init__(self, message, error_code=None, suggestion=None):
        super().__init__(message)
        self.error_code = error_code
        self.suggestion = suggestion
    
    def __str__(self):
        msg = super().__str__()
        if self.suggestion:
            msg += f"\nSuggestion: {self.suggestion}"
        return msg

class InvalidAPIKeyError(APIError):
    """Raised when API key is invalid or missing."""
    def __init__(self):
        super().__init__(
            "Invalid or missing API key",
            error_code="AUTH_ERROR",
            suggestion="Get a free API key at https://censusmapper.ca/users/sign_up"
        )

class InvalidRegionError(APIError):
    """Raised when region is invalid."""
    def __init__(self, region):
        super().__init__(
            f"Invalid region: {region}",
            error_code="INVALID_REGION",
            suggestion="Use list_census_regions() to find valid regions"
        )

class InvalidVectorError(APIError):
    """Raised when vector is invalid."""
    def __init__(self, vector):
        super().__init__(
            f"Invalid vector: {vector}",
            error_code="INVALID_VECTOR", 
            suggestion="Use list_census_vectors() to find valid vectors"
        )

class DataNotFoundError(APIError):
    """Raised when requested data is not available."""
    def __init__(self, details=""):
        super().__init__(
            f"Requested data not found{': ' + details if details else ''}",
            error_code="DATA_NOT_FOUND",
            suggestion="Check your region and vector specifications"
        )
```

### Task 6: Refactor Large Functions (MEDIUM PRIORITY)

**Refactor**: `pycancensus/core.py`

```python
def get_census(dataset, regions, vectors=None, level="Regions", 
              geo_format=None, use_cache=True, quiet=False, **kwargs):
    """Refactored get_census function."""
    
    # Validate inputs
    _validate_census_inputs(dataset, regions, vectors, level, geo_format)
    
    # Check cache first
    if use_cache:
        cached_data = _check_census_cache(dataset, regions, vectors, level, geo_format)
        if cached_data is not None:
            return cached_data
    
    # Fetch data
    if geo_format:
        data = _fetch_census_with_geometry(dataset, regions, vectors, level, geo_format, quiet)
    else:
        data = _fetch_census_data_only(dataset, regions, vectors, level, quiet)
    
    # Cache result
    if use_cache:
        _cache_census_data(dataset, regions, vectors, level, geo_format, data)
    
    return data

def _validate_census_inputs(dataset, regions, vectors, level, geo_format):
    """Validate all inputs for get_census."""
    # Input validation logic
    pass

def _fetch_census_data_only(dataset, regions, vectors, level, quiet):
    """Fetch census data without geometry."""
    # Data-only fetching logic
    pass

def _fetch_census_with_geometry(dataset, regions, vectors, level, geo_format, quiet):
    """Fetch census data with geometry."""
    # Geometry + data fetching logic
    pass
```

## Testing Implementation

### Add Comprehensive Integration Tests

**Create**: `tests/integration/test_r_equivalence.py`

```python
"""Tests that verify equivalence with R cancensus library."""

import pytest
import pandas as pd
import subprocess
import json
import tempfile
from pathlib import Path

import pycancensus as pc

class TestREquivalence:
    """Test equivalence with R cancensus library."""
    
    @pytest.fixture(autouse=True)
    def setup_api_key(self):
        """Setup API key for tests."""
        api_key = os.environ.get("CANCENSUS_API_KEY")
        if not api_key:
            pytest.skip("CANCENSUS_API_KEY not set")
        pc.set_api_key(api_key)
    
    def run_r_code(self, r_code):
        """Execute R code and return results."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.R', delete=False) as f:
            f.write(r_code)
            r_script = f.name
        
        try:
            result = subprocess.run(
                ['Rscript', r_script],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        finally:
            Path(r_script).unlink()
    
    def test_basic_data_equivalence(self):
        """Test that basic data retrieval matches R results."""
        # Define test case
        dataset = "CA21"
        regions = {"PR": "59"}  # BC
        vectors = ["v_CA21_1"]
        level = "PR"
        
        # Get Python results
        py_data = pc.get_census(
            dataset=dataset,
            regions=regions,
            vectors=vectors,
            level=level
        )
        
        # Get R results
        r_code = f'''
        library(cancensus)
        set_cancensus_api_key("{os.environ.get("CANCENSUS_API_KEY")}")
        
        data <- get_census(
            dataset = "{dataset}",
            regions = list(PR = "{regions['PR']}"),
            vectors = "{vectors[0]}",
            level = "{level}",
            geo_format = NA
        )
        
        cat(jsonlite::toJSON(as.data.frame(data), auto_unbox = TRUE))
        '''
        
        r_output = self.run_r_code(r_code)
        r_data = pd.DataFrame(json.loads(r_output))
        
        # Compare key columns
        assert py_data.shape == r_data.shape
        pd.testing.assert_series_equal(
            py_data[vectors[0]], 
            r_data[vectors[0]], 
            check_names=False
        )
```

## Documentation Improvements

### Update README with Better Examples

**Update**: `README.md`

```markdown
## Advanced Usage

### Working with Vector Hierarchies

```python
import pycancensus as pc

# Find all vectors related to income
income_vectors = pc.find_census_vectors("CA21", "income", "semantic")

# Get parent vectors for detailed breakdowns
parent_vectors = pc.parent_census_vectors(["v_CA21_906", "v_CA21_907"])

# Get child vectors for broader categories
child_vectors = pc.child_census_vectors(["v_CA21_906"])
```

### Performance Tips

```python
# Use connection pooling for multiple requests
from pycancensus.request_handler import EnhancedAPIClient

# Enable progress bars for large datasets
data = pc.get_census(
    dataset="CA21",
    regions={"PR": "35"},  # Ontario
    vectors=["v_CA21_1", "v_CA21_2"],
    level="DA",  # Many records
    show_progress=True
)

# Use caching to avoid repeated API calls
pc.set_cache_path("/path/to/cache")
data = pc.get_census(..., use_cache=True)
```
```

## Deployment Checklist

### Before Implementation

- [ ] Set up development environment with both R and Python
- [ ] Ensure API key is available for testing
- [ ] Create backup of current pycancensus code
- [ ] Set up testing database/cache for development

### Implementation Order

1. [ ] Task 1: Fix API request format
2. [ ] Task 2: Add retry logic and error handling
3. [ ] Task 3: Implement vector hierarchy functions
4. [ ] Task 4: Add progress indicators
5. [ ] Task 5: Refactor large functions
6. [ ] Task 6: Expand test coverage
7. [ ] Task 7: Update documentation

### Post-Implementation

- [ ] Run full cross-validation test suite
- [ ] Performance benchmarking against R library
- [ ] Update version number and changelog
- [ ] Create migration guide for existing users

## Getting Help

### If Tests Fail

1. Check API key is set: `echo $CANCENSUS_API_KEY`
2. Verify R dependencies: `Rscript -e "library(cancensus)"`
3. Check Python dependencies: `python -c "import pycancensus"`
4. Run individual tests to isolate issues
5. Check logs in `cross_validation/results/test_runner.log`

### Common Issues

- **API rate limiting**: Add delays between requests
- **Large dataset timeouts**: Increase timeout values
- **Memory issues**: Process data in chunks
- **Geometry errors**: Ensure geopandas is properly installed

This implementation guide provides a concrete roadmap for improving pycancensus while maintaining equivalence with the R cancensus library.