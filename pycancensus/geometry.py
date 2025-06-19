"""
Functions for working with census geometry.
"""

import geopandas as gpd
from typing import Dict, List, Optional, Union

from .core import get_census


def get_census_geometry(
    dataset: str,
    regions: Dict[str, Union[str, List[str]]],
    level: str = "Regions",
    resolution: str = "simplified",
    use_cache: bool = True,
    quiet: bool = False,
    api_key: Optional[str] = None,
) -> gpd.GeoDataFrame:
    """
    Get census boundary geometries from the CensusMapper API.

    Parameters
    ----------
    dataset : str
        A CensusMapper dataset identifier (e.g., 'CA16', 'CA21').
    regions : dict
        Dictionary of census regions to retrieve geometries for.
    level : str, default 'Regions'
        The census aggregation level to retrieve.
    resolution : str, default 'simplified'
        Resolution of geographic data. Either 'simplified' or 'high'.
    use_cache : bool, default True
        Whether to use cached data if available.
    quiet : bool, default False
        Whether to suppress messages and warnings.
    api_key : str, optional
        API key for CensusMapper API.

    Returns
    -------
    gpd.GeoDataFrame
        GeoDataFrame containing census boundary geometries.

    Examples
    --------
    >>> import pycancensus as pc
    >>> # Get geometries for Vancouver CMA
    >>> geometries = pc.get_census_geometry(
    ...     dataset='CA16',
    ...     regions={'CMA': '59933'},
    ...     level='CSD'
    ... )
    """
    # Use the main get_census function with geometry format
    # This ensures we use the same working API implementation
    return get_census(
        dataset=dataset,
        regions=regions,
        vectors=None,  # No vectors for geometry-only
        level=level,
        geo_format="geopandas",
        resolution=resolution,
        use_cache=use_cache,
        quiet=quiet,
        api_key=api_key,
    )
