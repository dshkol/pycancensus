"""
Statistics Canada GeoSuite and geographic attribute files.

Port of R cancensus geo_suite.R. Statistics Canada blocks programmatic
downloads of these files, so like R cancensus they come from parquet files
derived from them and hosted by MountainMath at
https://data.mountainmath.ca/census/. Reading them needs pyarrow, which
``pip install pycancensus[statcan]`` installs.
"""

import hashlib
import json
import os
import shutil
import tempfile
import warnings
from pathlib import Path
from typing import Any, Callable, Optional, Union

import pandas as pd
import requests

from .resilience import get_session
from .settings import get_cache_path, get_language, validate_language
from .statcan_downloads import _fallback_message

HOSTED_URL = "https://data.mountainmath.ca/census"

_COMMON_TABLES = [
    "CAN",
    "PR",
    "CD",
    "CDTYPE",
    "CCS",
    "CSD",
    "CSDTYPE",
    "SACTYPE",
    "ER",
    "FED",
    "CT",
    "DA",
    "DB",
    "DPL",
    "DPLTYPE",
    "PN",
    "LOCATOR_SOURCE_TYPE",
    "DISSOLVED_GA_TYPE",
    "CMA_CA",
    "CMA_CA_P",
    "CMA_CA_NCMA_CA",
    "CMA_CA_NCMA_CA_P",
]
_UA_TABLES = ["UA", "UA_P", "UA_RA", "UA_RA_P", "UARATYPE"]
_POPCTR_TABLES = ["POPCTR", "POPCTR_P", "POPCTR_RA", "POPCTR_RA_P", "POPCTRRATYPE"]

# Tables of the hosted GeoSuite files, so names can be checked without a download
_GEO_SUITE_TABLES = {
    "1996": [
        "CAN",
        "PR",
        "CD",
        "CCS",
        "CSD",
        "CSDTYPE",
        "ER",
        "FED",
        "CT",
        "EA",
        "DPL",
        "DPLTYPE",
        "PN",
        "CMA_CA",
        "CMA_CA_P",
        "CMATYPE",
        "PCMA_PCA",
        "PCMA_PCA_P",
        "UA",
        "UA_P",
        "UATYPE",
    ],
    "2001": _COMMON_TABLES + ["DPL_P"] + _UA_TABLES,
    "2006": _COMMON_TABLES + ["REFMAPS"] + _UA_TABLES,
    "2011": _COMMON_TABLES + ["REFMAPS", "CMATYPE"] + _POPCTR_TABLES,
    "2016": _COMMON_TABLES
    + ["ADA", "CMATYPE", "CSD_POPCHALL_ADJ", "DPL_POPCHALL_ADJ"]
    + _POPCTR_TABLES,
    "2021": _COMMON_TABLES
    + ["ADA", "CMATYPE"]
    + _POPCTR_TABLES
    + ["POPCTRRACLASSE", "SACCODE"],
}
_GEO_SUITE_ALIASES = {
    "CMA": "CMA_CA",
    "CA": "CMA_CA",
    "CMACA": "CMA_CA",
    "LOC": "PN",
    "CB": "DB",
}
_ATTRIBUTE_YEARS = [str(year) for year in range(1981, 2022, 5)]


