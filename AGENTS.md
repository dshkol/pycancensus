# AGENTS.md

Guidance for AI coding agents contributing to pycancensus. (If you are
*using* pycancensus on behalf of a user rather than developing it, read
https://pycancensus.readthedocs.io/en/latest/llm_usage.html instead.)

## What this project is

A production-grade Python port of the R
[cancensus](https://github.com/mountainMath/cancensus) package for the
CensusMapper Canadian Census API. **R compatibility is the north star**:
function names, signatures, and behavior mirror R cancensus, and changes
are cross-validated against it. When implementing or fixing anything,
check the R implementation first (often checked out at `../cancensus`).

## Commands

```bash
pip install -e .[dev]          # development install

pytest                                          # full suite
pytest tests/ --ignore=tests/cross_validation \
  --ignore=tests/integration --ignore=tests/performance   # unit tests only
pytest tests/integration/                       # live API (needs API key)

black pycancensus              # format (pinned <26)
flake8 pycancensus --count --select=E9,F63,F7,F82 --show-source --statistics

cd docs && make html           # docs build (executes tutorials live)
export CANCENSUS_API_KEY="..."  # required for live API calls
```

## Architecture

- `core.py` — `get_census()`: request building, response processing,
  cache read/write with metadata sidecars
- `vectors.py` — vector listing and search (exact/semantic/keyword)
- `hierarchy.py` — BFS traversal of vector parent/child relationships
- `vector_viz.py` — ASCII hierarchy trees
- `regions.py` — region listing/search and region-list helpers
- `recalls.py` — StatCan recalled-data detection against cache metadata
- `resilience.py` — ResilientSession: ALL HTTP goes through this
  (retries 5xx/408/429 with backoff, honors Retry-After, pools
  connections, rate-limits)
- `cache.py` — file cache + in-memory session cache + metadata sidecars
- `settings.py` — API key and cache-path config; API URL constants

## Conventions that matter

- All API calls use `get_session()` from `resilience.py` — never raw
  `requests`.
- `use_cache=False` means "skip reading stale data but still refresh the
  cache afterwards" (R semantics). Never cache unvalidated response
  bodies; the CSV path requires a `GeoUID` column before caching.
- UID/region identifier columns are strings, never numeric.
- Respect `quiet=` in any user-facing print; library-level problems use
  `warnings.warn`, not `print`.
- Unit tests mock at the `get_session` / cache-function boundary; new
  functionality needs unit tests, and behavior ported from R should be
  spot-verified against R (Rscript with `library(cancensus)`) when
  feasible.
- Format with black (pinned `<26`) before committing; CI runs
  `black --check`.
- CI: every PR runs tests on Python 3.8–3.11, a docs build, and a live
  example validator. The validate job and tutorials hit the real API.

## Gotchas

- The CensusMapper API embeds the dataset in vector IDs (`v_CA21_906`)
  and serves vector metadata at `/api/v1/vector_info/<dataset>.csv`
  (path param, not query param).
- `regions` request parameter must JSON-encode every value as an array,
  even single IDs (matches R).
- Docs tutorials are MyST notebooks executed at build time with live API
  calls — broken examples fail the docs build, not just look stale.
- `docs/api/generated/*.rst` autosummary stubs are committed; add stubs
  when adding public functions, and update `docs/api/index.rst` and
  `__init__.py`'s `__all__`.
