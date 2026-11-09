# Changelog

All notable changes to pycancensus will be documented in this file.

## [0.3.0] - 2026-11-08

This release synchronizes pycancensus with R cancensus 0.6.2: the client now
identifies itself to the CensusMapper API, labels are available in French,
`get_census()` gains R's `labels = "labelled"` mode and named vectors, and all
CensusMapper datasets can be requested. StatCan WDS and original-geography
support is planned for 0.4.0.

### Breaking Changes

- Python 3.8 and 3.9 are no longer supported; pycancensus requires Python
  3.10 or newer. Both versions are end-of-life. CI tests Python 3.10–3.13.
- `list_census_regions()` labels census agglomerations `"CA"` instead of
  `"CMA"`, like R. Code that filters `level == "CMA"` to get both census
  metropolitan areas and census agglomerations should use
  `level.isin(["CMA", "CA"])`. `get_census()` accepts `"CMA"`, `"CA"` and
  `"CMACA"` interchangeably.
- `get_census()` raises `ValueError` for invalid `labels` values; they were
  treated like `"detailed"` before.
- `explore_census_vectors()` defaults to CA21, and both explorer functions
  open https://censusmapper.ca/api, as the per-dataset links no longer
  resolve (R cancensus 0.6.2).

### Improvements

- `get_census()` accepts named vectors as a dict mapping column names to
  vector codes, e.g. `vectors={"pop": "v_CA21_1"}`, the equivalent of R's
  `vectors = c(pop = "v_CA21_1")`. Once any vector is named, the other vector
  columns are named by vector code. With `labels="labelled"` a named column
  keeps its variable's label, and a standard column with the same name gets a
  trailing underscore (e.g. `Population_`); other label modes raise an error
  for such clashes. Naming is applied after the cache read, so it doesn't
  download again.
- All CensusMapper datasets can be requested: the 1996 census (`CA1996`),
  the cross-tabulations (`CA01xSD` to `CA16xSD`) and the taxfiler datasets
  (`TX2000` to `TX2018`). Dataset IDs match case-insensitively, and census
  years translate like R (`2021` -> `CA21`). Before, only four-character
  `CA..` IDs were accepted.

- French labels (port of R cancensus 0.6.2, #229): `get_census()`,
  `list_census_vectors()`, `parent_census_vectors()`, `child_census_vectors()`,
  `find_census_vectors()`, `visualize_vector_hierarchy()` and
  `dataset_attribution()` gain a `language` parameter, `"en"` or `"fr"`. It
  defaults to the new `set_language()` session setting, the analog of R's
  `cancensus.language` option, then to the `PYCANCENSUS_LANGUAGE` environment
  variable, then to `"en"`. Columns are the same in both languages, and in
  `get_census()` changing the language does not download the data again.
  Vectors without French labels, currently the tax and cross-tabulation
  datasets, fall back to English with a warning once per session and dataset.
  Region names and the `type`, `units` and `aggregation` columns of
  `list_census_vectors()` stay as they are. `list_census_vectors()` no longer
  returns the raw `label_fr` and `details_fr` columns, their content is now in
  `label` and `details` with `language="fr"`.
- `get_census()` gains `labels="labelled"` (port of R cancensus 0.6.2, #230),
  which names vector columns by vector like `labels="short"` and stores the
  label of each column in `result.attrs["column_labels"]`, a dict keyed by
  column name (pandas has no per-column label attribute like R). The other
  columns get short names, types and an order that are the same across
  datasets and with or without `geo_format`, following R: `GeoUID`, `Type`,
  `Name`, `Area`, `Population`, `Dwellings`, `Households`,
  `Population_Previous`, `Quality`, the `*_UID` columns and so on. These also
  get labels in the requested language, with the census year where it
  applies, e.g. `Population 2021`. `labels="detailed"` and `labels="short"`
  do not change.
- The default of `labels` in `get_census()` is planned to change to
  `"labelled"` in a future version. It now defaults to the new `set_labels()`
  session setting (the analog of R's `cancensus.labels` option) or the
  `PYCANCENSUS_LABELS` environment variable, and otherwise still to
  `"detailed"`. `get_census()` prints a notice once per session if neither
  `labels` nor a default is set; `quiet=True` suppresses it.
- `get_census()` caches downloads independently of `labels` and `language`,
  which get applied after reading the cache, so switching either reuses the
  cached data. Data cached by earlier versions is downloaded again once.
- All requests to the CensusMapper API now identify the client through the
  user agent, in the form `pycancensus/<version> requests/<version>
  Python/<version>` (port of R cancensus 0.6.2). This lets the API tell
  pycancensus traffic apart from the R package and other clients.
- New `set_user_agent_prefix()` lets packages and tools built on pycancensus
  identify themselves, e.g. `pc.set_user_agent_prefix("mypackage/1.2.3")`;
  the `PYCANCENSUS_USER_AGENT_PREFIX` environment variable does the same
  without code changes. `get_user_agent()` returns the full string. Equivalent
  to R's `options(cancensus.user_agent_prefix = ...)`.

### Bug Fixes

- Sphinx-Gallery thumbnails now resolve to their example pages, generated
  notebooks no longer shadow the canonical gallery documents, and the
  geographic plotting example imports NumPy before fitting its trend line.
- `get_census()` cache keys now include geometry resolution,
  use canonical request serialization, and carry a schema version so
  incompatible legacy entries are not reused.
- Public API functions preserve `CensusAPIError` subclasses such as
  `RateLimitError`; exhausted network failures now raise `NetworkError`, which
  remains catchable through the documented base exception.
- Geography and vector responses must merge through complete, unique geographic
  identifiers. Missing, duplicate, or unmatched identifiers now raise an error
  instead of falling back to row-order alignment.
- `get_census()` accepts `"CA"` and `"CMACA"` in addition to `"CMA"`, both for
  `level` and as `regions` keys (R cancensus 0.6.2, #208), so census
  agglomerations from `list_census_regions()` pass through
  `as_census_region_list()` to `get_census()`.
- `list_census_regions()` and `list_census_vectors()` with `use_cache=False`
  now replace the cached copy, matching `get_census()`; before, a refresh
  never updated the cache. Lists cached by earlier versions are downloaded
  again once, which also clears stale copies with garbled names or numeric
  region IDs.
- Region names, vector details, data and the recall database are decoded as
  UTF-8 regardless of the response's charset header, like R; names such as
  "Montréal" could come out as "MontrÃ©al".
- `label_vectors()` works on GeoDataFrame results of `get_census()` with
  vectors; merging geometry and data dropped the vector metadata (R cancensus
  0.6.2).
- `find_census_vectors()` keyword and semantic search no longer drop accented
  letters such as "é" from the query (R cancensus 0.6.2).
- `find_census_vectors(query_type="keyword", interactive=True)` no longer
  fails with `EOFError` outside a terminal; it returns the top matches and
  reports how many less precise matches were left out (R cancensus 0.6.2).
- `get_census(quiet=True)` no longer prints the "Downloading ..." progress
  line for larger requests.

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
