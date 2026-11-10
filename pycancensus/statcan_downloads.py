"""
Downloads from Statistics Canada (port of R cancensus statcan_downloads.R).

Parts of the Statistics Canada website (www12.statcan.gc.ca) sit behind a
Cloudflare browser verification that can't be completed from Python. These
helpers detect the block and fall back on files that users download in their
browser and put in the ``statcan_downloads`` folder of the cache directory.
"""

import os
import platform
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Optional, Union

import requests

from .resilience import get_session
from .settings import get_cache_path

_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06")


def _statcan_downloads_path(base_path: Optional[Union[str, Path]] = None) -> Path:
    """Folder for manually downloaded files. ``base_path`` overrides the
    pycancensus cache path, for functions with a ``cache_path`` argument."""
    base = Path(base_path) if base_path is not None else Path(get_cache_path())
    return base / "statcan_downloads"


def _is_zip(path: Path) -> bool:
    """Check the file signature, which also catches HTML pages saved under a
    .zip name, without reading large archives."""
    path = Path(path)
    if not path.is_file():
        return False
    with open(path, "rb") as f:
        return f.read(4) in _ZIP_SIGNATURES


def _is_cloudflare_block(response: requests.Response) -> bool:
    headers = response.headers
    return "cf-mitigated" in headers or (
        response.status_code in (403, 429, 503)
        and headers.get("server", "").lower() == "cloudflare"
    )


def _display_path(path: Path) -> str:
    return str(Path(path).expanduser())


def _fallback_message(has_cache: bool) -> str:
    return (
        "Returning the existing cached data instead."
        if has_cache
        else "Returning None."
    )


def _blocked_message(url: str, manual_file: Path, has_cache: bool = False) -> str:
    unzipped_dir = manual_file.with_suffix("")
    parts = [
        "Statistics Canada blocked this download with a Cloudflare browser "
        "verification, which can't be completed from Python. ",
        _fallback_message(has_cache),
        "\n\nThe data can still be downloaded manually:\n",
        "1. Paste this link into your web browser and complete the "
        "verification if prompted:\n",
        f"   {url}\n",
    ]
    if platform.system() == "Darwin":
        parts.append(
            "   Safari unzips downloads automatically, so use another browser "
            "such as Chrome or Firefox, or turn off \"Open 'safe' files after "
            "downloading\" in Safari's settings.\n"
        )
    parts += [
        "2. Move the downloaded file, without unzipping or renaming it, to:\n",
        f"   {_display_path(manual_file)}\n",
        "3. Run this command again",
        " with `refresh=True`" if has_cache else "",
        ". pycancensus will load the data from that file, add it to the cache, "
        "and remove the downloaded file.",
    ]
    if unzipped_dir.is_dir():
        parts.append(
            f"\n\nThe folder\n   {_display_path(unzipped_dir)}\nlooks like an "
            "unzipped copy of this file, which pycancensus can't read. It needs "
            "the original zip file."
        )
    return "".join(parts)


def _statcan_download_zip(
    url: str,
    base_path: Optional[Union[str, Path]] = None,
    timeout: float = 10000,
    quiet: bool = False,
    has_cache: bool = False,
) -> Optional[Path]:
    """
    Get a zip file from Statistics Canada, preferring a manually downloaded copy.

    Returns the path to the zip file, which the caller should remove after
    use, or None with a warning if the file can't be obtained because of the
    Cloudflare block or because the manually downloaded file is invalid.
    Other download problems raise. Callers set ``has_cache`` when refreshing
    existing cached data, which they then fall back on if this returns None.
    """
    downloads_path = _statcan_downloads_path(base_path)
    manual_file = downloads_path / os.path.basename(url.split("?")[0])

    if manual_file.exists():
        if not _is_zip(manual_file):
            warnings.warn(
                "The manually downloaded file is not a valid zip file, it may be "
                "incomplete or have been saved in place of the actual data. "
                f"{_fallback_message(has_cache)}\n\nPlease replace\n   "
                f"{_display_path(manual_file)}\nwith a new download from\n   {url}",
                stacklevel=3,
            )
            return None
        if not quiet:
            print(f"Reading manually downloaded file {_display_path(manual_file)}")
        return manual_file

    response = get_session().get(url, stream=True, timeout=timeout, raise_errors=False)
    with response:
        if _is_cloudflare_block(response):
            downloads_path.mkdir(parents=True, exist_ok=True)
            warnings.warn(_blocked_message(url, manual_file, has_cache), stacklevel=3)
            return None
        if not response.ok:
            raise RuntimeError(
                f"Could not download {url} from Statistics Canada, the server "
                f"responded with HTTP status {response.status_code}."
            )
        fd, tmp_name = tempfile.mkstemp(suffix=".zip")
        tmp = Path(tmp_name)
        response.raw.decode_content = True
        with os.fdopen(fd, "wb") as f:
            shutil.copyfileobj(response.raw, f)
    if not _is_zip(tmp):
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"The download of {url} from Statistics Canada did not return a zip file."
        )
    return tmp
