# Contributing to pycancensus

Thank you for your interest in contributing to pycancensus! This document provides guidelines and instructions for contributing to the project.

## Getting Started

### Development Installation

1. Fork the repository on GitHub

2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pycancensus.git
   cd pycancensus
   ```

3. Install the package in development mode with all dependencies:
   ```bash
   pip install -e .[dev,docs]
   ```

### Setting up API Key

You'll need a CensusMapper API key for testing:

```bash
export CANCENSUS_API_KEY="your_api_key_here"
```

Get a free API key at: https://censusmapper.ca/users/sign_up

## Development Workflow

### Running Tests

Run the full test suite:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=pycancensus --cov-report=xml
```

Run specific test categories:
```bash
pytest tests/test_basic.py              # Basic tests
pytest tests/integration/               # Integration tests
pytest tests/performance/               # Performance tests
```

### Code Style

pycancensus follows PEP 8 style guidelines and uses Black for code formatting.

Before submitting code, ensure it's properly formatted:

```bash
# Format code automatically
black pycancensus

# Check formatting without changing files
black --check pycancensus
```

Run linting checks:
```bash
# Check for critical errors
flake8 pycancensus --count --select=E9,F63,F7,F82 --show-source --statistics

# Full linting check
flake8 pycancensus --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
```

### Building Documentation

Build the documentation locally to test your changes:

```bash
cd docs
make html
```

View the built documentation:
```bash
open _build/html/index.html  # macOS
# or
xdg-open _build/html/index.html  # Linux
```

## Making Changes

### Creating a Branch

Create a feature branch for your changes:

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-new-function` for new features
- `fix/issue-123` for bug fixes
- `docs/update-tutorial` for documentation changes

### Commit Messages

Write clear, descriptive commit messages:

```
Add support for national-level census data

- Add 'C' to valid census levels in utils.py
- Create test suite for national-level functionality
- Update documentation with national-level examples
```

**Guidelines:**
- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line should be 50 characters or less
- Reference issues and pull requests after the first line

### Code Guidelines

**General Principles:**
- Write clear, readable code
- Add docstrings to all public functions and classes
- Follow existing code patterns and conventions
- Keep functions focused and single-purpose
- Add type hints where appropriate

**Docstring Format:**

```python
def function_name(param1: str, param2: int) -> pd.DataFrame:
    """
    Brief description of what the function does.

    Parameters
    ----------
    param1 : str
        Description of param1.
    param2 : int
        Description of param2.

    Returns
    -------
    pd.DataFrame
        Description of return value.

    Examples
    --------
    >>> result = function_name("example", 42)
    >>> print(result)
    """
```

### Adding Tests

All new features and bug fixes should include tests:

**Test Organization:**
- `tests/test_basic.py` - Unit tests for core functionality
- `tests/integration/` - Integration tests requiring API calls
- `tests/performance/` - Performance and stress tests

**Writing Tests:**

```python
def test_new_feature():
    """Test description explaining what is being tested."""
    # Arrange
    input_data = prepare_test_data()

    # Act
    result = your_function(input_data)

    # Assert
    assert result is not None
    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0
```

## Submitting Changes

### Pull Request Process

1. Update documentation to reflect any changes

2. Add tests for new functionality

3. Ensure all tests pass:
   ```bash
   pytest
   black --check pycancensus
   flake8 pycancensus
   ```

4. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

5. Open a pull request on GitHub

### Pull Request Checklist

Before submitting, verify:

- [ ] Tests pass locally
- [ ] Code is formatted with Black
- [ ] No linting errors from flake8
- [ ] Documentation is updated
- [ ] Docstrings added for new functions
- [ ] Examples added where appropriate
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] Commit messages are clear and descriptive

### Pull Request Description

Provide a clear description of your changes:

```markdown
## Description
Brief summary of the changes and their purpose.

## Motivation
Why are these changes needed? What problem do they solve?

## Changes
- List of specific changes made
- Include any breaking changes
- Note any new dependencies

## Testing
How were these changes tested?

## Related Issues
Fixes #123
Relates to #456
```

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the bug
2. **Steps to Reproduce**: Minimal code to reproduce the issue
3. **Expected Behavior**: What you expected to happen
4. **Actual Behavior**: What actually happened
5. **Environment**:
   - pycancensus version
   - Python version
   - Operating system
   - Relevant dependencies

Example:

```markdown
**Description**
`get_census()` fails when requesting national-level data

**Steps to Reproduce**
```python
import pycancensus as pc
data = pc.get_census('CA21', level='C', regions={'C': '01'})
```

**Expected Behavior**
Should return national-level census data for Canada

**Actual Behavior**
Raises ValueError: Invalid level: C

**Environment**
- pycancensus 0.1.0
- Python 3.9.6
- macOS 12.0
```

### Feature Requests

When requesting features, include:

1. **Use Case**: Describe the problem this feature would solve
2. **Proposed Solution**: How you envision the feature working
3. **Alternatives**: Other approaches you've considered
4. **R cancensus Comparison**: If applicable, how R cancensus handles this

## Code Review Process

After submitting a pull request:

1. **Automated Checks**: CI will run tests and code quality checks
2. **Maintainer Review**: A maintainer will review your code
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, your PR will be merged

**Review Timeline:**
- Initial response within 7 days
- Most PRs reviewed within 2 weeks
- Complex changes may take longer

## Development Setup Tips

### Virtual Environment

Use a virtual environment for development:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

pip install -e .[dev,docs]
```

### Pre-commit Hooks

Consider setting up pre-commit hooks to automatically format code:

```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
```

## Questions?

If you have questions about contributing:

1. Check existing issues and pull requests
2. Review the documentation
3. Open a discussion on GitHub
4. Ask in your pull request or issue

## License

By contributing to pycancensus, you agree that your contributions will be licensed under the MIT License.

## Thank You!

Thank you for contributing to pycancensus! Your contributions help make Canadian census data more accessible to the Python community.
