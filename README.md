# pycancensus

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Documentation Status](https://readthedocs.org/projects/pycancensus/badge/?version=latest)](https://pycancensus.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)
[![R Equivalence](https://img.shields.io/badge/R%20equivalence-verified-blue.svg)](tests/cross_validation/)

Access, retrieve, and work with Canadian Census data and geography.

**pycancensus** is a Python package that provides integrated, convenient, and uniform access to Canadian Census data and geography retrieved using the CensusMapper API. This package produces analysis-ready tidy DataFrames and spatial data in multiple formats, with full equivalence to the R cancensus library.

## Recent Updates

- **Full R Library Equivalence**: Verified 100% data compatibility with R cancensus
- **Enhanced API Reliability**: Production-grade error handling and retry logic
- **Vector Hierarchy Functions**: Navigate census variable relationships like R
- **Improved Data Quality**: Fixed column naming and data processing issues
- **Comprehensive Testing**: 450+ integration tests covering real-world scenarios
- **National-Level Support**: Added level='C' for Canada-wide baseline comparisons

## Features

### Data Access
* Download Census data and geography in analysis-ready format
* Support for multiple Census years: 2021, 2016, 2011, 2006, 2001, 1996
* All Census geographic levels: PR, CMA, CD, CSD, CT, DA, EA, DB
* Taxfiler data at Census Tract level (2000-2018)

### Variable Discovery
* `list_census_vectors()` - Browse all available variables
* `search_census_vectors()` - Search variables by keyword
* `parent_census_vectors()` - Navigate variable hierarchies upward
* `child_census_vectors()` - Navigate variable hierarchies downward
* `find_census_vectors()` - Enhanced variable search with fuzzy matching

### Geographic Capabilities
* GeoPandas integration for spatial analysis
* Multiple resolution options (simplified/high)
* Seamless geometry + data integration

### Reliability & Performance
* Production-grade error handling with helpful messages
* Automatic retry logic with exponential backoff
* Connection pooling for improved performance
* Rate limiting to respect API constraints
* Comprehensive caching system

## Installation

**Note**: pycancensus is not yet published on PyPI. Install directly from GitHub:

```bash
# Install latest version from GitHub
pip install git+https://github.com/dshkol/pycancensus.git
```

Or for development:

```bash
git clone https://github.com/dshkol/pycancensus.git
cd pycancensus
pip install -e .[dev]
```

**Coming soon**: Publication to PyPI for `pip install pycancensus`

## API Key

**pycancensus** requires a valid CensusMapper API key to use. You can obtain a free API key by [signing up](https://censusmapper.ca/users/sign_up) for a CensusMapper account. 

Set your API key as an environment variable:

```bash
export CANCENSUS_API_KEY="your_api_key_here"
```

Or set it programmatically:

```python
import pycancensus as pc
pc.set_api_key("your_api_key_here")
```

## Quick Start

```python
import pycancensus as pc

# Set your API key
pc.set_api_key("your_api_key_here")

# List available datasets
datasets = pc.list_census_datasets()

# Discover variables with new hierarchy functions
vectors = pc.list_census_vectors("CA21")
income_vars = pc.search_census_vectors("income", "CA21")
related_vars = pc.child_census_vectors("v_CA21_1", dataset="CA21")

# Get census data
data = pc.get_census(
    dataset="CA21",
    regions={"CMA": "35535"},  # Toronto CMA  
    vectors=["v_CA21_1", "v_CA21_2", "v_CA21_3"],  # Population by gender
    level="CSD"
)

# Get census data with geography for mapping
geo_data = pc.get_census(
    dataset="CA21", 
    regions={"PR": "35"},  # Ontario
    vectors=["v_CA21_1"],  # Total population
    level="CSD",
    geo_format="geopandas"  # Returns GeoDataFrame
)

# Advanced: Compare multiple Census years
data_2021 = pc.get_census("CA21", {"CSD": "5915022"}, ["v_CA21_1"], "CSD")
data_2016 = pc.get_census("CA16", {"CSD": "5915022"}, ["v_CA16_401"], "CSD")
```

## Variable Discovery Examples

```python
# Search for housing-related variables
housing = pc.search_census_vectors("dwelling", "CA21")

# Navigate variable hierarchies
population_base = "v_CA21_1"
breakdowns = pc.child_census_vectors(population_base, dataset="CA21")
parent_categories = pc.parent_census_vectors(population_base, dataset="CA21")

# Enhanced search with fuzzy matching
income_vectors = pc.find_census_vectors("CA21", "median household income")
```

## Error Handling & Resilience

pycancensus includes production-grade error handling:

```python
from pycancensus.resilience import CensusAPIError, RateLimitError

try:
    data = pc.get_census("CA21", {"PR": "35"}, ["v_CA21_1"], "PR")
except RateLimitError as e:
    print(f"Rate limited: {e}")
    print(f"Retry after: {e.retry_after} seconds")
except CensusAPIError as e:
    print(f"API error: {e}")
    print(f"Suggestion: {e.suggestion}")
```

## Testing & Verification

pycancensus includes comprehensive testing to ensure reliability and R equivalence:

### Cross-Validation with R cancensus
- **4/4 tests passing** with full data equivalence
- Identical results for vector listing, data retrieval, and multi-region queries  
- Automated testing against R cancensus library

### Integration Testing
- **6 real-world scenarios** covering typical data analysis workflows
- Provincial population analysis, demographic breakdowns, income analysis
- Vector hierarchy navigation, time series comparisons, geographic analysis
- Performance benchmarking with large datasets

### Robustness Testing  
- Error handling with invalid regions/vectors
- Large dataset performance testing
- API resilience and retry logic validation

```bash
# Run the test suite
python -m pytest tests/ -v

# Run cross-validation against R
python tests/cross_validation/test_r_equivalence.py

# Run integration scenarios  
python tests/integration/test_comprehensive_scenarios.py
```

See [`tests/cross_validation/results/`](tests/cross_validation/results/) for detailed test results and validation reports.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Development setup
- Running tests
- Code style (Black, flake8)
- Submitting pull requests
- Reporting issues

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Related Packages

This package is inspired by and based on the R [cancensus](https://github.com/mountainMath/cancensus) package.

## Statistics Canada Attribution

Subject to the Statistics Canada Open Data License Agreement, licensed products using Statistics Canada data should employ the following acknowledgement of source:

**Acknowledgment of Source**

(a) You shall include and maintain the following notice on all licensed rights of the Information:

- Source: Statistics Canada, name of product, reference date. Reproduced and distributed on an "as is" basis with the permission of Statistics Canada.

(b) Where any Information is contained within a Value-added Product, you shall include on such Value-added Product the following notice:

- Adapted from Statistics Canada, name of product, reference date. This does not constitute an endorsement by Statistics Canada of this product.
