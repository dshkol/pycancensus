"""StatCan WDS, GeoSuite, geographic attributes and boundary files, ported
from R cancensus 0.6.2 (wds.R, geo_suite.R, geographies.R,
statcan_downloads.R).

Fixtures follow real responses: SDMX code lists from the WDS, its CSV data,
and parquet files with the metadata layout of data.mountainmath.ca.
"""

import io
import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point

import pycancensus as pc
from pycancensus import geo_suite, wds
from pycancensus.resilience import CensusAPIError

SDMX = """<?xml version="1.0" encoding="utf-8"?>
<message:Structure xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"
  xmlns:structure="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/structure"
  xmlns:common="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/common">
 <message:Structures><structure:Codelists>
  <structure:Codelist id="CL_CHARACTERISTIC" agencyID="STC_CP" version="1.0">
   <common:Name xml:lang="en">Characteristic</common:Name>
   <common:Name xml:lang="fr">Caractéristique</common:Name>
   <structure:Code id="1">
    <common:Name xml:lang="en">Population, 2021</common:Name>
    <common:Name xml:lang="fr">Population, 2021</common:Name>
   </structure:Code>
   <structure:Code id="8">
    <common:Name xml:lang="en">Total - Age groups of the population</common:Name>
    <common:Name xml:lang="fr">Total - Groupes d'âge de la population</common:Name>
   </structure:Code>
   <structure:Code id="9">
    <common:Name xml:lang="en">0 to 14 years</common:Name>
    <common:Name xml:lang="fr">0 à 14 ans</common:Name>
    <structure:Parent><Ref id="8"/></structure:Parent>
   </structure:Code>
  </structure:Codelist>
  <structure:Codelist id="CL_GEO_FED" agencyID="STC_CP" version="2.0">
   <common:Name xml:lang="en">Federal electoral district</common:Name>
   <common:Name xml:lang="fr">Circonscription électorale fédérale</common:Name>
   <structure:Code id="2023A000410001">
    <common:Name xml:lang="en">Avalon</common:Name>
    <common:Name xml:lang="fr">Avalon</common:Name>
   </structure:Code>
   <structure:Code id="2023A000459037">
    <common:Name xml:lang="en">Vancouver Fraserview--South Burnaby</common:Name>
    <common:Name xml:lang="fr">Vancouver Fraserview--Burnaby-Sud</common:Name>
   </structure:Code>
  </structure:Codelist>
 </structure:Codelists></message:Structures>
</message:Structure>
"""

WDS_CSV = (
    "DATAFLOW,FREQ,REF_AREA,GENDER,CHARACTERISTIC,STATISTIC,TIME_PERIOD,"
    "OBS_VALUE,DECIMALS,FLAG,TOPIC,NOTE,RELEASE_DATE,GEO_LEVEL,ALT_GEO_CODE,"
    "GEO_DESC,PROV_TERR,DATA_QUALITY_FLAG,TNR_LF,TNR_SF,CI_LOW,CI_HIGH\n"
    "STC_CP:DF_FED(2.0),A5,2023A000410001,1,8,1,2021,81735,0,,2,,2022-04-27,"
    "51,10001,2023A000410001,10,00000,3.6,2.8,,\n"
    "STC_CP:DF_FED(2.0),A5,2023A000410001,1,1,1,2021,,0,1,1,1,2022-02-09,"
    "51,10001,2023A000410001,10,00000,3.6,2.8,,\n"
    "STC_CP:DF_FED(2.0),A5,2023A000459037,1,8,1,2021,113700,0,,2,,2022-04-27,"
    "51,59037,2023A000459037,59,00000,3.1,2.4,,\n"
)


class Raw(io.BytesIO):
    """Response body that, like urllib3's, accepts decode_content."""

    decode_content = False


def make_response(body=b"", status=200, headers=None):
    if isinstance(body, str):
        body = body.encode("utf-8")
    response = MagicMock()
    response.status_code = status
    response.ok = status < 400
    response.content = body
    response.text = body.decode("utf-8", errors="replace")
    response.headers = headers or {}
    response.raw = Raw(body)
    return response


@pytest.fixture(autouse=True)
def fresh_wds_session_dir(monkeypatch):
    monkeypatch.setattr(wds, "_session_dir", None)


@pytest.fixture
def wds_api():
    session = MagicMock()

    def get(url, **kwargs):
        if "/dataflow/" in url:
            return make_response(SDMX)
        return make_response(WDS_CSV)

    session.get.side_effect = get
    with patch("pycancensus.wds.get_session", return_value=session):
        yield session


