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
