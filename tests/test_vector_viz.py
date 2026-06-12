"""Tests for visualize_vector_hierarchy ASCII tree rendering."""

from unittest.mock import patch

import pandas as pd
import pytest

from pycancensus.vector_viz import visualize_vector_hierarchy


def make_vector_list():
    """v_CA21_1 -> (v_CA21_2 -> v_CA21_4, v_CA21_3); v_CA21_4 -> v_CA21_5."""
    return pd.DataFrame(
        {
            "vector": ["v_CA21_1", "v_CA21_2", "v_CA21_3", "v_CA21_4", "v_CA21_5"],
            "parent_vector": [None, "v_CA21_1", "v_CA21_1", "v_CA21_2", "v_CA21_4"],
            "label": ["Root", "Branch", "Leaf A", "Twig", "Leaf B"],
            "type": ["Total"] * 5,
        }
    )


@pytest.fixture
def mock_vectors():
    with patch("pycancensus.vectors.list_census_vectors") as mock:
        mock.return_value = make_vector_list()
        yield mock


def test_full_tree_rendering(mock_vectors, capsys):
    result = visualize_vector_hierarchy("v_CA21_1", quiet=True)

    out = capsys.readouterr().out
    assert "v_CA21_1: Root" in out
    assert "├── v_CA21_2: Branch" in out
    assert "└── v_CA21_3: Leaf A (leaf)" in out
    assert "│   └── v_CA21_4: Twig" in out
    assert "└── v_CA21_5: Leaf B (leaf)" in out
    # Returns root + all descendants
    assert len(result) == 5


def test_max_depth_marks_truncated_nodes(mock_vectors, capsys):
    result = visualize_vector_hierarchy("v_CA21_1", max_depth=1, quiet=True)

    out = capsys.readouterr().out
    # v_CA21_2 has children in the dataset but not in the truncated tree
    assert "v_CA21_2: Branch ..." in out
    assert "v_CA21_3: Leaf A (leaf)" in out
    assert "Twig" not in out
    assert len(result) == 3  # root + 2 direct children


def test_show_type(mock_vectors, capsys):
    visualize_vector_hierarchy("v_CA21_1", show_type=True, quiet=True)
    out = capsys.readouterr().out
    assert "v_CA21_1: Root [Total]" in out


def test_unknown_vector_raises(mock_vectors):
    with pytest.raises(ValueError, match="not found in dataset"):
        visualize_vector_hierarchy("v_CA21_999", quiet=True)


def test_dataframe_input(mock_vectors, capsys):
    df = make_vector_list()
    result = visualize_vector_hierarchy(df[df["vector"] == "v_CA21_2"], quiet=True)
    out = capsys.readouterr().out
    assert "v_CA21_2: Branch" in out
    assert len(result) == 3  # v_CA21_2 + v_CA21_4 + v_CA21_5


def test_underivable_dataset_raises():
    with pytest.raises(ValueError, match="Cannot determine dataset"):
        visualize_vector_hierarchy("notavector")
