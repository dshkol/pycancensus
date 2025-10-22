# Publishing pycancensus to PyPI

This guide walks through publishing pycancensus to PyPI, making it installable via `pip`, `uv`, and other Python package managers.

## Prerequisites

### 1. PyPI Account Setup

Create accounts on both TestPyPI (for testing) and PyPI (for production):

**TestPyPI** (for testing):
1. Go to https://test.pypi.org/account/register/
2. Create an account and verify your email
3. Enable 2FA (required for publishing)
4. Generate an API token:
   - Go to Account Settings → API tokens
   - Click "Add API token"
   - Name: "pycancensus-test"
   - Scope: "Entire account" or specific to "pycancensus"
   - Save the token (starts with `pypi-`)

**PyPI** (production):
1. Go to https://pypi.org/account/register/
2. Create an account and verify your email
3. Enable 2FA (required for publishing)
4. Generate an API token:
   - Go to Account Settings → API tokens
   - Click "Add API token"
   - Name: "pycancensus"
   - Scope: "Entire account" (or specific after first upload)
   - Save the token

### 2. Install Build Tools

```bash
# Install build and publishing tools
pip install --upgrade build twine
```

## Pre-Publication Checklist

Before publishing, verify:

- [ ] Version number updated in `pyproject.toml`
- [ ] Version number updated in `pycancensus/__init__.py`
- [ ] CHANGELOG.md updated with release notes
- [ ] All tests passing: `pytest`
- [ ] Code formatted: `black --check pycancensus`
- [ ] No linting errors: `flake8 pycancensus`
- [ ] Documentation builds: `cd docs && make html`
- [ ] README.md is up to date
- [ ] LICENSE file present
- [ ] All commits pushed to GitHub

## Step 1: Update Version Number

Edit `pyproject.toml`:

```toml
[project]
name = "pycancensus"
version = "0.1.0"  # Update this for each release
```

Edit `pycancensus/__init__.py`:

```python
__version__ = "0.1.0"  # Must match pyproject.toml
```

Update `CHANGELOG.md`:

```markdown
## [0.1.0] - 2025-10-21

### Added
- Initial public release
- Full R cancensus equivalence
[... rest of changelog ...]
```

Commit the version bump:

```bash
git add pyproject.toml pycancensus/__init__.py CHANGELOG.md
git commit -m "Bump version to 0.1.0 for initial release"
git tag -a v0.1.0 -m "Version 0.1.0 - Initial public release"
git push origin main --tags
```

## Step 2: Build Distribution Files

Clean any previous builds:

```bash
# Remove old build artifacts
rm -rf dist/ build/ *.egg-info
```

Build the package:

```bash
# Build source distribution and wheel
python -m build
```

This creates:
- `dist/pycancensus-0.1.0.tar.gz` (source distribution)
- `dist/pycancensus-0.1.0-py3-none-any.whl` (wheel)

Verify the contents:

```bash
# Check what's in the wheel
unzip -l dist/pycancensus-0.1.0-py3-none-any.whl

# Check what's in the source distribution
tar -tzf dist/pycancensus-0.1.0.tar.gz
```

## Step 3: Test Upload to TestPyPI

First, test the upload process using TestPyPI:

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*
```

You'll be prompted for credentials:
- Username: `__token__`
- Password: Your TestPyPI API token (pypi-...)

Or configure credentials to avoid prompts:

```bash
# Create ~/.pypirc
cat > ~/.pypirc << 'EOF'
[testpypi]
username = __token__
password = pypi-YOUR_TESTPYPI_TOKEN_HERE

[pypi]
username = __token__
password = pypi-YOUR_PYPI_TOKEN_HERE
EOF

chmod 600 ~/.pypirc
```

View your test package:
- https://test.pypi.org/project/pycancensus/

## Step 4: Test Installation from TestPyPI

Test installing from TestPyPI:

```bash
# Create a fresh virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pycancensus

# Test it works
python -c "import pycancensus as pc; print(pc.__version__)"

# Run a quick test
python -c "import pycancensus as pc; pc.set_api_key('test'); datasets = pc.list_census_datasets.__doc__; print('Success!')"

