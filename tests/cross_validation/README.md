# Cross-Validation Framework: cancensus vs pycancensus

**🚨 IMPORTANT: This directory is excluded from library builds and distributions**

This directory contains development-only cross-validation framework for ensuring equivalence between the R cancensus library and the Python pycancensus port.

**Location**: `tests/cross_validation/` (excluded from package distribution)  
**Purpose**: Development testing and R-Python equivalence validation  
**Distribution**: Not included in pip installs or library builds

## Overview

The cross-validation framework tests the following aspects:
1. API Response Equivalence - Ensuring both libraries receive identical data from the CensusMapper API
2. Data Processing Equivalence - Verifying data transformation and type conversions match
3. Geometry Handling - Comparing spatial data processing between R and Python
4. Error Handling - Ensuring both libraries handle edge cases consistently
5. Performance Comparison - Benchmarking relative performance

## Structure

```
cross_validation/
├── README.md                 # This file
├── requirements.txt          # Python dependencies for testing
├── install_r_deps.R         # R dependencies installation script
├── tests/
│   ├── test_api_equivalence.py
│   ├── test_api_equivalence.R
│   ├── test_data_processing.py
│   ├── test_data_processing.R
│   ├── test_geometry_handling.py
│   ├── test_geometry_handling.R
│   ├── test_error_handling.py
│   ├── test_error_handling.R
│   └── test_performance.py
├── results/
│   ├── api_equivalence_results.md
│   ├── data_processing_results.md
│   ├── geometry_results.md
│   ├── error_handling_results.md
│   └── performance_results.md
├── utils/
│   ├── r_python_bridge.py   # Utilities for running R from Python
│   ├── data_comparison.py    # Data comparison utilities
│   └── test_runner.py        # Main test orchestration
└── run_all_tests.sh         # Shell script to run all tests

## Key Findings

### API Compatibility Issues Identified

1. **Region Parameter Format**: The R library always sends region values as arrays in JSON, even for single values. This was causing API errors in pycancensus.

2. **Missing geo_hierarchy Parameter**: The Python implementation was missing the `geo_hierarchy` parameter in API requests, leading to incomplete data returns.

3. **Vector Hierarchy Functions**: The Python implementation lacks parent/child vector navigation functions present in the R library.

### Data Processing Differences

1. **NA Value Handling**: Both libraries handle census-specific NA values ('x', 'F', '...') but with slightly different approaches.

2. **Type Conversion**: The R library has more sophisticated type detection based on vector metadata.

3. **Column Naming**: Both handle API response column names with trailing spaces, but implementation differs.

### Recommendations for pycancensus Improvements

Based on cross-validation results, the following improvements are recommended:

#### High Priority
1. Fix API request format to match R library exactly
2. Implement missing vector hierarchy functions
3. Add comprehensive error handling for recalled data
4. Improve test coverage

#### Medium Priority
1. Add retry logic with exponential backoff
2. Implement progress indicators for large downloads
3. Refactor large functions for maintainability
4. Add connection pooling for API requests

#### Low Priority
1. Add interactive exploration tools
2. Implement custom aggregation levels
3. Create visualization helpers
4. Enhance CLI functionality

## Running the Tests

### Prerequisites

1. Install R dependencies:
```bash
Rscript install_r_deps.R
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set your CensusMapper API key:
```bash
export CANCENSUS_API_KEY="your_api_key_here"
```

### Running All Tests

```bash
./run_all_tests.sh
```

### Running Individual Test Suites

```bash
# API Equivalence Tests
python tests/test_api_equivalence.py
Rscript tests/test_api_equivalence.R

# Data Processing Tests
python tests/test_data_processing.py
Rscript tests/test_data_processing.R

# Geometry Handling Tests
python tests/test_geometry_handling.py
Rscript tests/test_geometry_handling.R

# Error Handling Tests
python tests/test_error_handling.py
Rscript tests/test_error_handling.R

# Performance Tests
python tests/test_performance.py
```

## Test Design Principles

1. **Reproducibility**: All tests use fixed seeds and deterministic data selection
2. **Isolation**: Each test is independent and can be run separately
3. **Comprehensive Coverage**: Tests cover common use cases and edge cases
4. **Clear Reporting**: Results are saved in both human-readable and machine-parseable formats
5. **Performance Aware**: Tests are designed to minimize API calls while ensuring thorough validation