def get_statcan_geo_suite(
    level: Optional[str] = None,
    census_year: Union[str, int] = "2021",
    refresh: bool = False,
    language: Optional[str] = None,
    quiet: bool = False,
) -> Optional[pd.DataFrame]:
    """
    Read a table of the Statistics Canada GeoSuite.

    The GeoSuite has a table for each geographic level, with the codes and
    names of the areas, how they relate to other levels, population and
    dwelling counts, land areas and representative points, along with code
    tables like the census subdivision types. Called without ``level`` this
    lists the tables available for the census year. Mirrors R cancensus's
    ``get_statcan_geo_suite()``.

    The data comes from parquet files hosted at
    https://data.mountainmath.ca/census/geo_suite/, as Statistics Canada
    blocks programmatic downloads of the GeoSuite. The files are derived from
    Statistics Canada data under the Statistics Canada Open Licence. They get
    downloaded on first use and cached in the pycancensus cache path, and
    cached copies only get updated with ``refresh=True``. Reading tables
    needs pyarrow: ``pip install pycancensus[statcan]``.

    The GeoSuite is available for the censuses from 1996 to 2021, and tables
    differ between years: 1996 has enumeration areas (``EA``) instead of
    dissemination areas and blocks, 2001 to 2006 have urban areas (``UA``)
    and 2011 on population centres (``POPCTR``). Tables ending in ``_P`` hold
    the parts of areas that span provinces or other areas. Column names
    follow :func:`get_statcan_geographic_attributes`, e.g. ``CSDUID``,
    ``CSDPOP2021`` or ``DARPLAT``, and are the same across census years. A
    suffix ``A`` marks counts of the previous census adjusted to the current
    boundaries, and ``C`` or ``AC`` corrected counts.

    Parameters
    ----------
    level : str, optional
        The table to read, e.g. "DA", "CSD" or "CMA_CA". "CMA", "CA" and
        "CMACA" read "CMA_CA", "LOC" reads "PN" and "CB" reads "DB". If None,
        returns the list of tables for the census year.
    census_year : str or int, default "2021"
        One of 1996, 2001, 2006, 2011, 2016 or 2021. For older censuses
        :func:`get_statcan_geographic_attributes` has much of the same
        information.
    refresh : bool, default False
        Download the table again, and report whether it has changed.
    language : str, optional
        Language of the column labels and table titles, "en" or "fr".
        Defaults to :func:`get_language`. This does not change the data.
    quiet : bool, default False
        Suppress messages. Warnings about failed downloads are still shown.

    Returns
    -------
    pd.DataFrame or None
        The GeoSuite table. ``attrs["column_labels"]`` maps each column to a
        description, and ``attrs["metadata"]`` holds the metadata of the
        table, including the attribution, licence, source and notes; the
        Statistics Canada field name of each column is its ``source_field``
        in ``attrs["metadata"]["columns"]``. If ``level`` is None, a
        DataFrame with the ``table`` names, their ``title``,
        ``primary_key`` and file ``size`` in bytes. If the data can't be
        downloaded this warns, and returns the cached data when refreshing
        existing cached data and None otherwise.

    Examples
    --------
    >>> import pycancensus as pc
    >>> # list the tables of the 2021 GeoSuite
    >>> pc.get_statcan_geo_suite(census_year="2021")
    >>> # read the dissemination areas
    >>> das = pc.get_statcan_geo_suite("DA", "2021")
    """
    census_year = str(census_year)
    if census_year not in _GEO_SUITE_TABLES:
        raise ValueError(
            "The GeoSuite is only available for census years "
            f"{', '.join(_GEO_SUITE_TABLES)}. For older censuses "
            "get_statcan_geographic_attributes() has much of the same information."
        )
    language = get_language() if language is None else validate_language(language)
    base_url = f"{HOSTED_URL}/geo_suite/{census_year}/"
    cache_dir = Path(get_cache_path()) / "geo_suite" / census_year

    if level is None:
        return _geo_suite_table_list(
            base_url + "_manifest.json",
            cache_dir / "_manifest.json",
            refresh=refresh,
            language=language,
            quiet=quiet,
        )
    table = _geo_suite_table_name(level, census_year)
    _require_pyarrow("to read the GeoSuite.")
    return _read_hosted_parquet(
        f"{base_url}{table}.parquet",
        cache_dir / f"{table}.parquet",
        description=f"{census_year} GeoSuite table {table}",
        refresh=refresh,
        language=language,
        quiet=quiet,
    )


