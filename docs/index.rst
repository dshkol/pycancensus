pycancensus: Canadian Census Data in Python
===========================================

**pycancensus** provides a Python interface to access Canadian Census data and geographies, 
offering a Python equivalent to the R `cancensus` package.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tutorials/index
   auto_examples/index
   validation
   migration
   api/index

Key Features
------------

* Access to Canadian Census data through Statistics Canada's API
* Geographic data integration with Census boundaries  
* Data caching for improved performance
* Compatible with pandas and geopandas workflows
* Command-line interface for quick data access

Quick Start
-----------

Install pycancensus:

.. code-block:: bash

   pip install pycancensus

Get started with basic census data:

.. code-block:: python

   import pycancensus as pycan
   
   # Set your API key
   pycan.set_api_key("your_api_key_here")
   
   # Get census data
   data = pycan.get_census(
       dataset="CA21",
       regions={"CMA": "59933"},  # Vancouver CMA
       vectors=["v_CA21_1"]       # Population
   )

Installation
------------

Install from PyPI:

.. code-block:: bash

   pip install pycancensus

For development:

.. code-block:: bash

   git clone https://github.com/dshkol/pycancensus
   cd pycancensus
   pip install -e .[dev,docs]

Contributing
------------

Contributions are welcome! Please see our `GitHub repository <https://github.com/dshkol/pycancensus>`_ 
for more information.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`