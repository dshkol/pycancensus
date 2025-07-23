# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development Setup
```bash
# Install for development with all dependencies
pip install -e .[dev]

# Install with specific extras
pip install -e .[docs]              # Documentation dependencies
pip install -e .[cross-validation]  # R comparison tools
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pycancensus --cov-report=xml

# Run specific test categories
pytest tests/test_basic.py
pytest tests/integration/
pytest tests/performance/

# Run R cross-validation tests (requires R and rpy2)
pytest tests/cross_validation/test_r_equivalence.py --ignore-pytest-ini
```

### Code Quality
```bash
# Format code
black pycancensus

# Check formatting without changing files
black --check pycancensus

# Lint code
flake8 pycancensus --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 pycancensus --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
```

### Documentation
```bash
# Build documentation
cd docs && make html

# Check for broken links
cd docs && make linkcheck

# Clean and rebuild
cd docs && make clean html
```

### API Key Setup
```bash
# Set CensusMapper API key
export CANCENSUS_API_KEY="your_api_key_here"
```

## Architecture

### Core Design Principles
- **R Compatibility**: Mirror the R cancensus library's function signatures and behavior
- **Production Grade**: Enterprise-level error handling, retries, and rate limiting
- **Analysis Ready**: Return pandas/GeoPandas DataFrames ready for analysis
- **Performance**: Connection pooling, caching, and progress indicators for large operations

### Module Structure
- `core.py`: Main `get_census()` function that retrieves census data
- `datasets.py`: List available census datasets (CA21, CA16, etc.)
- `regions.py`: List and search geographic regions
- `vectors.py`: List, search, and find census variables
- `hierarchy.py`: Navigate parent/child relationships between variables
- `geometry.py`: Handle geographic data and spatial operations
- `cache.py`: Caching system to minimize API calls
- `settings.py`: API key and configuration management
- `resilience.py`: Error handling, retry logic, rate limiting
- `progress.py`: Progress bars for long-running operations
- `utils.py`: Shared utility functions
- `cli.py`: Command-line interface

### Key Technical Details

#### API Integration
- All API calls go through `resilience.py` for error handling
- Automatic retry with exponential backoff on failures
- Rate limiting respects CensusMapper API constraints
- Connection pooling for improved performance

#### Data Processing
- Census data returned as pandas DataFrames
- Geographic data returned as GeoPandas GeoDataFrames
- Handles census-specific NA values correctly
- Column naming matches R cancensus for compatibility

#### Caching Strategy
- File-based caching in `~/.pycancensus/cache/`
- Cache keys based on request parameters
- Automatic cache invalidation after 30 days
- Option to disable caching per request

#### Error Handling
- Custom exception hierarchy in `resilience.py`
- Helpful error messages with suggestions
- Special handling for rate limits with retry-after headers
- Connection error resilience with retry logic

### Testing Approach
- Unit tests mock API responses for reliability
- Integration tests use real API calls (requires API key)
- Cross-validation tests ensure R equivalence
- Performance tests verify handling of large datasets

### Important Patterns
- Always check for existing API key before making requests
- Use progress bars for operations over 100 items
- Return consistent DataFrame structures across all functions
- Maintain exact R function signatures for compatibility

## New Functions Added

### dataset_attribution()
- **Location**: `pycancensus/datasets.py`
- **Purpose**: Get combined attribution text for multiple datasets, merging similar attributions that only differ by year
- **Usage**: `pc.dataset_attribution(['CA16', 'CA21'])`
- **Testing**: Comprehensive cross-validation with R cancensus shows perfect equivalence

### label_vectors() 
- **Location**: `pycancensus/vectors.py`
- **Purpose**: Extract census vector metadata from DataFrames returned by get_census()
- **Usage**: `pc.label_vectors(census_data)` where census_data was retrieved with vectors
- **Implementation**: Stores metadata in DataFrame.attrs['census_vectors'] attribute
- **Testing**: Works with both regular and GeoDataFrames, handles short/detailed labels

### get_intersecting_geometries() (Partial Implementation)
- **Location**: `pycancensus/intersect_geometry.py` 
- **Purpose**: Find census regions that intersect with given geometries
- **Status**: Implementation complete but API endpoint requires premium access
- **Note**: Function framework ready for when API access is available

## Cross-Validation Results

The comprehensive cross-validation test suite reveals:

### ✅ Perfect Equivalence
- `list_census_datasets()`: 100% equivalent with R
- `dataset_attribution()`: 100% equivalent with R  
- `list_census_vectors()`: 100% equivalent with R

### ⚠️ Known Differences
- `search_census_vectors()`: Python returns more results (broader search)
- `get_census()`: Python includes additional metadata columns
- `list_census_regions()`: API endpoint differences between implementations

### Test Coverage
- **15 comprehensive cross-validation tests** covering major functions
- **Unit tests** for new functions with edge cases
- **Integration tests** ensuring functions work together
- **Performance tests** for large datasets