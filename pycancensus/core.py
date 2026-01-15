"""
Core functionality for accessing Canadian Census data through the CensusMapper API.
"""

import hashlib
import io
import json
import warnings
from typing import Dict, List, Optional, Union

import pandas as pd
import geopandas as gpd
import requests

from .settings import get_api_key, get_cache_path, CENSUSMAPPER_API_URL
from .resilience import get_session
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
            # Process labels for cached data
            cached_data = _extract_vector_metadata(cached_data, vectors, labels)
            return cached_data

    # Build API request exactly like the R package
    base_url = f"{CENSUSMAPPER_API_URL}/"

    # Format parameters exactly like the R package

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
            # Use dedicated function to fetch and merge geo + vector data
            result = _fetch_census_with_geometry_and_vectors(
                base_url, request_data, resolution, vectors, labels
            )
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

            response = get_session().post(f"{base_url}{endpoint}", files=multipart_data)

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
    # Create a string representation of the parameters
    params_str = f"{dataset}_{regions}_{vectors}_{level}_{geo_format}"

    # Create a hash of the parameters
    return hashlib.md5(params_str.encode()).hexdigest()


def _fetch_census_with_geometry_and_vectors(
    base_url: str,
    request_data: dict,
    resolution: str,
    vectors: List[str],
    labels: str,
) -> gpd.GeoDataFrame:
    """
    Fetch census data with both geometry and vector data.

    The CensusMapper geo.geojson endpoint doesn't properly return vector data,
    so this function makes separate calls to geo.geojson and data.csv endpoints,
    then merges the results on geographic identifier.

    Parameters
    ----------
    base_url : str
        The API base URL (e.g., "https://censusmapper.ca/api/v1/").
    request_data : dict
        The base request parameters (dataset, level, api_key, regions, etc.).
    resolution : str
        Resolution of geographic data - 'simplified' or 'high'.
    vectors : list of str
        Vector codes to retrieve.
    labels : str
        Label format - 'detailed' or 'short'.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame with geometry and vector data merged.
    """
    # 1. Fetch geometry data (without vectors)
    geo_request_data = request_data.copy()
    if "vectors" in geo_request_data:
        del geo_request_data["vectors"]
    if resolution == "high":
        geo_request_data["resolution"] = "high"

    geo_multipart_data = {key: (None, value) for key, value in geo_request_data.items()}
    geo_response = get_session().post(
        f"{base_url}geo.geojson", files=geo_multipart_data
    )
    geo_data = geo_response.json()
    geo_result = _process_geojson_response(geo_data, None, labels)

    # 2. Fetch vector data using CSV endpoint
    csv_multipart_data = {key: (None, value) for key, value in request_data.items()}
    csv_response = get_session().post(f"{base_url}data.csv", files=csv_multipart_data)
    csv_result = _process_csv_response(csv_response.text, vectors, labels)

    # 3. Merge the results on geographic identifier
    return _merge_geo_and_csv_results(geo_result, csv_result)


def _merge_geo_and_csv_results(
    geo_result: gpd.GeoDataFrame,
    csv_result: pd.DataFrame,
) -> gpd.GeoDataFrame:
    """
    Merge GeoDataFrame with CSV DataFrame on geographic identifier.

    Finds a common identifier column (GeoUID, id, or rgid) and merges
    the vector columns from CSV onto the GeoDataFrame.

    Parameters
    ----------
    geo_result : gpd.GeoDataFrame
        GeoDataFrame with geometry data.
    csv_result : pd.DataFrame
        DataFrame with vector data.

    Returns
    -------
    gpd.GeoDataFrame
        Merged GeoDataFrame with geometry and vector columns.
    """
    # Find merge keys in each DataFrame
    merge_key_csv = None
    merge_key_geo = None

    for potential_key in ["GeoUID", "id", "rgid"]:
        if potential_key in csv_result.columns:
            merge_key_csv = potential_key
            break

    for potential_key in ["id", "rgid", "GeoUID"]:
        if potential_key in geo_result.columns:
            merge_key_geo = potential_key
            break

    if merge_key_csv and merge_key_geo:
        # Merge on identifier - keep geo columns, add vector columns from CSV
        vector_columns = [col for col in csv_result.columns if col.startswith("v_")]
        merge_columns = [merge_key_csv] + vector_columns

        result = geo_result.merge(
            csv_result[merge_columns],
            left_on=merge_key_geo,
            right_on=merge_key_csv,
            how="left",
        )

        # Drop duplicate merge key if names differ
        if merge_key_csv != merge_key_geo and merge_key_csv in result.columns:
            result = result.drop(columns=[merge_key_csv])

    else:
        # Fallback: assume same row order and merge by index
        vector_columns = [col for col in csv_result.columns if col.startswith("v_")]
        result = geo_result.copy()
        for col in vector_columns:
            if len(csv_result) == len(geo_result):
                result[col] = csv_result[col].values

    return result


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

        # Store metadata as dict to avoid pandas attrs comparison bug
        # Convert DataFrame to list of dicts for storage
        df.attrs["census_vectors"] = metadata_df.to_dict(orient="records")

    return df


