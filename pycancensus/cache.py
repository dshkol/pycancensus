"""
Caching functionality for pycancensus.
"""

import os
import pickle
import hashlib
from pathlib import Path
from typing import Any, Optional, List
import pandas as pd
import geopandas as gpd

from .settings import get_cache_path


def get_cached_data(cache_key: str) -> Optional[Any]:
    """
    Retrieve data from cache if it exists.

    Parameters
    ----------
    cache_key : str
        Unique identifier for the cached data.

    Returns
    -------
    Any or None
        Cached data if found, None otherwise.
    """
    cache_path = Path(get_cache_path())
    cache_file = cache_path / f"{cache_key}.pkl"

    if cache_file.exists():
        try:
            with open(cache_file, "rb") as f:
                return pickle.load(f)
        except Exception:
            # If cache file is corrupted, remove it
            cache_file.unlink(missing_ok=True)

    return None


def cache_data(cache_key: str, data: Any) -> None:
    """
    Cache data to disk.

    Parameters
    ----------
    cache_key : str
        Unique identifier for the data.
    data : Any
        Data to cache.
    """
    cache_path = Path(get_cache_path())
    cache_path.mkdir(parents=True, exist_ok=True)

    cache_file = cache_path / f"{cache_key}.pkl"

    try:
        with open(cache_file, "wb") as f:
            pickle.dump(data, f)
    except Exception as e:
        print(f"Warning: Failed to cache data: {e}")


def list_cache() -> pd.DataFrame:
    """
    List all cached data files.

    Returns
    -------
    pd.DataFrame
        DataFrame with information about cached files including:
        - cache_key: The cache key
        - file_path: Full path to cached file
        - size_mb: File size in MB
        - created: Creation timestamp
        - modified: Last modification timestamp

    Examples
    --------
    >>> import pycancensus as pc
    >>> cache_list = pc.list_cache()
    >>> print(cache_list)
    """
    cache_path = Path(get_cache_path())

    if not cache_path.exists():
        return pd.DataFrame(
            columns=["cache_key", "file_path", "size_mb", "created", "modified"]
        )

    cache_files = []

    for cache_file in cache_path.glob("*.pkl"):
        try:
            stat = cache_file.stat()
            cache_files.append(
                {
                    "cache_key": cache_file.stem,
                    "file_path": str(cache_file),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": pd.Timestamp.fromtimestamp(stat.st_ctime),
                    "modified": pd.Timestamp.fromtimestamp(stat.st_mtime),
                }
            )
        except Exception:
            continue

    return pd.DataFrame(cache_files)


def remove_from_cache(
    cache_keys: Optional[List[str]] = None, all_cache: bool = False
) -> None:
    """
    Remove items from cache.

    Parameters
    ----------
    cache_keys : list of str, optional
        Specific cache keys to remove. If None and all_cache=False,
        does nothing.
    all_cache : bool, default False
        If True, removes all cached data.

    Examples
    --------
    >>> import pycancensus as pc
    >>> # Remove specific cache entries
    >>> pc.remove_from_cache(["regions_CA16", "vectors_CA16"])
    >>>
    >>> # Remove all cache (use with caution!)
    >>> pc.remove_from_cache(all_cache=True)
    """
    cache_path = Path(get_cache_path())

    if not cache_path.exists():
        print("No cache directory found.")
        return

    removed_count = 0

    if all_cache:
        # Remove all .pkl files
        for cache_file in cache_path.glob("*.pkl"):
            try:
                cache_file.unlink()
                removed_count += 1
            except Exception as e:
                print(f"Warning: Failed to remove {cache_file}: {e}")

        print(f"Removed {removed_count} cached files.")

    elif cache_keys:
        # Remove specific cache keys
        for cache_key in cache_keys:
            cache_file = cache_path / f"{cache_key}.pkl"
            if cache_file.exists():
                try:
                    cache_file.unlink()
                    removed_count += 1
                    print(f"Removed cache: {cache_key}")
                except Exception as e:
                    print(f"Warning: Failed to remove {cache_key}: {e}")
            else:
                print(f"Cache key not found: {cache_key}")

        if removed_count > 0:
            print(f"Removed {removed_count} cached files.")
    else:
        print("No cache keys specified and all_cache=False. Nothing to remove.")


def clear_cache() -> None:
    """
    Clear all cached data.

    This is an alias for remove_from_cache(all_cache=True).

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.clear_cache()
    """
    remove_from_cache(all_cache=True)
