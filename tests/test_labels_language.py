"""French labels (language=) and labels="labelled", ported from R cancensus
0.6.2 (mountainMath/cancensus#229, #230).

Fixtures follow real CensusMapper responses: the CSV and GeoJSON carry the
generic parent identifiers rpid/rgid/ruid/rguid, and vector_info carries the
French labels in label_fr and details_fr.
"""

import json
import warnings
from unittest.mock import MagicMock, patch

import geopandas as gpd
import numpy as np
import pandas as pd
import pytest

import pycancensus as pc
from pycancensus import settings
from pycancensus.core import _census_year_for_dataset, _generate_cache_key

DATA_CSV = (
    "GeoUID,Type,Region Name,Area (sq km),Population ,Dwellings ,Households ,"
    'rpid,rgid,ruid,rguid,"v_CA21_1: Population, 2021",'
    '"v_CA21_434: Occupied private dwellings by structural type of dwelling"\n'
    "5915001,CSD,Langley (DM),307.2193,132603,49011,46928,5915,59,59933,,132603,46928\n"
    "5915022,CSD,Vancouver (CY),115.1756,662248,328347,305336,5915,59,59933,,662248,305336\n"
)


def _feature(**properties):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-123.1, 49.2]},
        "properties": properties,
    }


GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        _feature(
            a="307.2193",
            q="0",
            t="CSD",
            dw="49011",
            hh="46928",
            id="5915001",
            pop="132603",
            dw16="43720",
            hh16="41982",
            name="Langley (DM)",
            rgid="59",
            rpid="5915",
            ruid="59933",
            pop16="117285",
        ),
        _feature(
            a="115.1756",
            q="0",
            t="CSD",
            dw="328347",
            hh="305336",
            id="5915022",
            pop="662248",
            dw16="309418",
            hh16="283916",
            name="Vancouver (CY)",
            rgid="59",
            rpid="5915",
            ruid="59933",
            pop16="631486",
        ),
    ],
}

REGIONS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        _feature(
            a="2878.9307",
            t="CMA",
            dw="1104532",
            hh="1043319",
            id="59933",
            pop="2642825",
            name="Vancouver (B)",
            ruid="59",
            rguid="01",
        ),
        _feature(
            a="115.1756",
            q="0",
            t="CSD",
            dw="328347",
            hh="305336",
            id="5915022",
            pop="662248",
            name="Vancouver (CY)",
            rgid="59",
            rpid="5915",
            ruid="59933",
        ),
    ],
}

VECTOR_INFO = pd.DataFrame(
    {
        "vector": ["v_CA21_1", "v_CA21_434", "v_CA21_435"],
        "label": [
            "Population, 2021",
            "Occupied private dwellings by structural type of dwelling",
            "Single-detached house",
        ],
        "type": ["Total", "Total", "Total"],
        "units": ["1", "1", "1"],
        "aggregation": ["1", "1", "1"],
        "parent_vector": [None, None, "v_CA21_434"],
        "details": [
            "CA 2021 Census; Population and Dwellings; Population, 2021",
            "CA 2021 Census; 100% data; Dwellings; Occupied private dwellings",
            "CA 2021 Census; 100% data; Dwellings; Single-detached house",
        ],
        "label_fr": [
            "Population, 2021",
            "Logements privés occupés par type de construction résidentielle",
            "Maison individuelle non attenante",
        ],
        "details_fr": [
            "Recensement CA 2021; Population et logements; Population, 2021",
            "Recensement CA 2021; Données intégrales (100 %); Logements; "
            "Logements privés occupés",
            "Recensement CA 2021; Données intégrales (100 %); Logements; "
            "Maison individuelle non attenante",
        ],
        "short_fr": ["Pop", "Logements", "Maison"],
    }
)

VECTORS = ["v_CA21_1", "v_CA21_434"]


def _response(text=None, payload=None):
    response = MagicMock()
    response.headers = {"data-version": "1"}
    if text is not None:
        response.text = text
        response.content = text.encode("utf-8")
    if payload is not None:
        response.json.return_value = payload
    return response


@pytest.fixture
def api():
    """Mock the CensusMapper endpoints get_census() and the vector list use."""
    session = MagicMock()

    def post(url, files=None):
        if url.endswith("geo.geojson"):
            regions = json.loads(files["regions"][1])
            if "CMA" in regions:
                return _response(payload=REGIONS_GEOJSON)
            return _response(payload=GEOJSON)
        return _response(text=DATA_CSV)

    session.post.side_effect = post
    with patch("pycancensus.core.get_session", return_value=session), patch(
        "pycancensus.core.get_api_key", return_value="test_key"
    ), patch(
        "pycancensus.vectors._fetch_census_vectors",
        side_effect=lambda *a, **k: VECTOR_INFO.copy(),
    ):
        yield session


