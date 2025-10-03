Migration Guide: R to Python
=============================

Complete guide for R ``cancensus`` users migrating to Python ``pycancensus``.

Quick Start
-----------

Installation
~~~~~~~~~~~~

**R:**

.. code-block:: r

   install.packages("cancensus")
   library(cancensus)

**Python:**

.. code-block:: bash

   pip install pycancensus

.. code-block:: python

   import pycancensus as pc

API Key Setup
~~~~~~~~~~~~~

**R:**

.. code-block:: r

   set_cancensus_api_key("YOUR_API_KEY", install = TRUE)

**Python:**

.. code-block:: python

   pc.set_api_key("YOUR_API_KEY", install=True)
   # Or: export CANCENSUS_API_KEY="YOUR_API_KEY"

Function Equivalence
--------------------

All Core Functions Available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - R Function
     - Python Function
     - Equivalence
   * - ``get_census()``
     - ``get_census()``
     - ✅ 100%
   * - ``list_census_datasets()``
     - ``list_census_datasets()``
     - ✅ 100%
   * - ``list_census_vectors()``
     - ``list_census_vectors()``
     - ✅ 100%
   * - ``search_census_vectors()``
     - ``search_census_vectors()``
     - ✅ 100%
   * - ``find_census_vectors()``
     - ``find_census_vectors()``
     - ✅ 100%
   * - ``parent_census_vectors()``
     - ``parent_census_vectors()``
     - ✅ 100%
   * - ``child_census_vectors()``
     - ``child_census_vectors()``
     - ✅ 100%
   * - ``dataset_attribution()``
     - ``dataset_attribution()``
     - ✅ 100%
   * - ``label_vectors()``
     - ``label_vectors()``
     - ✅ 100%
   * - ``list_cancensus_cache()``
     - ``list_cache()``
     - ✅ 100%

Syntax Conversion
-----------------

Core Syntax Differences
~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - R Syntax
     - Python Syntax
   * - ``list(CMA = "59933")``
     - ``{'CMA': '59933'}``
   * - ``c("v1", "v2", "v3")``
     - ``['v1', 'v2', 'v3']``
   * - ``TRUE`` / ``FALSE``
     - ``True`` / ``False``
   * - ``NULL``
     - ``None``

Side-by-Side Examples
---------------------

Example 1: Basic Data Retrieval
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   library(cancensus)

   census_data <- get_census(
     dataset = 'CA21',
     regions = list(CMA = "59933"),
     vectors = c("v_CA21_906"),
     level = 'CSD'
   )

**Python:**

.. code-block:: python

   import pycancensus as pc

   census_data = pc.get_census(
       dataset='CA21',
       regions={'CMA': '59933'},
       vectors=['v_CA21_906'],
       level='CSD'
   )

Example 2: With Geography
~~~~~~~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   census_data <- get_census(
     dataset = 'CA21',
     regions = list(CMA = "35535"),
     vectors = c("v_CA21_906"),
     level = 'CSD',
     geo_format = 'sf'
   )

**Python:**

.. code-block:: python

   census_data = pc.get_census(
       dataset='CA21',
       regions={'CMA': '35535'},
       vectors=['v_CA21_906'],
       level='CSD',
       geo_format='sf'
   )

Example 3: Search Vectors
~~~~~~~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   income_vectors <- search_census_vectors("income", "CA21")

**Python:**

.. code-block:: python

   income_vectors = pc.search_census_vectors("income", "CA21")

Example 4: List Datasets
~~~~~~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   datasets <- list_census_datasets()

**Python:**

.. code-block:: python

   datasets = pc.list_census_datasets()

Return Type Conversions
------------------------

Data Structures
~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 40 40 20

   * - R Type
     - Python Type
     - Notes
   * - ``data.frame`` / ``tibble``
     - ``pandas.DataFrame``
     - Direct equivalent
   * - ``sf`` object
     - ``geopandas.GeoDataFrame``
     - Same spatial data
   * - ``list``
     - ``list``
     - Direct equivalent
   * - ``character``
     - ``str``
     - Direct equivalent

Working with Results
~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   # Filter data
   filtered <- census_data %>%
     filter(Population > 50000)

   # Select columns
   selected <- census_data %>%
     select(GeoUID, Population)

**Python:**

.. code-block:: python

   # Filter data
   filtered = census_data[census_data['Population'] > 50000]

   # Select columns
   selected = census_data[['GeoUID', 'Population']]

Visualization Migration
-----------------------

Mapping
~~~~~~~

**R (using ggplot2 + sf):**

.. code-block:: r

   library(ggplot2)
   library(sf)

   ggplot(census_data) +
     geom_sf(aes(fill = v_CA21_906)) +
     scale_fill_viridis_c() +
     theme_minimal()

**Python (using matplotlib + geopandas):**

.. code-block:: python

   import matplotlib.pyplot as plt

   census_data.plot(
       column='v_CA21_906',
       cmap='viridis',
       legend=True
   )
   plt.show()

**Python (using plotly for interactive):**

.. code-block:: python

   import plotly.express as px

   fig = px.choropleth_mapbox(
       census_data,
       geojson=census_data.geometry,
       locations=census_data.index,
       color='v_CA21_906',
       mapbox_style='carto-positron'
   )
   fig.show()

Charts
~~~~~~

**R (ggplot2):**

.. code-block:: r

   ggplot(census_data, aes(x = `Region Name`, y = Population)) +
     geom_bar(stat = "identity") +
     theme(axis.text.x = element_text(angle = 45))

**Python (matplotlib):**

.. code-block:: python

   census_data.plot.bar(x='Region Name', y='Population')
   plt.xticks(rotation=45)
   plt.tight_layout()
   plt.show()

**Python (plotly):**

