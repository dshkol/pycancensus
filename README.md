# pycancensus

** :warning: this repo was vibecoded and is extremely likely to have bugs :warning: **


[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

Access, retrieve, and work with Canadian Census data and geography.

**pycancensus** is a Python package that provides integrated, convenient, and uniform access to Canadian Census data and geography retrieved using the CensusMapper API. This package produces analysis-ready tidy DataFrames and spatial data in multiple formats, as well as convenience functions for working with Census variables, variable hierarchies, and region selection.

## Features

* Download data and Census geography in tidy and analysis-ready format
* Convenience tools for searching for and working with Census regions and variable hierarchies  
* Provides Census geography in multiple Python spatial formats (GeoPandas)
* Provides data and geography at multiple Census geographic levels including province, Census Metropolitan Area, Census Division, Census Subdivision, Census Tract, Dissemination Areas, Enumeration Areas (for 1996), and Dissemination Blocks (for 2001-2021)
* Provides data for the 2021, 2016, 2011, 2006, 2001, and 1996 Census releases
* Access to taxfiler data at the Census Tract level for tax years 2000 through 2018

## Installation

```bash
pip install pycancensus
```

Or for development:

```bash
git clone https://github.com/dshkol/pycancensus.git
cd pycancensus
pip install -e .[dev]
```

## API Key

**pycancensus** requires a valid CensusMapper API key to use. You can obtain a free API key by [signing up](https://censusmapper.ca/users/sign_up) for a CensusMapper account. 

Set your API key as an environment variable:

```bash
export CANCENSUS_API_KEY="your_api_key_here"
```

Or set it programmatically:

```python
import pycancensus as pc
pc.set_api_key("your_api_key_here")
```

## Quick Start

```python
import pycancensus as pc

# List available datasets
datasets = pc.list_census_datasets()

# List regions for 2016 Census
regions = pc.list_census_regions("CA16")

# List available variables for 2016 Census  
vectors = pc.list_census_vectors("CA16")

# Get census data
data = pc.get_census(
    dataset="CA16",
    regions={"CMA": "59933"},  # Vancouver CMA
    vectors=["v_CA16_408", "v_CA16_409", "v_CA16_410"],
    level="CSD"
)

# Get census data with geography
geo_data = pc.get_census(
    dataset="CA16", 
    regions={"CMA": "59933"},
    vectors=["v_CA16_408", "v_CA16_409", "v_CA16_410"],
    level="CSD",
    geo_format="geopandas"
)
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Related Packages

This package is inspired by and based on the R [cancensus](https://github.com/mountainMath/cancensus) package.

## Statistics Canada Attribution

Subject to the Statistics Canada Open Data License Agreement, licensed products using Statistics Canada data should employ the following acknowledgement of source:

**Acknowledgment of Source**

(a) You shall include and maintain the following notice on all licensed rights of the Information:

- Source: Statistics Canada, name of product, reference date. Reproduced and distributed on an "as is" basis with the permission of Statistics Canada.

(b) Where any Information is contained within a Value-added Product, you shall include on such Value-added Product the following notice:

- Adapted from Statistics Canada, name of product, reference date. This does not constitute an endorsement by Statistics Canada of this product.
