# Changelog

All notable changes to pycancensus will be documented in this file.

## [0.2.0] - 2026-06-12

This release synchronizes pycancensus with R cancensus 0.6.1, porting its
bug fixes, performance work, and new features, and fixes several pycancensus
bugs found during the comparison. Items reference the R cancensus equivalent
where one exists.

### Breaking Changes

- `find_census_vectors()` now matches the R signature
  `find_census_vectors(query, dataset, type="all", query_type="exact")`.
  The previous package-level version took `(dataset, query, search_type=...)`.
  The `"regex"` search type is gone (R has no regex mode); `"semantic"` is new.
- `parent_census_vectors()` and `child_census_vectors()` now raise
  `ValueError("Unable to determine dataset")` for vectors spanning multiple
  datasets instead of silently inferring from the first vector (R parity).

### Bug Fixes

- **CRITICAL**: Fixed `list_census_vectors()` 404 error — the CensusMapper
  API serves `/vector_info/<dataset>.csv` (dataset in the path). This also
  broke `search_census_vectors()` and the hierarchy functions.
- **CRITICAL**: `parent_census_vectors()` / `child_census_vectors()`
  returned only direct parents/children; they now traverse the full
  hierarchy via BFS, matching R's results exactly (verified against
  R cancensus 0.6.1 on live data).
- API retry logic now retries all 5xx plus 408/429 responses with
  exponential backoff and honors numeric `Retry-After` headers (capped at
  60s). 429 responses previously raised immediately without retrying.
  [R 0.6.1]
- Exact vector search matches queries containing regex metacharacters
  (e.g. `"income ($)"`) literally instead of erroring; and
  `search_census_vectors()` no longer interprets the query as a regex.
  [R 0.6.1]
