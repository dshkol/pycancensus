"""
Tests for national-level (level='C') census data retrieval.
"""

import os
import pytest
import pandas as pd

import pycancensus as pc


@pytest.fixture(autouse=True)
def set_api_key():
    """Set API key for tests."""
    api_key = os.environ.get("CANCENSUS_API_KEY", "CensusMapper_7cb8d0ee55b67305388e0a7e8ba9c725")
    pc.set_api_key(api_key)


def test_national_level_basic():
    """Test retrieving basic national-level census data."""
    national = pc.get_census(
        dataset='CA16',
        level='C',
        regions={'C': '01'},
        vectors=['v_CA16_1'],
        labels='short',
        quiet=True,
        use_cache=False
    )

    # Should return exactly one row (Canada)
    assert len(national) == 1
    assert isinstance(national, pd.DataFrame)

    # Should have Canada as the region name
    assert 'Canada' in national['Region Name'].values

    # Should have population data
    assert national['Population'].values[0] > 30000000

    # Should have the requested vector
    assert 'v_CA16_1' in national.columns


def test_national_level_ca21():
    """Test national-level data with CA21 dataset."""
    national = pc.get_census(
        dataset='CA21',
        level='C',
        regions={'C': '01'},
        vectors=['v_CA21_1'],
        labels='short',
        quiet=True,
        use_cache=False
    )

    assert len(national) == 1
    assert 'Canada' in national['Region Name'].values
    assert national['Population'].values[0] > 35000000  # CA21 population


def test_national_level_multiple_vectors():
    """Test national-level data with multiple vectors."""
    vectors = ['v_CA16_1', 'v_CA16_2', 'v_CA16_3', 'v_CA16_4']

    national = pc.get_census(
        dataset='CA16',
        level='C',
        regions={'C': '01'},
        vectors=vectors,
        labels='short',
        quiet=True,
        use_cache=False
    )

    assert len(national) == 1

    # All requested vectors should be present
    for vector in vectors:
        assert vector in national.columns


def test_national_level_region_code_variants():
    """Test that both region code variants ('01' and '1') work."""
    # Test with '01'
    national_01 = pc.get_census(
        dataset='CA16',
        level='C',
        regions={'C': '01'},
        vectors=['v_CA16_1'],
        labels='short',
        quiet=True,
        use_cache=False
    )

    # Test with '1'
    national_1 = pc.get_census(
        dataset='CA16',
        level='C',
        regions={'C': '1'},
        vectors=['v_CA16_1'],
        labels='short',
        quiet=True,
        use_cache=False
    )

    # Both should return Canada data
    assert len(national_01) == 1
    assert len(national_1) == 1
    assert national_01['Population'].values[0] == national_1['Population'].values[0]


def test_national_baseline_comparison_pattern():
    """Test the blog post pattern: comparing regional vs national data."""
    # Get national data
    national = pc.get_census(
        dataset='CA16',
        level='C',
        regions={'C': '01'},
        vectors=['v_CA16_1', 'v_CA16_4'],  # Total population, 0-14 age
        labels='short',
        quiet=True,
        use_cache=False
    )

    # Get a regional data point (Toronto)
    toronto = pc.get_census(
        dataset='CA16',
        level='CSD',
        regions={'CSD': '3520005'},
        vectors=['v_CA16_1', 'v_CA16_4'],
        labels='short',
        quiet=True,
        use_cache=False
    )

    # Calculate proportions (pattern from 'normal-canadian-city' blog post)
    nat_prop = national['v_CA16_4'].values[0] / national['v_CA16_1'].values[0]
    tor_prop = toronto['v_CA16_4'].values[0] / toronto['v_CA16_1'].values[0]

    # Both should be reasonable proportions (children 0-14 should be 10-25% of population)
    assert 0.10 < nat_prop < 0.25
    assert 0.10 < tor_prop < 0.25

    # Can calculate difference (similarity measure)
    diff = abs(tor_prop - nat_prop)
    assert diff >= 0  # Valid calculation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