def get_census(**kwargs):
    args = dict(dataset="CA21", regions={"CD": "5915"}, level="CSD", vectors=VECTORS)
    args.update(kwargs)
    args.setdefault("quiet", True)
    return pc.get_census(**args)


class TestSettings:
    def test_language_defaults_to_english(self):
        assert pc.get_language() == "en"

    def test_set_language(self):
        pc.set_language("FR")
        assert pc.get_language() == "fr"
        pc.set_language(None)
        assert pc.get_language() == "en"

    def test_language_from_environment(self, monkeypatch):
        monkeypatch.setenv("PYCANCENSUS_LANGUAGE", "fr")
        assert pc.get_language() == "fr"
        pc.set_language("en")
        assert pc.get_language() == "en"

    def test_invalid_language(self):
        with pytest.raises(ValueError, match="Language must be one of en, fr"):
            pc.set_language("de")

    def test_labels_default_unset(self):
        assert pc.get_labels() is None

    def test_set_labels(self, monkeypatch):
        pc.set_labels("labelled")
        assert pc.get_labels() == "labelled"
        pc.set_labels(None)
        monkeypatch.setenv("PYCANCENSUS_LABELS", "short")
        assert pc.get_labels() == "short"

    def test_invalid_labels(self):
        with pytest.raises(ValueError, match="Invalid labels"):
            pc.set_labels("labeled")


class TestLabelled:
    def test_data_columns(self, api):
        result = get_census(labels="labelled")

        # Same names, order and labels as R cancensus 0.6.2
        assert list(result.columns) == [
            "GeoUID",
            "Type",
            "Name",
            "Area",
            "Population",
            "Dwellings",
            "Households",
            "PR_UID",
            "CD_UID",
            "CMA_UID",
            "v_CA21_1",
            "v_CA21_434",
        ]
        labels = result.attrs["column_labels"]
        assert labels["GeoUID"] == "Geographic identifier"
        assert labels["Name"] == "Region name"
        assert labels["Population"] == "Population 2021"
        assert labels["CMA_UID"] == (
            "Census metropolitan area or census agglomeration identifier"
        )
        assert labels["v_CA21_1"] == "Population, 2021"
        assert labels["v_CA21_434"] == (
            "Occupied private dwellings by structural type of dwelling"
        )

    def test_data_types(self, api):
        result = get_census(labels="labelled")

        assert result["Name"].tolist() == ["Langley (DM)", "Vancouver (CY)"]
        assert not isinstance(result["Name"].dtype, pd.CategoricalDtype)
        assert isinstance(result["Type"].dtype, pd.CategoricalDtype)
        assert result["CD_UID"].tolist() == ["5915", "5915"]
        assert result["PR_UID"].tolist() == ["59", "59"]
        assert result["CMA_UID"].tolist() == ["59933", "59933"]
        assert result["GeoUID"].tolist() == ["5915001", "5915022"]
        for column in ("Area", "Population", "Dwellings", "Households"):
            assert pd.api.types.is_numeric_dtype(result[column])

    def test_geometry_has_same_columns_as_data(self, api):
        data = get_census(labels="labelled")
        geo = get_census(labels="labelled", geo_format="geopandas")

        assert isinstance(geo, gpd.GeoDataFrame)
        assert list(geo.columns) == [
            "GeoUID",
            "Type",
            "Name",
            "Area",
            "Population",
            "Dwellings",
            "Households",
            "Population_Previous",
            "Dwellings_Previous",
            "Households_Previous",
            "Quality",
            "PR_UID",
            "CD_UID",
            "CMA_UID",
            "v_CA21_1",
            "v_CA21_434",
            "geometry",
        ]
        shared = [c for c in data.columns]
        pd.testing.assert_frame_equal(
            pd.DataFrame(geo[shared]).reset_index(drop=True),
            data.reset_index(drop=True),
            check_dtype=False,
            check_categorical=False,
        )
        assert geo.attrs["column_labels"]["Population_Previous"] == "Population 2016"
        assert geo.attrs["column_labels"]["Quality"] == "Data quality flags"
        assert pd.api.types.is_numeric_dtype(geo["Population_Previous"])

    def test_regions_of_different_levels(self, api):
        result = get_census(
            regions={"CSD": "5915022", "CMA": "59933"},
            level="Regions",
            vectors=None,
            labels="labelled",
            geo_format="geopandas",
        )

        assert [c for c in result.columns if c.endswith("_UID")] == [
            "C_UID",
            "PR_UID",
            "CD_UID",
            "CMA_UID",
        ]
        cma = result[result["GeoUID"] == "59933"].iloc[0]
        csd = result[result["GeoUID"] == "5915022"].iloc[0]
        assert csd["CD_UID"] == "5915"
        assert csd["PR_UID"] == "59"
        assert csd["CMA_UID"] == "59933"
        assert pd.isna(cma["CD_UID"])
        assert not any(c in result.columns for c in ("rpid", "rgid", "ruid"))

    def test_french_labels(self, api):
        result = get_census(labels="labelled", language="fr")

        labels = result.attrs["column_labels"]
        assert labels["Name"] == "Nom de la région"
        assert labels["Area"] == "Superficie (km²)"
        assert labels["Dwellings"] == "Logements 2021"
        assert labels["v_CA21_434"] == (
            "Logements privés occupés par type de construction résidentielle"
        )
        # Column names don't depend on the language
        assert list(result.columns) == list(get_census(labels="labelled").columns)

    def test_label_vectors(self, api):
        result = get_census(labels="labelled", language="fr")

        details = pc.label_vectors(result)
        assert details["Vector"].tolist() == VECTORS
        assert details["Detail"].tolist()[1].startswith("Logements privés")

    @pytest.mark.parametrize(
        "dataset, year", [("CA21", 2021), ("CA06", 2006), ("CA1996", 1996)]
    )
    def test_census_year(self, dataset, year):
        assert _census_year_for_dataset(dataset) == year

    def test_year_of_derived_dataset(self):
        # Tax and cross-tabulation datasets use the year of their geography
        datasets = pd.DataFrame(
            {"dataset": ["TX2018"], "geo_dataset": ["CA16"], "attribution": [""]}
        )
        with patch("pycancensus.datasets.list_census_datasets", return_value=datasets):
            assert _census_year_for_dataset("TX2018") == 2016

    def test_unknown_year_leaves_it_out(self, api):
        with patch("pycancensus.core._census_year_for_dataset", return_value=None):
            result = get_census(vectors=None, labels="labelled")

        assert result.attrs["column_labels"]["Population"] == "Population"
        assert result.attrs["column_labels"]["Dwellings"] == "Dwellings"

    def test_detailed_and_short_unchanged(self, api):
        detailed = get_census(labels="detailed")
        short = get_census(labels="short")

        assert "Region Name" in detailed.columns
        assert "v_CA21_1: Population, 2021" in detailed.columns
        assert "Region Name" in short.columns
        assert "v_CA21_1" in short.columns
        assert "column_labels" not in short.attrs


