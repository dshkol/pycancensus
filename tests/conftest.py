"""Shared pytest fixtures."""

import pytest

from pycancensus import settings


@pytest.fixture(autouse=True)
def isolated_cache_path(tmp_path, monkeypatch):
    """Point the file cache at a temporary folder for every test.

    Fresh downloads always write to the cache, so without this a mocked
    response could overwrite the user's real cached region or vector lists.
    """
    cache_dir = tmp_path / "pycancensus_cache"
    monkeypatch.setattr(settings, "_CACHE_PATH", str(cache_dir))
    yield cache_dir


@pytest.fixture(autouse=True)
def default_label_settings(monkeypatch):
    """Start every test with no language or labels default set, and with
    once-per-session notices not yet shown."""
    monkeypatch.setattr(settings, "_LANGUAGE", None)
    monkeypatch.setattr(settings, "_LABELS", None)
    monkeypatch.setattr(settings, "_SHOWN_ONCE", set())
    monkeypatch.delenv(settings.LANGUAGE_ENV_VAR, raising=False)
    monkeypatch.delenv(settings.LABELS_ENV_VAR, raising=False)