# Deactivate and remove test environment
deactivate
rm -rf test_env
```

**Note:** The `--extra-index-url` is needed because dependencies (pandas, requests, geopandas) are on regular PyPI.

## Step 5: Publish to PyPI (Production)

Once testing is successful, publish to the real PyPI:

```bash
# Upload to PyPI
python -m twine upload dist/*
```

Credentials:
- Username: `__token__`
- Password: Your PyPI API token

**View your package:**
- https://pypi.org/project/pycancensus/

## Step 6: Verify Installation

Test the production installation:

```bash
# Install from PyPI
pip install pycancensus

# Verify it works
python -c "import pycancensus as pc; print(f'pycancensus v{pc.__version__} installed successfully!')"
```

## Installation Methods After Publishing

Once published to PyPI, users can install via multiple methods:

### Standard pip

```bash
pip install pycancensus
```

### uv (fast Python package installer)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install pycancensus with uv
uv pip install pycancensus

# Or create a new project with pycancensus
uv init my-census-project
cd my-census-project
uv add pycancensus
```

### poetry

```bash
poetry add pycancensus
```

### conda/mamba

After PyPI publication, you can also publish to conda-forge:

```bash
# First install from PyPI, then create conda recipe
# This is a separate process - see conda-forge documentation
```

## Updating the Package

For subsequent releases:

1. Make your changes and commit them
2. Update version numbers:
   ```bash
   # Edit pyproject.toml and __init__.py
   # Update CHANGELOG.md
   ```
3. Create a new tag:
   ```bash
   git tag -a v0.2.0 -m "Version 0.2.0 - Description"
   git push origin main --tags
   ```
4. Build and upload:
   ```bash
   rm -rf dist/
   python -m build
   python -m twine upload dist/*
   ```

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR** version (1.0.0): Incompatible API changes
- **MINOR** version (0.1.0): Add functionality (backwards compatible)
- **PATCH** version (0.0.1): Bug fixes (backwards compatible)

Examples:
- `0.1.0` → `0.1.1`: Bug fixes
- `0.1.0` → `0.2.0`: New features, backwards compatible
- `0.9.0` → `1.0.0`: Stable API, breaking changes from 0.x

## Troubleshooting

### Build fails

```bash
# Check pyproject.toml syntax
python -m build --no-isolation

# Verify all files are included
python -m build --verbose
```

### Upload fails - "File already exists"

```bash
# You cannot reupload the same version
# Increment version number and rebuild
```

### Import fails after installation

```bash
# Check what was actually installed
pip show pycancensus

# Check for import issues
python -c "import pycancensus; print(dir(pycancensus))"
```

### Missing dependencies in installation

Edit `pyproject.toml` to ensure all dependencies are listed:

```toml
dependencies = [
    "requests>=2.25.0",
    "pandas>=1.0.0",
    "geopandas>=0.8.0",
]
```

## Security Best Practices

1. **Never commit API tokens** to git
2. **Use API tokens, not passwords** for PyPI
3. **Enable 2FA** on PyPI account
4. **Rotate tokens** periodically
5. **Use scoped tokens** (project-specific) when possible
6. **Store tokens securely** (use `~/.pypirc` with restricted permissions)

## GitHub Release Integration

Create a GitHub release to match the PyPI release:

1. Go to https://github.com/dshkol/pycancensus/releases
2. Click "Create a new release"
3. Tag: `v0.1.0`
4. Title: `pycancensus 0.1.0`
5. Description: Copy from CHANGELOG.md
6. Attach the distribution files from `dist/`
7. Publish release

## Automation (Optional)

Automate releases with GitHub Actions (`.github/workflows/publish.yml`):

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install build tools
        run: pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: python -m twine upload dist/*
```

Add `PYPI_API_TOKEN` to repository secrets:
1. GitHub repo → Settings → Secrets → Actions
2. New repository secret
3. Name: `PYPI_API_TOKEN`
4. Value: Your PyPI token

## Post-Publication Checklist

- [ ] Package appears on PyPI: https://pypi.org/project/pycancensus/
- [ ] Test installation works: `pip install pycancensus`
- [ ] GitHub release created and tagged
- [ ] Update README.md badges if needed
- [ ] Announce on relevant channels
- [ ] Update documentation site if separate from PyPI

## Resources

- PyPI: https://pypi.org
- TestPyPI: https://test.pypi.org
- Packaging Guide: https://packaging.python.org/
- Semantic Versioning: https://semver.org/
- Twine Documentation: https://twine.readthedocs.io/
- uv Documentation: https://docs.astral.sh/uv/

## Quick Reference Commands

```bash
# Complete release workflow
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin main --tags
rm -rf dist/
python -m build
python -m twine upload --repository testpypi dist/*  # Test first
python -m twine upload dist/*  # Then production

# Verify
pip install pycancensus
python -c "import pycancensus; print(pycancensus.__version__)"
```
