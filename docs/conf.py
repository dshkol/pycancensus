# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
project = 'pycancensus'
copyright = '2024, Dmitry Shkolnik'
author = 'Dmitry Shkolnik'
release = '0.1.0'

# Check if we're building on Read the Docs
on_rtd = os.environ.get('READTHEDOCS') == 'True'

# Configure for RTD environment
if on_rtd:
    # Mock imports for packages that might cause issues on RTD
    autodoc_mock_imports = []
    
    # Set environment variables for better RTD compatibility
    os.environ['MPLBACKEND'] = 'Agg'  # Use non-interactive backend
    
    # Disable problematic extensions on RTD if needed
    print("Building on Read the Docs - using RTD-optimized configuration")

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx_gallery.gen_gallery',
    'myst_nb',
    'sphinx_copybutton',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output ------------------------------------------------
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# -- Extension configuration -------------------------------------------------

# Autosummary
autosummary_generate = True
autosummary_imported_members = True

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False

# MyST-NB settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "html_admonition",
    "html_image",
    "linkify",
    "replacements",
    "smartquotes",
    "substitution",
    "tasklist",
]

nb_execution_mode = "auto"
nb_execution_timeout = 300

# Sphinx Gallery configuration
sphinx_gallery_conf = {
    'examples_dirs': 'examples',
    'gallery_dirs': 'auto_examples',
    'filename_pattern': r'^plot_',
    'remove_config_comments': True,
    'plot_gallery': 'True',
    'backreferences_dir': 'gen_modules/backreferences',
    'doc_module': ('pycancensus',),
    'reference_url': {
        'pycancensus': None,  # The module you locally document
    },
    'expected_failing_examples': [],
    'first_notebook_cell': (
        "# This cell is added by sphinx-gallery\n"
        "# It can be customized to whatever you like\n"
        "%matplotlib inline"
    ),
    # Don't execute examples on RTD if they require API keys
    'plot_gallery': 'False' if on_rtd else 'True',
}

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'geopandas': ('https://geopandas.org/en/stable/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
}

# Doctest configuration
doctest_global_setup = """
import pycancensus
"""