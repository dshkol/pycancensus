"""Tests for vector hierarchy traversal in pycancensus.hierarchy."""

from unittest.mock import patch

import pandas as pd
import pytest

from pycancensus.hierarchy import child_census_vectors, parent_census_vectors


def make_vector_list():
    """Build a small synthetic hierarchy.

    v_CA21_1
    ├── v_CA21_2
    │   ├── v_CA21_4
    │   └── v_CA21_5
    │       └── v_CA21_6
    └── v_CA21_3
    v_CA21_7 (separate root)
    """
    return pd.DataFrame(
        {
            "vector": [f"v_CA21_{i}" for i in range(1, 8)],
            "parent_vector": [
                None,
                "v_CA21_1",
                "v_CA21_1",
                "v_CA21_2",
                "v_CA21_2",
                "v_CA21_5",
                None,
            ],
            "label": [f"Label {i}" for i in range(1, 8)],
            "type": ["Total"] * 7,
        }
    )


@pytest.fixture
def mock_vectors():
    with patch("pycancensus.vectors.list_census_vectors") as mock:
        mock.return_value = make_vector_list()
        yield mock


class TestParentCensusVectors:
    def test_full_ancestry_returned(self, mock_vectors):
        result = parent_census_vectors("v_CA21_6")
        # Full chain up to the root, not just the direct parent
        assert result["vector"].tolist() == ["v_CA21_5", "v_CA21_2", "v_CA21_1"]

    def test_root_has_no_parents(self, mock_vectors):
        result = parent_census_vectors("v_CA21_1")
        assert result.empty

    def test_multiple_inputs_deduplicate_ancestors(self, mock_vectors):
        result = parent_census_vectors(["v_CA21_4", "v_CA21_5"])
        assert result["vector"].tolist() == ["v_CA21_2", "v_CA21_1"]

    def test_dataframe_input(self, mock_vectors):
        df = make_vector_list()
        result = parent_census_vectors(df[df["vector"] == "v_CA21_6"])
        assert result["vector"].tolist() == ["v_CA21_5", "v_CA21_2", "v_CA21_1"]

    def test_mixed_dataset_input_errors(self, mock_vectors):
        with pytest.raises(ValueError, match="Unable to determine dataset"):
            parent_census_vectors(["v_CA21_6", "v_CA16_2510"])

    def test_empty_input(self, mock_vectors):
        assert parent_census_vectors([]).empty


class TestChildCensusVectors:
    def test_full_descendants_returned(self, mock_vectors):
        result = child_census_vectors("v_CA21_1")
        # BFS discovery order: direct children, then grandchildren, etc.
        assert result["vector"].tolist() == [
            "v_CA21_2",
            "v_CA21_3",
            "v_CA21_4",
            "v_CA21_5",
            "v_CA21_6",
        ]

    def test_leaf_has_no_children(self, mock_vectors):
        assert child_census_vectors("v_CA21_6").empty

    def test_max_level_limits_depth(self, mock_vectors):
        result = child_census_vectors("v_CA21_1", max_level=1)
        assert result["vector"].tolist() == ["v_CA21_2", "v_CA21_3"]

    def test_leaves_only(self, mock_vectors):
        result = child_census_vectors("v_CA21_1", leaves_only=True)
        # v_CA21_2 and v_CA21_5 are internal nodes and are excluded
        assert result["vector"].tolist() == ["v_CA21_3", "v_CA21_4", "v_CA21_6"]

    def test_keep_parent_includes_input(self, mock_vectors):
        result = child_census_vectors("v_CA21_2", keep_parent=True)
        assert result["vector"].tolist() == [
            "v_CA21_2",
            "v_CA21_4",
            "v_CA21_5",
            "v_CA21_6",
        ]

    def test_mixed_dataset_input_errors(self, mock_vectors):
        with pytest.raises(ValueError, match="Unable to determine dataset"):
            child_census_vectors(["v_CA21_1", "v_CA16_2510"])

    def test_explicit_dataset_skips_inference(self, mock_vectors):
        result = child_census_vectors("v_CA21_1", dataset="CA21", max_level=1)
        assert len(result) == 2
