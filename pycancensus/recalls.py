"""Detection and removal of locally cached data recalled by Statistics Canada.

Statistics Canada occasionally recalls published census data. CensusMapper
tracks these recalls and exposes them at /api/v1/recall.csv. Cached
get_census() results record the server's data-version header, which is
matched against the recall database to flag stale local data.
"""

import io
import warnings
from typing import Optional

import pandas as pd

from .cache import list_cache, remove_from_cache, session_cache_get, session_cache_set
from .settings import CENSUSMAPPER_API_URL
from .resilience import get_session

_RECALL_CACHE_KEY = "_recall_database"
_warned_this_session = False


def get_recalled_database(refresh: bool = False) -> Optional[pd.DataFrame]:
    """
    Fetch the database of recalled data from CensusMapper.

    Parameters
    ----------
    refresh : bool, default False
        Force a re-download instead of using the session-cached copy.

    Returns
    -------
    pd.DataFrame or None
        Rows describing recalled data with columns api_version, dataset,
        level, vector — or None if the database cannot be downloaded.
    """
    if not refresh:
        cached = session_cache_get(_RECALL_CACHE_KEY)
        if cached is not None:
            return cached

    try:
        response = get_session().get(f"{CENSUSMAPPER_API_URL}/recall.csv")
        data = pd.read_csv(io.StringIO(response.text), dtype=str)
    except Exception:
        warnings.warn("Unable to download recall database at this point.")
        return None

    if "api_version" not in data.columns:
        warnings.warn("Unable to download recall database at this point.")
        return None

    session_cache_set(_RECALL_CACHE_KEY, data)
    return data


def _version_number(version: Optional[str]) -> Optional[int]:
    """Parse the numeric part of a data version like "d.12" or "g.3"."""
    if not isinstance(version, str) or "." not in version:
        return None
    try:
        return int(version.split(".", 1)[1])
    except ValueError:
        return None


def _level_matches(recall_level, entry_level) -> bool:
    """A recall applies to its level, all levels (NaN), or 'Regions' entries."""
    if pd.isna(recall_level) or recall_level == "":
        return True
    return entry_level == recall_level or entry_level == "Regions"


def list_recalled_cached_data(
    cached_data: Optional[pd.DataFrame] = None,
) -> Optional[pd.DataFrame]:
    """
    List locally cached data that has been recalled by Statistics Canada.

    Only cache entries written by pycancensus versions that record request
    metadata (dataset, vectors, data version) can be checked.

    Parameters
    ----------
    cached_data : pd.DataFrame, optional
        Cache listing to check, as returned by list_cache(). Defaults to
        the full local cache.

    Returns
    -------
    pd.DataFrame or None
        Rows of list_cache() describing recalled entries, or None if the
        recall database could not be downloaded.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.list_recalled_cached_data()
    """
    recall_db = get_recalled_database()
    if recall_db is None:
        return None

    if cached_data is None:
        cached_data = list_cache()
    if cached_data.empty or "dataset" not in cached_data.columns:
        return cached_data.iloc[0:0]

    recalled_keys = []
    for _, entry in cached_data.iterrows():
        if pd.isna(entry.get("dataset")):
            continue  # no metadata recorded for this entry
        entry_vectors = set(entry.get("vectors") or [])
        data_version = _version_number(entry.get("version"))
        geo_version = _version_number(entry.get("geo_version"))

        for _, recall in recall_db.iterrows():
            if recall["dataset"] != entry["dataset"]:
                continue
            if not _level_matches(recall.get("level"), entry.get("level")):
                continue
            recall_num = _version_number(recall["api_version"])
            if recall_num is None:
                continue
            if recall["api_version"].startswith("d."):
                # Data recall: exact vector ID match (a recall of v_CA21_1
                # must not flag v_CA21_10) for data at or below the
                # recalled version
                if (
                    data_version is not None
                    and data_version <= recall_num
                    and recall.get("vector") in entry_vectors
                ):
                    recalled_keys.append(entry["cache_key"])
                    break
            elif recall["api_version"].startswith("g."):
                # Geometry recall: applies to any cached geometry at or
                # below the recalled version
                if geo_version is not None and geo_version <= recall_num:
                    recalled_keys.append(entry["cache_key"])
                    break

    return cached_data[cached_data["cache_key"].isin(recalled_keys)]


def remove_recalled_cached_data() -> None:
    """
    Remove locally cached data that has been recalled by Statistics Canada.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.remove_recalled_cached_data()
    """
    recalled = list_recalled_cached_data()
    if recalled is None:
        return
    if recalled.empty:
        print("No recalled data in cached data.")
        return
    size = recalled["size_mb"].sum()
    remove_from_cache(cache_keys=recalled["cache_key"].tolist())
    print(f"Removed {len(recalled)} recalled datasets totalling {size:.2f} MB.")


def check_recalled_data_and_warn(cache_key: str) -> None:
    """Warn (once per session) if a cached entry being read was recalled."""
    global _warned_this_session
    if _warned_this_session:
        return

    cache_listing = list_cache()
    entry = cache_listing[cache_listing["cache_key"] == cache_key]
    if entry.empty:
        return
    recalled = list_recalled_cached_data(entry)
    if recalled is not None and not recalled.empty:
        _warned_this_session = True
        warnings.warn(
            "Currently loaded data has been recalled by Statistics Canada. "
            "Use list_recalled_cached_data() to inspect recalled locally "
            "cached data and remove_recalled_cached_data() to remove it."
        )