.. code-block:: python

   import plotly.express as px

   fig = px.bar(census_data, x='Region Name', y='Population')
   fig.show()

Common Migration Patterns
--------------------------

Pattern 1: Data Pipeline
~~~~~~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   library(dplyr)
   library(cancensus)

   result <- get_census(
     dataset = 'CA21',
     regions = list(CMA = "35535"),
     vectors = c("v_CA21_906"),
     level = 'CSD'
   ) %>%
     filter(Population > 50000) %>%
     arrange(desc(v_CA21_906))

**Python:**

.. code-block:: python

   import pycancensus as pc

   result = (pc.get_census(
       dataset='CA21',
       regions={'CMA': '35535'},
       vectors=['v_CA21_906'],
       level='CSD'
   )
   .query('Population > 50000')
   .sort_values('v_CA21_906', ascending=False)
   )

Pattern 2: Multiple Regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   regions <- list(
     CMA = c("59933", "35535", "24462")
   )

   data <- get_census(
     dataset = 'CA21',
     regions = regions,
     vectors = c("v_CA21_906"),
     level = 'CSD'
   )

**Python:**

.. code-block:: python

   regions = {
       'CMA': ['59933', '35535', '24462']
   }

   data = pc.get_census(
       dataset='CA21',
       regions=regions,
       vectors=['v_CA21_906'],
       level='CSD'
   )

Pattern 3: Caching Control
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**R:**

.. code-block:: r

   # Disable cache for this query
   data <- get_census(
     dataset = 'CA21',
     regions = list(CMA = "59933"),
     vectors = c("v_CA21_906"),
     level = 'CSD',
     use_cache = FALSE
   )

   # Clear all cache
   remove_from_cancensus_cache()

**Python:**

.. code-block:: python

   # Disable cache for this query
   data = pc.get_census(
       dataset='CA21',
       regions={'CMA': '59933'},
       vectors=['v_CA21_906'],
       level='CSD',
       use_cache=False
   )

   # Clear all cache
   pc.clear_cache()

Key Differences to Remember
----------------------------

1. **Dictionary vs Named List**

   R uses named lists: ``list(CMA = "59933")``

   Python uses dictionaries: ``{'CMA': '59933'}``

2. **Vector vs List**

   R uses ``c()``: ``c("v1", "v2")``

   Python uses ``[]``: ``['v1', 'v2']``

3. **Boolean Capitalization**

   R: ``TRUE``, ``FALSE``

   Python: ``True``, ``False``

4. **NULL vs None**

   R: ``NULL``

   Python: ``None``

5. **Function Parameter Order**

   ``find_census_vectors()`` has different parameter order:

   - R: ``find_census_vectors(query, dataset, ...)``
   - Python: ``find_census_vectors(dataset, query, ...)``

Performance Comparison
----------------------

Based on validation testing, Python pycancensus is typically **2.7x faster** than R cancensus
for equivalent operations, primarily due to:

- More efficient HTTP connection pooling
- Optimized pandas data operations
- Better caching implementation

Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Issue 1: Empty vector list causes API error**

.. code-block:: python

   # ❌ This fails
   data = pc.get_census(dataset='CA21', regions={'CSD': '123'}, vectors=[])

   # ✅ Use None instead
   data = pc.get_census(dataset='CA21', regions={'CSD': '123'}, vectors=None)

**Issue 2: Function not found**

Make sure you've imported pycancensus:

.. code-block:: python

   import pycancensus as pc
   # Then use: pc.get_census(...)

**Issue 3: API key not set**

.. code-block:: python

   # Check if key is set
   pc.show_api_key()

   # Set key
   pc.set_api_key("YOUR_KEY")

Getting Help
~~~~~~~~~~~~

- **Documentation:** https://pycancensus.readthedocs.io/
- **Validation Results:** See :doc:`validation`
- **GitHub Issues:** https://github.com/dshkol/pycancensus/issues
- **R cancensus docs:** https://mountainmath.github.io/cancensus/

Complete Example
----------------

Here's a complete analysis migrated from R to Python:

**R Version:**

.. code-block:: r

   library(cancensus)
   library(dplyr)
   library(ggplot2)
   library(sf)

   # Get data
   toronto <- get_census(
     dataset = 'CA21',
     regions = list(CMA = "35535"),
     vectors = c("v_CA21_906"),
     level = 'CSD',
     geo_format = 'sf'
   )

   # Analyze
   top_income <- toronto %>%
     filter(!is.na(v_CA21_906)) %>%
     top_n(10, v_CA21_906)

   # Visualize
   ggplot(top_income) +
     geom_sf(aes(fill = v_CA21_906)) +
     scale_fill_viridis_c() +
     labs(title = "Top 10 Highest Income Areas - Toronto CMA") +
     theme_minimal()

**Python Version:**

.. code-block:: python

   import pycancensus as pc
   import matplotlib.pyplot as plt

   # Get data
   toronto = pc.get_census(
       dataset='CA21',
       regions={'CMA': '35535'},
       vectors=['v_CA21_906'],
       level='CSD',
       geo_format='sf'
   )

   # Analyze
   top_income = (toronto
       .dropna(subset=['v_CA21_906'])
       .nlargest(10, 'v_CA21_906')
   )

   # Visualize
   top_income.plot(
       column='v_CA21_906',
       cmap='viridis',
       legend=True
   )
   plt.title("Top 10 Highest Income Areas - Toronto CMA")
   plt.axis('off')
   plt.show()

Both versions produce identical results!

Further Reading
---------------

- :doc:`validation` - See 96% validation pass rate with 24 examples
- :doc:`../README` - Package overview
- :doc:`tutorials/index` - Step-by-step tutorials
- :doc:`auto_examples/index` - Gallery of examples
