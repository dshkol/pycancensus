"""Tests for region/vector list downloads: caching, encoding and CA levels."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import pycancensus as pc
import pycancensus.cache as cache_mod
from pycancensus.cache import cache_data, get_cached_data, has_current_list_schema
from pycancensus.utils import process_regions, validate_level

REGIONS_CSV = (
    "name,geo_uid,type,population,flag,CMA_UID,CD_UID,PR_UID\n"
    "Montréal,24462,CMA,4291732,B,,,24\n"
    "Sarnia,35562,CMA,104422,K,,,35\n"
    "Montréal,2466,CD,2004265,TÉ,,,24\n"
)
VECTORS_CSV = (
    "vector,type,label,units,add,parent,details\n"
    "v_CA21_1,Total,Population,Number,1,,Population\n"
)


@pytest.fixture(autouse=True)
def clean_session_cache():
    cache_mod._session_cache.clear()
    yield
    cache_mod._session_cache.clear()


def mock_session(csv_text, charset_header=False):
    """A session returning UTF-8 bytes; .text mimics requests' ISO-8859-1
    fallback when the server sends no charset."""
    response = MagicMock()
    response.content = csv_text.encode("utf-8")
    response.text = (
        csv_text
        if charset_header
        else response.content.decode("latin-1")  # what requests would guess
    )
    session = MagicMock()
    session.get.return_value = response
    return session


@pytest.fixture
def api_key(monkeypatch):
    monkeypatch.setattr(pc.settings, "_API_KEY", "test_key")


@pytest.mark.usefixtures("api_key")
class TestListCensusRegions:
    @patch("pycancensus.regions.get_session")
    def test_names_decode_as_utf8_without_charset_header(self, get_session):
        get_session.return_value = mock_session(REGIONS_CSV)
        regions = pc.list_census_regions("CA21", quiet=True)
        assert "Montréal" in regions["name"].tolist()

    @patch("pycancensus.regions.get_session")
    def test_census_agglomerations_are_labelled_ca(self, get_session):
        get_session.return_value = mock_session(REGIONS_CSV)
        regions = pc.list_census_regions("CA21", quiet=True)
        levels = dict(zip(regions["region"], regions["level"]))
        assert levels == {"24462": "CMA", "35562": "CA", "2466": "CD"}

    @patch("pycancensus.regions.get_session")
    def test_ca_regions_round_trip_to_a_valid_region_list(self, get_session):
        get_session.return_value = mock_session(REGIONS_CSV)
        regions = pc.list_census_regions("CA21", quiet=True)
        region_list = pc.as_census_region_list(regions[regions["level"] == "CA"])
        assert process_regions(region_list) == {"CA": ["35562"]}

    @patch("pycancensus.regions.get_session")
    def test_use_cache_false_refreshes_the_file_cache(self, get_session):
        cache_data("regions_CA21", pd.DataFrame({"name": ["stale"]}))
        get_session.return_value = mock_session(REGIONS_CSV)

        pc.list_census_regions("CA21", quiet=True, use_cache=False)

        cached = get_cached_data("regions_CA21")
        assert "stale" not in cached["name"].tolist()
        assert has_current_list_schema(cached)

    @patch("pycancensus.regions.get_session")
    def test_cache_from_older_version_is_downloaded_again(self, get_session):
        cache_data("regions_CA21", pd.DataFrame({"name": ["MontrÃ©al"]}))
        get_session.return_value = mock_session(REGIONS_CSV)

        regions = pc.list_census_regions("CA21", quiet=True)

        get_session.return_value.get.assert_called_once()
        assert "Montréal" in regions["name"].tolist()

    @patch("pycancensus.regions.get_session")
    def test_current_cache_is_reused(self, get_session):
        get_session.return_value = mock_session(REGIONS_CSV)
        pc.list_census_regions("CA21", quiet=True)
        cache_mod._session_cache.clear()

        pc.list_census_regions("CA21", quiet=True)

        get_session.return_value.get.assert_called_once()


@pytest.mark.usefixtures("api_key")
class TestListCensusVectors:
    @patch("pycancensus.vectors.get_session")
    def test_use_cache_false_refreshes_the_file_cache(self, get_session):
        cache_data("vectors_CA21", pd.DataFrame({"vector": ["stale"]}))
        get_session.return_value = mock_session(VECTORS_CSV)

        pc.list_census_vectors("CA21", quiet=True, use_cache=False)

        cached = get_cached_data("vectors_CA21")
        assert cached["vector"].tolist() == ["v_CA21_1"]
        assert has_current_list_schema(cached)

    @patch("pycancensus.vectors.get_session")
    def test_cache_from_older_version_is_downloaded_again(self, get_session):
        cache_data("vectors_CA21", pd.DataFrame({"vector": ["stale"]}))
        get_session.return_value = mock_session(VECTORS_CSV)

        vectors = pc.list_census_vectors("CA21", quiet=True)

        assert vectors["vector"].tolist() == ["v_CA21_1"]


@pytest.mark.parametrize("level", ["CMA", "CA", "CMACA"])
def test_cma_ca_and_cmaca_are_valid_levels(level):
    assert validate_level(level) == level
    assert process_regions({level: "35562"}) == {level: "35562"}
