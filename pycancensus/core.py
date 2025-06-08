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
    
    # Check cache first
    if use_cache:
        cache_key = _generate_cache_key(dataset, processed_regions, vectors, level, geo_format)
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
        "geo_hierarchy": "true"  # KEY FIX: Missing parameter from R package
    }
    
    # Add vectors if specified (JSON-encoded like R package)
    if vectors:
        request_data["vectors"] = json.dumps(vectors)
    
    # Determine endpoint based on geometry request
    if geo_format == "geopandas":
        endpoint = "geo.geojson"
        if resolution == "high":
            request_data["resolution"] = "high"
    else:
        endpoint = "data.csv"
    
    try:
        if not quiet:
            print(f"Querying CensusMapper API...")
            
        # Use multipart/form-data like the R package
        # Convert all values to tuple format for multipart encoding
        multipart_data = {}
        for key, value in request_data.items():
            multipart_data[key] = (None, value)
        
        response = requests.post(f"{base_url}{endpoint}", files=multipart_data, timeout=30)
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
            
        if not quiet:
            print(f"Retrieved data for {len(result)} regions")
            
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


def _process_csv_response(csv_text, vectors, labels):
    """Process CSV API response into a pandas DataFrame."""
    import io
    
    # Read CSV from string
    df = pd.read_csv(io.StringIO(csv_text))
    
    # TODO: Add label processing based on labels parameter
    # TODO: Add vector name mapping
    
    return df


def _process_json_response(data, vectors, labels):
    """Process JSON API response into a pandas DataFrame."""
    if "data" not in data:
        raise ValueError("Invalid API response: missing 'data' field")
        
    df = pd.DataFrame(data["data"])
    
    # TODO: Add label processing based on labels parameter
    # TODO: Add vector name mapping
    
    return df


def _process_geojson_response(data, vectors, labels):
    """Process GeoJSON API response into a GeoDataFrame."""
    if "features" not in data:
        raise ValueError("Invalid GeoJSON response: missing 'features' field")
    
    gdf = gpd.GeoDataFrame.from_features(data["features"])
    
    # TODO: Add label processing based on labels parameter
    # TODO: Add vector name mapping
    
    return gdf