def get_statcan_geographic_attributes(
    census_year: Union[str, int] = "2021",
    refresh: bool = False,
    language: Optional[str] = None,
    quiet: bool = False,
) -> Optional[pd.DataFrame]:
    """
    Read the Statistics Canada geographic attribute file.

    One row for each area of the lowest census geography, with how all the
    geographic levels relate for each area, population and dwelling counts
    and representative points. Mirrors R cancensus's
    ``get_statcan_geographic_attributes()``.

    The data comes from parquet files hosted at
    https://data.mountainmath.ca/census/geo_attributes/, as Statistics
    Canada blocks programmatic downloads of these files. The files are
    derived from Statistics Canada data under the Statistics Canada Open
    Licence. They get downloaded on first use and cached in the pycancensus
    cache path, and cached copies only get updated with ``refresh=True``.
    Reading them needs pyarrow: ``pip install pycancensus[statcan]``. A
    reference guide for the 2021 file is at
    https://www150.statcan.gc.ca/n1/en/catalogue/92-151-G2021001

    Column names follow the 2021 file, but the columns differ between
    census years. 2001 to 2021 have one row per dissemination block,
    identified by ``DBUID``; the 2001 data was derived from the 2001 GeoSuite
    and has no total dwelling counts or block areas. 1981 to 1996 have one
    row per enumeration area, identified by ``EAUID``, with different
    columns, e.g. ``CTCODE`` instead of ``CTUID``. Identifiers are only
    unique within a census year. The ``notes_en`` entry of the metadata has
    details on each file.

    Parameters
    ----------
    census_year : str or int, default "2021"
        One of 1981, 1986, 1991, 1996, 2001, 2006, 2011, 2016 or 2021.
    refresh : bool, default False
        Download the file again, and report whether it has changed.
    language : str, optional
        Language of the column labels, "en" or "fr". Defaults to
        :func:`get_language`. This does not change the data.
    quiet : bool, default False
        Suppress messages. Warnings about failed downloads are still shown.

    Returns
    -------
    pd.DataFrame or None
        The attribute data. ``attrs["column_labels"]`` maps each column to a
        description, and ``attrs["metadata"]`` holds the metadata of the
        file, including the attribution, licence, source and notes. If the
        file can't be downloaded this warns, and returns the cached data when
        refreshing existing cached data and None otherwise.

    Examples
    --------
    >>> import pycancensus as pc
    >>> attributes = pc.get_statcan_geographic_attributes("2021")
    >>> # where the data comes from
    >>> attributes.attrs["metadata"]["attribution_en"]
    """
    census_year = str(census_year)
    if census_year not in _ATTRIBUTE_YEARS:
        raise ValueError(
            f"Only census years {', '.join(_ATTRIBUTE_YEARS)} are supported "
            "for the geographic attributes."
        )
    language = get_language() if language is None else validate_language(language)
    _require_pyarrow("to read the geographic attributes.")
    return _read_hosted_parquet(
        f"{HOSTED_URL}/geo_attributes/geo_attributes_{census_year}.parquet",
        Path(get_cache_path()) / f"geo_attributes_{census_year}.parquet",
        description="Geographic attributes",
        refresh=refresh,
        language=language,
        quiet=quiet,
    )


def _require_pyarrow(reason: str) -> None:
    try:
        import pyarrow.parquet  # noqa: F401
    except ImportError:
        raise ImportError(
            f"pyarrow is required {reason} Install it with "
            "`pip install pycancensus[statcan]` or `pip install pyarrow`."
        ) from None


def _geo_suite_table_name(level, census_year: str) -> str:
    """The hosted table name for ``level``, or an error listing the tables."""
    if not isinstance(level, str):
        raise ValueError('level must be a single table name, e.g. "DA".')
    table = level.upper()
    table = _GEO_SUITE_ALIASES.get(table, table)
    tables = _GEO_SUITE_TABLES[census_year]
    if table not in tables:
        hint = (
            " The 1996 GeoSuite is based on enumeration areas, in the EA table."
            if census_year == "1996" and table in ("DA", "DB", "ADA")
            else ""
        )
        raise ValueError(
            f"There is no {level} table in the {census_year} GeoSuite.{hint} "
            f"Available tables are {', '.join(sorted(tables))}, "
            f'get_statcan_geo_suite(census_year="{census_year}") lists them '
            "with descriptions."
        )
    return table


def _parse_metadata_value(value: Any) -> Any:
    """JSON objects and arrays get parsed, the rest stays as it is."""
    if not isinstance(value, str) or not value.lstrip().startswith(("[", "{")):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value


def _manifest_field(metadata: dict, name: str) -> str:
    value = _parse_metadata_value((metadata or {}).get(name))
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return ", ".join(str(v) for v in value)
    return str(value)


def _is_manifest_file(path: Path) -> bool:
    if not Path(path).is_file():
        return False
    try:
        with open(path, encoding="utf-8") as f:
            return isinstance(json.load(f).get("files"), list)
    except (ValueError, AttributeError, OSError):
        return False


def _geo_suite_table_list(
    url: str, file_path: Path, refresh: bool, language: str, quiet: bool
) -> Optional[pd.DataFrame]:
    """The tables listed in the manifest of a GeoSuite year."""
    has_cache = _is_manifest_file(file_path)
    if refresh or not has_cache:
        downloaded = _download_hosted_file(
            url,
            file_path,
            has_cache=has_cache,
            quiet=quiet,
            is_valid=_is_manifest_file,
            kind="list of tables",
        )
        if not downloaded and not has_cache:
            return None
    with open(file_path, encoding="utf-8") as f:
        files = json.load(f)["files"]
    files = [f for f in files if str(f.get("path", "")).endswith(".parquet")]
    rows = []
    for f in files:
        metadata = f.get("metadata") or {}
        title = _manifest_field(metadata, f"title_{language}") or _manifest_field(
            metadata, "title_en"
        )
        rows.append(
            {
                "table": f["path"][: -len(".parquet")],
                "title": title,
                "primary_key": _manifest_field(metadata, "primary_key"),
                "size": float(f.get("size", float("nan"))),
            }
        )
    return pd.DataFrame(rows, columns=["table", "title", "primary_key", "size"])


