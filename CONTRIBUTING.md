# Contributing to ClimateGPT

Thank you for your interest in contributing to ClimateGPT! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Documentation](#documentation)
7. [Submitting Changes](#submitting-changes)
8. [Review Process](#review-process)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment for all contributors.

### Our Standards

**Positive behavior includes:**
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

**Unacceptable behavior includes:**
- Trolling, insulting comments, or personal attacks
- Public or private harassment
- Publishing others' private information without permission
- Other conduct which could reasonably be considered inappropriate

---

## Getting Started

### Prerequisites

- Python 3.11
- Git
- uv (package manager)
- Basic understanding of:
  - FastAPI / Streamlit
  - DuckDB
  - Model Context Protocol (MCP)

### Fork and Clone

1. **Fork the repository** on GitHub
2. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Team-1B-Fusion.git
   cd Team-1B-Fusion
   ```

3. **Add upstream remote:**
   ```bash
   git remote add upstream https://github.com/DharmpratapSingh/Team-1B-Fusion.git
   ```

### Install Dependencies

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install development dependencies
pip install black ruff pytest mypy
```

### Verify Setup

```bash
# Run tests
pytest

# Run validation
python validate_phase5.py

# Start services
make serve  # Terminal 1
make ui     # Terminal 2
```

---

## Development Workflow

### Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-new-feature
```

### Branch Naming Convention

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring
- `test/description` - Test improvements
- `chore/description` - Maintenance tasks

### Make Changes

1. **Write code** following our [coding standards](#coding-standards)
2. **Add tests** for new functionality
3. **Update documentation** as needed
4. **Run validation:**
   ```bash
   # Format code
   black .

   # Lint code
   ruff check .

   # Type check
   mypy mcp_server_stdio.py

   # Run tests
   pytest -v
   ```

### Commit Messages

Follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
# Good commit messages
git commit -m "feat(api): add new compare_sectors tool"
git commit -m "fix(db): resolve index creation performance issue"
git commit -m "docs(api): update API documentation with new endpoints"

# Bad commit messages
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "changes"
```

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://peps.python.org/pep-0008/) with some modifications:

- **Line length:** 100 characters (not 79)
- **Quotes:** Double quotes for strings
- **Imports:** Grouped and sorted

### Code Formatting

Use `black` for automatic formatting:

```bash
# Format all Python files
black .

# Format specific file
black mcp_server_stdio.py

# Check without modifying
black --check .
```

### Linting

Use `ruff` for linting:

```bash
# Lint all files
ruff check .

# Fix auto-fixable issues
ruff check --fix .
```

### Type Hints

**Required for all new code:**

```python
# Good - with type hints
def query_emissions(
    sector: str,
    year: int,
    country_name: str | None = None
) -> dict[str, Any]:
    ...

# Bad - no type hints
def query_emissions(sector, year, country_name=None):
    ...
```

Use modern Python 3.11+ syntax:
- ✅ `list[str]` not `List[str]`
- ✅ `dict[str, Any]` not `Dict[str, Any]`
- ✅ `str | None` not `Optional[str]`

### Documentation Strings

Use Google-style docstrings:

```python
def analyze_trend(
    entity_name: str,
    sector: str,
    start_year: int,
    end_year: int
) -> dict[str, Any]:
    """
    Analyze emissions trend over time.

    Args:
        entity_name: Country, state, or city name
        sector: Emissions sector (transport, power, etc.)
        start_year: Start year (2000-2024)
        end_year: End year (2000-2024)

    Returns:
        Dictionary with trend analysis including:
        - pattern: "increasing", "decreasing", or "stable"
        - total_change_pct: Percentage change
        - cagr_pct: Compound annual growth rate
        - yearly_data: List of emissions per year

    Raises:
        ValueError: If end_year < start_year
        EntityNotFoundError: If entity not in database

    Example:
        >>> result = analyze_trend("China", "transport", 2018, 2023)
        >>> print(result["pattern"])
        "increasing"
    """
    ...
```

### File Organization

```python
# Standard module structure
"""
Module docstring describing purpose.
"""

# 1. Standard library imports
import os
import sys
from typing import Any

# 2. Third-party imports
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel

# 3. Local imports
from shared.entity_normalization import normalize_entity_name
from models.schemas import QueryEmissionsRequest
from utils.config import Config

# 4. Constants
DEFAULT_CACHE_SIZE = 1000

# 5. Type aliases
JsonDict = dict[str, Any]

# 6. Classes and functions
class MyClass:
    ...

def my_function():
    ...
```

---

## Testing

### Writing Tests

We use `pytest` for testing:

```python
# tests/test_entity_normalization.py
import pytest
from shared.entity_normalization import normalize_entity_name


def test_normalize_usa():
    """Test USA alias normalization"""
    assert normalize_entity_name("USA") == "United States of America"
    assert normalize_entity_name("US") == "United States of America"
    assert normalize_entity_name("America") == "United States of America"


def test_normalize_abbreviated_countries():
    """Test database-specific abbreviations"""
    assert normalize_entity_name("Bosnia and Herz.") == "Bosnia and Herzegovina"
    assert normalize_entity_name("Dem. Rep. Congo") == "Democratic Republic of the Congo"


@pytest.mark.parametrize("input,expected", [
    ("USA", "United States of America"),
    ("UK", "United Kingdom"),
    ("NYC", "New York City"),
])
def test_normalize_multiple(input, expected):
    """Test multiple aliases"""
    assert normalize_entity_name(input) == expected
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_entity_normalization.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run verbose
pytest -v

# Run specific test
pytest tests/test_entity_normalization.py::test_normalize_usa
```

### Test Requirements

- **All new features must have tests**
- **All bug fixes must have regression tests**
- **Aim for 80%+ code coverage**
- **Tests must pass before merging**

---

## Documentation

### When to Update Documentation

**Required for:**
- New features or tools
- API changes
- Configuration changes
- Breaking changes

**Files to update:**
- `README.md` - High-level overview
- `docs/API.md` - API documentation
- `docs/ARCHITECTURE.md` - Architecture changes
- `docs/DEPLOYMENT.md` - Deployment updates
- Inline code documentation

### Documentation Standards

- Use Markdown for all documentation
- Include code examples
- Add diagrams where helpful (ASCII art is fine)
- Keep language clear and concise
- Update table of contents

---

## Submitting Changes

### Before Submitting

**Checklist:**
- [ ] Code follows style guidelines
- [ ] Code is properly formatted (`black .`)
- [ ] Code passes linting (`ruff check .`)
- [ ] Type hints added (`mypy` passes)
- [ ] Tests added and passing (`pytest`)
- [ ] Documentation updated
- [ ] Commit messages follow convention
- [ ] Branch is up to date with main

### Create Pull Request

1. **Push to your fork:**
   ```bash
   git push origin feature/my-new-feature
   ```

2. **Create PR on GitHub:**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your fork and branch
   - Fill out the PR template

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added
- [ ] All tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Ready for review
```

---

## Review Process

### What Reviewers Look For

- **Correctness:** Does it work as intended?
- **Tests:** Are there adequate tests?
- **Code Quality:** Is it maintainable?
- **Documentation:** Is it documented?
- **Performance:** Are there any performance concerns?
- **Security:** Are there any security issues?

### Responding to Feedback

- Be open to feedback and suggestions
- Ask for clarification if needed
- Make requested changes or discuss alternatives
- Update PR description if scope changes
- Mark conversations as resolved when addressed

### Approval Process

1. **Automated checks** must pass:
   - Linting
   - Type checking
   - Tests
   - Security scanning

2. **Code review** from maintainers
3. **Approval** from at least one maintainer
4. **Merge** by maintainer

---

## Development Tips

### Working with Database

```python
# Use context managers
with _get_db_connection() as conn:
    result = conn.execute(sql, params).fetchall()

# Always use parameterized queries
sql = "SELECT * FROM table WHERE year = ?"
result = conn.execute(sql, [2023]).fetchall()

# Never use string formatting
# Bad:
sql = f"SELECT * FROM table WHERE year = {year}"
```

### Debugging

```python
# Use logging, not print
import logging
logger = logging.getLogger(__name__)

logger.debug("Query parameters: sector=%s, year=%s", sector, year)
logger.info("Query executed in %.2fms", query_time)
logger.error("Failed to execute query: %s", error)
```

### Performance

```python
# Use ISO3 codes for faster queries
# Good:
iso3 = get_iso3_code(country_name)  # "USA"
WHERE iso3 = ?

# Slower:
WHERE country_name = ?

# Prefer yearly tables when month not needed
# Good:
table = f"{sector}_country_year"

# Slower (12x more rows):
table = f"{sector}_country_month"
```

---

## Getting Help

### Resources

- **Documentation:** `docs/` directory
- **API Docs:** http://localhost:8010/docs
- **Examples:** Search codebase for similar implementations

### Questions

- **GitHub Issues:** For bugs and feature requests
- **GitHub Discussions:** For questions and ideas
- **Code Comments:** Inline questions in PR reviews

---

## Recognition

Contributors will be recognized in:
- `CONTRIBUTORS.md` (alphabetical)
- Release notes for significant contributions
- GitHub contributors page

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

---

## Additional Resources

- [Python PEP 8 Style Guide](https://peps.python.org/pep-0008/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [pytest Documentation](https://docs.pytest.org/)
- [MCP Protocol](https://modelcontextprotocol.io)

---

**Thank you for contributing to ClimateGPT!** 🌍

---

**Document Version:** 1.0.0
**Last Updated:** 2025-11-16