def _normalize_census_dataframe(
    df: Union[pd.DataFrame, gpd.GeoDataFrame],
    vectors: Optional[List[str]],
    labels: str,
) -> Union[pd.DataFrame, gpd.GeoDataFrame]:
    """
    Normalize a census DataFrame or GeoDataFrame.

    Applies consistent data type conversions and metadata extraction:
    - Converts census NA values ('x', 'X', 'F', '...', '-', '') to pd.NA
    - Converts numeric columns (population, households, etc.) to numeric dtype
    - Converts categorical columns (Type, Region Name) to category dtype
    - Extracts and stores vector metadata

    Parameters
    ----------
    df : pd.DataFrame or gpd.GeoDataFrame
        The data to normalize.
    vectors : list of str, optional
        Vector codes that were requested (for metadata extraction).
    labels : str
        Label format - 'detailed' or 'short'.

    Returns
    -------
    pd.DataFrame or gpd.GeoDataFrame
        The normalized data with proper dtypes.
    """
    # Census-specific NA values (matching R package)
    census_na_values = ["x", "X", "F", "...", "-", ""]

    # Standard census columns that should be numeric
    # Include both long names (CSV endpoint) and short names (GeoJSON endpoint)
    standard_numeric = [
        "Population",
        "Households",
        "Dwellings",
        "Area (sq km)",
        "pop",  # GeoJSON short name
        "dw",  # GeoJSON short name
        "hh",  # GeoJSON short name
        "a",  # GeoJSON short name
    ]

    # Find numeric columns to convert
    numeric_columns = []
    for expected_col in standard_numeric:
        # Check for exact match
        if expected_col in df.columns:
            numeric_columns.append(expected_col)
            continue
        # Check for variations with trailing/leading spaces (API quirk)
        for actual_col in df.columns:
            if actual_col.strip() == expected_col:
                numeric_columns.append(actual_col)
                break

    # Vector columns (v_* pattern) are always numeric
    for col in df.columns:
        if col.startswith("v_"):
            numeric_columns.append(col)

    # Convert to numeric with census NA handling
    for col in numeric_columns:
        if col in df.columns:
            df[col] = df[col].replace(census_na_values, pd.NA)
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Standard categorical columns
    # Include both long names (CSV endpoint) and short names (GeoJSON endpoint)
    categorical_columns = [
        "Type",
        "Region Name",
        "name",  # GeoJSON short name
        "t",  # GeoJSON short name
    ]

    for expected_col in categorical_columns:
        # Check for exact match
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


def _process_csv_response(csv_text, vectors, labels):
    """Process CSV API response into a pandas DataFrame."""
    # Read all columns as strings initially (like R package)
    df = pd.read_csv(io.StringIO(csv_text), dtype=str, encoding="utf-8")

    # Fix column names by removing trailing/leading spaces (critical fix for API compatibility)
    df.columns = df.columns.str.strip()

    # Apply shared normalization
    return _normalize_census_dataframe(df, vectors, labels)


def _process_json_response(data, vectors, labels):
    """Process JSON API response into a pandas DataFrame."""
    if "data" not in data:
        raise ValueError("Invalid API response: missing 'data' field")

    df = pd.DataFrame(data["data"])

    # Apply shared normalization
    return _normalize_census_dataframe(df, vectors, labels)


def _process_geojson_response(data, vectors, labels):
    """Process GeoJSON API response into a GeoDataFrame."""
    if "features" not in data:
        raise ValueError("Invalid GeoJSON response: missing 'features' field")

    gdf = gpd.GeoDataFrame.from_features(data["features"], crs="EPSG:4326")

    # Apply shared normalization
    return _normalize_census_dataframe(gdf, vectors, labels)
