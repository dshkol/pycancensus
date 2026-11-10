"""
User settings and configuration for pycancensus.
"""

import os
import re
import json
from pathlib import Path
from typing import Optional, Dict, Any


# Global variables to store settings
_API_KEY = None
_CACHE_PATH = None

# API configuration
CENSUSMAPPER_API_URL = "https://censusmapper.ca/api/v1"
CENSUSMAPPER_DATA_URL = "https://censusmapper.ca/data_sets"

# Optional prefix identifying a tool built on pycancensus (see set_user_agent_prefix)
_USER_AGENT_PREFIX = None
USER_AGENT_PREFIX_ENV_VAR = "PYCANCENSUS_USER_AGENT_PREFIX"


def _clean_header_value(value: str) -> str:
    """Collapse control characters so the value is a valid single-line header."""
    return " ".join(re.sub(r"[\x00-\x1f\x7f]+", " ", value).split())


def set_user_agent_prefix(prefix: Optional[str]) -> None:
    """
    Identify a package or tool built on pycancensus to the CensusMapper API.

    The prefix is prepended to the user agent sent with every API request,
    e.g. ``"mypackage/1.2.3 pycancensus/0.3.0 requests/2.32.3 Python/3.12.4"``.
    Equivalent to ``options(cancensus.user_agent_prefix = ...)`` in R
    cancensus. The ``PYCANCENSUS_USER_AGENT_PREFIX`` environment variable
    sets a prefix without code changes; a prefix set here takes precedence.

    Parameters
    ----------
    prefix : str or None
        Product token(s) such as ``"mypackage/1.2.3"``. ``None`` or an empty
        string removes a prefix set by this function.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.set_user_agent_prefix("mypackage/1.2.3")
    """
    global _USER_AGENT_PREFIX
    if prefix is not None and not isinstance(prefix, str):
        raise TypeError("prefix must be a string or None")
    _USER_AGENT_PREFIX = _clean_header_value(prefix) if prefix else None


def get_user_agent() -> str:
    """
    Return the user agent sent with CensusMapper API requests.

    It identifies the package and its version, in the form
    ``pycancensus/<version> requests/<version> Python/<version>``, so the API
    can tell which clients make requests and keep older versions working as
    it evolves. A prefix from :func:`set_user_agent_prefix` or the
    ``PYCANCENSUS_USER_AGENT_PREFIX`` environment variable is prepended.

    Returns
    -------
    str
        The user agent string.
    """
    import platform

    import requests

    from . import __version__

    ua = (
        f"pycancensus/{__version__} requests/{requests.__version__} "
        f"Python/{platform.python_version()}"
    )
    prefix = _USER_AGENT_PREFIX
    if prefix is None:
        prefix = _clean_header_value(os.environ.get(USER_AGENT_PREFIX_ENV_VAR, ""))
    if prefix:
        ua = f"{prefix} {ua}"
    return ua


VALID_LANGUAGES = ("en", "fr")
VALID_LABELS = ("detailed", "short", "labelled")

# Session defaults for the language and labels parameters (see set_language
# and set_labels), the analogs of R's cancensus.language and cancensus.labels
# options. None means not set.
_LANGUAGE = None
_LABELS = None
LANGUAGE_ENV_VAR = "PYCANCENSUS_LANGUAGE"
LABELS_ENV_VAR = "PYCANCENSUS_LABELS"

# Keys of notices and warnings already shown in this session
_SHOWN_ONCE = set()


def first_time_this_session(key: str) -> bool:
    """True the first time it is called with ``key`` in a session."""
    if key in _SHOWN_ONCE:
        return False
    _SHOWN_ONCE.add(key)
    return True


def validate_language(language) -> str:
    """Return ``language`` lowercased, or raise if it isn't "en" or "fr"."""
    lowered = language.lower() if isinstance(language, str) else None
    if lowered not in VALID_LANGUAGES:
        raise ValueError(
            f"Language must be one of {', '.join(VALID_LANGUAGES)}, got {language!r}."
        )
    return lowered


def validate_labels(labels) -> str:
    """Return ``labels``, or raise if it isn't a valid labels option."""
    if not isinstance(labels, str) or labels not in VALID_LABELS:
        raise ValueError(
            f"Invalid labels: {labels!r}. Must be one of "
            f"{', '.join(repr(v) for v in VALID_LABELS)}."
        )
    return labels


def set_language(language: Optional[str]) -> None:
    """
    Set the default language of census variable labels for this session.

    Used by :func:`get_census`, :func:`list_census_vectors`,
    :func:`find_census_vectors`, :func:`parent_census_vectors`,
    :func:`child_census_vectors`, :func:`visualize_vector_hierarchy` and
    :func:`dataset_attribution` when their ``language`` parameter is not
    given. Equivalent to ``options(cancensus.language = ...)`` in R
    cancensus. The ``PYCANCENSUS_LANGUAGE`` environment variable sets a
    default without code changes; a language set here takes precedence.

    Parameters
    ----------
    language : str or None
        ``"en"`` or ``"fr"``. ``None`` removes a default set by this function.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.set_language("fr")
    """
    global _LANGUAGE
    _LANGUAGE = None if language is None else validate_language(language)


def get_language() -> str:
    """
    Return the default language of census variable labels.

    This is the language set by :func:`set_language`, otherwise the
    ``PYCANCENSUS_LANGUAGE`` environment variable, otherwise ``"en"``.

    Returns
    -------
    str
        ``"en"`` or ``"fr"``.
    """
    if _LANGUAGE is not None:
        return _LANGUAGE
    env_language = os.environ.get(LANGUAGE_ENV_VAR)
    if env_language:
        return validate_language(env_language)
    return "en"