class TestLanguage:
    def test_detailed_column_names_in_french(self, api):
        result = get_census(language="fr", labels="detailed")

        assert "v_CA21_1: Population, 2021" in result.columns
        assert (
            "v_CA21_434: Logements privés occupés par type de construction "
            "résidentielle"
        ) in result.columns
        # Region names and other columns stay as they are
        assert "Region Name" in result.columns

    def test_short_labels_in_french(self, api):
        result = get_census(language="fr", labels="short")

        assert list(result.columns[-2:]) == VECTORS
        assert result.attrs["census_vectors"][1]["Detail"].startswith("Logements")

    def test_session_default(self, api):
        pc.set_language("fr")
        result = get_census(labels="short")

        assert result.attrs["census_vectors"][1]["Detail"].startswith("Logements")

    def test_invalid_language(self, api):
        with pytest.raises(ValueError, match="Language must be one of"):
            get_census(language="es")

    def test_switching_language_or_labels_does_not_download_again(self, api):
        english = get_census(labels="detailed")
        assert api.post.call_count == 1

        french = get_census(labels="detailed", language="fr")
        labelled = get_census(labels="labelled", language="fr")

        assert api.post.call_count == 1
        assert list(french.columns) != list(english.columns)
        assert "Name" in labelled.columns

    def test_cache_key_ignores_labels_and_language(self):
        key = _generate_cache_key(
            "CA21", {"CD": ["5915"]}, VECTORS, "CSD", None, "simplified"
        )
        assert len(key) == 64

    def test_fallback_to_english_warns_once_per_dataset(self, api):
        untranslated = VECTOR_INFO.assign(label_fr=np.nan, details_fr=np.nan)
        with patch(
            "pycancensus.vectors._fetch_census_vectors",
            side_effect=lambda *a, **k: untranslated.copy(),
        ):
            with pytest.warns(UserWarning, match="not available for dataset CA21"):
                result = get_census(language="fr", quiet=False)
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                get_census(language="fr")

        assert "v_CA21_1: Population, 2021" in result.columns

    def test_label_lookup_failure_keeps_english(self, api):
        with patch(
            "pycancensus.vectors._fetch_census_vectors",
            side_effect=RuntimeError("offline"),
        ):
            with pytest.warns(UserWarning, match="Could not retrieve French labels"):
                result = get_census(language="fr", quiet=False, labels="detailed")

        assert (
            "v_CA21_434: Occupied private dwellings by structural type of dwelling"
        ) in result.columns


