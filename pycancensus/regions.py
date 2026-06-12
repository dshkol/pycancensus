"""
Functions for working with census regions.
"""

import io
from typing import Optional

import pandas as pd
import requests

from .settings import get_api_key, CENSUSMAPPER_DATA_URL
from .resilience import get_session
from .utils import validate_dataset
from .cache import get_cached_data, cache_data, session_cache_get, session_cache_set


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

    # Check caches first: in-memory session cache, then file cache
    cache_key = f"regions_{dataset}"
    if use_cache:
        cached_data = session_cache_get(cache_key)
        if cached_data is not None:
            return cached_data
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            if not quiet:
                print("Reading regions from cache...")
            session_cache_set(cache_key, cached_data)
            return cached_data

    # Query API using the correct endpoint (same as R cancensus)
    url = f"{CENSUSMAPPER_DATA_URL}/{dataset}/place_names.csv"

    try:
        if not quiet:
            print(f"Querying CensusMapper API for {dataset} regions...")

        # The endpoint returns gzip-compressed CSV data
        response = get_session().get(url)

        # Parse CSV response. Identifier columns must stay strings to match
        # R cancensus — pandas would otherwise infer them as floats
        # (e.g. CMA_UID 59933.0), silently breaking string comparisons
        df = pd.read_csv(
            io.StringIO(response.text),
            dtype={
                "geo_uid": str,
                "CMA_UID": str,
                "CD_UID": str,
                "PR_UID": str,
            },
        )

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
        session_cache_set(cache_key, df)
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


def as_census_region_list(tbl: pd.DataFrame) -> dict:
    """
    Convert a (suitably filtered) DataFrame from list_census_regions()
    to a regions dict suitable for passing to get_census().

    Parameters
    ----------
    tbl : pd.DataFrame
        A data frame, suitably filtered, as returned by
        list_census_regions().

    Returns
    -------
    dict
        Mapping of aggregation level to list of region identifiers,
        e.g. {"CSD": ["5915022", "3520005"]}.

    Examples
    --------
    >>> import pycancensus as pc
    >>> regions = pc.list_census_regions("CA16")
    >>> csds = regions[regions["level"] == "CSD"].head(20)
    >>> data = pc.get_census("CA16", regions=pc.as_census_region_list(csds),
    ...                      vectors=["v_CA16_408"], level="Regions")
    """
    if not {"level", "region"}.issubset(tbl.columns):
        raise ValueError(
            "as_census_region_list() can only handle data frames "
            "returned by list_census_regions()."
        )
    return {
        level: group["region"].astype(str).tolist()
        for level, group in tbl.groupby("level", sort=False)
    }


def add_unique_names_to_region_list(region_list: pd.DataFrame) -> pd.DataFrame:
    """
    Add a de-duplicated "Name" column to a region list.

    Municipality names are not always unique, especially at the CSD level.
    Duplicated names get the municipal status appended in parentheses; if
    that still does not make them unique, the region identifier is added
    as well.

    Parameters
    ----------
    region_list : pd.DataFrame
        A subset of a region list as returned by list_census_regions().

    Returns
    -------
    pd.DataFrame
        The same regions with an extra column "Name" with de-duplicated
        names.
    """
    required = {"name", "municipal_status", "region"}
    if not required.issubset(region_list.columns):
        raise ValueError(
            "add_unique_names_to_region_list() requires the columns "
            f"{sorted(required)} as returned by list_census_regions()."
        )
    result = region_list.copy()
    counts = result.groupby("name")["name"].transform("size")
    result["Name"] = result["name"].where(
        counts == 1,
        result["name"] + " (" + result["municipal_status"].astype(str) + ")",
    )
    counts = result.groupby("Name")["Name"].transform("size")
    result["Name"] = result["Name"].where(
        counts == 1,
        result["Name"] + " (" + result["region"].astype(str) + ")",
    )
    return result


def explore_census_regions(dataset: str = "CA16") -> None:
    """
    Open the interactive CensusMapper region explorer in a browser.

    Parameters
    ----------
    dataset : str, default "CA16"
        The dataset to explore regions for.
    """
    import webbrowser

    dataset = validate_dataset(dataset)
    print(
        "Opening interactive census region explorer at censusmapper.ca/api "
        "in the browser"
    )
    webbrowser.open(f"https://censusmapper.ca/api/{dataset}#api_region")
