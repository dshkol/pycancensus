"""
National-Level Census Data Analysis
====================================

This example demonstrates how to retrieve and analyze national-level census data
using the newly added level='C' functionality. This is particularly useful for
establishing national baselines when comparing regional data.
"""

# %%
# Setting up pycancensus
# ----------------------
#
# First, import the necessary libraries and configure the API key.

import pycancensus as pc
import pandas as pd
import os

# Set your API key
api_key = os.environ.get('CANCENSUS_API_KEY')
if api_key:
    pc.set_api_key(api_key)
    print("API key configured")
else:
    print("No API key - examples will show code structure")
    print("Get your API key at: https://censusmapper.ca/users/sign_up")

# %%
# Retrieving National-Level Data
# -------------------------------
#
# The level='C' parameter allows you to retrieve Canada-wide census data,
# which is useful for establishing national baselines.

print("\nRetrieving national-level census data:")
try:
    # Get national data for 2021 Census
    national_data = pc.get_census(
        dataset='CA21',
        level='C',
        regions={'C': '01'},  # Canada
        vectors=[
            'v_CA21_1',   # Total population
            'v_CA21_2',   # Male population
            'v_CA21_3',   # Female population
        ],
        labels='short',
        use_cache=False
    )

    print(f"\nNational Census Data (CA21):")
    print(national_data)

    # Display key statistics
    total_pop = national_data['v_CA21_1'].iloc[0]
    male_pop = national_data['v_CA21_2'].iloc[0]
    female_pop = national_data['v_CA21_3'].iloc[0]

    print(f"\nNational Statistics:")
    print(f"Total Population: {total_pop:,}")
    print(f"Male: {male_pop:,} ({male_pop/total_pop*100:.1f}%)")
    print(f"Female: {female_pop:,} ({female_pop/total_pop*100:.1f}%)")

except Exception as e:
    print(f"Error retrieving national data: {e}")

# %%
# Comparing Regional vs National Data
# ------------------------------------
#
# A common analysis pattern is to compare regional demographics against
# national baselines. This example compares Toronto's demographics with
# national averages.

print("\nComparing regional vs national demographics:")
try:
    # Get national income data
    national_income = pc.get_census(
        dataset='CA21',
        level='C',
        regions={'C': '01'},
        vectors=[
            'v_CA21_923',  # Total household income groups
            'v_CA21_939',  # $100,000 and over
        ],
        labels='short',
        use_cache=False
    )

    # Get Toronto CMA income data
    toronto_income = pc.get_census(
        dataset='CA21',
        level='CMA',
        regions={'CMA': '535'},  # Toronto CMA
        vectors=[
            'v_CA21_923',  # Total household income groups
            'v_CA21_939',  # $100,000 and over
        ],
        labels='short',
        use_cache=False
    )

    # Calculate proportions
    nat_total = national_income['v_CA21_923'].iloc[0]
    nat_high_income = national_income['v_CA21_939'].iloc[0]
    nat_prop = nat_high_income / nat_total * 100

    tor_total = toronto_income['v_CA21_923'].iloc[0]
    tor_high_income = toronto_income['v_CA21_939'].iloc[0]
    tor_prop = tor_high_income / tor_total * 100

    print(f"\nHousehold Income Comparison ($100k+):")
    print(f"National: {nat_high_income:,} / {nat_total:,} = {nat_prop:.1f}%")
    print(f"Toronto:  {tor_high_income:,} / {tor_total:,} = {tor_prop:.1f}%")
    print(f"Difference: {tor_prop - nat_prop:+.1f} percentage points")

    if tor_prop > nat_prop:
        print(f"\nToronto has a higher proportion of high-income households")
    else:
        print(f"\nToronto has a lower proportion of high-income households")

except Exception as e:
    print(f"Error in comparison analysis: {e}")

# %%
# Multi-Year National Comparison
# -------------------------------
#
# National-level data is also useful for analyzing trends over time
# across different Census years.

print("\nComparing national data across Census years:")
try:
    # Get 2021 data
    national_2021 = pc.get_census(
        dataset='CA21',
        level='C',
        regions={'C': '01'},
        vectors=['v_CA21_1'],  # Total population
        labels='short',
        use_cache=False
    )

    # Get 2016 data
    national_2016 = pc.get_census(
        dataset='CA16',
        level='C',
        regions={'C': '01'},
        vectors=['v_CA16_1'],  # Total population
        labels='short',
        use_cache=False
    )

    pop_2021 = national_2021['v_CA21_1'].iloc[0]
    pop_2016 = national_2016['v_CA16_1'].iloc[0]
    growth = pop_2021 - pop_2016
    growth_pct = (pop_2021 / pop_2016 - 1) * 100

    print(f"\nNational Population Growth (2016-2021):")
    print(f"2016: {pop_2016:,}")
    print(f"2021: {pop_2021:,}")
    print(f"Growth: {growth:,} ({growth_pct:.2f}%)")

except Exception as e:
    print(f"Error in multi-year comparison: {e}")

# %%
# Summary
# -------
#
# This example demonstrated:
#
# 1. Retrieving national-level data using level='C'
# 2. Comparing regional demographics against national baselines
# 3. Analyzing national trends across Census years
#
# National-level data is essential for contextualizing regional analyses
# and understanding how local areas compare to the country as a whole.