class TestWdsMetadata:
    def test_code_lists(self, wds_api):
        meta = pc.get_statcan_wds_metadata("2021", "FED")

        assert list(meta.columns) == [
            "Agency ID",
            "Codelist ID",
            "Codelist en",
            "Codelist fr",
            "ID",
            "en",
            "fr",
            "Parent ID",
        ]
        assert len(meta) == 5
        child = meta[meta["ID"] == "9"].iloc[0]
        assert child["Parent ID"] == "8"
        assert child["fr"] == "0 à 14 ans"
        assert child["Codelist fr"] == "Caractéristique"
        assert pd.isna(meta[meta["ID"] == "8"].iloc[0]["Parent ID"])

    def test_url_and_session_cache(self, wds_api):
        pc.get_statcan_wds_metadata(2021, "FED", version="1.3")
        pc.get_statcan_wds_metadata(2021, "FED", version="1.3")

        assert wds_api.get.call_count == 1
        url = wds_api.get.call_args[0][0]
        assert url == (
            "https://api.statcan.gc.ca/census-recensement/profile/sdmx/rest/"
            "dataflow/STC_CP/DF_FED/1.3?references=all"
        )
        pc.get_statcan_wds_metadata(2021, "FED", version="1.3", refresh=True)
        assert wds_api.get.call_count == 2

    @pytest.mark.parametrize(
        "year, level, message",
        [("2016", "FED", "Census year"), ("2021", "DB", "Level must be one of")],
    )
    def test_validation(self, year, level, message):
        with pytest.raises(ValueError, match=message):
            pc.get_statcan_wds_metadata(year, level)


class TestWdsData:
    def test_data_with_names(self, wds_api):
        data = pc.get_statcan_wds_data(
            ["2023A000459037", "2023A000410001"], members=[8, 1], gender="Total"
        )

        assert data["GEO_NAME"].tolist() == [
            "Avalon",
            "Avalon",
            "Vancouver Fraserview--South Burnaby",
        ]
        assert data["CHARACTERISTIC_NAME"].tolist()[:2] == [
            "Total - Age groups of the population",
            "Population, 2021",
        ]
        assert data["OBS_VALUE"].tolist()[0] == 81735
        assert pd.isna(data["OBS_VALUE"].iloc[1])
        # Like R, only OBS_VALUE is numeric, identifiers stay strings
        assert data["REF_AREA"].iloc[0] == "2023A000410001"
        assert data["PROV_TERR"].iloc[0] == "10"
        assert data["TNR_LF"].iloc[0] == "3.6"

    def test_request(self, wds_api):
        pc.get_statcan_wds_data(
            ["2023A000459037", "2023A000410001"], members=[9, 10, 8], gender="male"
        )

        data_call = wds_api.get.call_args_list[0]
        # DGUIDs and members sorted like R, members by value
        assert data_call[0][0] == (
            "https://api.statcan.gc.ca/census-recensement/profile/sdmx/rest/data/"
            "STC_CP,DF_FED/A5.2023A000410001+2023A000459037.2.8+9+10.1"
        )
        assert data_call[1]["headers"]["Accept"] == "text/csv"

    def test_all_genders_all_members_and_version(self, wds_api):
        pc.get_statcan_wds_data("2023A000410001", version="2.0")

        assert wds_api.get.call_args_list[0][0][0].endswith(
            "STC_CP,DF_FED,2.0/A5.2023A000410001...1"
        )

    def test_french_names(self, wds_api):
        data = pc.get_statcan_wds_data("2023A000459037", language="FR")

        assert "Vancouver Fraserview--Burnaby-Sud" in data["GEO_NAME"].tolist()
        assert "Total - Groupes d'âge de la population" in (
            data["CHARACTERISTIC_NAME"].tolist()
        )

    def test_language_does_not_follow_session_default(self, wds_api):
        pc.set_language("fr")
        data = pc.get_statcan_wds_data("2023A000459037")

        assert "Vancouver Fraserview--South Burnaby" in data["GEO_NAME"].tolist()

    def test_error_response_raises_and_is_not_cached(self, wds_api):
        wds_api.get.side_effect = lambda url, **kwargs: make_response(
            "NoRecordsFound", status=404
        )
        for _ in range(2):
            with pytest.raises(CensusAPIError, match="NoRecordsFound"):
                pc.get_statcan_wds_data("2013A000410001")

        assert wds_api.get.call_count == 2

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            ({"gender": "other"}, "Gender must be one of"),
            ({"language": "de"}, "Language"),
        ],
    )
    def test_validation(self, kwargs, message):
        with pytest.raises(ValueError, match=message):
            pc.get_statcan_wds_data("2023A000410001", **kwargs)

    @pytest.mark.parametrize(
        "dguid, level",
        [
            ("2021A000210", "PR"),
            ("2023A000410001", "FED"),
            ("2021S0503933", "CMACA"),
            ("2021S0504001", "CMACA"),
            ("2022A000759001", "HR"),
            ("2021S051259150001", "DA"),
            ("2021A00115910", "FSA"),
        ],
    )
    def test_level_from_dguid(self, dguid, level):
        assert wds._geo_level_from_dguid(dguid) == level


