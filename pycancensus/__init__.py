"""
pycancensus: Access, retrieve, and work with Canadian Census data and geography.

This package provides integrated, convenient, and uniform access to Canadian
Census data and geography retrieved using the CensusMapper API.
"""

__version__ = "0.1.0"
__author__ = "Dmitry Shkolnik"
__email__ = "shkolnikd@gmail.com"

from .core import get_census
from .regions import list_census_regions, search_census_regions
from .vectors import list_census_vectors, search_census_vectors, label_vectors
from .datasets import list_census_datasets, dataset_attribution
from .settings import (
    set_api_key,
    get_api_key,
    set_cache_path,
    get_cache_path,
    remove_api_key,
    show_api_key,
)
from .geometry import get_census_geometry
from .cache import list_cache, remove_from_cache, clear_cache
from .hierarchy import parent_census_vectors, child_census_vectors, find_census_vectors
from .intersect_geometry import get_intersecting_geometries

__all__ = [
    "get_census",
    "list_census_regions",
    "search_census_regions",
    "list_census_vectors",
    "search_census_vectors",
    "label_vectors",
    "list_census_datasets",
    "dataset_attribution",
    "set_api_key",
    "get_api_key",
    "remove_api_key",
    "show_api_key",
    "set_cache_path",
    "get_cache_path",
    "get_census_geometry",
    "list_cache",
    "remove_from_cache",
    "clear_cache",
    "parent_census_vectors",
    "child_census_vectors",
    "find_census_vectors",
    "get_intersecting_geometries",
]
