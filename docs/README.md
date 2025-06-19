# pycancensus Documentation

This directory contains the documentation system for pycancensus, built with Sphinx and featuring:

- **Sphinx-Gallery**: Executable Python examples with beautiful thumbnails
- **MyST-NB**: Markdown tutorials that execute as notebooks
- **Autosummary**: Auto-generated API documentation
- **Professional Theming**: Read the Docs theme with copy buttons

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
pip install -e .[docs]
```

### Build Commands

```bash
# Build HTML documentation
cd docs
make html

# Clean and rebuild
make clean-all && make html

# Live rebuilding during development
make livehtml  # Requires sphinx-autobuild
```

The built documentation will be in `docs/_build/html/`.

## Documentation Structure

```
docs/
├── conf.py                    # Sphinx configuration
├── index.rst                  # Main documentation page
├── tutorials/                 # MyST-NB tutorials
│   ├── getting_started.md     # Main tutorial
│   ├── working_with_geometry.md
│   └── caching_data.md
├── examples/                  # Sphinx-Gallery examples
│   ├── plot_basic_census_data.py
│   └── plot_geographic_analysis.py
├── api/                       # Auto-generated API docs
│   └── index.rst
└── _static/                   # Static files (CSS, images)
```

## Adding New Content

### Adding a New Tutorial

1. Create a new `.md` file in `docs/tutorials/`
2. Use MyST-NB format with executable code cells:

```markdown
---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# Your Tutorial Title

Tutorial introduction text.

``{code-cell} python
import pycancensus as pc
print("Your code here")
``
```

3. Add the tutorial to `docs/tutorials/index.rst`

### Adding a New Example

1. Create a new Python file in `docs/examples/` with filename starting with `plot_`
2. Use Sphinx-Gallery format with docstring introduction:

```python
"""
Example Title
=============

Detailed description of what this example demonstrates.
"""

# %%
# Section Header
# --------------
# 
# Explanation of this section.

import pycancensus as pc
# Your code here

# %%
# Another Section
# ---------------
# 
# More explanation and code.

print("Examples are automatically executed!")
```

3. Examples are automatically included in the gallery

### Adding API Documentation

API documentation is automatically generated from docstrings. To add a new function:

1. Ensure the function is exported in `pycancensus/__init__.py`
2. Add it to the appropriate section in `docs/api/index.rst`:

```rst
New Section
-----------

.. autosummary::
   :toctree: generated/

   your_new_function
```

## Documentation Standards

### Code Examples

- **Always include working examples** in docstrings and tutorials
- **Handle API key requirements** gracefully (show setup but don't require real keys)
- **Use realistic but sample data** when possible
- **Add error handling** to show users what can go wrong

### Writing Style

- **Be concise but complete** - explain what users need to know
- **Use active voice** and clear instructions
- **Include "why" not just "how"** - explain the purpose
- **Cross-reference** related functions and tutorials

### Code Style in Examples

- **Follow PEP 8** and project conventions
- **Use meaningful variable names**
- **Add comments** to explain complex steps
- **Show intermediate results** to help debugging

## Common Issues and Solutions

### Build Errors

**Problem**: `ModuleNotFoundError` during build
**Solution**: Install all dependencies with `pip install -e .[docs,dev]`

**Problem**: Examples fail to execute
**Solution**: 
- Check that examples handle missing API keys gracefully
- Ensure all required packages are imported
- Test examples independently: `python docs/examples/plot_example.py`

**Problem**: MyST-NB execution errors
**Solution**:
- Check code cell syntax (triple backticks with `{code-cell} python`)
- Verify notebook metadata in frontmatter
- Test with: `jupyter-book build docs/tutorials/`

### Link Errors

**Problem**: Broken cross-references
**Solution**: Use proper Sphinx references:
- Functions: `:func:`pycancensus.get_census``
- Tutorials: `:doc:`tutorials/getting_started``
- External: `External Link <https://example.com>`_

## Continuous Integration

Documentation builds automatically on:
- Every push to main/develop branches
- Pull requests to main
- Scheduled daily builds (to catch external dependency issues)

The CI workflow:
1. Installs dependencies
2. Builds documentation with `make html`
3. Checks for broken links
4. Fails if any errors occur

## Publishing

Documentation is published automatically to Read the Docs:
- **Development**: Built from `develop` branch
- **Stable**: Built from tagged releases
- **Latest**: Built from `main` branch

### Read the Docs Configuration

The `.readthedocs.yaml` file configures:
- Python version and dependencies
- Build environment
- Documentation format

## Performance Tips

### Fast Development Builds

```bash
# Skip example execution during development
export SPHINX_GALLERY_CONF_PLOT_GALLERY=False
make html

# Build only specific sections
sphinx-build -b html -D exclude_patterns="auto_examples/*" . _build/html
```

### Caching

- **Jupyter Cache**: MyST-NB caches notebook execution results
- **Sphinx Cache**: Reuses unchanged documentation
- **Gallery Cache**: Sphinx-Gallery caches example outputs

Clear caches if you encounter stale content:
```bash
make clean-all
rm -rf docs/_build/.jupyter_cache
```

## Contributing Documentation

1. **Fork** the repository
2. **Create** a feature branch for your documentation changes
3. **Test** your changes locally with `make html`
4. **Submit** a pull request with a clear description

### Documentation Pull Request Checklist

- [ ] Documentation builds without errors
- [ ] Examples execute successfully
- [ ] Links work correctly
- [ ] Spelling and grammar checked
- [ ] Screenshots updated if UI changed
- [ ] Cross-references added where helpful

## Resources

- [Sphinx Documentation](https://www.sphinx-doc.org/)
- [MyST-NB Guide](https://myst-nb.readthedocs.io/)
- [Sphinx-Gallery Examples](https://sphinx-gallery.github.io/)
- [Read the Docs Guide](https://docs.readthedocs.io/)

For questions about documentation, open an issue or discussion on GitHub.