# --- GeoSuite and geographic attributes -------------------------------------

try:
    import pyarrow as pa
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - CI installs the statcan extra
    pa = pq = None

needs_pyarrow = pytest.mark.skipif(pa is None, reason="needs pyarrow")


def parquet_bytes(tmp_path, table_name="PR"):
    table = pa.table(
        {
            "PRUID": pa.array(["10", "11"]),
            "PRNAME": pa.array(["Newfoundland and Labrador", "Prince Edward Island"]),
            "PRPOP2021": pa.array([510550, None], type=pa.int32()),
            "PRAREA2021": pa.array([358170.3732, 5681.179]),
        }
    )
    columns = {
        "PRUID": {
            "label_en": "Province or territory ID",
            "label_fr": "Identificateur unique de la province ou du territoire",
            "source_field": "PRcode",
        },
        "PRNAME": {"label_en": "Province or territory name"},
        "PRPOP2021": {"label_en": "Population, 2021", "label_fr": "Population, 2021"},
    }
    table = table.replace_schema_metadata(
        {
            "title_en": f"2021 Census – GeoSuite – {table_name}",
            "attribution_en": "Statistics Canada, 2021 Census GeoSuite",
            "licence_en": "Statistics Canada Open Licence",
            "columns": json.dumps(columns),
            "primary_key": '["PRUID"]',
        }
    )
    path = tmp_path / f"{table_name}_source.parquet"
    pq.write_table(table, path)
    return path.read_bytes()


MANIFEST = {
    "directory": True,
    "metadata": {"attribution_en": "Statistics Canada"},
    "files": [
        {
            "path": "ADA.parquet",
            "size": 288073,
            "metadata": {
                "title_en": "2021 Census – GeoSuite – Aggregate dissemination areas",
                "title_fr": "Recensement de 2021 – GéoSuite – Aires de diffusion agrégées",
                "primary_key": '["ADAUID"]',
            },
        },
        {
            "path": "CMA_CA_P.parquet",
            "size": 9000,
            "metadata": {
                "title_en": "Parts of CMAs and CAs",
                "primary_key": ["CMAPUID", "PRUID"],
            },
        },
        {"path": "README.md", "size": 10, "metadata": {}},
    ],
}


@pytest.fixture
def hosted(tmp_path):
    session = MagicMock()
    files = {
        "_manifest.json": json.dumps(MANIFEST).encode(),
        "PR.parquet": parquet_bytes(tmp_path),
        "geo_attributes_1991.parquet": parquet_bytes(tmp_path, "EA"),
    }

    def get(url, **kwargs):
        name = url.rsplit("/", 1)[-1]
        if name in files:
            return make_response(files[name])
        return make_response(b"Not Found", status=404)

    session.get.side_effect = get
    with patch("pycancensus.geo_suite.get_session", return_value=session):
        yield session, files


