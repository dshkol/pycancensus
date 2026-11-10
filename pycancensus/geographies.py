"""
Original Statistics Canada boundary files (port of R cancensus geographies.R).
"""

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, Union

import geopandas as gpd

from .settings import get_cache_path
from .statcan_downloads import _statcan_download_zip

_VALID_CENSUS_YEARS = ("2021",)
_VALID_LEVELS = (
    "PR",
    "CD",
    "CMACA",
    "CMA",
    "CA",
    "CSD",
    "CT",
    "ADA",
    "DA",
    "DB",
    "ER",
    "FED",
    "DPL",
    "POPCNTR",
    "POPCTR",
    "FSA",
    "HR",
)
_VALID_TYPES = ("cartographic", "digital")
_LEVEL_MAP = {"CMACA": "CMA", "CA": "CMA", "POPCNTR": "PC", "POPCTR": "PC"}
_HEALTH_REGION_URLS = {
    "cartographic": "https://www150.statcan.gc.ca/n1/en/pub/82-402-x/2024001/"
    "hrbf-flrs/carto/ArcGIS/HR_000b23a_e.zip?st=wQRRL7PQ",
    "digital": "https://www150.statcan.gc.ca/n1/en/pub/82-402-x/2024001/"
    "hrbf-flrs/digi/ArcGIS/HR_000a23a_e.zip",
}


def get_statcan_geographies(
    census_year: Union[str, int],
    level: str,
    type: str = "cartographic",
    cache_path: Optional[Union[str, Path]] = None,
    timeout: float = 1000,
    refresh: bool = False,
    quiet: bool = False,
) -> Optional[gpd.GeoDataFrame]:
    """
    Read the original boundary files from Statistics Canada.

    Downloads the unprocessed geographic boundary files from Statistics
    Canada, including levels CensusMapper doesn't have, like federal and
    provincial electoral districts, population centres, forward sortation
    areas and health regions. Mirrors R cancensus's
    ``get_statcan_geographies()``.

    Statistics Canada currently blocks programmatic downloads of these files
    with a Cloudflare browser verification. When that happens this warns
    with a link to download the file in a browser and the folder to put it
    in, and picks the file up from there on the next call.

    Parameters
    ----------
    census_year : str or int
        Census year to get the data for, only 2021 is supported.
    level : str
        One of "PR", "CD", "CMACA", "CMA", "CA", "CSD", "CT", "ADA", "DA",
        "DB", "ER", "FED", "DPL", "POPCNTR", "POPCTR", "FSA" or "HR".
    type : str, default "cartographic"
        "cartographic" (clipped to the shoreline) or "digital" (extending
        into water).
    cache_path : str or Path, optional
        Where to cache the data. Defaults to the "geographies" folder of the
        pycancensus cache path.
    timeout : float, default 1000
        Download timeout in seconds, raise it for slow connections.
    refresh : bool, default False
        Download the data again.
    quiet : bool, default False
        Suppress messages.

    Returns
    -------
    gpd.GeoDataFrame or None
        The boundaries. If Statistics Canada blocks the download this warns
        and returns the cached data when refreshing existing cached data,
        and None otherwise.

    Examples
    --------
    >>> import pycancensus as pc
    >>> provinces = pc.get_statcan_geographies("2021", "PR", type="digital")
    """
    census_year = str(census_year)
    if census_year not in _VALID_CENSUS_YEARS:
        raise ValueError(
            f"Census year must be one of {', '.join(_VALID_CENSUS_YEARS)}."
        )
    if type not in _VALID_TYPES:
        raise ValueError(f"Type must be one of {', '.join(_VALID_TYPES)}.")
    if level not in _VALID_LEVELS:
        raise ValueError(f"Level must be one of {', '.join(_VALID_LEVELS)}.")
    level = _LEVEL_MAP.get(level, level)

    base = Path(cache_path) if cache_path is not None else Path(get_cache_path())
    geo_base_path = base / "geographies" / type
    geo_base_path.mkdir(parents=True, exist_ok=True)
    exdir = geo_base_path / level
    has_cache = any(exdir.glob("*.shp"))

    if refresh or not has_cache:
        if level == "HR":
            url = _HEALTH_REGION_URLS[type]
        else:
            type_id = "b" if type == "cartographic" else "a"
            filler = "_000" if len(level) == 2 else "000"
            url = (
                f"https://www12.statcan.gc.ca/census-recensement/{census_year}/geo/"
                "sip-pis/boundary-limites/files-fichiers/"
                f"l{level.lower()}{filler}{type_id}21a_e.zip"
            )
        tmp = _statcan_download_zip(
            url, base_path=cache_path, timeout=timeout, quiet=quiet, has_cache=has_cache
        )
        if tmp is None and not has_cache:
            return None
        if tmp is not None:
            _unzip_flat(tmp, exdir)
            tmp.unlink(missing_ok=True)
    elif not quiet:
        print("Reading geographic data from local cache.")

    shapefiles = sorted(exdir.glob("*.shp"))
    return gpd.read_file(shapefiles[0])


def _unzip_flat(zip_path: Path, exdir: Path) -> None:
    """Unzip into ``exdir``, moving the files up if the archive holds a single
    folder."""
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(exdir)
    entries = list(exdir.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        tmp_dir = Path(tempfile.mkdtemp(prefix="pycancensus_geo_", dir=exdir.parent))
        inner = tmp_dir / entries[0].name
        shutil.move(str(entries[0]), str(inner))
        for entry in inner.iterdir():
            shutil.move(str(entry), str(exdir / entry.name))
        shutil.rmtree(tmp_dir)
