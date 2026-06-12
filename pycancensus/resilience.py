"""Production-grade resilience features for pycancensus API calls."""

import atexit
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class CensusAPIError(Exception):
    """Custom exception for Census API errors with helpful context."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        suggestion: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.suggestion = suggestion
        self.retry_after = retry_after

    def __str__(self):
        msg = super().__str__()
        if self.suggestion:
            msg += f"\n💡 Suggestion: {self.suggestion}"
        if self.retry_after:
            msg += f"\n⏱️  Retry after: {self.retry_after} seconds"
        return msg


class RateLimitError(CensusAPIError):
    """Raised when API rate limit is exceeded."""

    pass


class AuthenticationError(CensusAPIError):
    """Raised when API key is invalid or missing."""

    def __init__(self):
        super().__init__(
            "Invalid or missing API key",
            status_code=401,
            suggestion="Get a free API key at https://censusmapper.ca/users/sign_up",
        )


class DataNotFoundError(CensusAPIError):
    """Raised when requested data is not available."""

    def __init__(self, details: str = ""):
        super().__init__(
            f"Requested data not found{': ' + details if details else ''}",
            status_code=404,
            suggestion="Check your region and vector specifications",
        )


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
):
    """
    Decorator for retrying functions with exponential backoff.

    Parameters
    ----------
    max_retries : int
        Maximum number of retry attempts
    base_delay : float
        Base delay in seconds before first retry
    max_delay : float
        Maximum delay between retries
    exponential_base : float
        Base for exponential backoff calculation
    jitter : bool
        Whether to add random jitter to delays
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)

                except (
                    requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout,
                    requests.exceptions.RequestException,
                ) as e:
                    last_exception = e

                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (exponential_base**attempt), max_delay)

                        # Add jitter to prevent thundering herd
                        if jitter:
                            delay = delay * (0.5 + random.random() * 0.5)

                        logger.warning(
                            f"Request failed (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay:.1f}s: {e}"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed")

                except Exception as e:
                    # Don't retry for non-network errors
                    raise e

            raise last_exception

        return wrapper

    return decorator


class ResilientSession:
    """
    Resilient HTTP session with connection pooling, retry logic, and rate limit handling.
    """

    def __init__(
        self,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        max_retries: int = 3,
        retry_on_status: tuple = (408, 429),
        respect_retry_after: bool = True,
    ):
        """
        Initialize resilient session.

        Parameters
        ----------
        pool_connections : int
            Number of connection pools to cache
        pool_maxsize : int
            Maximum number of connections to save in the pool
        max_retries : int
            Number of retries for failed requests
        retry_on_status : tuple
            HTTP status codes to retry on, in addition to all 5xx responses
            (which are always treated as transient)
        respect_retry_after : bool
            Whether to respect Retry-After headers
        """
        self.session = requests.Session()

        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=0,  # We handle retries manually for better control
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.max_retries = max_retries
        self.retry_on_status = retry_on_status
        self.respect_retry_after = respect_retry_after

        # Rate limiting state
        self._last_request_time = 0
        self._min_request_interval = 0.1  # Minimum 100ms between requests

    def _enforce_rate_limit(self):
        """Enforce minimum interval between requests."""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self._min_request_interval:
            sleep_time = self._min_request_interval - time_since_last
            time.sleep(sleep_time)

        self._last_request_time = time.time()

    def _is_retryable_status(self, status_code: int) -> bool:
        """Check if a status code represents a transient, retryable error."""
        return 500 <= status_code < 600 or status_code in self.retry_on_status

    def _retry_after_seconds(self, response: requests.Response) -> Optional[int]:
        """Parse a numeric Retry-After header, if present and respected."""
        if not self.respect_retry_after:
            return None
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return None
        try:
            seconds = int(float(retry_after))
        except ValueError:
            # Retry-After might be an HTTP date instead of seconds
            return None
        return seconds if seconds > 0 else None

    def _backoff_delay(self, attempt: int) -> float:
        """Exponential backoff (1, 2, 4, ... seconds) with jitter, capped at 60s."""
        delay = min(2.0**attempt, 60.0)
        return delay * (0.5 + random.random() * 0.5)

    def _create_appropriate_exception(
        self, response: requests.Response
    ) -> CensusAPIError:
        """Create appropriate exception based on response status."""
        if response.status_code == 401:
            return AuthenticationError()
        elif response.status_code == 404:
            return DataNotFoundError("API endpoint or data not found")
        elif response.status_code == 429:
            return RateLimitError(
                "Rate limit exceeded",
                status_code=429,
                retry_after=self._retry_after_seconds(response),
                suggestion="Reduce request frequency or contact API provider",
            )
        elif response.status_code >= 500:
            return CensusAPIError(
                f"Server error: {response.status_code}",
                status_code=response.status_code,
                suggestion="Try again later or contact API provider",
            )
        else:
            return CensusAPIError(
                f"HTTP error: {response.status_code}", status_code=response.status_code
            )

    def request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Make a resilient HTTP request with automatic retries.

        Transient failures (network errors, 5xx responses, and the status
        codes in ``retry_on_status`` — by default 408 and 429) are retried
        with exponential backoff. A numeric Retry-After header extends the
        wait, capped at 60 seconds.

        Parameters
        ----------
        method : str
            HTTP method (GET, POST, etc.)
        url : str
            Request URL
        **kwargs
            Additional arguments passed to requests

        Returns
        -------
        requests.Response
            HTTP response

        Raises
        ------
        CensusAPIError
            For various API error conditions
        """
        # Set default timeout if not provided
        if "timeout" not in kwargs:
            kwargs["timeout"] = 30

        for attempt in range(self.max_retries + 1):
            # Enforce rate limiting
            self._enforce_rate_limit()

            try:
                response = self.session.request(method, url, **kwargs)
            except requests.exceptions.RequestException as e:
                if attempt < self.max_retries:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        f"Network error: {e}. Retrying in {delay:.1f}s "
                        f"(attempt {attempt + 2}/{self.max_retries + 1})..."
                    )
                    time.sleep(delay)
                    continue
                logger.error(f"All {self.max_retries + 1} attempts failed: {e}")
                raise

            if response.ok:
                return response

            if self._is_retryable_status(response.status_code) and (
                attempt < self.max_retries
            ):
                delay = self._backoff_delay(attempt)
                retry_after = self._retry_after_seconds(response)
                if retry_after is not None:
                    delay = max(delay, min(retry_after, 60))
                logger.warning(
                    f"Transient error (HTTP {response.status_code}), retrying "
                    f"in {delay:.1f}s (attempt {attempt + 2}/{self.max_retries + 1})..."
                )
                time.sleep(delay)
                continue

            # Permanent error, or transient error with retries exhausted
            raise self._create_appropriate_exception(response)

    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request."""
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> requests.Response:
        """Make a POST request."""
        return self.request("POST", url, **kwargs)

    def close(self):
        """Close the session and clean up resources."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Global session instance for use throughout pycancensus
_global_session = None


def get_session() -> ResilientSession:
    """Get or create the global resilient session."""
    global _global_session

    if _global_session is None:
        _global_session = ResilientSession()

    return _global_session


def close_session():
    """Close the global session."""
    global _global_session

    if _global_session is not None:
        _global_session.close()
        _global_session = None


# Cleanup on module exit
atexit.register(close_session)
