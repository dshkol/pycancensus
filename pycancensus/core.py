"""
Core functionality for accessing Canadian Census data through the CensusMapper API.
"""

import hashlib
import io
import json
import re
import sys
import warnings
from datetime import datetime
from typing import Dict, List, Optional, Union

import pandas as pd
import geopandas as gpd
import requests

from .settings import (
    get_api_key,
    get_language,
    get_labels,
    validate_language,
    validate_labels,
    first_time_this_session,
    CENSUSMAPPER_API_URL,
    VALID_LABELS,
)
from .resilience import CensusAPIError, NetworkError, get_session
from .cache import get_cached_data, cache_data
from .utils import validate_dataset, validate_level, process_regions
from .progress import show_request_preview, create_progress_for_request


# Version 3: cached results no longer depend on labels or language, these
# get applied after reading the cache
_CACHE_SCHEMA_VERSION = 3


def get_census(
    dataset: str,
    regions: Dict[str, Union[str, List[str]]],
    vectors: Optional[List[str]] = None,
    level: str = "Regions",
    geo_format: Optional[str] = None,
    resolution: str = "simplified",
    labels: Optional[str] = None,
    use_cache: bool = True,
    quiet: bool = False,
    api_key: Optional[str] = None,
    language: Optional[str] = None,
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
        'CMA', 'CA', 'CMACA', 'CD', 'CSD', 'CT', 'DA', 'EA' (for 1996), or
        'DB' (for 2001-2021). 'CMA', 'CA' and 'CMACA' all refer to the same
        level, which contains both census metropolitan areas and census
        agglomerations.
    geo_format : str, optional
        Format for geographic information. Set to 'geopandas' to return a
        GeoDataFrame with geometry. If None, returns DataFrame without geometry.
    resolution : str, default 'simplified'
        Resolution of geographic data. Either 'simplified' or 'high'.
    labels : str, optional
        How to name and label the columns, one of 'detailed', 'short' or
        'labelled'. Defaults to :func:`get_labels`, and to 'detailed' if no
        default is set. The default is planned to change to 'labelled' in a
        future version, so to keep code working pass ``labels`` or set a
        default with e.g. ``pc.set_labels("detailed")``. A notice points this
        out once per session if neither is set.

        - 'detailed' names census variable columns by vector and label, e.g.
          ``"v_CA21_1: Population, 2021"``.
        - 'short' names them by vector only, e.g. ``"v_CA21_1"``; use
          :func:`label_vectors` for the labels.
        - 'labelled' also names them by vector only, and stores the label of
          each column in ``result.attrs["column_labels"]``, a dict mapping
          column names to labels (the analog of R's per-column ``"label"``
          attribute). The other columns get short names, types and an order
          that are the same across datasets and with or without
          ``geo_format``: ``GeoUID``, ``Type``, ``Name``, ``Area``,
          ``Population``, ``Dwellings``, ``Households``,
          ``Population_Previous``, ``Quality``, the ``*_UID`` columns and so
          on. These have labels too, e.g. ``"Population 2021"`` for
          ``Population``, with the year of the census the column refers to.
    use_cache : bool, default True
        Whether to use cached data if available.
    quiet : bool, default False
        Whether to suppress messages and warnings.
    api_key : str, optional
        API key for CensusMapper API. If None, uses environment variable
        or previously set key.
    language : str, optional
        Language of the census variable labels, 'en' or 'fr'. Defaults to
        :func:`get_language`, which is 'en' unless set with
        :func:`set_language`. This applies to the column names with
        ``labels='detailed'``, to the column labels with
        ``labels='labelled'``, and to :func:`label_vectors`. It does not
        apply to region names or the names of the other columns. Not all
        datasets have French labels: vectors without them fall back to
        English, with a warning once per session and dataset. Changing the
        language does not download the data again.

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

    >>> # Name columns by vector, with the labels in attrs["column_labels"]
    >>> data = pc.get_census(
    ...     dataset='CA16',
    ...     regions={'CMA': '59933'},
    ...     vectors=['v_CA16_408', 'v_CA16_409'],
    ...     level='CSD',
    ...     labels='labelled'
    ... )
    >>> data.attrs["column_labels"]["v_CA16_408"]

    >>> # Get the labels in French
    >>> data = pc.get_census(
    ...     dataset='CA16',
    ...     regions={'CMA': '59933'},
    ...     vectors=['v_CA16_408', 'v_CA16_409'],
    ...     level='CSD',
    ...     language='fr'
    ... )
    """

    # Validate inputs
    language = get_language() if language is None else validate_language(language)
    if labels is None:
        labels = get_labels()
        if labels is None:
            labels = "detailed"
            if not quiet:
                _notice_labels_default()
    labels = validate_labels(labels)
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

    # Check cache first. The cache holds the data as downloaded, labels and
    # language get applied afterwards, so changing them doesn't download again
    cache_key = _generate_cache_key(
        dataset,
        processed_regions,
        vectors,
        level,
        geo_format,
        resolution,
    )
    result = None
    if use_cache:
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            if not quiet:
                print(f"Reading data from cache...")
            from .recalls import check_recalled_data_and_warn

            check_recalled_data_and_warn(cache_key)
            result = cached_data

    if result is None:
        result = _download_census(
            dataset,
            processed_regions,
            vectors,
            level,
            geo_format,
            resolution,
            use_cache,
            quiet,
            api_key,
            cache_key,
        )

    return _apply_labels(
        result, dataset, level, vectors, labels, language, quiet, api_key
    )


def _notice_labels_default() -> None:
    """
    Prepare users for the planned change of the labels default, once per
    session. A notice and not a warning, like R cancensus, so code that
    turns warnings into errors keeps working.
    """
    if not first_time_this_session("labels_default_notice"):
        return
    print(
        'The default of `labels="detailed"` in `get_census()` is planned to '
        'change to `labels="labelled"` in a future version. To make sure your '
        "code keeps working, set the `labels` parameter or set a default, e.g. "
        '`pc.set_labels("detailed")`.\n'
        'Check out `labels="labelled"`, which gives short and consistent column '
        "names, with the full descriptions in column labels. See "
        "`help(pc.get_census)` for details.\n"
        "This message is shown once per session.",
        file=sys.stderr,
    )


def _download_census(
    dataset,
    processed_regions,
    vectors,
    level,
    geo_format,
    resolution,
    use_cache,
    quiet,
    api_key,
    cache_key,
):
    """Download census data and cache it, with English, detailed labels."""
    labels = "detailed"
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
            result, data_version, geo_version = _fetch_census_with_geometry_and_vectors(
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

            # Track the server data version for recalled-data detection
            data_version = None
            geo_version = None
            if geo_format == "geopandas":
                geo_version = response.headers.get("data-version")
            else:
                data_version = response.headers.get("data-version")

            # Process the response data based on endpoint
            if geo_format == "geopandas":
                # geo.geojson returns JSON
                data = response.json()
                result = _process_geojson_response(data, vectors, labels)
            else:
                # data.csv returns CSV
                result = _process_csv_response(
                    response.content.decode("utf-8"), vectors, labels
                )

        # Cache the result. use_cache=False means "don't read stale data",
        # not "don't cache": a forced refresh still updates the cache,
        # matching the R package. Metadata enables recalled-data detection.
        cache_data(
            cache_key,
            result,
            metadata={
                "dataset": dataset,
                "regions": regions_for_json,
                "level": level,
                "vectors": list(vectors) if vectors else [],
                "created_at": datetime.now().isoformat(),
                "version": data_version,
                "geo_version": geo_version,
            },
        )

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

    except CensusAPIError:
        raise
    except requests.exceptions.RequestException as e:
        raise NetworkError(str(e)) from e
    except Exception as e:
        raise RuntimeError(f"Failed to process API response: {e}") from e


def _generate_cache_key(dataset, regions, vectors, level, geo_format, resolution):
    """
    Generate a cache key for the given parameters.

    Labels and language are left out on purpose: they get applied after
    reading the cache, so changing them reuses the cached download.
    """
    payload = {
        "schema": _CACHE_SCHEMA_VERSION,
        "dataset": dataset,
        "regions": regions,
        "vectors": vectors or [],
        "level": level,
        "geo_format": geo_format,
        "resolution": resolution,
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _fetch_census_with_geometry_and_vectors(
    base_url: str,
    request_data: dict,
    resolution: str,
    vectors: List[str],
    labels: str,
):
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
    tuple of (gpd.GeoDataFrame, str or None, str or None)
        GeoDataFrame with geometry and vector data merged, plus the
        data-version and geometry-version headers reported by the server.
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
    geo_version = geo_response.headers.get("data-version")
    geo_data = geo_response.json()
    geo_result = _process_geojson_response(geo_data, None, labels)

    # 2. Fetch vector data using CSV endpoint
    csv_multipart_data = {key: (None, value) for key, value in request_data.items()}
    csv_response = get_session().post(f"{base_url}data.csv", files=csv_multipart_data)
    data_version = csv_response.headers.get("data-version")
    csv_result = _process_csv_response(
        csv_response.content.decode("utf-8"), vectors, labels
    )

    # 3. Merge the results on geographic identifier
    return _merge_geo_and_csv_results(geo_result, csv_result), data_version, geo_version


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

    if not merge_key_csv or not merge_key_geo:
        raise ValueError(
            "Cannot safely merge geography and census data: no supported "
            "geographic identifier was found in both responses"
        )

    if geo_result[merge_key_geo].isna().any():
        raise ValueError(
            f"Cannot safely merge geography and census data: missing "
            f"identifiers in geography column {merge_key_geo!r}"
        )
    if csv_result[merge_key_csv].isna().any():
        raise ValueError(
            f"Cannot safely merge geography and census data: missing "
            f"identifiers in census column {merge_key_csv!r}"
        )
    if geo_result[merge_key_geo].duplicated().any():
        raise ValueError(
            f"Cannot safely merge geography and census data: duplicate "
            f"identifiers in geography column {merge_key_geo!r}"
        )
    if csv_result[merge_key_csv].duplicated().any():
        raise ValueError(
            f"Cannot safely merge geography and census data: duplicate "
            f"identifiers in census column {merge_key_csv!r}"
        )

    extra_census_ids = csv_result.loc[
        ~csv_result[merge_key_csv].isin(geo_result[merge_key_geo]), merge_key_csv
    ]
    if not extra_census_ids.empty:
        sample = ", ".join(map(str, extra_census_ids.head(5)))
        raise ValueError(
            "Cannot safely merge geography and census data: "
            f"{len(extra_census_ids)} census identifier(s) had no geography match "
            f"(sample: {sample})"
        )

    vector_columns = [col for col in csv_result.columns if col.startswith("v_")]
    merge_columns = [merge_key_csv] + vector_columns
    result = geo_result.merge(
        csv_result[merge_columns],
        left_on=merge_key_geo,
        right_on=merge_key_csv,
        how="left",
        validate="one_to_one",
        indicator=True,
    )

    unmatched = result.loc[result["_merge"] != "both", merge_key_geo]
    if not unmatched.empty:
        sample = ", ".join(map(str, unmatched.head(5)))
        raise ValueError(
            "Cannot safely merge geography and census data: "
            f"{len(unmatched)} geography identifier(s) had no census match "
            f"(sample: {sample})"
        )

    result = result.drop(columns=["_merge"])
    if merge_key_csv != merge_key_geo and merge_key_csv in result.columns:
        result = result.drop(columns=[merge_key_csv])

    # The merge keeps the geometry frame's attrs, which lack the vector
    # metadata that label_vectors() reads (R cancensus 0.6.2 fix)
    if "census_vectors" in csv_result.attrs:
        result.attrs["census_vectors"] = csv_result.attrs["census_vectors"]

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

    # A 200 response can still carry an error payload instead of census
    # data; never let that be processed (and cached) as data
    if "GeoUID" not in df.columns:
        raise ValueError(
            f"Invalid API response, expected census CSV data but got: "
            f"{csv_text[:200]!r}"
        )

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


# ---------------------------------------------------------------------------
# Labels and language, applied after reading the cache (R cancensus 0.6.2)
# ---------------------------------------------------------------------------

# Column names and labels for the columns that are not census vectors, used
# for labels="labelled". Mirrors census_column_labels in R cancensus: rows are
# in the order columns get returned in, names are the same across datasets
# and for data and geometry requests, and the year goes in the label.
# {year} is the year of the census the data refers to, {previous_year} that
# of the census before it.
_CENSUS_COLUMN_LABELS = [
    # (column, short_name, en, fr)
    ("GeoUID", "GeoUID", "Geographic identifier", "Identifiant géographique"),
    ("Type", "Type", "Geographic level", "Niveau géographique"),
    ("Region Name", "Name", "Region name", "Nom de la région"),
    ("name", "Name", "Region name", "Nom de la région"),
    ("Area (sq km)", "Area", "Area (sq km)", "Superficie (km²)"),
    ("Shape Area", "Area", "Area (sq km)", "Superficie (km²)"),
    ("Population", "Population", "Population {year}", "Population {year}"),
    ("Dwellings", "Dwellings", "Dwellings {year}", "Logements {year}"),
    ("Households", "Households", "Households {year}", "Ménages {year}"),
    (
        "Adjusted Population (previous Census)",
        "Population_Previous",
        "Population {previous_year}",
        "Population {previous_year}",
    ),
    ("Population 2016", "Population_Previous", "Population 2016", "Population 2016"),
    ("Population 2011", "Population_Previous", "Population 2011", "Population 2011"),
    ("Dwellings 2016", "Dwellings_Previous", "Dwellings 2016", "Logements 2016"),
    ("Dwellings 2011", "Dwellings_Previous", "Dwellings 2011", "Logements 2011"),
    ("Households 2016", "Households_Previous", "Households 2016", "Ménages 2016"),
    ("Households 2011", "Households_Previous", "Households 2011", "Ménages 2011"),
    (
        "NHS Non-Return Rate",
        "NHS_Non_Response",
        "NHS non-response rate {year}",
        "Taux de non-réponse de l'ENM {year}",
    ),
    (
        "Quality Flags",
        "Quality",
        "Data quality flags",
        "Indicateurs de qualité des données",
    ),
    ("key", "Key", "Geographic key", "Clé géographique"),
    ("C_UID", "C_UID", "Canada identifier", "Identifiant du Canada"),
    (
        "PR_UID",
        "PR_UID",
        "Province or territory identifier",
        "Identifiant de la province ou du territoire",
    ),
    (
        "CD_UID",
        "CD_UID",
        "Census division identifier",
        "Identifiant de la division de recensement",
    ),
    (
        "CMA_UID",
        "CMA_UID",
        "Census metropolitan area or census agglomeration identifier",
        "Identifiant de la région métropolitaine de recensement ou de "
        "l'agglomération de recensement",
    ),
    (
        "CSD_UID",
        "CSD_UID",
        "Census subdivision identifier",
        "Identifiant de la subdivision de recensement",
    ),
    (
        "CT_UID",
        "CT_UID",
        "Census tract identifier",
        "Identifiant du secteur de recensement",
    ),
    (
        "DA_UID",
        "DA_UID",
        "Dissemination area identifier",
        "Identifiant de l'aire de diffusion",
    ),
]

# GeoJSON property names and the names R cancensus gives them (base_name_change)
_GEO_BASE_NAMES = {
    "id": "GeoUID",
    "a": "Shape Area",
    "t": "Type",
    "dw": "Dwellings",
    "hh": "Households",
    "pop": "Population",
    "pop2": "Adjusted Population (previous Census)",
    "nrr": "NHS Non-Return Rate",
    "q": "Quality Flags",
    "pop11": "Population 2011",
    "pop16": "Population 2016",
    "hh11": "Households 2011",
    "hh16": "Households 2016",
    "dw11": "Dwellings 2011",
    "dw16": "Dwellings 2016",
}

# What the generic parent identifiers of GeoJSON features refer to at each
# level (R cancensus name_change_for_level)
_GEO_LEVEL_NAMES = {
    "DB": {"rpid": "DA_UID", "rgid": "CSD_UID", "ruid": "CT_UID", "rguid": "CMA_UID"},
    "DA": {"rpid": "CSD_UID", "rgid": "CD_UID", "ruid": "CT_UID", "rguid": "CMA_UID"},
    "EA": {"rpid": "CSD_UID", "rgid": "CD_UID", "ruid": "CT_UID", "rguid": "CMA_UID"},
    "CT": {"rpid": "CMA_UID", "rgid": "PR_UID", "ruid": "CSD_UID", "rguid": "CD_UID"},
    "CSD": {"rpid": "CD_UID", "rgid": "PR_UID", "ruid": "CMA_UID"},
    "CD": {"rpid": "PR_UID", "rgid": "C_UID"},
    "CMA": {"rpid": "PR_UID", "rgid": "C_UID"},
    "CA": {"rpid": "PR_UID", "rgid": "C_UID"},
    "CMACA": {"rpid": "PR_UID", "rgid": "C_UID"},
    "PR": {"rpid": "C_UID"},
    "C": {},
}
_GEO_PARENT_IDS = ("rpid", "rgid", "ruid", "rguid")

_COUNT_COLUMNS = [
    f"{name}{suffix}"
    for name in ("Population", "Dwellings", "Households")
    for suffix in ("", "_Previous")
]
_NUMERIC_COLUMNS = _COUNT_COLUMNS + ["Area", "NHS_Non_Response"]


def _apply_labels(result, dataset, level, vectors, labels, language, quiet, api_key):
    """
    Name and label the columns of downloaded data as requested.

    The cached data has detailed English column names; this renames vector
    columns for 'short' and 'labelled', harmonizes the other columns for
    'labelled', and swaps in labels in the requested language.
    """
    if labels == "labelled":
        result = _label_census_columns(result, dataset, level, language)

    if not vectors:
        return result

    vector_columns = [
        c for c in result.columns if isinstance(c, str) and c.startswith("v_")
    ]
    census_vectors = [_parse_vector_column(c) for c in vector_columns]
    census_vectors = _translate_census_vectors(
        census_vectors, dataset, language, quiet, api_key
    )

    column_labels = dict(result.attrs.get("column_labels", {}))
    to_rename = {}
    if labels != "detailed":
        to_rename = {
            column: info["Vector"]
            for column, info in zip(vector_columns, census_vectors)
            if column != info["Vector"]
        }
    elif language != "en":
        to_rename = {
            column: f"{info['Vector']}: {info['Detail']}"
            for column, info in zip(vector_columns, census_vectors)
        }
        to_rename = {old: new for old, new in to_rename.items() if old != new}
    if to_rename:
        result = result.rename(columns=to_rename)

    if labels == "labelled":
        for info in census_vectors:
            column_labels[info["Vector"]] = info["Detail"]
        result.attrs["column_labels"] = column_labels

    result.attrs["census_vectors"] = census_vectors
    return result


def _parse_vector_column(column: str) -> dict:
    """
    Split a column name "<vector>: <label>" into vector and label. Only the
    first colon separates the two, labels can contain further colons, e.g.
    "Size of census family: 2 persons".
    """
    vector, _, detail = column.partition(":")
    return {"Vector": vector, "Detail": detail.strip()}


def _translate_census_vectors(census_vectors, dataset, language, quiet, api_key):
    """
    Replace the English labels the API attaches to the data with labels in
    the requested language. The data itself doesn't depend on the language,
    so this doesn't touch the data cache. If the labels can't be retrieved
    the data is still usable with English labels, so this doesn't raise.
    """
    if language == "en" or not census_vectors:
        return census_vectors
    from .vectors import _fetch_census_vectors, _localize_census_vectors

    try:
        vector_info = _fetch_census_vectors(dataset, quiet=True, api_key=api_key)
    except Exception as e:
        if not quiet:
            warnings.warn(
                "Could not retrieve French labels, using English labels "
                f"instead. {e}",
                stacklevel=3,
            )
        return census_vectors
    wanted = {info["Vector"] for info in census_vectors}
    localized = _localize_census_vectors(
        vector_info[vector_info["vector"].isin(wanted)],
        dataset,
        language,
        warn=not quiet,
    )
    translations = dict(zip(localized["vector"], localized["label"]))
    return [
        {**info, "Detail": translations.get(info["Vector"], info["Detail"])}
        for info in census_vectors
    ]


def _census_year_for_dataset(dataset: str) -> Optional[int]:
    """
    The year of the census the non-vector columns of a dataset refer to.

    Tax and cross-tabulation datasets report these columns for the census
    whose geography they use, e.g. TX2018 has the 2016 population. Returns
    None if the year can't be determined.
    """
    geo_dataset = dataset
    if not re.fullmatch(r"CA\d+", dataset):
        try:
            from .datasets import list_census_datasets

            datasets = list_census_datasets(quiet=True)
            match = datasets.loc[datasets["dataset"] == dataset, "geo_dataset"]
            geo_dataset = match.iloc[0] if len(match) else None
        except Exception:
            return None
        if not isinstance(geo_dataset, str) or not re.fullmatch(r"CA\d+", geo_dataset):
            return None
    year = int(geo_dataset[2:])
    return year + 2000 if year < 100 else year


def _standardize_geo_columns(result, level):
    """
    Give GeoJSON properties the column names R cancensus gives them, so data
    and geometry requests have the same columns (R transform_geo()).
    """
    to_rename = {
        raw: name
        for raw, name in _GEO_BASE_NAMES.items()
        if raw in result.columns and name not in result.columns
    }
    if to_rename:
        result = result.rename(columns=to_rename)

    parent_ids = [c for c in _GEO_PARENT_IDS if c in result.columns]
    if not parent_ids:
        return result

    if level != "Regions":
        names = _GEO_LEVEL_NAMES.get(level, {})
        to_rename = {
            raw: name
            for raw, name in names.items()
            if raw in result.columns and name not in result.columns
        }
        result = result.rename(columns=to_rename)
    elif "Type" in result.columns:
        # Regions of different levels, the identifiers refer to different
        # levels row by row
        types = result["Type"].astype(str)
        new_columns = {}
        for region_type in types.unique():
            rows = (types == region_type).to_numpy()
            for raw, name in _GEO_LEVEL_NAMES.get(region_type, {}).items():
                if raw not in result.columns or name in result.columns:
                    continue
                column = new_columns.setdefault(
                    name, pd.Series(pd.NA, index=result.index, dtype=object)
                )
                values = result.loc[rows, raw].replace("", pd.NA)
                column.loc[rows] = values.to_numpy()
        for name, column in new_columns.items():
            result[name] = column

    remaining = [c for c in _GEO_PARENT_IDS if c in result.columns]
    return result.drop(columns=remaining)


def _as_string_ids(series: pd.Series) -> pd.Series:
    """Identifiers as strings, keeping missing values missing."""
    return (
        series.astype(object)
        .where(series.notna(), None)
        .map(lambda v: v if v is None or isinstance(v, str) else str(v))
    )


def _label_census_columns(result, dataset, level, language):
    """
    Harmonize the columns that are not census vectors for labels='labelled':
    give them the same names, types and order for data and geometry
    requests, and record their labels in attrs["column_labels"].
    """
    result = _standardize_geo_columns(result, level)

    # Requests for both data and geometry have these twice, with the same values
    duplicates = [
        geo
        for data, geo in (("Region Name", "name"), ("Area (sq km)", "Shape Area"))
        if data in result.columns and geo in result.columns
    ]
    if duplicates:
        result = result.drop(columns=duplicates)

    rows = [row for row in _CENSUS_COLUMN_LABELS if row[0] in result.columns]
    column_names = []
    taken = set()
    for column, short_name, _, _ in rows:
        # Only the first column with a short name gets it
        column_names.append(short_name if short_name not in taken else column)
        taken.add(short_name)
    to_rename = {
        row[0]: name for row, name in zip(rows, column_names) if row[0] != name
    }
    if to_rename:
        result = result.rename(columns=to_rename)

    if "Name" in result.columns:
        result["Name"] = _as_string_ids(result["Name"])
    for column in _NUMERIC_COLUMNS:
        if column in column_names:
            # float like the CSV columns, so types don't depend on geo_format
            result[column] = pd.to_numeric(result[column], errors="coerce").astype(
                "float64"
            )
    for column in column_names:
        if column in ("GeoUID", "Key", "Quality") or column.endswith("_UID"):
            result[column] = _as_string_ids(result[column])
    if "Type" in column_names and not isinstance(
        result["Type"].dtype, pd.CategoricalDtype
    ):
        result["Type"] = result["Type"].astype("category")

    year = _census_year_for_dataset(dataset)
    column_labels = {}
    for (_, _, en, fr), name in zip(rows, column_names):
        label = en if language == "en" else fr
        label = label.replace("{year}", "" if year is None else str(year))
        label = label.replace("{previous_year}", "" if year is None else str(year - 5))
        column_labels[name] = label.strip()

    # Geometry stays last
    geometry = getattr(result, "_geometry_column_name", None)
    if geometry not in result.columns:
        geometry = None
    ordered = column_names + [c for c in result.columns if c not in column_names]
    if geometry is not None:
        ordered = [c for c in ordered if c != geometry] + [geometry]
    result = result[ordered]
    result.attrs["column_labels"] = column_labels
    return result
