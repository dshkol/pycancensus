"""Tests for recalled-data detection."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import pycancensus.cache as cache_mod
import pycancensus.recalls as recalls_mod
from pycancensus.recalls import (
    check_recalled_data_and_warn,
    get_recalled_database,
    list_recalled_cached_data,
)

RECALL_CSV = (
    "api_version,dataset,level,vector\n"
    "d.2,CA21,,v_CA21_1\n"
    "d.2,CA21,,v_CA21_983\n"
    "g.1,CA21,,\n"
    "d.5,CA16,CSD,v_CA16_401\n"
)


def make_recall_db():
    import io

    return pd.read_csv(io.StringIO(RECALL_CSV), dtype=str)


def make_cache_listing(rows):
    base = {
        "cache_key": "k",
        "file_path": "/tmp/k.pkl",
        "size_mb": 0.5,
        "created": pd.Timestamp("2026-01-01"),
        "modified": pd.Timestamp("2026-01-01"),
        "dataset": None,
        "level": None,
        "vectors": None,
        "version": None,
        "geo_version": None,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


@pytest.fixture(autouse=True)
def clean_state():
    cache_mod._session_cache.clear()
    recalls_mod._warned_this_session = False
    yield
    cache_mod._session_cache.clear()
    recalls_mod._warned_this_session = False


@pytest.fixture
def mock_recall_db():
    with patch.object(recalls_mod, "get_recalled_database") as mock:
        mock.return_value = make_recall_db()
        yield mock


class TestGetRecalledDatabase:
    @patch("pycancensus.recalls.get_session")
    def test_downloads_and_session_caches(self, mock_get_session):
        response = MagicMock()
        response.text = RECALL_CSV
        session = MagicMock()
        session.get.return_value = response
        mock_get_session.return_value = session

        first = get_recalled_database()
        second = get_recalled_database()

        assert session.get.call_count == 1  # second call served from memory
        assert list(first.columns) == ["api_version", "dataset", "level", "vector"]
        pd.testing.assert_frame_equal(first, second)

    @patch("pycancensus.recalls.get_session")
    def test_download_failure_warns_and_returns_none(self, mock_get_session):
        mock_get_session.return_value.get.side_effect = ConnectionError("down")
        with pytest.warns(UserWarning, match="Unable to download"):
            assert get_recalled_database() is None


class TestListRecalledCachedData:
    def test_exact_vector_match_flagged(self, mock_recall_db):
        listing = make_cache_listing(
            [
                {
                    "cache_key": "hit",
                    "dataset": "CA21",
                    "level": "CSD",
                    "vectors": ["v_CA21_983"],
                    "version": "d.1",
                }
            ]
        )
        result = list_recalled_cached_data(listing)
        assert result["cache_key"].tolist() == ["hit"]

    def test_recall_does_not_overmatch_vector_prefix(self, mock_recall_db):
        # Recall of v_CA21_1 must NOT flag v_CA21_10 (R 0.6.1 fix)
        listing = make_cache_listing(
            [
                {
                    "cache_key": "prefix",
                    "dataset": "CA21",
                    "level": "CSD",
                    "vectors": ["v_CA21_10"],
                    "version": "d.1",
                }
            ]
        )
        assert list_recalled_cached_data(listing).empty

    def test_newer_data_not_flagged(self, mock_recall_db):
        # Data downloaded after the recall (version d.3 > recall d.2) is fixed
        listing = make_cache_listing(
            [
                {
                    "cache_key": "fresh",
                    "dataset": "CA21",
                    "level": "CSD",
                    "vectors": ["v_CA21_983"],
                    "version": "d.3",
                }
            ]
        )
        assert list_recalled_cached_data(listing).empty

    def test_geometry_recall_flagged(self, mock_recall_db):
        listing = make_cache_listing(
            [
                {
                    "cache_key": "geo",
                    "dataset": "CA21",
                    "level": "CT",
                    "vectors": [],
                    "geo_version": "g.1",
                }
            ]
        )
        assert list_recalled_cached_data(listing)["cache_key"].tolist() == ["geo"]

    def test_level_specific_recall(self, mock_recall_db):
        listing = make_cache_listing(
            [
                {
                    "cache_key": "right-level",
                    "dataset": "CA16",
                    "level": "CSD",
                    "vectors": ["v_CA16_401"],
                    "version": "d.4",
                },
                {
                    "cache_key": "other-level",
                    "dataset": "CA16",
                    "level": "CT",
                    "vectors": ["v_CA16_401"],
                    "version": "d.4",
                },
            ]
        )
        result = list_recalled_cached_data(listing)
        assert result["cache_key"].tolist() == ["right-level"]

    def test_entries_without_metadata_skipped(self, mock_recall_db):
        listing = make_cache_listing([{"cache_key": "legacy"}])
        assert list_recalled_cached_data(listing).empty

    def test_returns_none_when_db_unavailable(self):
        with patch.object(recalls_mod, "get_recalled_database", return_value=None):
            assert list_recalled_cached_data(make_cache_listing([])) is None


class TestWarnOnCacheRead:
    def test_warns_once_per_session(self, mock_recall_db):
        listing = make_cache_listing(
            [
                {
                    "cache_key": "hit",
                    "dataset": "CA21",
                    "level": "CSD",
                    "vectors": ["v_CA21_983"],
                    "version": "d.1",
                }
            ]
        )
        with patch.object(recalls_mod, "list_cache", return_value=listing):
            with pytest.warns(UserWarning, match="has been recalled"):
                check_recalled_data_and_warn("hit")
            # Second read: no warning (once per session)
            check_recalled_data_and_warn("hit")

    def test_no_warning_for_clean_entry(self, mock_recall_db):
        listing = make_cache_listing(
            [
                {
                    "cache_key": "clean",
                    "dataset": "CA21",
                    "level": "CSD",
                    "vectors": ["v_CA21_2"],
                    "version": "d.9",
                }
            ]
        )
        with patch.object(recalls_mod, "list_cache", return_value=listing):
            check_recalled_data_and_warn("clean")
        assert recalls_mod._warned_this_session is False