def _is_parquet_file(path: Path) -> bool:
    """Parquet files start and end with the same signature, so this also
    catches truncated downloads."""
    path = Path(path)
    if not path.is_file():
        return False
    size = path.stat().st_size
    if size < 8:
        return False
    with open(path, "rb") as f:
        start = f.read(4)
        f.seek(size - 4)
        return start == b"PAR1" and f.read(4) == b"PAR1"


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download_hosted_file(
    url: str,
    path: Path,
    has_cache: bool = False,
    quiet: bool = False,
    is_valid: Callable[[Path], bool] = _is_parquet_file,
    kind: str = "parquet file",
) -> bool:
    """
    Download a hosted file to ``path``, which only gets replaced by a file
    that passes ``is_valid``. Returns whether that worked; anything else is a
    warning, so this fails gracefully when the file is unavailable.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(suffix=path.suffix, dir=path.parent)
    tmp = Path(tmp_name)
    try:
        problem = None
        try:
            response = get_session().get(
                url, stream=True, timeout=600, raise_errors=False
            )
            with response:
                if not response.ok:
                    problem = (
                        "the server responded with HTTP status "
                        f"{response.status_code}"
                    )
                else:
                    response.raw.decode_content = True
                    with os.fdopen(fd, "wb") as f:
                        fd = None
                        shutil.copyfileobj(response.raw, f)
        except (requests.exceptions.RequestException, OSError) as e:
            problem = str(e)
        if problem is None and not is_valid(tmp):
            problem = f"the server did not return a complete {kind}"
        if problem is not None:
            warnings.warn(
                f"Could not download {url}: {problem}. {_fallback_message(has_cache)}",
                stacklevel=4,
            )
            return False
        if has_cache and not quiet:
            changed = _file_digest(tmp) != _file_digest(path)
            print(
                "The hosted file has changed, updating the cached copy."
                if changed
                else "The hosted file has not changed."
            )
        os.replace(tmp, path)
        return True
    finally:
        if fd is not None:
            os.close(fd)
        tmp.unlink(missing_ok=True)


def _read_hosted_parquet(
    url: str,
    file_path: Path,
    description: str,
    refresh: bool = False,
    language: str = "en",
    quiet: bool = False,
) -> Optional[pd.DataFrame]:
    """Read a hosted parquet file through the cache at ``file_path``,
    downloading it if needed or asked for with ``refresh``."""
    has_cache = _is_parquet_file(file_path)
    downloaded = False
    if refresh or not has_cache:
        downloaded = _download_hosted_file(
            url, file_path, has_cache=has_cache, quiet=quiet
        )
        if not downloaded and not has_cache:
            return None
    result = _read_parquet_file(file_path, language=language)
    if downloaded and not quiet:
        metadata = result.attrs["metadata"]
        print(
            f"{description} hosted by MountainMath, source: "
            f"{metadata.get('attribution_en')}. Licence: {metadata.get('licence_en')}."
        )
    return result


def _read_parquet_file(path: Path, language: str = "en") -> pd.DataFrame:
    """
    Read a parquet file along with its metadata, the analog of R cancensus
    read_parquet_file(): column labels go in attrs["column_labels"] and the
    file metadata in attrs["metadata"].
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pq.read_table(path)
    # Integers stay integers with missing values, like R
    integer_types = {
        pa.int8(): pd.Int8Dtype(),
        pa.int16(): pd.Int16Dtype(),
        pa.int32(): pd.Int32Dtype(),
        pa.int64(): pd.Int64Dtype(),
    }
    data = table.to_pandas(types_mapper=integer_types.get)
    raw = table.schema.metadata or {}
    metadata = {
        key.decode("utf-8"): _parse_metadata_value(value.decode("utf-8"))
        for key, value in raw.items()
        if key != b"ARROW:schema" and not key.startswith(b"pandas")
    }
    columns = (
        metadata.get("columns") if isinstance(metadata.get("columns"), dict) else {}
    )
    column_labels = {}
    for column in data.columns:
        entry = columns.get(column) or {}
        label = entry.get(f"label_{language}") or entry.get("label_en")
        if label is not None:
            column_labels[column] = label
    data.attrs["column_labels"] = column_labels
    data.attrs["metadata"] = metadata
    return data
