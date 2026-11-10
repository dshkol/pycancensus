API Reference
=============

.. currentmodule:: pycancensus

This page contains auto-generated API reference documentation for all public functions.

Core Data Access
----------------

.. autosummary::
   :toctree: generated/

   get_census
   get_census_geometry
   get_intersecting_geometries

Dataset Management
------------------

.. autosummary::
   :toctree: generated/

   list_census_datasets
   dataset_attribution

Region Operations
-----------------

.. autosummary::
   :toctree: generated/

   list_census_regions
   search_census_regions
   as_census_region_list
   add_unique_names_to_region_list
   explore_census_regions

Vector/Variable Operations
--------------------------

.. autosummary::
   :toctree: generated/

   list_census_vectors
   search_census_vectors
   find_census_vectors
   parent_census_vectors
   child_census_vectors
   visualize_vector_hierarchy
   label_vectors
   explore_census_vectors

Statistics Canada Data
----------------------

Data straight from Statistics Canada, for geographies and tables that
CensusMapper doesn't cover. ``get_statcan_geo_suite`` and
``get_statcan_geographic_attributes`` need pyarrow
(``pip install pycancensus[statcan]``).

.. autosummary::
   :toctree: generated/

   get_statcan_wds_data
   get_statcan_wds_metadata
   get_statcan_geo_suite
   get_statcan_geographic_attributes
   get_statcan_geographies

Configuration Management
------------------------

.. autosummary::
   :toctree: generated/

   set_api_key
   get_api_key
   remove_api_key
   show_api_key
   set_cache_path
   get_cache_path
   set_user_agent_prefix
   get_user_agent
   set_language
   get_language
   set_labels
   get_labels

Cache Management
----------------

.. autosummary::
   :toctree: generated/

   list_cache
   remove_from_cache
   clear_cache
   get_recalled_database
   list_recalled_cached_data
   remove_recalled_cached_data