- A 200 response carrying an error payload is no longer parsed and cached
  as census data. [parallels R 0.6.1's WDS error-caching fix]
- `use_cache=False` now refreshes the cache after re-downloading instead
  of leaving stale data in place (R semantics).
- `list_census_regions()` returned UID columns (`region`, `CMA_UID`,
  `CD_UID`, `PR_UID`) as floats (`59933.0`); they are now strings,
  matching R.
- Cache-write failures warn via `warnings.warn` instead of printing.
- Added support for national-level census data retrieval (level='C') for
  national baseline comparisons, with validation and tests.

### New Features

- `find_census_vectors()` semantic search: n-gram edit-distance matching
  tolerant of misspellings and phrasing, with per-word best matching and
  length-bound pruning; and keyword search with match-count ranking.
  [R 0.6.0/0.6.1]
- `visualize_vector_hierarchy()`: ASCII tree visualization of vector
  hierarchies with `max_depth` and `show_type`; nodes truncated by
  `max_depth` are marked `...` rather than mislabeled as leaves.
  [R 0.6.0/0.6.1]
- Recalled-data handling: `get_census()` records the server's data version
  with each cache entry and warns when reading recalled data;
  `list_recalled_cached_data()` and `remove_recalled_cached_data()`
  inspect and clean recalled entries. Vector matching is by exact ID.
  [R 0.5.x/0.6.1]
- `child_census_vectors()` gains `leaves_only`, `max_level`, and
  `keep_parent`; both hierarchy functions accept DataFrame input.
- Region-list helpers: `as_census_region_list()` converts a filtered
  `list_census_regions()` result into the `regions` argument for
  `get_census()`; `add_unique_names_to_region_list()` de-duplicates
  region names by municipal status and region ID. [R parity]
- `explore_census_vectors()` / `explore_census_regions()`: open the
  CensusMapper interactive explorer in a browser. [R parity]
- `list_cache()` reports per-entry metadata (dataset, level, vectors,
  data version) for entries written by this version onward.

### Performance

- In-memory session cache for `list_census_vectors()` and
  `list_census_regions()`: repeated calls within a session skip disk
  entirely (~9x faster cache hits locally). [R 0.6.1]
- Hierarchy traversal uses hash-based BFS instead of repeated DataFrame
  filtering. [R 0.6.1]

### Test Infrastructure & Documentation

- Unit suite grew from 28 to 114 tests; new suites for retry behavior,
  hierarchy traversal, search modes, session cache, cache semantics,
  recalls, and region helpers.
- Fixed `list_census_regions()` endpoint (`/data_sets/{dataset}/place_names.csv`)
  and CI failures across Python versions; pinned black below 26 so new
  stable-style releases don't break formatting checks.
- Removed emojis from public-facing documentation and improved clarity.

## [0.1.0] - 2025-06-18

### Major Improvements

#### Full R Library Equivalence
- **BREAKING**: Achieved 100% data compatibility with R cancensus library
- Cross-validation testing shows identical results across all core functions
- Fixed API request formatting to match R package exactly

#### New Vector Hierarchy Functions
- Added `parent_census_vectors()` - Navigate variable hierarchies upward
- Added `child_census_vectors()` - Navigate variable hierarchies downward  
- Added `find_census_vectors()` - Enhanced variable search with fuzzy matching
- Full compatibility with R cancensus hierarchy navigation

#### Production-Grade Reliability
- New `resilience.py` module with enterprise-level error handling
- Custom exception classes with helpful error messages and suggestions
- Automatic retry logic with exponential backoff and jitter
- Connection pooling for improved performance
- Rate limiting to respect API constraints
- Comprehensive timeout handling

### Bug Fixes

#### API Compatibility
- **CRITICAL**: Fixed vector listing endpoint (`/list_vectors` → `/vector_info.csv`)
- **CRITICAL**: Fixed column name issues (trailing spaces in API responses)
- Fixed region parameter formatting to match R package exactly
- Added missing `geo_hierarchy: "true"` parameter

#### Data Quality
- Fixed numeric conversion of census data columns
- Improved handling of census-specific NA values (`x`, `X`, `F`, `...`, `-`)
- Better categorical column detection and conversion
- Enhanced CSV and JSON response processing

### Testing & Validation

#### Comprehensive Test Suite
- Added cross-validation testing against R cancensus library (4/4 tests passing)
- Added integration testing with 6 real-world scenarios
- Added robustness testing for error handling and large datasets
- Added performance benchmarking
- Total: 450+ test cases covering all functionality

#### Test Coverage
- Provincial population analysis
- Toronto demographic breakdown
- Income inequality analysis  
- Vector hierarchy navigation
- Multi-dataset time series comparison
- Geographic data analysis with boundaries

### Documentation

#### Enhanced README
- Added comprehensive feature overview and sections
- Added variable discovery examples showcasing new hierarchy functions
- Added error handling examples with resilience features
- Added testing & verification section with cross-validation results
- Updated quick start examples with latest best practices

#### New Documentation Files
- `IMPLEMENTATION_GUIDE.md` - Detailed technical implementation notes
- `CHANGELOG.md` - This comprehensive changelog
- Test result documentation in `tests/cross_validation/results/`

### Internal Improvements

#### Code Organization
- Moved test files to proper directory structure (`tests/cross_validation/`)
- Created `MANIFEST.in` for proper packaging
- Updated `pyproject.toml` with modern packaging standards
- Updated `setup.py` for test exclusion from builds

#### Performance
- Implemented connection pooling for API requests
- Added intelligent caching system
- Optimized CSV parsing and data processing
- Reduced API calls through better caching strategies

### Migration Guide

#### For Existing Users
Most existing code will continue to work without changes. However, you may notice:

1. **Improved Error Messages**: More helpful error messages with suggestions
2. **Better Performance**: Faster API calls due to connection pooling
3. **Cleaner Data**: Column names are now properly cleaned (no trailing spaces)

#### New Capabilities
```python
# New hierarchy functions (not available in v0.1.x)
parents = pc.parent_census_vectors("v_CA21_1", dataset="CA21")
children = pc.child_census_vectors("v_CA21_1", dataset="CA21")
search_results = pc.find_census_vectors("CA21", "income")

# Enhanced error handling
from pycancensus.resilience import CensusAPIError, RateLimitError
try:
    data = pc.get_census(...)
except RateLimitError as e:
    print(f"Rate limited: retry after {e.retry_after}s")
```

### Compatibility

- **Python**: 3.7+ (unchanged)
- **R cancensus**: Full equivalence verified with v0.5.7
- **API**: CensusMapper API v1
- **Dependencies**: pandas, requests, geopandas (optional)

---

## [0.1.0] - Initial Release

- Basic census data retrieval functionality
- Geographic data support  
- Caching system
- Basic vector and region listing
- GeoPandas integration

---

**Format:** This changelog follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) principles.