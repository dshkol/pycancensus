"""Fixes ported from R cancensus 0.6.2."""

from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

import pycancensus as pc
from pycancensus.core import _merge_geo_and_csv_results


def make_french_vector_list():
    return pd.DataFrame(
        {
            "vector": ["v_X_1", "v_X_2", "v_X_3"],
            "type": ["Total", "Total", "Total"],
            "label": ["Société", "Soci t", "Générale"],
            "details": [
                "Population; société générale",
                "Population; soci t",
                "Population; générale",
            ],
        }
    )


@pytest.fixture
def french_vectors():
    with patch("pycancensus.vectors.list_census_vectors") as mock:
        mock.return_value = make_french_vector_list()
        yield mock


class TestNonAsciiQueries:
    def test_keyword_search_keeps_accented_letters(self, french_vectors):
        result = pc.find_census_vectors("société", "CA21", query_type="keyword")
        assert result["vector"].tolist() == ["v_X_1"]

    def test_semantic_search_keeps_accented_letters(self, french_vectors):
        result = pc.find_census_vectors("société", "CA21", query_type="semantic")
        assert "v_X_1" in result["vector"].tolist()
        assert "v_X_2" not in result["vector"].tolist()


class TestKeywordSearchNonInteractive:
    def test_does_not_prompt_without_a_terminal(self, french_vectors, capsys):
        # "société générale" ranks v_X_1 (2 words) above v_X_3 (1 word)
        with patch("pycancensus.vectors._session_is_interactive", return_value=False):
            with patch("builtins.input", side_effect=AssertionError("prompted")):
                result = pc.find_census_vectors(
                    "société générale",
                    "CA21",
                    query_type="keyword",
                    interactive=True,
                )
        assert result["vector"].tolist() == ["v_X_1"]
        assert "1 additional keyword matches" in capsys.readouterr().out


def test_get_census_rejects_invalid_labels():
    with pytest.raises(ValueError, match="Invalid labels"):
        pc.get_census("CA21", regions={"CSD": "5915022"}, labels="labeled")


def test_vector_metadata_survives_geometry_merge():
    geo = gpd.GeoDataFrame(
        {"GeoUID": ["1", "2"], "Region Name": ["A", "B"]},
        geometry=[Point(0, 0), Point(1, 1)],
    )
    csv = pd.DataFrame({"GeoUID": ["1", "2"], "v_CA21_1": [10, 20]})
    meta = pd.DataFrame({"Vector": ["v_CA21_1"], "Detail": ["Population, 2021"]})
    csv.attrs["census_vectors"] = meta

    merged = _merge_geo_and_csv_results(geo, csv)

    pd.testing.assert_frame_equal(pc.label_vectors(merged), meta)


@pytest.mark.parametrize(
    "explore", [pc.explore_census_vectors, pc.explore_census_regions]
)
def test_explorers_open_the_api_page(explore):
    with patch("webbrowser.open") as browser_open:
        explore("CA21")
    browser_open.assert_called_once_with("https://censusmapper.ca/api")
