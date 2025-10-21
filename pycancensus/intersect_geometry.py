"""
Functions for finding census regions that intersect with geometries.
"""

import json
import hashlib
import requests
import geopandas as gpd
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from typing import Union, List, Dict, Any, Optional
import warnings

from .settings import get_api_key
from .cache import get_cached_data, cache_data
from .utils import validate_dataset


def get_intersecting_geometries(
    dataset: str,
    level: str,
    geometry: Union[gpd.GeoDataFrame, gpd.GeoSeries, Point, Polygon, MultiPolygon],
    simplified: bool = False,
    use_cache: bool = True,
    quiet: bool = False,
    api_key: Optional[str] = None,
) -> Union[List[str], Dict[str, List[str]]]:
    """
    Get identifiers for census regions intersecting a geometry.

    This function returns a list of regions that intersect a given geometry input.
    This list of regions can be used directly to query census when one is interested
    in census data for a particular geographic region that does not coincide with
    defined census geometries.

    Parameters
    ----------
    dataset : str
        A CensusMapper dataset identifier.
    level : str
        The census aggregation level to retrieve. One of "Regions", "PR", "CMA",
        "CD", "CSD", "CT", "DA", "EA" (for 1996), or "DB" (for 2001-2021).
    geometry : gpd.GeoDataFrame, gpd.GeoSeries, Point, Polygon, or MultiPolygon
        A valid geometry object. Any projection is accepted - objects will be
        reprojected to WGS84 (EPSG:4326) for server-side intersections.
    simplified : bool, default False
        If True, returns a list of region IDs. If False, returns a dictionary
        compatible with get_census() regions parameter.
    use_cache : bool, default True
        Whether to use cached data if available.
    quiet : bool, default False
        Whether to suppress messages and warnings.
    api_key : str, optional
        API key for CensusMapper API. If None, uses environment variable
        or previously set key.

    Returns
    -------
    List[str] or Dict[str, List[str]]
        If simplified=True, returns a list of region identifiers.
        If simplified=False, returns a dictionary with level as key and
        list of region IDs as value, suitable for use with get_census().

    Examples
    --------
    >>> import pycancensus as pc
    >>> from shapely.geometry import Point
    >>>
    >>> # Example using a Point from lat/lon coordinates
    >>> point_geo = Point(-123.25149, 49.27026)
    >>> regions = pc.get_intersecting_geometries(
    ...     dataset='CA21',
    ...     level='CT',
    ...     geometry=point_geo
    ... )
    >>>
    >>> # Use regions to get census data
    >>> census_data = pc.get_census(
    ...     dataset='CA21',
    ...     regions=regions,
    ...     vectors=['v_CA21_1', 'v_CA21_2'],
    ...     level='CT'
    ... )
    """
    # Validate inputs
    validate_dataset(dataset)

    if api_key is None:
        api_key = get_api_key()
        if api_key is None:
            raise ValueError(
                "API key required. Set with set_api_key() or CANCENSUS_API_KEY "
                "environment variable."
            )

    # Process geometry input
    processed_geometry = _process_geometry_input(geometry)

    # Ensure geometry is in WGS84 (EPSG:4326)
    if processed_geometry.crs is None:
        warnings.warn("No CRS specified for geometry, assuming WGS84 (EPSG:4326)")
        processed_geometry = processed_geometry.set_crs("EPSG:4326")
    elif processed_geometry.crs.to_epsg() != 4326:
        processed_geometry = processed_geometry.to_crs("EPSG:4326")

    # Union multiple geometries if needed
    if len(processed_geometry) > 1:
        geometry_union = unary_union(processed_geometry.geometry)
        processed_geometry = gpd.GeoSeries([geometry_union], crs="EPSG:4326")

    # Convert to GeoJSON
    geojson_str = processed_geometry.to_json()

    # Calculate area in square meters (approximate for WGS84)
    # Using area in degrees^2 * conversion factor for rough area estimate
    area = processed_geometry.area.iloc[0]
    # Convert from square degrees to approximate square meters at equator
    area_m2 = area * (111320**2)  # Rough conversion

    # Create cache key
    param_string = f"dataset={dataset}&level={level}&geometry={geojson_str}"
    cache_key = f"intersect_{hashlib.md5(param_string.encode()).hexdigest()}"

    # Check cache first
    if use_cache:
        cached_data = get_cached_data(cache_key)
        if cached_data is not None:
            if not quiet:
                print("Reading intersection data from cache...")
            result = cached_data
        else:
            result = _query_intersecting_geometries_api(
                dataset, level, geojson_str, area_m2, api_key, quiet
            )
            cache_data(cache_key, result)
    else:
        result = _query_intersecting_geometries_api(
            dataset, level, geojson_str, area_m2, api_key, quiet
        )

    # Format output based on simplified parameter
    if simplified:
        # Return simple list of region IDs
        if isinstance(result, list):
            return [str(r) for r in result]
        else:
            return list(result.keys()) if isinstance(result, dict) else []
    else:
        # Return in format suitable for get_census()
        if isinstance(result, list):
            return {level: [str(r) for r in result]}
        elif isinstance(result, dict):
            # Assume API returns dict with level as key
            return result
        else:
            return {level: []}


def _process_geometry_input(geometry) -> gpd.GeoSeries:
    """Process various geometry input types into a GeoSeries."""
    if isinstance(geometry, gpd.GeoDataFrame):
        return geometry.geometry
    elif isinstance(geometry, gpd.GeoSeries):
        return geometry
    elif hasattr(geometry, "__geo_interface__"):
        # Shapely geometry or similar
        return gpd.GeoSeries([geometry])
    else:
        raise ValueError(
            "The geometry parameter must be a GeoDataFrame, GeoSeries, "
            "or Shapely geometry object"
        )


def _query_intersecting_geometries_api(
    dataset: str, level: str, geojson_str: str, area: float, api_key: str, quiet: bool
) -> Any:
    """Query the CensusMapper API for intersecting geometries."""
    base_url = "https://censusmapper.ca/api/v1/"

    # Prepare request data
    request_data = {
        "dataset": dataset,
        "level": level,
        "geometry": geojson_str,
        "area": area,
        "api_key": api_key,
    }

    if not quiet:
        print("Querying CensusMapper API for intersecting geometries...")

    try:
        response = requests.post(
            f"{base_url}intersecting_geographies",
            json=request_data,
            headers={"Accept": "application/json"},
            timeout=60,
        )
        response.raise_for_status()

        result = response.json()

        if not quiet:
            if isinstance(result, list):
                print(f"✅ Found {len(result)} intersecting regions")
            elif isinstance(result, dict):
                total = sum(
                    len(v) if isinstance(v, list) else 1 for v in result.values()
                )
                print(f"✅ Found {total} intersecting regions")

        return result

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"API request failed: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to process API response: {e}")
