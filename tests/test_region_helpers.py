"""Tests for region-list helper functions."""

import pandas as pd
import pytest

from pycancensus.regions import (
    add_unique_names_to_region_list,
    as_census_region_list,
)


def make_region_list():
    return pd.DataFrame(
        {
            "region": ["5915022", "3520005", "5917034", "5915025", "5915804"],
            "name": ["Vancouver", "Toronto", "Victoria", "Langley", "Langley"],
            "level": ["CSD", "CSD", "CSD", "CSD", "CSD"],
            "municipal_status": ["CY", "C", "CY", "CY", "DM"],
            "pop": [662248, 2794356, 91867, 28963, 132603],
        }
    )


class TestAsCensusRegionList:
    def test_groups_by_level(self):
        df = pd.DataFrame(
            {
                "region": ["59", "5915022", "3520005"],
                "level": ["PR", "CSD", "CSD"],
                "name": ["BC", "Vancouver", "Toronto"],
            }
        )
        result = as_census_region_list(df)
        assert result == {"PR": ["59"], "CSD": ["5915022", "3520005"]}

    def test_regions_coerced_to_str(self):
        df = pd.DataFrame({"region": [59, 35], "level": ["PR", "PR"]})
        assert as_census_region_list(df) == {"PR": ["59", "35"]}

    def test_missing_columns_raises(self):
        with pytest.raises(ValueError, match="list_census_regions"):
            as_census_region_list(pd.DataFrame({"GeoUID": ["59"]}))

    def test_roundtrip_works_with_get_census_format(self):
        regions = as_census_region_list(make_region_list())
        assert set(regions) == {"CSD"}
        assert len(regions["CSD"]) == 5


class TestAddUniqueNames:
    def test_unique_names_unchanged(self):
        result = add_unique_names_to_region_list(make_region_list())
        assert result.loc[result["region"] == "5915022", "Name"].iloc[0] == "Vancouver"

    def test_duplicates_get_municipal_status(self):
        result = add_unique_names_to_region_list(make_region_list())
        langley_names = set(result.loc[result["name"] == "Langley", "Name"])
        assert langley_names == {"Langley (CY)", "Langley (DM)"}

    def test_still_duplicated_names_get_region_id(self):
        df = make_region_list()
        # Make both Langleys the same municipal status so status alone
        # cannot disambiguate
        df["municipal_status"] = "CY"
        result = add_unique_names_to_region_list(df)
        langley_names = set(result.loc[result["name"] == "Langley", "Name"])
        assert langley_names == {
            "Langley (CY) (5915025)",
            "Langley (CY) (5915804)",
        }

    def test_original_columns_preserved(self):
        result = add_unique_names_to_region_list(make_region_list())
        for col in ["region", "name", "level", "municipal_status", "pop"]:
            assert col in result.columns

    def test_missing_columns_raises(self):
        with pytest.raises(ValueError, match="list_census_regions"):
            add_unique_names_to_region_list(pd.DataFrame({"name": ["a"]}))
