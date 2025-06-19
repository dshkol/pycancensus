"""
Functions for working with census datasets.
"""

import requests
import pandas as pd
from typing import Optional

from .settings import get_api_key
from .cache import get_cached_data, cache_data


def list_census_datasets(
    use_cache: bool = True, quiet: bool = False, api_key: Optional[str] = None
) -> pd.DataFrame:
    """
    Query the CensusMapper API for available datasets.

    Parameters
    ----------
    use_cache : bool, default True
        If True, data will be read from local cache if available.
    quiet : bool, default False
        When True, suppress messages and warnings.
    api_key : str, optional
        API key for CensusMapper API. If None, uses environment variable.

    Returns
    -------
    pd.DataFrame
        DataFrame with information about available census datasets including:
        - dataset: Dataset identifier (e.g., 'CA16', 'CA21')
        - description: Human-readable description of the dataset
        - geo_dataset: Geographic dataset identifier
        - attribution: Attribution requirements for the dataset

    Examples
    --------
    >>> import pycancensus as pc
    >>> datasets = pc.list_census_datasets()
    >>> print(datasets)
    """
    if api_key is None:
        api_key = get_api_key()
        if api_key is None:
            raise ValueError(
                "API key required. Set with set_api_key() or CANCENSUS_API_KEY "
                "environment variable."
            )

    # Check cache first
    if use_cache:
        cache_key = "datasets"
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            if not quiet:
                print("Reading datasets from cache...")
            return cached_data

    # Query API
    base_url = "https://censusmapper.ca/api/v1"
    params = {"api_key": api_key, "format": "json"}

    try:
        if not quiet:
            print("Querying CensusMapper API for available datasets...")

        response = requests.get(f"{base_url}/list_datasets", params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # API returns a list directly, not a dict with "datasets" key
        if isinstance(data, list):
            df = pd.DataFrame(data)
        elif isinstance(data, dict) and "datasets" in data:
            # Fallback for alternative API response format
            df = pd.DataFrame(data["datasets"])
        else:
            raise ValueError(
                "Invalid API response: expected list of datasets or dict with 'datasets' field"
            )

        # Cache the result
        if use_cache:
            cache_data(cache_key, df)

        if not quiet:
            print(f"Retrieved {len(df)} datasets")

        return df

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to process API response: {e}")


def get_dataset_attribution(dataset: str) -> str:
    """
    Get the required attribution text for a dataset.

    Parameters
    ----------
    dataset : str
        Dataset identifier (e.g., 'CA16').

    Returns
    -------
    str
        Attribution text that should be included when using the dataset.

    Examples
    --------
    >>> import pycancensus as pc
    >>> attribution = pc.get_dataset_attribution("CA16")
    >>> print(attribution)
    """
    datasets_df = list_census_datasets(quiet=True)

    dataset_row = datasets_df[datasets_df["dataset"] == dataset.upper()]

    if len(dataset_row) == 0:
        raise ValueError(f"Dataset {dataset} not found")

    attribution = dataset_row.iloc[0].get("attribution", "")

    if not attribution:
        # Default attribution text
        attribution = (
            "Source: Statistics Canada, Census Profile. "
            "Reproduced and distributed on an 'as is' basis with the "
            "permission of Statistics Canada."
        )

    return attribution
