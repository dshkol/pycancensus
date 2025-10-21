"""
Functions for working with census regions.
"""

import requests
import pandas as pd
from typing import Optional

from .settings import get_api_key
from .utils import validate_dataset
from .cache import get_cached_data, cache_data


def list_census_regions(
    dataset: str,
    use_cache: bool = True,
    quiet: bool = False,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Query the CensusMapper API for available regions in a given dataset.

    Parameters
    ----------
    dataset : str
        The dataset to query for available regions (e.g., 'CA16').
    use_cache : bool, default True
        If True, data will be read from local cache if available.
    quiet : bool, default False
        When True, suppress messages and warnings.
    api_key : str, optional
        API key for CensusMapper API. If None, uses environment variable.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - region: The region identifier
        - name: The name of that region
        - level: The census aggregation level of that region
        - pop: The population of that region
        - municipal_status: Additional identifiers for municipal status
        - CMA_UID: The identifier for the Census Metropolitan Area (if any)
        - CD_UID: The identifier for the Census District (if any)

    Examples
    --------
    >>> import pycancensus as pc
    >>> regions = pc.list_census_regions("CA16")
    >>> print(regions.head())
    """
    dataset = validate_dataset(dataset)

    if api_key is None:
        api_key = get_api_key()
        if api_key is None:
            raise ValueError(
                "API key required. Set with set_api_key() or CANCENSUS_API_KEY "
                "environment variable."
            )

    # Check cache first
    if use_cache:
        cache_key = f"regions_{dataset}"
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            if not quiet:
                print("Reading regions from cache...")
            return cached_data

    # Query API using the correct endpoint (same as R cancensus)
    # R cancensus uses: https://censusmapper.ca/data_sets/{dataset}/place_names.csv
    url = f"https://censusmapper.ca/data_sets/{dataset}/place_names.csv"

    try:
        if not quiet:
            print(f"Querying CensusMapper API for {dataset} regions...")

        # The endpoint returns gzip-compressed CSV data
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse CSV response
        import io

        df = pd.read_csv(io.StringIO(response.text))

        # Map column names to match expected output format
        # CSV columns: name, geo_uid, type, population, flag, CMA_UID, CD_UID, PR_UID
        # Expected: region, name, level, pop, municipal_status, CMA_UID, CD_UID, PR_UID
        column_mapping = {
            "geo_uid": "region",
            "type": "level",
            "population": "pop",
            "flag": "municipal_status",
        }

        df = df.rename(columns=column_mapping)

        # Cache the result
        if use_cache:
            cache_data(cache_key, df)

        if not quiet:
            print(f"Retrieved {len(df)} regions")

        return df

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to process API response: {e}")


def search_census_regions(
    search_term: str,
    dataset: str,
    level: Optional[str] = None,
    use_cache: bool = True,
    quiet: bool = False,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Search for census regions by name.

    Parameters
    ----------
    search_term : str
        Term to search for in region names.
    dataset : str
        The dataset to search in (e.g., 'CA16').
    level : str, optional
        Filter by census aggregation level.
    use_cache : bool, default True
        If True, uses cached region list if available.
    quiet : bool, default False
        When True, suppress messages and warnings.
    api_key : str, optional
        API key for CensusMapper API.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame of regions matching the search term.

    Examples
    --------
    >>> import pycancensus as pc
    >>> vancouver_regions = pc.search_census_regions("Vancouver", "CA16")
    >>> toronto_cmas = pc.search_census_regions("Toronto", "CA16", level="CMA")
    """
    # Get all regions first
    regions_df = list_census_regions(
        dataset=dataset, use_cache=use_cache, quiet=quiet, api_key=api_key
    )

    # Filter by search term (case-insensitive)
    mask = regions_df["name"].str.contains(search_term, case=False, na=False)
    filtered_df = regions_df[mask].copy()

    # Filter by level if specified
    if level is not None:
        level_mask = filtered_df["level"] == level
        filtered_df = filtered_df[level_mask].copy()

    if not quiet and len(filtered_df) > 0:
        print(f"Found {len(filtered_df)} regions matching '{search_term}'")
    elif not quiet:
        print(f"No regions found matching '{search_term}'")

    return filtered_df