def set_labels(labels: Optional[str]) -> None:
    """
    Set the default ``labels`` option of :func:`get_census` for this session.

    Equivalent to ``options(cancensus.labels = ...)`` in R cancensus. The
    default of ``labels`` is planned to change from ``"detailed"`` to
    ``"labelled"`` in a future version; setting a default here, or passing
    ``labels`` explicitly, keeps code working when it does. The
    ``PYCANCENSUS_LABELS`` environment variable sets a default without code
    changes; a default set here takes precedence.

    Parameters
    ----------
    labels : str or None
        One of ``"detailed"``, ``"short"`` or ``"labelled"``. ``None``
        removes a default set by this function.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.set_labels("detailed")
    """
    global _LABELS
    _LABELS = None if labels is None else validate_labels(labels)


def get_labels() -> Optional[str]:
    """
    Return the default ``labels`` option of :func:`get_census`, if one is set.

    This is the value set by :func:`set_labels`, otherwise the
    ``PYCANCENSUS_LABELS`` environment variable.

    Returns
    -------
    str or None
        The default, or ``None`` if none is set, in which case
        :func:`get_census` uses ``"detailed"``.
    """
    if _LABELS is not None:
        return _LABELS
    env_labels = os.environ.get(LABELS_ENV_VAR)
    if env_labels:
        return validate_labels(env_labels)
    return None


# Config file location
def _get_config_path() -> Path:
    """Get the path to the config file."""
    config_dir = Path.home() / ".pycancensus"
    config_dir.mkdir(exist_ok=True, mode=0o700)  # Secure permissions
    return config_dir / "config.json"


def _load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    config_path = _get_config_path()
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = _get_config_path()
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        # Set secure file permissions (read/write for owner only)
        config_path.chmod(0o600)
    except IOError as e:
        print(f"Warning: Could not save config file: {e}")


def set_api_key(api_key: str, install: bool = False) -> None:
    """
    Set the CensusMapper API key.

    Parameters
    ----------
    api_key : str
        Your CensusMapper API key. Get a free key at
        https://censusmapper.ca/users/sign_up
    install : bool, default False
        If True, saves the API key persistently for future sessions.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.set_api_key("your_api_key_here")
    >>> pc.set_api_key("your_api_key_here", install=True)  # Persist for future sessions
    """
    global _API_KEY
    _API_KEY = api_key

    if install:
        # Save to config file for persistence
        config = _load_config()
        config["api_key"] = api_key
        _save_config(config)
        print("API key set for current session and saved persistently.")
    else:
        print("API key set for current session.")


def get_api_key() -> Optional[str]:
    """
    Get the current CensusMapper API key.

    Returns
    -------
    str or None
        The current API key, or None if not set.
    """
    global _API_KEY

    # Check session variable first
    if _API_KEY is not None:
        return _API_KEY

    # Check environment variable
    env_key = os.environ.get("CANCENSUS_API_KEY")
    if env_key:
        _API_KEY = env_key
        return _API_KEY

    # Check config file
    config = _load_config()
    config_key = config.get("api_key")
    if config_key:
        _API_KEY = config_key
        return _API_KEY

    return None


def show_api_key() -> None:
    """
    Display the current API key status.
    """
    api_key = get_api_key()
    if api_key:
        # Only show first few characters for security
        masked_key = api_key[:8] + "..." if len(api_key) > 8 else api_key
        print(f"Current API key: {masked_key}")
    else:
        print("No API key set. Use set_api_key() to set one.")


def remove_api_key() -> None:
    """
    Remove the stored API key from both session and persistent storage.
    """
    global _API_KEY
    _API_KEY = None

    # Remove from environment variable if set
    if "CANCENSUS_API_KEY" in os.environ:
        del os.environ["CANCENSUS_API_KEY"]

    # Remove from config file
    config = _load_config()
    if "api_key" in config:
        del config["api_key"]
        _save_config(config)
        print("API key removed from persistent storage.")
    else:
        print("API key removed from session.")


def set_cache_path(cache_path: str, install: bool = False) -> None:
    """
    Set the local cache path for downloaded data.

    Parameters
    ----------
    cache_path : str
        Path to directory for caching downloaded data.
    install : bool, default False
        If True, saves the cache path persistently for future sessions.

    Examples
    --------
    >>> import pycancensus as pc
    >>> pc.set_cache_path("./data_cache")
    >>> pc.set_cache_path("./data_cache", install=True)  # Persist for future sessions
    """
    global _CACHE_PATH

    cache_path = Path(cache_path).expanduser().resolve()

    # Create directory if it doesn't exist
    cache_path.mkdir(parents=True, exist_ok=True)

    _CACHE_PATH = str(cache_path)

    if install:
        # Save to config file for persistence
        config = _load_config()
        config["cache_path"] = str(cache_path)
        _save_config(config)
        print(f"Cache path set to: {cache_path} and saved persistently.")
    else:
        print(f"Cache path set to: {cache_path} for current session.")


def get_cache_path() -> str:
    """
    Get the current cache path.

    Returns
    -------
    str
        The current cache path.
    """
    global _CACHE_PATH

    # Check session variable first
    if _CACHE_PATH is not None:
        return _CACHE_PATH

    # Check environment variable
    env_path = os.environ.get("CANCENSUS_CACHE_PATH")
    if env_path:
        _CACHE_PATH = env_path
        return _CACHE_PATH

    # Check config file
    config = _load_config()
    config_path = config.get("cache_path")
    if config_path:
        _CACHE_PATH = config_path
        return _CACHE_PATH

    # Default to user's home directory
    default_path = Path.home() / ".cancensus_cache"
    default_path.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH = str(default_path)

    return _CACHE_PATH


def show_cache_path() -> None:
    """
    Display the current cache path.
    """
    cache_path = get_cache_path()
    print(f"Current cache path: {cache_path}")
