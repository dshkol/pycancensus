"""
Core functionality for accessing Canadian Census data through the CensusMapper API.
"""

import os
import requests
import pandas as pd
import geopandas as gpd
from typing import Dict, List, Optional, Union
import warnings

from .settings import get_api_key, get_cache_path
from .cache import get_cached_data, cache_data
from .utils import validate_dataset, validate_level, process_regions
from .progress import show_request_preview, create_progress_for_request


def get_census(
    dataset: str,
    regions: Dict[str, Union[str, List[str]]],
    vectors: Optional[List[str]] = None,
    level: str = "Regions",
    geo_format: Optional[str] = None,
    resolution: str = "simplified",
    labels: str = "detailed",
    use_cache: bool = True,
    quiet: bool = False,
    api_key: Optional[str] = None,
) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Access Canadian census data through the CensusMapper API.

    This function allows convenient access to Canadian census data and boundary
    files through the CensusMapper API. An API key is required to retrieve data.

    Parameters
    ----------
    dataset : str
        A CensusMapper dataset identifier (e.g., 'CA16', 'CA21').
    regions : dict
        A dictionary of census regions to retrieve. Keys must be valid census
        aggregation levels.
    vectors : list of str, optional
        CensusMapper variable names of the census variables to download.
        If None, only geographic data will be downloaded.
    level : str, default 'Regions'
        The census aggregation level to retrieve. One of 'Regions', 'PR',
        'CMA', 'CD', 'CSD', 'CT', 'DA', 'EA' (for 1996), or 'DB' (for 2001-2021).
    geo_format : str, optional
        Format for geographic information. Set to 'geopandas' to return a
        GeoDataFrame with geometry. If None, returns DataFrame without geometry.
    resolution : str, default 'simplified'
        Resolution of geographic data. Either 'simplified' or 'high'.
    labels : str, default 'detailed'
        Variable label format. Either 'detailed' or 'short'.
    use_cache : bool, default True
        Whether to use cached data if available.
    quiet : bool, default False
        Whether to suppress messages and warnings.
    api_key : str, optional
        API key for CensusMapper API. If None, uses environment variable
        or previously set key.

    Returns
    -------
    pd.DataFrame or gpd.GeoDataFrame
        Census data in tidy format. Returns GeoDataFrame if geo_format='geopandas'.

    Examples
    --------
    >>> import pycancensus as pc
    >>> # Get data for Vancouver CMA
    >>> data = pc.get_census(
    ...     dataset='CA16',
    ...     regions={'CMA': '59933'},
    ...     vectors=['v_CA16_408', 'v_CA16_409'],
    ...     level='CSD'
    ... )

    >>> # Get data with geography
    >>> geo_data = pc.get_census(
    ...     dataset='CA16',
    ...     regions={'CMA': '59933'},
    ...     vectors=['v_CA16_408', 'v_CA16_409'],
    ...     level='CSD',
    ...     geo_format='geopandas'
    ... )
    """

    # Validate inputs
    dataset = validate_dataset(dataset)
    level = validate_level(level)

    if api_key is None:
        api_key = get_api_key()
        if api_key is None:
            raise ValueError(
                "API key required. Set with set_api_key() or CANCENSUS_API_KEY "
                "environment variable. Get a free key at https://censusmapper.ca/users/sign_up"
            )

    # Process regions
    processed_regions = process_regions(regions)

    # Show request preview for large downloads
    if not quiet:
        show_request_preview(
            processed_regions, vectors, level, dataset, geo_format, quiet=False
        )

    # Check cache first
    if use_cache:
        cache_key = _generate_cache_key(
            dataset, processed_regions, vectors, level, geo_format
        )
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            if not quiet:
                print(f"Reading data from cache...")
            return cached_data

    # Build API request exactly like the R package
    base_url = "https://censusmapper.ca/api/v1/"

    # Format parameters exactly like the R package
    import json

    # Convert regions to JSON format exactly like R package: jsonlite::toJSON(lapply(regions, as.character))
    # R package ALWAYS puts region values in arrays - this was the key missing piece!
    regions_for_json = {}
    for region_level, region_ids in processed_regions.items():
        if isinstance(region_ids, list):
            regions_for_json[region_level] = [str(rid) for rid in region_ids]
        else:
            # KEY FIX: R package always makes this an array, even for single values
            regions_for_json[region_level] = [str(region_ids)]

    request_data = {
        "dataset": dataset,
        "level": level,
        "api_key": api_key,
        "regions": json.dumps(regions_for_json),
        "geo_hierarchy": "true",  # KEY FIX: Missing parameter from R package
    }

    # Add vectors if specified (JSON-encoded like R package)
    if vectors:
        request_data["vectors"] = json.dumps(vectors)

    # Create progress indicator for large requests
    progress = create_progress_for_request(
        processed_regions, vectors or [], level, geo_format
    )

    try:
        if not quiet and not progress:
            print(
                f"🔄 Querying CensusMapper API for {len(processed_regions)} region(s)..."
            )
            if vectors:
                print(f"📊 Retrieving {len(vectors)} variable(s) at {level} level...")

        if progress:
            progress.start()

        # Handle geo_format='geopandas' with vectors using hybrid approach
        if geo_format == "geopandas" and vectors:
            # The geo.geojson endpoint doesn't properly return vector data
            # So we need to fetch geometry and data separately, then merge

            # 1. Fetch geometry data
            geo_request_data = request_data.copy()
            if "vectors" in geo_request_data:
                del geo_request_data["vectors"]  # Remove vectors for geo request
            if resolution == "high":
                geo_request_data["resolution"] = "high"

            geo_multipart_data = {}
            for key, value in geo_request_data.items():
                geo_multipart_data[key] = (None, value)

            geo_response = requests.post(
                f"{base_url}geo.geojson", files=geo_multipart_data, timeout=30
            )
            geo_response.raise_for_status()
            geo_data = geo_response.json()
            geo_result = _process_geojson_response(geo_data, None, labels)  # No vectors

            # 2. Fetch vector data using CSV endpoint
            csv_multipart_data = {}
            for key, value in request_data.items():
                csv_multipart_data[key] = (None, value)

            csv_response = requests.post(
                f"{base_url}data.csv", files=csv_multipart_data, timeout=30
            )
            csv_response.raise_for_status()
            csv_result = _process_csv_response(csv_response.text, vectors, labels)

            # 3. Merge the results
            # Use a common identifier to merge - typically 'GeoUID' from CSV and 'id' from GeoJSON
            merge_key_csv = None
            merge_key_geo = None

            # Find the appropriate merge keys
            for potential_key in ["GeoUID", "id", "rgid"]:
                if potential_key in csv_result.columns:
                    merge_key_csv = potential_key
                    break

            for potential_key in ["id", "rgid", "GeoUID"]:
                if potential_key in geo_result.columns:
                    merge_key_geo = potential_key
                    break

            if merge_key_csv and merge_key_geo:
                # Merge on the identifier
                # Keep all columns from geo_result, add vector columns from csv_result
                vector_columns = [
                    col for col in csv_result.columns if col.startswith("v_")
                ]
                merge_columns = [merge_key_csv] + vector_columns

                result = geo_result.merge(
                    csv_result[merge_columns],
                    left_on=merge_key_geo,
                    right_on=merge_key_csv,
                    how="left",
                )

                # Drop the duplicate merge key if it was added
                if merge_key_csv != merge_key_geo and merge_key_csv in result.columns:
                    result = result.drop(columns=[merge_key_csv])

            else:
                # Fallback: assume same order and merge by index
                vector_columns = [
                    col for col in csv_result.columns if col.startswith("v_")
                ]
                for col in vector_columns:
                    if len(csv_result) == len(geo_result):
                        geo_result[col] = csv_result[col].values
                result = geo_result

        else:
            # Standard single-endpoint approach
            if geo_format == "geopandas":
                endpoint = "geo.geojson"
                if resolution == "high":
                    request_data["resolution"] = "high"
            else:
                endpoint = "data.csv"

            # Use multipart/form-data like the R package
            # Convert all values to tuple format for multipart encoding
            multipart_data = {}
            for key, value in request_data.items():
                multipart_data[key] = (None, value)

            response = requests.post(
                f"{base_url}{endpoint}", files=multipart_data, timeout=30
            )
            response.raise_for_status()

            # Process the response data based on endpoint
            if geo_format == "geopandas":
                # geo.geojson returns JSON
                data = response.json()
                result = _process_geojson_response(data, vectors, labels)
            else:
                # data.csv returns CSV
                result = _process_csv_response(response.text, vectors, labels)

        # Cache the result
        if use_cache:
            cache_data(cache_key, result)

        # Finish progress indicator
        if progress:
            vector_count = len([col for col in result.columns if col.startswith("v_")])
            if vectors and vector_count > 0:
                progress.finish(
                    f"Retrieved {len(result)} regions with {vector_count} variables"
                )
            else:
                progress.finish(f"Retrieved {len(result)} regions")
        elif not quiet:
            print(f"✅ Successfully retrieved data for {len(result)} regions")
            if vectors:
                print(
                    f"📈 Data includes {len([col for col in result.columns if col.startswith('v_')])} vector columns"
                )

        return result

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to process API response: {e}")


def _generate_cache_key(dataset, regions, vectors, level, geo_format):
    """Generate a cache key for the given parameters."""
    import hashlib

    # Create a string representation of the parameters
    params_str = f"{dataset}_{regions}_{vectors}_{level}_{geo_format}"

    # Create a hash of the parameters
    return hashlib.md5(params_str.encode()).hexdigest()


def _extract_vector_metadata(df, vectors, labels):
    """Extract vector metadata from column names and store as attribute."""
    if not vectors:
        return df

    # Find vector columns - they have format "v_DATASET_NUM: Description"
    vector_cols = [col for col in df.columns if col.startswith("v_")]

    if not vector_cols:
        return df

    # Build metadata DataFrame
    metadata_rows = []
    rename_dict = {}

    for col in vector_cols:
        if ": " in col:
            # Column has format "v_CA21_1: Total - Population"
            parts = col.split(": ", 1)
            vector_code = parts[0]
            detail = parts[1] if len(parts) > 1 else ""

            metadata_rows.append({"Vector": vector_code, "Detail": detail})

            # For short labels, rename column to just the vector code
            if labels == "short":
                rename_dict[col] = vector_code
        else:
            # Column is already just the vector code
            vector_code = col
            # Try to get detail from vector list if available
            metadata_rows.append({"Vector": vector_code, "Detail": ""})

    # Create metadata DataFrame
    if metadata_rows:
        metadata_df = pd.DataFrame(metadata_rows)

        # Rename columns if using short labels
        if rename_dict:
            df = df.rename(columns=rename_dict)

        # Store metadata as attribute (always store, but mainly useful with short labels)
        df.attrs["census_vectors"] = metadata_df

    return df


def _process_csv_response(csv_text, vectors, labels):
    """Process CSV API response into a pandas DataFrame."""
    import io

    # Read all columns as strings initially (like R package)
    df = pd.read_csv(io.StringIO(csv_text), dtype=str, encoding="utf-8")

    # Fix column names by removing trailing/leading spaces (critical fix for API compatibility)
    df.columns = df.columns.str.strip()

    # Define census-specific NA values (matching R package)
    census_na_values = ["x", "X", "F", "...", "-", ""]

    # Convert specific columns to numeric (matching R package exactly)
    numeric_columns = []

    # Standard census columns that should be numeric
    # Note: API may return column names with trailing spaces, so we need flexible matching
    standard_numeric = ["Population", "Households", "Dwellings", "Area (sq km)"]

    # Create a mapping of actual column names to expected names for flexible matching
    column_mapping = {}
    for expected_col in standard_numeric:
        # Check for exact match first
        if expected_col in df.columns:
            numeric_columns.append(expected_col)
            continue

        # Check for variations with trailing/leading spaces
        for actual_col in df.columns:
            if actual_col.strip() == expected_col:
                numeric_columns.append(actual_col)
                column_mapping[actual_col] = expected_col
                break

    # Vector columns (v_* pattern) - handle both short and descriptive names
    for col in df.columns:
        if col.startswith("v_CA") or col.startswith("v_"):
            numeric_columns.append(col)

    # Convert to numeric with census NA handling
    for col in numeric_columns:
        # Replace census NA values with NaN, then convert to numeric
        df[col] = df[col].replace(census_na_values, pd.NA)
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Convert categorical columns to pandas categorical (matching R factors)
    categorical_columns = ["Type", "Region Name"]
    for expected_col in categorical_columns:
        # Check for exact match first
        if expected_col in df.columns:
            df[expected_col] = df[expected_col].astype("category")
            continue

        # Check for variations with trailing/leading spaces
        for actual_col in df.columns:
            if actual_col.strip() == expected_col:
                df[actual_col] = df[actual_col].astype("category")
                break

    # Extract vector metadata and handle labels
    df = _extract_vector_metadata(df, vectors, labels)

    return df


def _process_json_response(data, vectors, labels):
    """Process JSON API response into a pandas DataFrame."""
    if "data" not in data:
        raise ValueError("Invalid API response: missing 'data' field")

    df = pd.DataFrame(data["data"])

    # Extract vector metadata and handle labels
    df = _extract_vector_metadata(df, vectors, labels)

    return df


def _process_geojson_response(data, vectors, labels):
    """Process GeoJSON API response into a GeoDataFrame."""
    if "features" not in data:
        raise ValueError("Invalid GeoJSON response: missing 'features' field")

    gdf = gpd.GeoDataFrame.from_features(data["features"])

    # Apply the same numeric conversion logic as CSV processing
    # This was missing and causing all columns to remain as strings

    # Define census-specific NA values (matching R package)
    census_na_values = ["x", "X", "F", "...", "-", ""]

    # Convert specific columns to numeric (matching R package exactly)
    numeric_columns = []

    # Standard census columns that should be numeric
    # Note: API may return column names with trailing spaces, so we need flexible matching
    standard_numeric = [
        "Population",
        "Households",
        "Dwellings",
        "Area (sq km)",
        "pop",
        "dw",
        "hh",
        "a",
    ]

    # Create a mapping of actual column names to expected names for flexible matching
    column_mapping = {}
    for expected_col in standard_numeric:
        # Check for exact match first
        if expected_col in gdf.columns:
            numeric_columns.append(expected_col)
            continue

        # Check for variations with trailing/leading spaces
        for actual_col in gdf.columns:
            if actual_col.strip() == expected_col:
                numeric_columns.append(actual_col)
                column_mapping[actual_col] = expected_col
                break

    # Vector columns (v_* pattern) - handle both short and descriptive names
    for col in gdf.columns:
        if col.startswith("v_CA") or col.startswith("v_"):
            numeric_columns.append(col)

    # Convert to numeric with census NA handling
    for col in numeric_columns:
        if col in gdf.columns:  # Additional safety check
            # Replace census NA values with NaN, then convert to numeric
            gdf[col] = gdf[col].replace(census_na_values, pd.NA)
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce")

    # Convert categorical columns to pandas categorical (matching R factors)
    categorical_columns = ["Type", "Region Name", "name", "t"]
    for expected_col in categorical_columns:
        # Check for exact match first
        if expected_col in gdf.columns:
            gdf[expected_col] = gdf[expected_col].astype("category")
            continue

        # Check for variations with trailing/leading spaces
        for actual_col in gdf.columns:
            if actual_col.strip() == expected_col:
                gdf[actual_col] = gdf[actual_col].astype("category")
                break

    # Extract vector metadata and handle labels
    gdf = _extract_vector_metadata(gdf, vectors, labels)

    return gdf
