# pycancensus

[![PyPI](https://img.shields.io/pypi/v/pycancensus.svg)](https://pypi.org/project/pycancensus/)
[![DOI](https://zenodo.org/badge/998148421.svg)](https://doi.org/10.5281/zenodo.20670029)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/dshkol/pycancensus/actions/workflows/ci.yml/badge.svg)](https://github.com/dshkol/pycancensus/actions/workflows/ci.yml)
[![Documentation Status](https://readthedocs.org/projects/pycancensus/badge/?version=latest)](https://pycancensus.readthedocs.io/en/latest/?badge=latest)

Access, retrieve, and work with Canadian Census data and geography.

**pycancensus** is a Python package that provides integrated, convenient, and uniform access to Canadian Census data and geography retrieved using the CensusMapper API. This package produces analysis-ready tidy DataFrames and spatial data in multiple formats, with full equivalence to the R cancensus library.

## What's New in 0.2.0

Synchronized with R cancensus 0.6.1 — see [CHANGELOG.md](CHANGELOG.md) for details:

- **Full hierarchy traversal**: `parent/child_census_vectors()` return complete
  ancestor/descendant trees, verified identical to R
- **Semantic variable search**: typo-tolerant `find_census_vectors(query_type="semantic")`,
  now with the R-parity signature `(query, dataset, ...)` (breaking change)
- **StatCan recall detection**: cached data is checked against published data recalls
- **New helpers**: `visualize_vector_hierarchy()`, `as_census_region_list()`,
  `add_unique_names_to_region_list()`, `explore_census_vectors()/regions()`
- **Reliability**: retries honor Retry-After; error payloads can no longer poison
  the cache; in-memory session cache for metadata

## Features

### Data Access
* Download Census data and geography in analysis-ready format
* Support for multiple Census years: 2021, 2016, 2011, 2006, 2001, 1996
* All Census geographic levels: PR, CMA, CD, CSD, CT, DA, EA, DB
* Taxfiler data at Census Tract level (2000-2018)

### Variable Discovery
* `list_census_vectors()` - Browse all available variables
* `search_census_vectors()` - Search variables by keyword
* `find_census_vectors()` - Exact, semantic (fuzzy), and keyword search
* `parent_census_vectors()` - Full ancestry of a variable, like R cancensus
* `child_census_vectors()` - Full descendant tree, with `leaves_only` and `max_level`
* `visualize_vector_hierarchy()` - ASCII tree view of variable hierarchies
* `explore_census_vectors()` - Open the interactive CensusMapper explorer

### Region Discovery
* `list_census_regions()` / `search_census_regions()` - Browse and search regions
* `as_census_region_list()` - Convert filtered region lists into `get_census()` input
* `add_unique_names_to_region_list()` - De-duplicate ambiguous municipality names
* `explore_census_regions()` - Open the interactive CensusMapper explorer

### Geographic Capabilities
* GeoPandas integration for spatial analysis
* Multiple resolution options (simplified/high)
* Seamless geometry + data integration

### Reliability & Performance
* Production-grade error handling with helpful messages
* Automatic retry with exponential backoff, honoring server Retry-After headers
* Connection pooling and in-memory session caching for metadata
* Rate limiting to respect API constraints
* Comprehensive file caching with StatCan data-recall detection
  (`list_recalled_cached_data()` / `remove_recalled_cached_data()`)

## Installation

Install from PyPI:

```bash
pip install pycancensus
```

Or install the latest development version from GitHub:

```bash
pip install git+https://github.com/dshkol/pycancensus.git
```

For development:

```bash
git clone https://github.com/dshkol/pycancensus.git
cd pycancensus
pip install -e .[dev]
```

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

## Documentation

**Full documentation is available at [pycancensus.readthedocs.io](https://pycancensus.readthedocs.io/)**

The documentation includes:
- **[Getting Started Tutorial](https://pycancensus.readthedocs.io/en/latest/tutorials/getting_started.html)** - Learn the basics
- **[Working with Geographic Data](https://pycancensus.readthedocs.io/en/latest/tutorials/working_with_geometry.html)** - Maps and spatial analysis
- **[Example Gallery](https://pycancensus.readthedocs.io/en/latest/auto_examples/index.html)** - Real-world usage examples
- **[API Reference](https://pycancensus.readthedocs.io/en/latest/api/index.html)** - Complete function documentation
- **[R to Python Migration Guide](https://pycancensus.readthedocs.io/en/latest/migration.html)** - For R cancensus users
- **[LLM Usage Guide](https://pycancensus.readthedocs.io/en/latest/llm_usage.html)** - For AI agents using the library ([llms.txt](https://pycancensus.readthedocs.io/en/latest/llms.txt))

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

# Enhanced search: exact, semantic (typo-tolerant), or keyword
income_vectors = pc.find_census_vectors("median household income", "CA21",
                                        query_type="semantic")
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

### Unit Testing
- **114 unit tests** covering retry behavior, hierarchy traversal, search modes,
  caching semantics, recall detection, and region helpers
- CI runs on Python 3.8-3.11 with formatting and lint checks

### Cross-Validation with R cancensus
- Hierarchy traversal, search modes, and name de-duplication verified
  **byte-identical** to R cancensus 0.6.1 on live data
- Automated example validator runs the R documentation examples against
  the Python implementation on every PR

### Integration & Robustness Testing
- Real-world scenarios: demographic breakdowns, time series comparisons,
  geographic analysis with live API calls
- Error handling with invalid regions/vectors, large-dataset performance,
  retry logic validation

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

## Citing pycancensus

If you use pycancensus in your research, please cite it (see
[CITATION.cff](CITATION.cff), or use GitHub's "Cite this repository" button):

> Shkolnik, D. and J. von Bergmann (2026). pycancensus: access, retrieve,
> and work with Canadian Census data and geography in Python. v0.2.0.
> https://github.com/dshkol/pycancensus

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
The license covers the pycancensus code; census **data** retrieved with it
is subject to the Statistics Canada Open Licence — see the attribution
requirements below.

## Related Packages

This package is explicitly a python port of the R [cancensus](https://github.com/mountainMath/cancensus) package.

## Statistics Canada Attribution

Subject to the Statistics Canada Open Data License Agreement, licensed products using Statistics Canada data should employ the following acknowledgement of source.
pycancensus can generate the correct attribution text for the datasets you
used: `pc.dataset_attribution(["CA16", "CA21"])`.

**Acknowledgment of Source**

(a) You shall include and maintain the following notice on all licensed rights of the Information:

- Source: Statistics Canada, name of product, reference date. Reproduced and distributed on an "as is" basis with the permission of Statistics Canada.

(b) Where any Information is contained within a Value-added Product, you shall include on such Value-added Product the following notice:

- Adapted from Statistics Canada, name of product, reference date. This does not constitute an endorsement by Statistics Canada of this product.
