# pycancensus Package Structure and Build Configuration

This document explains how the pycancensus package is structured and how tests/development content is excluded from library distributions.

## Python Packaging Exclusion Methods (Python's equivalent to R's .Rbuildignore)

### 1. **pyproject.toml Configuration**
- **Primary packaging configuration** using modern Python standards
- **`[tool.setuptools.exclude-package-data]`** - Excludes test directories from builds
- **`[tool.pytest.ini_options]`** - Excludes cross-validation tests from normal test runs
- **`[project.optional-dependencies]`** - Separates cross-validation dependencies

### 2. **MANIFEST.in** 
- **Controls source distribution contents** (equivalent to R's .Rbuildignore)
- **`prune tests`** - Excludes entire tests directory from source distributions
- **`prune tests/cross_validation`** - Specifically excludes cross-validation framework

### 3. **setup.py**
- **`find_packages(exclude=["tests*", ...])`** - Excludes test packages from wheel builds
- **Compatibility layer** for older packaging tools

### 4. **.gitignore**
- **Version control exclusions** for temporary files and build artifacts
- **Excludes cross-validation results** and R temporary files

## Directory Structure

```
pycancensus/
├── pycancensus/                    # ✅ INCLUDED in distribution
│   ├── __init__.py
│   ├── core.py
│   ├── datasets.py
│   ├── regions.py
│   ├── vectors.py
│   ├── geometry.py
│   ├── cache.py
│   ├── settings.py
│   ├── utils.py
│   └── cli.py
├── examples/                       # ✅ INCLUDED (selected files only)
│   ├── basic_usage.py
│   └── getting_started.ipynb
├── tests/                          # ❌ EXCLUDED from distribution
│   ├── __init__.py
│   ├── test_basic.py               # Regular unit tests
│   ├── integration/                # Integration tests (dev only)
│   │   └── test_cancensus_compatibility.py
│   └── cross_validation/           # ❌ EXCLUDED - Cross-validation framework
│       ├── README.md
│       ├── requirements.txt
│       ├── install_r_deps.R
│       ├── run_all_tests.sh
│       ├── utils/
│       │   ├── r_python_bridge.py
│       │   ├── data_comparison.py
│       │   └── test_runner.py
│       ├── tests/
│       │   └── test_api_equivalence.py
│       ├── results/                # Test outputs (gitignored)
│       ├── ANALYSIS_REPORT.md
│       ├── IMPLEMENTATION_GUIDE.md
│       └── FINAL_TEST_RESULTS.md
├── docs/                           # ✅ INCLUDED (if present)
├── pyproject.toml                  # ✅ INCLUDED - Main packaging config
├── setup.py                       # ✅ INCLUDED - Compatibility setup
├── MANIFEST.in                     # ✅ INCLUDED - Distribution control
├── README.md                       # ✅ INCLUDED
├── LICENSE                         # ✅ INCLUDED
├── requirements.txt                # ✅ INCLUDED
├── requirements-dev.txt            # ✅ INCLUDED
└── PACKAGE_STRUCTURE.md            # ✅ INCLUDED - This file
```

## Package Installation Scenarios

### 1. **Regular User Installation**
```bash
pip install pycancensus
```
**Includes**: Core library only (`pycancensus/` package)  
**Excludes**: All tests, cross-validation framework, development tools

### 2. **Development Installation**
```bash
pip install -e .[dev]
```
**Includes**: Core library + basic development dependencies  
**Excludes**: Cross-validation framework (rpy2, R dependencies)

### 3. **Full Development with Cross-Validation**
```bash
pip install -e .[cross-validation]
```
**Includes**: Core library + cross-validation dependencies (rpy2, etc.)  
**Note**: Still excludes test files from wheel builds

### 4. **Development from Source**
```bash
git clone repo && cd pycancensus && pip install -e .
```
**Includes**: Everything in git repository (for development)  
**Tests available**: Can run both regular and cross-validation tests

## Test Execution

### 1. **Regular Tests Only**
```bash
pytest                              # Runs tests/, excludes cross_validation/
pytest tests/test_basic.py          # Unit tests
pytest tests/integration/           # Integration tests
```

### 2. **Cross-Validation Tests** (Development Only)
```bash
cd tests/cross_validation
./run_all_tests.sh                  # Full R-Python comparison
pytest tests/                       # Cross-validation specific tests
```

### 3. **All Tests** (Override Exclusion)
```bash
pytest tests/ --ignore=            # Remove pytest exclusions
```

## Verification Commands

### Check Package Contents
```bash
# What gets included in distribution
python -c "import setuptools; print(setuptools.find_packages())"

# What gets excluded  
python -c "import setuptools; print(setuptools.find_packages(include=['tests*']))"
```

### Test Exclusion Verification
```bash
# Should only show regular tests, not cross_validation
pytest --collect-only tests/

# Should show cross_validation tests
pytest --collect-only tests/cross_validation/tests/
```

### Build Verification
```bash
# Create source distribution (tests should be excluded)
python -m build --sdist

# Create wheel (only pycancensus package should be included)
python -m build --wheel
```

## Configuration Files Summary

| File | Purpose | Exclusion Method |
|------|---------|------------------|
| `pyproject.toml` | Modern Python packaging | `[tool.setuptools.exclude-package-data]` |
| `MANIFEST.in` | Source distribution control | `prune tests/cross_validation` |
| `setup.py` | Legacy compatibility | `find_packages(exclude=["tests*"])` |
| `.gitignore` | Version control | Ignores build artifacts, temp files |

## Benefits of This Structure

1. **Clean Distribution**: End users get only the core library
2. **Developer Access**: Full testing framework available in development
3. **Separation of Concerns**: Cross-validation is development-only tooling
4. **Standard Compliance**: Uses modern Python packaging best practices
5. **Flexible Installation**: Optional dependencies for different use cases
6. **CI/CD Friendly**: Tests can be run in different configurations

This structure ensures that the cross-validation framework and development tests are available for library maintainers while keeping the distributed package clean and minimal for end users.