@needs_pyarrow
class TestGeoSuite:
    def test_table_list(self, hosted):
        tables = pc.get_statcan_geo_suite(census_year=2021, language="fr", quiet=True)

        assert tables["table"].tolist() == ["ADA", "CMA_CA_P"]
        assert tables["title"].tolist() == [
            "Recensement de 2021 – GéoSuite – Aires de diffusion agrégées",
            "Parts of CMAs and CAs",
        ]
        assert tables["primary_key"].tolist() == ["ADAUID", "CMAPUID, PRUID"]
        assert tables["size"].tolist() == [288073, 9000]

    def test_read_table_with_labels_and_metadata(self, hosted, capsys):
        session, _ = hosted
        result = pc.get_statcan_geo_suite("pr", "2021", language="fr")

        assert result["PRUID"].tolist() == ["10", "11"]
        assert str(result["PRPOP2021"].dtype) == "Int32"
        assert pd.isna(result["PRPOP2021"].iloc[1])
        labels = result.attrs["column_labels"]
        assert labels["PRUID"].startswith("Identificateur unique")
        assert labels["PRNAME"] == "Province or territory name"  # English fallback
        assert "PRAREA2021" not in labels
        metadata = result.attrs["metadata"]
        assert metadata["primary_key"] == ["PRUID"]
        assert metadata["columns"]["PRUID"]["source_field"] == "PRcode"
        assert "hosted by MountainMath" in capsys.readouterr().out

        # Cached after the first download
        pc.get_statcan_geo_suite("PR", "2021", quiet=True)
        assert session.get.call_count == 1

    def test_refresh_reports_changes(self, hosted, capsys):
        session, files = hosted
        pc.get_statcan_geo_suite("PR", quiet=True)
        pc.get_statcan_geo_suite("PR", refresh=True)
        assert "has not changed" in capsys.readouterr().out

        files["PR.parquet"] = parquet_bytes(Path(pc.get_cache_path()), "PRX")
        result = pc.get_statcan_geo_suite("PR", refresh=True)
        assert "has changed" in capsys.readouterr().out
        assert "PRX" in result.attrs["metadata"]["title_en"]

    def test_failed_download_warns_and_returns_none(self, hosted):
        session, files = hosted
        del files["PR.parquet"]

        with pytest.warns(UserWarning, match="HTTP status 404. Returning None"):
            assert pc.get_statcan_geo_suite("PR", quiet=True) is None

    def test_failed_refresh_keeps_cached_data(self, hosted):
        session, files = hosted
        pc.get_statcan_geo_suite("PR", quiet=True)
        files["PR.parquet"] = b"PAR1 truncated"

        with pytest.warns(UserWarning, match="did not return a complete parquet"):
            result = pc.get_statcan_geo_suite("PR", refresh=True, quiet=True)
        assert result["PRUID"].tolist() == ["10", "11"]

    def test_aliases(self):
        assert geo_suite._geo_suite_table_name("CMACA", "2021") == "CMA_CA"
        assert geo_suite._geo_suite_table_name("loc", "2021") == "PN"
        assert geo_suite._geo_suite_table_name("CB", "2016") == "DB"

    def test_unknown_table(self):
        with pytest.raises(ValueError, match="based on enumeration areas"):
            pc.get_statcan_geo_suite("DA", "1996")
        with pytest.raises(ValueError, match="There is no XYZ table"):
            pc.get_statcan_geo_suite("XYZ")

    def test_unknown_year(self):
        with pytest.raises(ValueError, match="only available for census years"):
            pc.get_statcan_geo_suite("PR", 1991)

    def test_missing_pyarrow(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "pyarrow.parquet", None)
        with pytest.raises(ImportError, match=r"pycancensus\[statcan\]"):
            pc.get_statcan_geo_suite("PR")


@needs_pyarrow
class TestGeographicAttributes:
    def test_read(self, hosted):
        result = pc.get_statcan_geographic_attributes(1991, quiet=True)

        assert result["PRUID"].tolist() == ["10", "11"]
        assert result.attrs["metadata"]["licence_en"] == (
            "Statistics Canada Open Licence"
        )

    def test_session_language_default(self, hosted):
        pc.set_language("fr")
        result = pc.get_statcan_geographic_attributes(1991, quiet=True)

        assert result.attrs["column_labels"]["PRUID"].startswith("Identificateur")

    def test_unknown_year(self):
        with pytest.raises(ValueError, match="Only census years 1981"):
            pc.get_statcan_geographic_attributes(2020)


# --- Boundary files -----------------------------------------------------------


def shapefile_zip(tmp_path, nested=False):
    folder = tmp_path / "shape_src"
    folder.mkdir(exist_ok=True)
    gpd.GeoDataFrame(
        {"PRUID": ["10"], "PRNAME": ["Newfoundland and Labrador"]},
        geometry=[Point(-57, 49)],
        crs="EPSG:4326",
    ).to_file(folder / "lpr_000b21a_e.shp")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for path in folder.iterdir():
            name = f"lpr_000b21a_e/{path.name}" if nested else path.name
            archive.write(path, name)
    return buffer.getvalue()


