"""Tests for the in-memory session cache layer."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import pycancensus.cache as cache_mod
from pycancensus.cache import (
    remove_from_cache,
    session_cache_get,
    session_cache_set,
)
from pycancensus.vectors import list_census_vectors


@pytest.fixture(autouse=True)
def clean_session_cache():
    cache_mod._session_cache.clear()
    yield
    cache_mod._session_cache.clear()


def make_vectors_df():
    return pd.DataFrame(
        {
            "vector": ["v_CA21_1", "v_CA21_2"],
            "label": ["Population", "Dwellings"],
            "type": ["Total", "Total"],
            "parent_vector": [None, None],
        }
    )


class TestSessionCachePrimitives:
    def test_get_returns_none_on_miss(self):
        assert session_cache_get("nope") is None

    def test_set_then_get_roundtrip(self):
        df = make_vectors_df()
        session_cache_set("key", df)
        result = session_cache_get("key")
        pd.testing.assert_frame_equal(result, df)

    def test_cached_value_immune_to_caller_mutation(self):
        df = make_vectors_df()
        session_cache_set("key", df)
        df.loc[0, "label"] = "CORRUPTED"

        assert session_cache_get("key")["label"].iloc[0] == "Population"

    def test_returned_value_immune_to_later_mutation(self):
        session_cache_set("key", make_vectors_df())
        first = session_cache_get("key")
        first.loc[0, "label"] = "CORRUPTED"

        assert session_cache_get("key")["label"].iloc[0] == "Population"

    def test_remove_from_cache_invalidates_keys(self):
        session_cache_set("vectors_CA21", make_vectors_df())
        with patch.object(cache_mod, "get_cache_path", return_value="/nonexistent"):
            remove_from_cache(["vectors_CA21"])
        assert session_cache_get("vectors_CA21") is None

    def test_remove_all_clears_session_cache(self):
        session_cache_set("a", 1)
        session_cache_set("b", 2)
        with patch.object(cache_mod, "get_cache_path", return_value="/nonexistent"):
            remove_from_cache(all_cache=True)
        assert session_cache_get("a") is None
        assert session_cache_get("b") is None


class TestListVectorsSessionCache:
    @patch("pycancensus.vectors.get_session")
    @patch("pycancensus.vectors.get_cached_data", return_value=None)
    @patch("pycancensus.vectors.cache_data")
    @patch("pycancensus.vectors.get_api_key", return_value="test_key")
    def test_second_call_skips_api_and_file_cache(
        self, mock_key, mock_cache_write, mock_file_cache, mock_get_session
    ):
        response = MagicMock()
        response.text = (
            "vector,type,label,units,add,parent,details\n"
            "v_CA21_1,Total,Population,Number,1,,Population\n"
        )
        session = MagicMock()
        session.get.return_value = response
        mock_get_session.return_value = session

        first = list_census_vectors("CA21", quiet=True)
        second = list_census_vectors("CA21", quiet=True)

        assert session.get.call_count == 1  # API hit only once
        assert mock_file_cache.call_count == 1  # file cache read only once
        pd.testing.assert_frame_equal(first, second)

    @patch("pycancensus.vectors.get_session")
    @patch("pycancensus.vectors.get_cached_data")
    @patch("pycancensus.vectors.get_api_key", return_value="test_key")
    def test_file_cache_hit_populates_session_cache(
        self, mock_key, mock_file_cache, mock_get_session
    ):
        mock_file_cache.return_value = make_vectors_df()

        list_census_vectors("CA21", quiet=True)
        list_census_vectors("CA21", quiet=True)

        assert mock_file_cache.call_count == 1
        mock_get_session.assert_not_called()

    @patch("pycancensus.vectors.get_session")
    @patch("pycancensus.vectors.get_cached_data", return_value=None)
    @patch("pycancensus.vectors.cache_data")
    @patch("pycancensus.vectors.get_api_key", return_value="test_key")
    def test_use_cache_false_bypasses_session_cache(
        self, mock_key, mock_cache_write, mock_file_cache, mock_get_session
    ):
        response = MagicMock()
        response.text = (
            "vector,type,label,units,add,parent,details\n"
            "v_CA21_1,Total,Population,Number,1,,Population\n"
        )
        session = MagicMock()
        session.get.return_value = response
        mock_get_session.return_value = session

        list_census_vectors("CA21", quiet=True, use_cache=False)
        list_census_vectors("CA21", quiet=True, use_cache=False)

        assert session.get.call_count == 2
