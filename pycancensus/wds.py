"""
Census data from the Statistics Canada Web Data Service (WDS).

Port of R cancensus wds.R. The WDS serves the 2021 Census Profile for
geographic levels that CensusMapper doesn't cover, like federal and
provincial electoral districts, designated places, population centres,
forward sortation areas and health regions.
"""

import hashlib
import io
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Union

import pandas as pd
import requests

from .resilience import CensusAPIError, NetworkError, get_session

WDS_URL = "https://api.statcan.gc.ca/census-recensement/profile/sdmx/rest"

_VALID_CENSUS_YEARS = ("2021",)
_VALID_LEVELS = (
    "PR",
    "CD",
    "CMACA",
    "CSD",
    "CT",
    "ADA",
    "DA",
    "ER",
    "FED",
    "DPL",
    "POPCNTR",
    "FSA",
    "HR",
)
_GENDERS = {"All": "", "Total": "1", "Male": "2", "Female": "3"}

_NS = {
    "structure": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure",
    "common": "http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common",
}
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

# DGUID schema (characters 6 to 9) to geographic level
_SCHEMA_TO_LEVEL = {
    "0000": "C",
    "0001": "C",
    "0002": "PR",
    "0003": "CD",
    "0004": "FED",
    "0005": "CSD",
    "0006": "DPL",
    "0007": "HR",
    "0008": "LHR",
    "0011": "FSA",
    "0500": "ER",
    "0501": "CAR",
    "0502": "CCSD",
    "0503": "CMA",
    "0504": "CA",
    "0505": "CMAP",
    "0507": "CT",
    "0510": "PC",
    "0511": "PCP",
    "0512": "DA",
    "0513": "DB",
    "0516": "ADA",
}
_SIMPLE_LEVELS = {"LHR": "HR", "CMA": "CMACA", "CA": "CMACA", "CMAP": "CMACA"}

# Downloads are kept for the Python session, like R keeps them in tempdir()
_session_dir: Optional[Path] = None


def _session_cache_file(name: str) -> Path:
    global _session_dir
    if _session_dir is None or not _session_dir.is_dir():
        _session_dir = Path(tempfile.mkdtemp(prefix="pycancensus_wds_"))
    return _session_dir / name