@pytest.fixture
def statcan():
    session = MagicMock()
    with patch("pycancensus.statcan_downloads.get_session", return_value=session):
        yield session


CLOUDFLARE = {"cf-mitigated": "challenge", "server": "cloudflare"}


class TestGeographies:
    @pytest.mark.parametrize("nested", [False, True])
    def test_download_and_cache(self, statcan, tmp_path, nested):
        statcan.get.return_value = make_response(shapefile_zip(tmp_path, nested))

        result = pc.get_statcan_geographies("2021", "PR", quiet=True)
        assert isinstance(result, gpd.GeoDataFrame)
        assert result["PRNAME"].tolist() == ["Newfoundland and Labrador"]
        assert statcan.get.call_args[0][0] == (
            "https://www12.statcan.gc.ca/census-recensement/2021/geo/sip-pis/"
            "boundary-limites/files-fichiers/lpr_000b21a_e.zip"
        )

        pc.get_statcan_geographies(2021, "PR", quiet=True)
        assert statcan.get.call_count == 1

    @pytest.mark.parametrize(
        "level, kind, file",
        [
            ("CMACA", "cartographic", "lcma000b21a_e.zip"),
            ("POPCNTR", "digital", "lpc_000a21a_e.zip"),
            ("ADA", "digital", "lada000a21a_e.zip"),
            ("HR", "digital", "HR_000a23a_e.zip"),
        ],
    )
    def test_urls(self, statcan, level, kind, file):
        statcan.get.return_value = make_response(b"x", status=403, headers=CLOUDFLARE)
        with pytest.warns(UserWarning):
            pc.get_statcan_geographies("2021", level, type=kind, quiet=True)

        assert statcan.get.call_args[0][0].endswith(file)

    def test_cloudflare_block(self, statcan):
        statcan.get.return_value = make_response(
            b"<html>Just a moment</html>", status=403, headers=CLOUDFLARE
        )

        with pytest.warns(UserWarning, match="Cloudflare") as record:
            assert pc.get_statcan_geographies("2021", "PR", quiet=True) is None
        message = str(record[0].message)
        assert "lpr_000b21a_e.zip" in message
        assert "statcan_downloads" in message
        assert (Path(pc.get_cache_path()) / "statcan_downloads").is_dir()

    def test_manual_download_is_used_and_removed(self, statcan, tmp_path, capsys):
        downloads = Path(pc.get_cache_path()) / "statcan_downloads"
        downloads.mkdir(parents=True)
        manual = downloads / "lpr_000b21a_e.zip"
        manual.write_bytes(shapefile_zip(tmp_path))

        result = pc.get_statcan_geographies("2021", "PR")
        assert result["PRUID"].tolist() == ["10"]
        assert "Reading manually downloaded file" in capsys.readouterr().out
        assert not manual.exists()
        statcan.get.assert_not_called()

    def test_invalid_manual_download(self, statcan):
        downloads = Path(pc.get_cache_path()) / "statcan_downloads"
        downloads.mkdir(parents=True)
        (downloads / "lpr_000b21a_e.zip").write_text("<html>challenge</html>")

        with pytest.warns(UserWarning, match="not a valid zip file"):
            assert pc.get_statcan_geographies("2021", "PR", quiet=True) is None

    def test_blocked_refresh_keeps_cache(self, statcan, tmp_path):
        statcan.get.return_value = make_response(shapefile_zip(tmp_path))
        pc.get_statcan_geographies("2021", "PR", quiet=True)
        statcan.get.return_value = make_response(b"x", status=403, headers=CLOUDFLARE)

        with pytest.warns(UserWarning, match="Returning the existing cached data"):
            result = pc.get_statcan_geographies("2021", "PR", refresh=True, quiet=True)
        assert len(result) == 1

    def test_other_http_errors_raise(self, statcan):
        statcan.get.return_value = make_response(b"oops", status=500)

        with pytest.raises(RuntimeError, match="HTTP status 500"):
            pc.get_statcan_geographies("2021", "PR", quiet=True)

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            ({"census_year": "2016"}, "Census year"),
            ({"type": "vector"}, "Type must be one of"),
            ({"level": "XX"}, "Level must be one of"),
        ],
    )
    def test_validation(self, kwargs, message):
        args = {"census_year": "2021", "level": "PR", **kwargs}
        with pytest.raises(ValueError, match=message):
            pc.get_statcan_geographies(**args)
