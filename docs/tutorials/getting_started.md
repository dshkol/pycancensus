---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.14.1
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Getting Started with pycancensus

This tutorial demonstrates the enhanced pycancensus functionality with clear hierarchy examples and real data access.

## Key Features Demonstrated:
- 📊 **list_census_vectors()** - Browse all available data variables
- 🌳 **Vector Hierarchies** - Navigate parent-child relationships
- 🔍 **find_census_vectors()** - Smart search functionality
- 📈 **Real Data Retrieval** - Get actual census data

```{note}
You'll need a free API key from [CensusMapper](https://censusmapper.ca/users/sign_up) to run these examples with real data.
```

## Setup and Installation

First, let's import pycancensus and set up our environment:

```{code-cell} python
import pycancensus
from pycancensus import (
    list_census_datasets, 
    list_census_vectors, 
    get_census,
    parent_census_vectors,
    child_census_vectors,
    find_census_vectors
)
import pandas as pd

# Set your API key (replace with your actual key)
# pycancensus.set_api_key("your_api_key_here")
print("✅ pycancensus imported successfully!")
```

## 1. Exploring Census Vectors

The `list_census_vectors()` function shows all available data variables:

```{code-cell} python
# List all vectors for 2021 Census
try:
    vectors_ca21 = list_census_vectors('CA21')
    print(f"📊 CA21 Census has {len(vectors_ca21):,} vectors available")
    print(f"📋 Columns: {list(vectors_ca21.columns)}")
    
    # Show how many vectors have parent relationships
    with_parents = vectors_ca21[vectors_ca21['parent_vector'].notna()]
    print(f"🔗 Vectors with parent relationships: {len(with_parents):,} out of {len(vectors_ca21):,}")
    print("\nSample hierarchy examples:")
    display(with_parents[['vector', 'parent_vector', 'label']].head())
    
except Exception as e:
    print(f"Error: {e}")
    print("Make sure you have set your API key!")
```

## 2. Vector Hierarchy Navigation

Unlike previous versions with limited hierarchy examples, pycancensus now provides clear parent-child relationships:

```{code-cell} python
try:
    # Find the age total vector (this is our ROOT)
    age_total = vectors_ca21[vectors_ca21['label'] == 'Total - Age'].iloc[0]
    print(f"🌳 Age Demographics Hierarchy\n")
    print(f"📊 ROOT: {age_total['vector']} - {age_total['label']}")
    print(f"\n📊 LEVEL 1 - Major Age Groups:")
    
    # Get its direct children (major age groups)
    age_children = child_census_vectors(age_total['vector'], 'CA21')
    display(age_children[['vector', 'label', 'parent_vector']])
    
except Exception as e:
    print(f"Error exploring hierarchy: {e}")
```

### Drilling Down Further

```{code-cell} python
try:
    # Drill down into 0-14 age group
    child_ages = child_census_vectors('v_CA21_11', 'CA21')
    print(f"📊 LEVEL 2 - Detailed breakdown of '0 to 14 years' (v_CA21_11):")
    display(child_ages[['vector', 'label', 'parent_vector']])
    
    # Even more detailed: individual years
    detailed_ages = child_census_vectors('v_CA21_14', 'CA21')
    print(f"📊 LEVEL 3 - Individual years for '0 to 4 years' (v_CA21_14):")
    display(detailed_ages[['vector', 'label', 'parent_vector']])
    
except Exception as e:
    print(f"Error exploring detailed hierarchy: {e}")
```

### Finding Parent Vectors

You can also navigate **upward** in the hierarchy:

```{code-cell} python
try:
    # Find parent of a specific vector
    parent = parent_census_vectors('v_CA21_17', 'CA21')  # Under 1 year
    print(f"⬆️  Finding parent of 'Under 1 year' (v_CA21_17):")
    display(parent[['vector', 'label', 'parent_vector']])
    
except Exception as e:
    print(f"Error finding parent: {e}")
```

## 3. Enhanced Vector Search

The `find_census_vectors()` function provides smart search with relevance scoring:

```{code-cell} python
try:
    # Search for income-related vectors
    income_vectors = find_census_vectors('CA21', 'income')
    print(f"🔍 Found {len(income_vectors)} income-related vectors")
    print(f"\nTop income vectors (sorted by relevance):")
    display(income_vectors[['vector', 'label', 'relevance_score']].head(3))
    
except Exception as e:
    print(f"Error searching vectors: {e}")
```

## 4. Real Data Retrieval

Finally, let's get actual census data using our hierarchy vectors:

```{code-cell} python
try:
    # Get real data for Toronto CMA using our hierarchy vectors
    toronto_data = get_census(
        dataset='CA21',
        regions={'cma': '535'},  # Toronto CMA
        vectors=['v_CA21_8', 'v_CA21_11', 'v_CA21_68', 'v_CA21_251'],
        level='cma',
        use_cache=False
    )
    
    print(f"📈 Toronto CMA Age Demographics:")
    print(f"\nAge Distribution:")
    total_pop = toronto_data['v_CA21_8'].iloc[0]
    age_0_14 = toronto_data['v_CA21_11'].iloc[0]
    age_15_64 = toronto_data['v_CA21_68'].iloc[0] 
    age_65_plus = toronto_data['v_CA21_251'].iloc[0]
    
    print(f"• 0-14 years: {age_0_14:,} ({age_0_14/total_pop*100:.1f}%)")
    print(f"• 15-64 years: {age_15_64:,} ({age_15_64/total_pop*100:.1f}%)")
    print(f"• 65+ years: {age_65_plus:,} ({age_65_plus/total_pop*100:.1f}%)")
    print(f"• TOTAL: {total_pop:,}")
    
except Exception as e:
    print(f"Error retrieving data: {e}")
    print("This requires a valid API key and internet connection")
```

## Summary

✅ **This tutorial demonstrates the enhanced pycancensus capabilities:**

1. **list_census_vectors()** - Browse 7,709+ available variables with explicit parent-child relationships
2. **Hierarchy Navigation** - Navigate through age demographics from broad categories to individual years
3. **parent_census_vectors()** & **child_census_vectors()** - Navigate up and down the hierarchy
4. **find_census_vectors()** - Smart search with relevance scoring 
5. **Real Data** - Actual census data retrieved and analyzed

🎯 **Key Improvement**: Unlike previous versions, these hierarchy functions now work with **clear, well-defined parent-child relationships** in the census data structure.

### Next Steps:
- Explore other hierarchies (income, education, housing)
- Try different geographic levels (province, census division, etc.)
- Use `geo_format='geopandas'` for spatial analysis
- Check out the gallery examples for more advanced use cases

### Getting Help

- **Documentation**: Explore the API reference and other tutorials
- **Examples**: Browse the example gallery for specific use cases
- **Issues**: Report problems on [GitHub](https://github.com/dshkol/pycancensus/issues)
- **API Key**: Get your free key at [CensusMapper](https://censusmapper.ca/users/sign_up)