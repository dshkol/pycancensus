# Quick Publish Guide - Ready to Publish pycancensus

## Current Status

Package is ready for initial PyPI publication. Follow these steps in order.

## Step 1: Install Publishing Tools

```bash
pip install --upgrade build twine
```

## Step 2: Set Up PyPI Accounts

### TestPyPI (for testing)
1. Register: https://test.pypi.org/account/register/
2. Verify email
3. Enable 2FA
4. Create API token: https://test.pypi.org/manage/account/token/
   - Save the token (starts with `pypi-`)

### PyPI (production)
1. Register: https://pypi.org/account/register/
2. Verify email
3. Enable 2FA
4. Create API token: https://pypi.org/manage/account/token/
   - Save the token

## Step 3: Configure Credentials

```bash
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

**Replace the placeholder tokens with your actual tokens.**

## Step 4: Pre-Flight Check

```bash
# Verify all tests pass
pytest

# Verify code is formatted
black --check pycancensus

# Verify no linting errors
flake8 pycancensus --count --select=E9,F63,F7,F82

# Verify current directory
pwd  # Should be /Users/dmitryshkolnik/Projects/pycancensus
```

## Step 5: Build the Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build
python -m build
```

This creates:
- `dist/pycancensus-0.1.0.tar.gz`
- `dist/pycancensus-0.1.0-py3-none-any.whl`

## Step 6: Test on TestPyPI First

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# View on TestPyPI
# https://test.pypi.org/project/pycancensus/
```

## Step 7: Test Install from TestPyPI

```bash
# Create test environment
python -m venv /tmp/test_pypi
source /tmp/test_pypi/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ pycancensus

# Quick test
python -c "import pycancensus as pc; print(f'Version: {pc.__version__}')"
python -c "import pycancensus as pc; print('Functions:', len(dir(pc)))"

# Cleanup
deactivate
rm -rf /tmp/test_pypi
```

## Step 8: Publish to Production PyPI

```bash
# Upload to PyPI
python -m twine upload dist/*

# View on PyPI
# https://pypi.org/project/pycancensus/
```

## Step 9: Test Production Install

```bash
# Create fresh environment
python -m venv /tmp/test_prod
source /tmp/test_prod/bin/activate

# Install from PyPI
pip install pycancensus

# Test it
python -c "import pycancensus as pc; print(f'pycancensus v{pc.__version__} installed!')"

# Test with uv (if you have it)
# uv pip install pycancensus

# Cleanup
deactivate
rm -rf /tmp/test_prod
```

## Step 10: Create GitHub Release

```bash
# Tag the release
git tag -a v0.1.0 -m "Version 0.1.0 - Initial public release"
git push origin v0.1.0
```

Then on GitHub:
1. Go to https://github.com/dshkol/pycancensus/releases/new
2. Choose tag: `v0.1.0`
3. Title: `pycancensus 0.1.0 - Initial Release`
4. Description: Copy from CHANGELOG.md
5. Attach `dist/*.tar.gz` and `dist/*.whl`
6. Click "Publish release"

## Step 11: Update README

After publishing, update README.md to change:

```markdown
**Note**: pycancensus is not yet published on PyPI. Install directly from GitHub:
```

To:

```markdown
Install from PyPI:
```

And update installation examples to show the simple version:

```bash
pip install pycancensus
```

Then commit:

```bash
git add README.md docs/index.rst
git commit -m "Update installation instructions after PyPI publication"
git push origin main
```

## Done!

After publishing, users can install with:

```bash
# pip
pip install pycancensus

# uv
uv pip install pycancensus

# poetry
poetry add pycancensus

# pipenv
pipenv install pycancensus
```

## Troubleshooting

**Build fails:**
```bash
python -m build --verbose
```

**Upload fails - "File already exists":**
- Cannot re-upload same version
- Increment version and rebuild

**Module not found after install:**
```bash
pip show pycancensus
python -c "import sys; print(sys.path)"
```

**Missing dependencies:**
- Check `pyproject.toml` dependencies section
- Test in clean virtualenv

## One-Line Commands (for quick reference)

```bash
# Complete workflow
rm -rf dist/ && python -m build && python -m twine upload --repository testpypi dist/* && python -m twine upload dist/*
```
