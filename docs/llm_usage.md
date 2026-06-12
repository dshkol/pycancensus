# Usage Guide for LLMs and Agents

This page is written for language models and coding agents using pycancensus
on behalf of a user. It states the current API precisely, including things
that changed in 0.2.0 and may differ from your training data.

```{note}
A machine-readable index of this documentation is available at
[`llms.txt`](../llms.txt), and the full documentation as a single markdown
file at [`llms-full.txt`](../llms-full.txt).
```

## What this package is

pycancensus retrieves Canadian Census data and geographies from the
[CensusMapper API](https://censusmapper.ca/api). It is an explicit Python
port of the R [cancensus](https://github.com/mountainMath/cancensus)
package and mirrors its function names and semantics. Data comes back as
pandas DataFrames; geographies as GeoPandas GeoDataFrames.

## Setup

```python
# pip install pycancensus
import pycancensus as pc
pc.set_api_key("CENSUSMAPPER_API_KEY")   # or env var CANCENSUS_API_KEY
```

Free API keys: https://censusmapper.ca/users/sign_up. Requests are cached
locally, retried on transient failures, and rate-limited automatically —
do not add your own retry loops or sleeps.

## The core workflow

Census analysis with this package is a three-step funnel: discover
variables ("vectors"), select regions, then fetch data.

```python
# 1. Discover vectors. Datasets: CA21, CA16, CA11, CA06, CA01, CA1996.
vectors = pc.search_census_vectors("median income", "CA21", quiet=True)
# or fuzzy/semantic search (tolerates misspellings):
vectors = pc.find_census_vectors("median income", "CA21", query_type="semantic")
# Drill into a variable's full hierarchy:
children = pc.child_census_vectors("v_CA21_906", leaves_only=True)
pc.visualize_vector_hierarchy("v_CA21_906")   # prints an ASCII tree

# 2. Select regions. region IDs are STRINGS (StatCan GeoUIDs).
regions = pc.list_census_regions("CA21", quiet=True)
csds = regions[(regions["level"] == "CSD") & (regions["CMA_UID"] == "59933")]
region_arg = pc.as_census_region_list(csds)   # -> {"CSD": ["5915022", ...]}

# 3. Fetch data.
df = pc.get_census(
    dataset="CA21",
    regions={"CMA": "59933"},          # dict: level -> ID or list of IDs
    vectors=["v_CA21_1", "v_CA21_906"],
    level="CSD",                       # aggregation level of the result
    quiet=True,
)

# With geometries for mapping / spatial analysis:
gdf = pc.get_census(..., geo_format="geopandas")  # GeoDataFrame, EPSG:4326
```

Key facts:

- `regions` is a dict mapping a geographic level to ID(s):
  `{"PR": "59"}`, `{"CMA": "59933"}`, `{"CSD": ["5915022", "5915025"]}`.
- `level` values: `"Regions"` (as queried), `"PR"`, `"CMA"`, `"CD"`,
  `"CSD"`, `"CT"`, `"DA"`, `"EA"` (1996 only), `"DB"` (2001+), `"C"`
  (Canada-wide).
- Vector IDs look like `v_CA21_906` (dataset embedded in the ID).
- Census NA codes (`x`, `F`, `...`, `-`) are converted to NaN automatically.
- Pass `quiet=True` everywhere when running non-interactively.

## API differences from your training data (0.2.0, June 2026)

If you learned pycancensus ≤0.1.0 or infer from R cancensus, note:

- `find_census_vectors(query, dataset, type="all", query_type="exact")` —
  query comes FIRST (R-parity). Older pycancensus had
  `find_census_vectors(dataset, query, search_type=...)`; that no longer
  works. `query_type` is one of `"exact"`, `"semantic"`, `"keyword"`
  (there is no `"regex"`).
- `parent_census_vectors()` / `child_census_vectors()` return the FULL
  ancestry/descendant tree (recursive), not just direct relations.
  `child_census_vectors()` supports `leaves_only=`, `max_level=`,
  `keep_parent=`.
- New in 0.2.0: `visualize_vector_hierarchy()`, `as_census_region_list()`,
  `add_unique_names_to_region_list()`, `explore_census_vectors()`,
  `explore_census_regions()`, `list_recalled_cached_data()`,
  `remove_recalled_cached_data()`.
- `use_cache=False` re-downloads AND refreshes the cache (it is not just
  a bypass).

## Differences from R cancensus

| R | Python |
|---|--------|
| `list(CMA = "59933")` | `{"CMA": "59933"}` |
| `geo_format = "sf"` | `geo_format = "geopandas"` |
| `set_cancensus_api_key()` | `set_api_key()` |
| `list_cancensus_cache()` | `list_cache()` |
| returns tibble / sf | returns DataFrame / GeoDataFrame |

Function names otherwise match R (`get_census`, `list_census_vectors`,
`find_census_vectors`, `parent_census_vectors`, `child_census_vectors`,
`dataset_attribution`, `label_vectors`, ...), with verified-equivalent
results.

## Common pitfalls

- Do not guess vector IDs; they are dataset-specific and non-obvious.
  Always discover them via search or hierarchy traversal first.
- Region IDs and UID columns are strings — `"59933"`, never `59933`.
- Vector columns in results are named `"v_CA21_1: Total ..."` by default;
  pass `labels="short"` for bare vector IDs and use `pc.label_vectors(df)`
  to recover the descriptions.
- Comparing census years means different vector IDs per dataset
  (`v_CA21_1` vs `v_CA16_401` are both population).
- StatCan occasionally recalls data; if a warning about recalled data
  appears, call `pc.remove_recalled_cached_data()` and re-fetch.
