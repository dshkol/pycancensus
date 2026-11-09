"""Named vectors in get_census(), mirroring R's c(pop = "v_CA21_1")."""

from unittest.mock import patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

import pycancensus as pc
from pycancensus.core import _split_named_vectors

DETAILED = pd.DataFrame(
    {
        "GeoUID": ["5915022"],
        "Type": ["CSD"],
        "Region Name": ["Vancouver (CY)"],
        "Area (sq km)": [115.0],
        "Population": [662248.0],
        "Dwellings": [328347.0],
        "Households": [305336.0],
        "v_CA21_1: Population, 2021": [662248.0],
        "v_CA21_2: Population, 2016": [631486.0],
    }
)


@pytest.fixture
def cached_data():
    """Serve DETAILED from the cache so no request is made."""
    with patch("pycancensus.core.get_cached_data", return_value=DETAILED.copy()):
        with patch("pycancensus.recalls.check_recalled_data_and_warn"):
            yield


def census(vectors, labels):
    return pc.get_census(
        "CA21",
        regions={"CSD": "5915022"},
        vectors=vectors,
        labels=labels,
        quiet=True,
        api_key="test",
    )


class TestSplitNamedVectors:
    def test_list_has_no_names(self):
        assert _split_named_vectors(["v_CA21_1"]) == (["v_CA21_1"], {})

    def test_dict_names_and_unnamed(self):
        codes, names = _split_named_vectors(
            {"pop": "v_CA21_1", "v_CA21_2": "v_CA21_2", "": "v_CA21_3"}
        )
        assert codes == ["v_CA21_1", "v_CA21_2", "v_CA21_3"]
        assert names == {"v_CA21_1": "pop"}

    def test_vector_named_twice_is_an_error(self):
        with pytest.raises(ValueError, match="more than once"):
            _split_named_vectors({"a": "v_CA21_1", "b": "v_CA21_1"})

    def test_non_string_vector_is_an_error(self):
        with pytest.raises(ValueError):
            _split_named_vectors({"a": 1})


@pytest.mark.usefixtures("cached_data")
class TestNamedVectors:
    def test_detailed_names_vectors_by_code_when_any_is_named(self):
        result = census({"pop": "v_CA21_1", "v_CA21_2": "v_CA21_2"}, "detailed")
        assert list(result.columns)[-2:] == ["pop", "v_CA21_2"]

    def test_metadata_keeps_vector_codes(self):
        result = census({"pop": "v_CA21_1"}, "short")
        assert pc.label_vectors(result)["Vector"].tolist() == [
            "v_CA21_1",
            "v_CA21_2",
        ]

    def test_cache_key_ignores_names(self):
        with patch("pycancensus.core._generate_cache_key", return_value="k") as key:
            census({"pop": "v_CA21_1"}, "short")
            census(["v_CA21_1"], "short")
        assert key.call_args_list[0] == key.call_args_list[1]

    def test_labelled_named_column_keeps_its_label(self):
        result = census({"pop": "v_CA21_1"}, "labelled")
        assert result.attrs["column_labels"]["pop"] == "Population, 2021"
        assert "v_CA21_1" not in result.attrs["column_labels"]

    def test_labelled_clash_gets_trailing_underscore(self):
        result = census({"Population": "v_CA21_1"}, "labelled")
        assert "Population_" in result.columns
        assert result["Population"].iloc[0] == 662248.0
        labels = result.attrs["column_labels"]
        assert labels["Population"] == "Population, 2021"
        assert labels["Population_"] == "Population 2021"

    def test_labelled_clash_with_taken_underscore_name_is_an_error(self):
        with pytest.raises(ValueError, match="Population_"):
            census({"Population": "v_CA21_1", "Population_": "v_CA21_2"}, "labelled")

    @pytest.mark.parametrize("labels", ["detailed", "short"])
    def test_clash_outside_labelled_is_an_error(self, labels):
        with pytest.raises(ValueError, match="clash"):
            census({"Population": "v_CA21_1"}, labels)

    def test_names_can_swap_with_renamed_vector_codes(self):
        result = census({"v_CA21_2": "v_CA21_1", "two": "v_CA21_2"}, "labelled")
        assert result["v_CA21_2"].iloc[0] == 662248.0
        assert result["two"].iloc[0] == 631486.0

    def test_name_clashing_with_an_unrenamed_vector_is_an_error(self):
        with pytest.raises(ValueError, match="clash"):
            census({"v_CA21_2": "v_CA21_1"}, "labelled")


def test_quiet_suppresses_progress_output(capsys):
    with patch("pycancensus.core.get_cached_data", return_value=None):
        with patch("pycancensus.core._download_census", return_value=DETAILED.copy()):
            census(["v_CA21_1"], "detailed")
    assert capsys.readouterr().out == ""
