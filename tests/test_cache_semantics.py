"""Tests for get_census cache semantics and response validation."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from pycancensus.core import get_census, _process_csv_response

VALID_CSV = 'GeoUID,Type,"Region Name",Population\n' '5915022,CSD,"Vancouver",662248\n'


def make_response(text):
    response = MagicMock()
    response.text = text
    return response


class TestErrorBodyNotCached:
    @patch("pycancensus.core.cache_data")
    @patch("pycancensus.core.get_cached_data", return_value=None)
    @patch("pycancensus.core.get_session")
    @patch("pycancensus.core.get_api_key", return_value="test_key")
    def test_error_payload_raises_and_is_not_cached(
        self, mock_key, mock_get_session, mock_read, mock_write
    ):
        session = MagicMock()
        session.post.return_value = make_response('{"error": "no data found"}')
        mock_get_session.return_value = session

        with pytest.raises(RuntimeError, match="Invalid API response"):
            get_census("CA21", {"CSD": "5915022"}, quiet=True)

        mock_write.assert_not_called()

    @patch("pycancensus.core.cache_data")
    @patch("pycancensus.core.get_cached_data", return_value=None)
    @patch("pycancensus.core.get_session")
    @patch("pycancensus.core.get_api_key", return_value="test_key")
    def test_valid_response_is_cached(
        self, mock_key, mock_get_session, mock_read, mock_write
    ):
        session = MagicMock()
        session.post.return_value = make_response(VALID_CSV)
        mock_get_session.return_value = session

        result = get_census("CA21", {"CSD": "5915022"}, quiet=True)

        assert len(result) == 1
        mock_write.assert_called_once()


class TestUseCacheFalseRefreshesCache:
    @patch("pycancensus.core.cache_data")
    @patch("pycancensus.core.get_cached_data")
    @patch("pycancensus.core.get_session")
    @patch("pycancensus.core.get_api_key", return_value="test_key")
    def test_refresh_skips_read_but_still_writes(
        self, mock_key, mock_get_session, mock_read, mock_write
    ):
        session = MagicMock()
        session.post.return_value = make_response(VALID_CSV)
        mock_get_session.return_value = session

        get_census("CA21", {"CSD": "5915022"}, quiet=True, use_cache=False)

        mock_read.assert_not_called()  # stale data not read
        mock_write.assert_called_once()  # but the cache is refreshed


class TestCsvValidation:
    def test_html_error_page_rejected(self):
        with pytest.raises(ValueError, match="Invalid API response"):
            _process_csv_response("<html>Server Error</html>", None, "detailed")

    def test_valid_csv_accepted(self):
        result = _process_csv_response(VALID_CSV, None, "detailed")
        assert result["GeoUID"].tolist() == ["5915022"]
