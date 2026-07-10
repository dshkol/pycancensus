"""Tests for public API exception propagation."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from shapely.geometry import Point

import pycancensus as pc
from pycancensus.resilience import NetworkError, RateLimitError


@pytest.mark.parametrize(
    ("session_patch", "method", "call"),
    [
        (
            "pycancensus.core.get_session",
            "post",
            lambda: pc.get_census(
                "CA21", {"PR": "35"}, quiet=True, use_cache=False, api_key="key"
            ),
        ),
        (
            "pycancensus.datasets.get_session",
            "get",
            lambda: pc.list_census_datasets(quiet=True, use_cache=False, api_key="key"),
        ),
        (
            "pycancensus.regions.get_session",
            "get",
            lambda: pc.list_census_regions(
                "CA21", quiet=True, use_cache=False, api_key="key"
            ),
        ),
        (
            "pycancensus.vectors.get_session",
            "get",
            lambda: pc.list_census_vectors(
                "CA21", quiet=True, use_cache=False, api_key="key"
            ),
        ),
        (
            "pycancensus.intersect_geometry.get_session",
            "post",
            lambda: pc.get_intersecting_geometries(
                "CA21",
                "CT",
                Point(-123.1, 49.2),
                quiet=True,
                use_cache=False,
                api_key="key",
            ),
        ),
    ],
)
@pytest.mark.filterwarnings("ignore:No CRS specified for geometry")
@pytest.mark.filterwarnings("ignore:Geometry is in a geographic CRS")
def test_rate_limit_error_survives_public_api(session_patch, method, call):
    session = MagicMock()
    getattr(session, method).side_effect = RateLimitError("rate limited")

    with patch(session_patch, return_value=session):
        with pytest.raises(RateLimitError):
            call()


@patch("pycancensus.core.get_session")
def test_exhausted_network_error_uses_public_error_hierarchy(mock_get_session):
    session = MagicMock()
    session.post.side_effect = requests.exceptions.ConnectionError("offline")
    mock_get_session.return_value = session

    with pytest.raises(NetworkError, match="offline") as excinfo:
        pc.get_census("CA21", {"PR": "35"}, quiet=True, use_cache=False, api_key="key")

    assert isinstance(excinfo.value.__cause__, requests.exceptions.ConnectionError)