class TestLabelsDefaultNotice:
    def test_notice_once_per_session(self, api, capsys):
        get_census(quiet=False)
        assert "planned to change" in capsys.readouterr().err
        get_census(quiet=False)
        assert "planned to change" not in capsys.readouterr().err

    def test_no_notice_when_labels_given_or_quiet(self, api, capsys):
        get_census(quiet=False, labels="detailed")
        get_census(quiet=True)
        assert "planned to change" not in capsys.readouterr().err

    def test_session_default_is_used_without_notice(self, api, capsys):
        pc.set_labels("labelled")
        result = get_census(quiet=False)

        assert "planned to change" not in capsys.readouterr().err
        assert "Name" in result.columns

    def test_invalid_labels(self, api):
        with pytest.raises(ValueError, match="Invalid labels"):
            get_census(labels="labeled")


@pytest.fixture
def vector_list():
    with patch("pycancensus.vectors.get_api_key", return_value="test_key"), patch(
        "pycancensus.vectors._fetch_census_vectors",
        side_effect=lambda *a, **k: VECTOR_INFO.copy(),
    ) as fetch:
        yield fetch


class TestVectorFunctions:
    def test_list_census_vectors_in_french(self, vector_list):
        english = pc.list_census_vectors("CA21")
        french = pc.list_census_vectors("CA21", language="fr")

        assert list(french.columns) == list(english.columns)
        assert "label_fr" not in french.columns
        assert "details_fr" not in french.columns
        assert french["label"].iloc[2] == "Maison individuelle non attenante"
        assert french["details"].iloc[0].startswith("Recensement CA 2021")
        assert english["label"].iloc[2] == "Single-detached house"
        assert french.attrs["language"] == "fr"
        # One download serves both languages
        assert vector_list.call_count == 2

    def test_partial_translation_falls_back(self, vector_list):
        partial = VECTOR_INFO.copy()
        partial.loc[2, "label_fr"] = ""
        vector_list.side_effect = lambda *a, **k: partial.copy()

        with pytest.warns(UserWarning, match="1 of 3 vectors in dataset CA21"):
            french = pc.list_census_vectors("CA21", language="fr")
        assert french["label"].iloc[2] == "Single-detached house"

        # Once per session and dataset, regardless of quiet
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            pc.list_census_vectors("CA21", language="fr")

    def test_find_census_vectors_in_french(self, vector_list):
        result = pc.find_census_vectors(
            "maison individuelle", "CA21", query_type="exact", language="fr"
        )

        assert result["vector"].tolist() == ["v_CA21_435"]
        # The French census prefix is stripped from details, like R
        assert (
            result["details"].iloc[0] == "Logements; Maison individuelle non attenante"
        )

    def test_child_vectors_keep_language_of_input(self, vector_list):
        parent = pc.list_census_vectors("CA21", language="fr")
        parent = parent[parent["vector"] == "v_CA21_434"]

        children = pc.child_census_vectors(parent)

        assert children["label"].tolist() == ["Maison individuelle non attenante"]
        assert children.attrs["language"] == "fr"

    def test_parent_vectors_explicit_language(self, vector_list):
        parents = pc.parent_census_vectors("v_CA21_435", language="fr")

        assert parents["label"].tolist() == [
            "Logements privés occupés par type de construction résidentielle"
        ]

    def test_visualize_in_french(self, vector_list, capsys):
        pc.visualize_vector_hierarchy("v_CA21_434", language="fr", quiet=True)

        assert "Maison individuelle non attenante" in capsys.readouterr().out


def test_dataset_attribution_in_french():
    datasets = pd.DataFrame(
        {
            "dataset": ["CA16", "CA21", "TX2018"],
            "attribution": [
                "StatCan 2016 Census",
                "StatCan 2021 Census",
                "StatCan T1FF 2018",
            ],
            "attribution_fr": [
                "StatCan, Recensement de 2016",
                "StatCan, Recensement de 2021",
                None,
            ],
        }
    )
    with patch("pycancensus.datasets.list_census_datasets", return_value=datasets):
        assert pc.dataset_attribution(["CA16", "CA21"], language="fr") == [
            "StatCan, Recensement de 2016, 2021"
        ]
        assert pc.dataset_attribution(["TX2018"], language="fr") == [
            "StatCan T1FF 2018"
        ]
        assert pc.dataset_attribution(["CA16"]) == ["StatCan 2016 Census"]
