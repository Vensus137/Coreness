---
title: Testing Guide
description: Testing approaches in Coreness. Unit tests, integration testing, E2E tests and scenario testing.
keywords: coreness testing, unit tests, integration testing, e2e testing, pytest
---

# Testing Guide

Complete guide for project testing, including Python tests (pytest).

## Test Structure

### Python Tests

```
tests/
├── conftest.py          # Base fixtures for all tests
├── utils.py             # Test utilities (find_project_root)
├── requirements.txt     # Test dependencies (include main + pytest)
├── unit/                # Unit tests (isolated module tests)
└── integration/         # Integration tests (tests via DI-container)
```

Tests can also be directly in service/utility folders:

```
plugins/
└── utilities/
    └── core/
        └── condition_parser/
            ├── condition_parser.py
            └── tests/
                ├── conftest.py          # Local fixtures
                └── test_baseline.py    # Tests
```

## Installing Dependencies

### Python Tests

```bash
# Install test dependencies (include main + pytest)
pip install -r tests/requirements.txt
```

**Important:** `tests/requirements.txt` includes all main dependencies via `-r ../requirements.txt`, so tests can import project modules.

## Running Tests

### Python Tests (pytest)

#### All Tests
```bash
# From project root
pytest

# With verbose output
pytest -v

# With code coverage
pytest --cov=plugins --cov=app
```

#### Specific Test
```bash
# By file path
pytest plugins/utilities/core/condition_parser/tests/test_baseline.py

# Specific function
pytest plugins/utilities/core/condition_parser/tests/test_baseline.py::test_basic_comparison_operators

# With marker
pytest -m unit
pytest -m integration
```

#### Test Filtering
```bash
# Only unit tests
pytest -m unit

# Only integration tests
pytest -m integration

# By file/function name
pytest -k "condition_parser"
pytest -k "test_basic"
```

#### Debugging
```bash
# Stop on first error
pytest -x

# Show print() output
pytest -s

# Verbose traceback
pytest --tb=long

# Run only last failed tests
pytest --lf
```

## Test Types

### Unit Tests (`tests/unit/` or next to code)

- Isolated module tests without external dependencies
- All dependencies replaced with mocks
- Fast and simple to debug

**Example:**
```python
# plugins/utilities/core/condition_parser/tests/test_baseline.py
import pytest
from plugins.utilities.core.condition_parser.condition_parser import ConditionParser

@pytest.fixture
def parser(logger):
    return ConditionParser(logger=logger)

@pytest.mark.asyncio
async def test_condition_parser(parser):
    result = await parser.check_match("$x == 1", {"x": 1})
    assert result is True
```

### Integration Tests (`tests/integration/`)

- Component interaction tests via DI-container
- Use real dependencies (via DI)
- Can use test DB

**Example:**
```python
# tests/integration/test_di_container.py
import pytest

@pytest.mark.asyncio
async def test_di_resolves_dependencies(initialized_di_container):
    db_manager = initialized_di_container.get_utility("database_manager")
    assert db_manager is not None
```

## Available Fixtures (Python Tests)

See `tests/conftest.py` for complete fixture list:

- `logger` - Logger for tests
- `di_container` - DI-container (without initialization)
- `initialized_di_container` - DI-container with initialized plugins
- `test_database_url` - Test DB URL (SQLite in memory)
- `test_database_engine` - SQLAlchemy engine for test DB
- `test_database_session` - SQLAlchemy session for test DB
- `temp_dir` - Temporary directory for tests
- `project_root` - Project root

## Determining Project Root

**No need to manually determine project root in tests!**

Project root automatically added to `sys.path` via `pythonpath = ["."]` in `pyproject.toml`. This happens BEFORE loading all `conftest.py` files, so all tests can use absolute imports.

If need to get project root path in test, use `project_root` fixture:

```python
def test_something(project_root):
    config_path = project_root / "config" / "settings.yaml"
    assert config_path.exists()
```

## Markers (pytest)

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.asyncio` - Asynchronous tests

## CI/CD

### GitHub Actions

Tests automatically run in CI:

1. **Python tests** - via pytest in workflow

```yaml
# Install dependencies
- name: Install dependencies
  run: |
    pip install -r requirements.txt
    pip install -r tests/requirements.txt

# Run tests
- name: Run tests
  run: |
    pytest -v --tb=short -rA
```

## Problems and Solutions

### Test Won't Run

**Problem:** `ModuleNotFoundError: No module named 'plugins'`

**Solution:** Ensure running tests via `pytest`, not directly via Python:
```bash
# ✅ Correct
pytest plugins/utilities/core/condition_parser/tests/test_baseline.py

# ❌ Incorrect
python plugins/utilities/core/condition_parser/tests/test_baseline.py
```

### Fixture Not Found

**Problem:** `fixture 'logger' not found`

**Solution:** Ensure fixture correctly imported in local `conftest.py`:
```python
from tests.conftest import logger  # noqa: F401
```

### Tests Not Found

**Problem:** `pytest` doesn't find tests

**Solution:** Check file named `test_*.py` or `*_test.py` and functions start with `test_*`.
