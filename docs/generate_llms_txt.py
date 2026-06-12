"""Generate llms.txt and llms-full.txt during the Sphinx build.

llms.txt is a curated, LLM-friendly index of the documentation
(https://llmstxt.org). llms-full.txt is the consumable version: the
project overview, the LLM usage guide, and the full public API reference
extracted from live docstrings, concatenated into one markdown file an
agent can load whole. Generating from the installed package at build time
keeps both files from going stale.
"""

import inspect
from pathlib import Path

DOCS_DIR = Path(__file__).parent
OUT_DIR = DOCS_DIR / "_llms"

BASE_URL = "https://pycancensus.readthedocs.io/en/latest"

LLMS_TXT = f"""# pycancensus

> Python interface to Canadian Census data and geographies via the
> CensusMapper API. An explicit port of the R cancensus package with
> verified-equivalent results: same function names, pandas/GeoPandas
> output. Free API key required (https://censusmapper.ca/users/sign_up).

Datasets cover the 1996-2021 Canadian censuses (CA1996...CA21). The core
workflow is: discover variables ("vectors") -> select regions -> call
get_census(), which returns an analysis-ready DataFrame (or GeoDataFrame
with geo_format="geopandas").

## Docs

- [Usage guide for LLMs and agents]({BASE_URL}/llm_usage.html): exact
  current signatures, 0.2.0 changes, R differences, pitfalls
- [Getting started]({BASE_URL}/tutorials/getting_started.html): discovery,
  hierarchies, region selection, data retrieval
- [API reference]({BASE_URL}/api/index.html): all public functions
- [R to Python migration]({BASE_URL}/migration.html): for R cancensus users
- [Working with geometry]({BASE_URL}/tutorials/working_with_geometry.html)
- [Caching and recalled data]({BASE_URL}/tutorials/caching_data.html)

## Source

- [GitHub repository](https://github.com/dshkol/pycancensus)
- [Changelog](https://github.com/dshkol/pycancensus/blob/main/CHANGELOG.md)
- [R cancensus (reference implementation)](https://github.com/mountainMath/cancensus)

## Optional

- [Full docs as one markdown file]({BASE_URL}/llms-full.txt)
"""


def _api_reference_markdown() -> str:
    """Render every public function's signature and docstring as markdown."""
    import pycancensus

    lines = ["# API Reference (generated from docstrings)\n"]
    for name in sorted(pycancensus.__all__):
        obj = getattr(pycancensus, name)
        if not callable(obj):
            continue
        try:
            sig = str(inspect.signature(obj))
        except (TypeError, ValueError):
            sig = "(...)"
        doc = inspect.getdoc(obj) or "(no docstring)"
        lines.append(f"## `{name}{sig}`\n\n{doc}\n")
    return "\n".join(lines)


def generate() -> None:
    """Write llms.txt and llms-full.txt into docs/_llms/."""
    OUT_DIR.mkdir(exist_ok=True)

    (OUT_DIR / "llms.txt").write_text(LLMS_TXT)

    readme = (DOCS_DIR.parent / "README.md").read_text()
    usage_guide = (DOCS_DIR / "llm_usage.md").read_text()
    full = "\n\n---\n\n".join(
        [
            LLMS_TXT,
            readme,
            usage_guide,
            _api_reference_markdown(),
        ]
    )
    (OUT_DIR / "llms-full.txt").write_text(full)


if __name__ == "__main__":
    generate()