def _digest(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _geo_level_from_dguid(dguid: str, simple: bool = True) -> str:
    """The geographic level of a DGUID, from its schema."""
    schema = str(dguid)[5:9]
    if schema not in _SCHEMA_TO_LEVEL:
        raise ValueError(f"Unknown geographic level for DGUID {dguid!r}.")
    level = _SCHEMA_TO_LEVEL[schema]
    if simple:
        level = _SIMPLE_LEVELS.get(level, level)
    return level


def _wds_get(url: str, **kwargs) -> requests.Response:
    """GET from the WDS, raising with the server's explanation on errors."""
    try:
        response = get_session().get(url, raise_errors=False, **kwargs)
    except requests.exceptions.SSLError as e:
        raise NetworkError(
            f"{e}\nThis means that the authenticity of the StatCan API server "
            "can't be verified. Statistics Canada has a history of faulty SSL "
            "certificates on their API."
        ) from e
    if not response.ok:
        raise CensusAPIError(
            f"Invalid request.\n{response.text.strip()}",
            status_code=response.status_code,
        )
    return response


def get_statcan_wds_metadata(
    census_year: Union[str, int],
    level: str,
    version: Optional[str] = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Query the Statistics Canada WDS for metadata.

    Gets official metadata from Statistics Canada for a geographic level:
    the codes and English and French names of the geographic areas, census
    characteristics and other code lists of the census profile. Only
    available for the 2021 census. Data is cached for the duration of the
    Python session. Mirrors R cancensus's ``get_statcan_wds_metadata()``.

    Parameters
    ----------
    census_year : str or int
        Census year to get the data for, only 2021 is supported.
    level : str
        Geographic level, one of "PR", "CD", "CMACA", "CSD", "CT", "ADA",
        "DA", "ER", "FED", "DPL", "POPCNTR", "FSA" or "HR".
    version : str, optional
        Version of the data. For example, for FED level data, version "1.3"
        accesses the 2013 representation order and "2.0" the 2023
        representation order. Defaults to the latest version.
    refresh : bool, default False
        Download the metadata again instead of using the session cache.

    Returns
    -------
    pd.DataFrame
        One row per code with columns "Agency ID", "Codelist ID",
        "Codelist en", "Codelist fr", "ID", "en", "fr" and "Parent ID".

    Examples
    --------
    >>> import pycancensus as pc
    >>> # metadata for federal electoral districts
    >>> meta = pc.get_statcan_wds_metadata("2021", "FED")
    >>> ridings = meta[meta["Codelist ID"] == "CL_GEO_FED"]
    """
    census_year = str(census_year)
    if census_year not in _VALID_CENSUS_YEARS:
        raise ValueError(
            f"Census year must be one of {', '.join(_VALID_CENSUS_YEARS)}."
        )
    if level not in _VALID_LEVELS:
        raise ValueError(f"Level must be one of {', '.join(_VALID_LEVELS)}.")

    meta_url = (
        f"{WDS_URL}/dataflow/STC_CP/DF_{level}"
        f"{'' if version is None else '/' + str(version)}?references=all"
    )
    cache_file = _session_cache_file(f"census_wds_metadata_{_digest(meta_url)}.sdmx")
    if refresh or not cache_file.exists():
        response = _wds_get(meta_url, timeout=600)
        cache_file.write_bytes(response.content)

    root = ET.parse(cache_file).getroot()
    frames = []
    for codelist in root.iterfind(".//structure:Codelist", _NS):
        codes = codelist.findall("structure:Code", _NS)
        parents = [code.find("structure:Parent/Ref", _NS) for code in codes]
        frames.append(
            pd.DataFrame(
                {
                    "Agency ID": codelist.get("agencyID"),
                    "Codelist ID": codelist.get("id"),
                    "Codelist en": _name(codelist, "en"),
                    "Codelist fr": _name(codelist, "fr"),
                    "ID": [code.get("id") for code in codes],
                    "en": [_name(code, "en") for code in codes],
                    "fr": [_name(code, "fr") for code in codes],
                    "Parent ID": [
                        None if parent is None else parent.get("id")
                        for parent in parents
                    ],
                },
                columns=[
                    "Agency ID",
                    "Codelist ID",
                    "Codelist en",
                    "Codelist fr",
                    "ID",
                    "en",
                    "fr",
                    "Parent ID",
                ],
            )
        )
    if not frames:
        return pd.DataFrame(
            columns=[
                "Agency ID",
                "Codelist ID",
                "Codelist en",
                "Codelist fr",
                "ID",
                "en",
                "fr",
                "Parent ID",
            ]
        )
    return pd.concat(frames, ignore_index=True)


def _name(element: ET.Element, language: str) -> Optional[str]:
    for name in element.findall("common:Name", _NS):
        if name.get(_XML_LANG) == language:
            return name.text
    return None


def _sorted_members(members) -> List[str]:
    """Members in R's sort order: numeric ones by value."""
    members = [str(m) for m in members]
    if all(m.isdigit() for m in members):
        return sorted(members, key=int)
    return sorted(members)


def get_statcan_wds_data(
    DGUIDs: Union[str, List[str]],
    members: Optional[List[Union[str, int]]] = None,
    version: Optional[str] = None,
    gender: str = "All",
    language: str = "en",
    refresh: bool = False,
) -> pd.DataFrame:
    """
    Query the Statistics Canada WDS for census data.

    Gets official 2021 Census Profile data from Statistics Canada for a set
    of DGUIDs (dissemination geography unique identifiers), including levels
    CensusMapper doesn't have, like federal electoral districts or health
    regions. The data gets enriched with the names of the geographies and
    characteristics, from :func:`get_statcan_wds_metadata`. Data is cached
    for the duration of the Python session. Mirrors R cancensus's
    ``get_statcan_wds_data()``.

    Parameters
    ----------
    DGUIDs : str or list of str
        DGUIDs of the areas, all of the same geographic level. Valid DGUIDs
        for a level are the IDs of its ``CL_GEO_<level>`` code list in
        :func:`get_statcan_wds_metadata`.
    members : list of str or int, optional
        Characteristic member IDs to get. Defaults to all. Valid IDs are in
        the ``CL_CHARACTERISTIC`` code list of
        :func:`get_statcan_wds_metadata`.
    version : str, optional
        Version of the data. For example, for FED level data, version "1.3"
        accesses the 2013 representation order and "2.0" the 2023
        representation order. Defaults to the latest version.
    gender : str, default "All"
        "All" for all genders, or "Total", "Male" or "Female" for only one.
    language : str, default "en"
        Language of the added ``GEO_NAME`` and ``CHARACTERISTIC_NAME``
        columns, "en" or "fr". Like R, this doesn't follow
        :func:`set_language`.
    refresh : bool, default False
        Download the data again instead of using the session cache.

    Returns
    -------
    pd.DataFrame
        The data as returned by Statistics Canada, with ``OBS_VALUE``
        numeric, plus ``GEO_NAME`` and ``CHARACTERISTIC_NAME``.

    Examples
    --------
    >>> import pycancensus as pc
    >>> # population of two federal electoral districts (2023 representation
    >>> # order), from the total of the age characteristics
    >>> data = pc.get_statcan_wds_data(
    ...     ["2023A000410001", "2023A000410002"], members=[8], gender="Total"
    ... )
    """
    if isinstance(DGUIDs, str):
        DGUIDs = [DGUIDs]
    DGUIDs = sorted(str(d) for d in DGUIDs)
    if not DGUIDs:
        raise ValueError("At least one DGUID is required.")
    members = _sorted_members(members or [])
    level = _geo_level_from_dguid(DGUIDs[0])

    gender = str(gender).lower().capitalize()
    if gender not in _GENDERS:
        raise ValueError(f"Gender must be one of {', '.join(_GENDERS)}.")
    language = str(language).lower()
    if language not in ("en", "fr"):
        raise ValueError("Language must be one of en, fr.")

    query = (
        f"DF_{level}{'' if version is None else ',' + str(version)}"
        f"/A5.{'+'.join(DGUIDs)}.{_GENDERS[gender]}.{'+'.join(members)}.1"
    )
    cache_file = _session_cache_file(f"wds_data_{_digest(query)}.csv")
    if refresh or not cache_file.exists():
        response = _wds_get(
            f"{WDS_URL}/data/STC_CP,{query}",
            headers={"Accept": "text/csv", "Accept-Encoding": "gzip, deflate"},
            timeout=600,
        )
        # Only valid responses get cached, so errors aren't read back as data
        cache_file.write_bytes(response.content)

    meta_data = get_statcan_wds_metadata(
        "2021", level=level, version=version, refresh=refresh
    )
    meta_geos = meta_data.loc[
        meta_data["Codelist ID"] == f"CL_GEO_{level}", ["ID", language]
    ].rename(columns={"ID": "GEO_DESC", language: "GEO_NAME"})
    meta_characteristics = meta_data.loc[
        meta_data["Codelist ID"] == "CL_CHARACTERISTIC", ["ID", language]
    ].rename(columns={"ID": "CHARACTERISTIC", language: "CHARACTERISTIC_NAME"})

    data = pd.read_csv(io.BytesIO(cache_file.read_bytes()), dtype=str)
    # Same columns as R, which matches "OBS_VALUE|TNR_CI_"
    for column in data.columns:
        if "OBS_VALUE" in column or "TNR_CI_" in column:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.merge(meta_geos, on="GEO_DESC", how="left")
    data = data.merge(meta_characteristics, on="CHARACTERISTIC", how="left")
    return data
