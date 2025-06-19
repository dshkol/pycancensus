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
    # Find household income vector (this is our ROOT with real hierarchy)
    income_root = "v_CA21_923"  # Household total income groups in 2020
    
    # Get the vector details for context
    income_info = vectors_ca21[vectors_ca21['vector'] == income_root]
    if not income_info.empty:
        print(f"🌳 Household Income Hierarchy\n")
        print(f"📊 ROOT: {income_root} - {income_info['label'].iloc[0][:50]}...")
        print(f"\n📊 LEVEL 1 - Income Brackets:")
    
    # Get its direct children (income brackets)
    income_children = child_census_vectors(income_root, 'CA21')
    display(income_children[['vector', 'label', 'parent_vector']].head(8))  # Show first 8 brackets
    
except Exception as e:
    print(f"Error exploring hierarchy: {e}")
```

### Drilling Down Further

```{code-cell} python
try:
    # Drill down into the high-income bracket (shows grandparent -> parent -> child)
    high_income_bracket = "v_CA21_939"  # $100,000 and over
    print(f"📊 LEVEL 2 - High-income sub-categories for '{high_income_bracket}':")
    
    # Get the children of the $100,000+ bracket
    high_income_subcats = child_census_vectors(high_income_bracket, 'CA21')
    display(high_income_subcats[['vector', 'label', 'parent_vector']])
    
    # Show the parent relationship for context
    parent_info = parent_census_vectors(high_income_bracket, 'CA21')
    if not parent_info.empty:
        print(f"\n⬆️  Parent of this bracket: {parent_info['vector'].iloc[0]} - {parent_info['label'].iloc[0][:50]}...")
    
except Exception as e:
    print(f"Error exploring detailed hierarchy: {e}")
```

### Finding Parent Vectors

You can also navigate **upward** in the hierarchy:

```{code-cell} python
try:
    # Find parent of a specific income bracket
    income_bracket = "v_CA21_942"  # $150,000 to $199,999
    parent = parent_census_vectors(income_bracket, 'CA21')
    print(f"⬆️  Finding parent of income bracket '{income_bracket}':")
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
    # Get real data for Toronto CMA using our income hierarchy vectors
    toronto_data = get_census(
        dataset='CA21',
        regions={'cma': '535'},  # Toronto CMA
        vectors=['v_CA21_923', 'v_CA21_939', 'v_CA21_942', 'v_CA21_943'],  # Income categories
        level='cma',
        use_cache=False
    )
    
    print(f"📈 Toronto CMA Income Demographics:")
    print(f"\nHousehold Income Distribution:")
    total_households = toronto_data['v_CA21_923'].iloc[0]
    high_income = toronto_data['v_CA21_939'].iloc[0]  # $100,000+
    very_high_1 = toronto_data['v_CA21_942'].iloc[0]  # $150,000-$199,999
    very_high_2 = toronto_data['v_CA21_943'].iloc[0]  # $200,000+
    
    print(f"• Total households: {total_households:,}")
    print(f"• $100,000+ income: {high_income:,} ({high_income/total_households*100:.1f}%)")
    print(f"  - $150,000-$199,999: {very_high_1:,} ({very_high_1/total_households*100:.1f}%)")
    print(f"  - $200,000+: {very_high_2:,} ({very_high_2/total_households*100:.1f}%)")
    
except Exception as e:
    print(f"Error retrieving data: {e}")
    print("This requires a valid API key and internet connection")
```

## Summary

✅ **This tutorial demonstrates the enhanced pycancensus capabilities:**

1. **list_census_vectors()** - Browse 7,709+ available variables with explicit parent-child relationships
2. **Hierarchy Navigation** - Navigate through income hierarchies from main categories to detailed brackets
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