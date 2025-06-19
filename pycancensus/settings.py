"""
User settings and configuration for pycancensus.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


# Global variables to store settings
_API_KEY = None
_CACHE_PATH = None


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
