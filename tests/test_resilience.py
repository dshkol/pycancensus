"""Tests for retry and error handling in pycancensus.resilience."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from pycancensus.resilience import (
    AuthenticationError,
    CensusAPIError,
    DataNotFoundError,
    RateLimitError,
    ResilientSession,
)


def make_response(status_code, headers=None):
    """Build a mock requests.Response with the given status."""
    response = MagicMock(spec=requests.Response)
    response.status_code = status_code
    response.ok = status_code < 400
    response.headers = headers or {}
    return response


def make_session(**kwargs):
    """Build a ResilientSession with rate-limit pacing disabled."""
    session = ResilientSession(**kwargs)
    session._min_request_interval = 0
    return session


class TestRetryableStatuses:
    """Transient statuses (5xx, 408, 429) are retried; permanent ones are not."""

    @pytest.mark.parametrize("status", [408, 429, 500, 502, 503, 504])
    @patch("pycancensus.resilience.time.sleep")
    def test_transient_status_retried_until_success(self, mock_sleep, status):
        session = make_session(max_retries=3)
        responses = [make_response(status), make_response(200)]
        session.session.request = MagicMock(side_effect=responses)

        result = session.request("GET", "https://example.com")

        assert result.status_code == 200
        assert session.session.request.call_count == 2

    @pytest.mark.parametrize("status", [429, 503])
    @patch("pycancensus.resilience.time.sleep")
    def test_transient_status_raises_after_exhausting_retries(self, mock_sleep, status):
        session = make_session(max_retries=2)
        session.session.request = MagicMock(return_value=make_response(status))

        with pytest.raises(CensusAPIError):
            session.request("GET", "https://example.com")

        assert session.session.request.call_count == 3  # initial + 2 retries

    @pytest.mark.parametrize(
        "status,exception",
        [(401, AuthenticationError), (404, DataNotFoundError)],
    )
    @patch("pycancensus.resilience.time.sleep")
    def test_permanent_status_not_retried(self, mock_sleep, status, exception):
        session = make_session(max_retries=3)
        session.session.request = MagicMock(return_value=make_response(status))

        with pytest.raises(exception):
            session.request("GET", "https://example.com")

        assert session.session.request.call_count == 1
        mock_sleep.assert_not_called()

    @patch("pycancensus.resilience.time.sleep")
    def test_network_error_retried(self, mock_sleep):
        session = make_session(max_retries=3)
        session.session.request = MagicMock(
            side_effect=[
                requests.exceptions.ConnectionError("boom"),
                make_response(200),
            ]
        )

        result = session.request("GET", "https://example.com")

        assert result.status_code == 200
        assert session.session.request.call_count == 2

    @patch("pycancensus.resilience.time.sleep")
    def test_network_error_raises_after_exhausting_retries(self, mock_sleep):
        session = make_session(max_retries=2)
        session.session.request = MagicMock(
            side_effect=requests.exceptions.ConnectionError("boom")
        )

        with pytest.raises(requests.exceptions.ConnectionError):
            session.request("GET", "https://example.com")

        assert session.session.request.call_count == 3


class TestRetryAfter:
    """Numeric Retry-After headers extend the backoff wait, capped at 60s."""

    @patch("pycancensus.resilience.time.sleep")
    def test_retry_after_extends_wait(self, mock_sleep):
        session = make_session(max_retries=1)
        responses = [
            make_response(429, headers={"Retry-After": "42"}),
            make_response(200),
        ]
        session.session.request = MagicMock(side_effect=responses)

        session.request("GET", "https://example.com")

        (waited,) = mock_sleep.call_args[0]
        assert waited >= 42

    @patch("pycancensus.resilience.time.sleep")
    def test_retry_after_capped_at_60s(self, mock_sleep):
        session = make_session(max_retries=1)
        responses = [
            make_response(429, headers={"Retry-After": "600"}),
            make_response(200),
        ]
        session.session.request = MagicMock(side_effect=responses)

        session.request("GET", "https://example.com")

        (waited,) = mock_sleep.call_args[0]
        assert waited <= 60

    @patch("pycancensus.resilience.time.sleep")
    def test_http_date_retry_after_ignored(self, mock_sleep):
        session = make_session(max_retries=1)
        responses = [
            make_response(
                429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}
            ),
            make_response(200),
        ]
        session.session.request = MagicMock(side_effect=responses)

        result = session.request("GET", "https://example.com")

        assert result.status_code == 200

    def test_rate_limit_error_carries_retry_after(self):
        session = make_session(max_retries=0)
        session.session.request = MagicMock(
            return_value=make_response(429, headers={"Retry-After": "17"})
        )

        with pytest.raises(RateLimitError) as excinfo:
            session.request("GET", "https://example.com")

        assert excinfo.value.retry_after == 17
