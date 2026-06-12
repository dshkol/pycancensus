"""Tests for find_census_vectors search modes."""

from unittest.mock import patch

import pandas as pd
import pytest

from pycancensus.vectors import find_census_vectors, search_census_vectors


def make_vector_list():
    return pd.DataFrame(
        {
            "vector": [f"v_CA16_{i}" for i in range(1, 7)],
            "type": ["Total", "Total", "Female", "Male", "Total", "Total"],
            "label": [
                "Income ($)",
                "After-tax income",
                "Commute duration",
                "Commute duration",
                "Ojibway",
                "Oji-cree",
            ],
            "details": [
                "Income ($); total income",
                "Income; after-tax income of households",
                "Commuting; commute duration for females",
                "Commuting; commute duration for males",
                "Aboriginal languages; Ojibway speakers",
                "Aboriginal languages; Oji-cree speakers",
            ],
        }
    )


@pytest.fixture
def mock_vectors():
    with patch("pycancensus.vectors.list_census_vectors") as mock:
        mock.return_value = make_vector_list()
        yield mock


class TestExactSearch:
    def test_regex_metacharacters_match_literally(self, mock_vectors):
        result = find_census_vectors("income ($)", "CA16")
        assert result["vector"].tolist() == ["v_CA16_1"]

    def test_case_insensitive(self, mock_vectors):
        result = find_census_vectors("OJIBWAY", "CA16")
        assert result["vector"].tolist() == ["v_CA16_5"]

    def test_no_match_warns_and_returns_empty(self, mock_vectors):
        with pytest.warns(UserWarning, match="No exact matches"):
            result = find_census_vectors("xyzzy", "CA16")
        assert result.empty

    def test_type_filter(self, mock_vectors):
        result = find_census_vectors("commute", "CA16", type="female")
        assert result["vector"].tolist() == ["v_CA16_3"]


class TestSemanticSearch:
    def test_close_misspelling_matches(self, mock_vectors):
        # One substitution away from "ojibway"
        result = find_census_vectors(
            "ojibwey", "CA16", query_type="semantic", quiet=True
        )
        assert "v_CA16_5" in result["vector"].tolist()

    def test_distant_query_warns_and_returns_empty(self, mock_vectors):
        with pytest.warns(UserWarning, match="No close matches"):
            result = find_census_vectors(
                "zzzzqqqqxxxx", "CA16", query_type="semantic", quiet=True
            )
        assert result.empty


class TestKeywordSearch:
    def test_ranked_by_match_count(self, mock_vectors):
        result = find_census_vectors("commute duration", "CA16", query_type="keyword")
        # Both commute vectors match both words; income rows match neither
        assert set(result["vector"]) == {"v_CA16_3", "v_CA16_4"}

    def test_digit_query_does_not_match_everything(self, mock_vectors):
        with pytest.warns(UserWarning, match="No matches"):
            result = find_census_vectors("12345", "CA16", query_type="keyword")
        assert result.empty

    def test_no_match_warns(self, mock_vectors):
        with pytest.warns(UserWarning, match="No matches"):
            result = find_census_vectors("xyzzy", "CA16", query_type="keyword")
        assert result.empty


class TestValidation:
    def test_bad_type_raises(self, mock_vectors):
        with pytest.raises(ValueError, match="Type must be one of"):
            find_census_vectors("income", "CA16", type="banana")

    def test_bad_query_type_raises(self, mock_vectors):
        with pytest.raises(ValueError, match="Query type must be one of"):
            find_census_vectors("income", "CA16", query_type="banana")


class TestSearchCensusVectorsLiteral:
    def test_regex_metacharacters_match_literally(self, mock_vectors):
        result = search_census_vectors("income ($)", "CA16", quiet=True)
        assert result["vector"].tolist() == ["v_CA16_1"]
