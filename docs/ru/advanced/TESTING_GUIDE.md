---
title: Руководство по тестированию
description: Подходы к тестированию в Coreness. Unit тесты, интеграционное тестирование, E2E тесты и тестирование сценариев.
keywords: тестирование coreness, unit tests, integration testing, e2e testing, pytest
---

# Руководство по тестированию

Полное руководство по тестированию проекта, включая Python тесты (pytest).

## Структура тестов

### Python тесты

```
tests/
├── conftest.py          # Базовые фикстуры для всех тестов
├── utils.py             # Утилиты для тестов (find_project_root)
├── requirements.txt     # Тестовые зависимости (включают основные + pytest)
├── unit/                # Unit-тесты (изолированные тесты модулей)
└── integration/         # Integration-тесты (тесты через DI-контейнер)
```

Тесты также могут находиться прямо в папках сервисов/утилит:

```
plugins/
└── utilities/
    └── core/
        └── condition_parser/
            ├── condition_parser.py
            └── tests/
                ├── conftest.py          # Локальные фикстуры
                └── test_baseline.py    # Тесты
```

## Установка зависимостей

### Python тесты

```bash
# Установить тестовые зависимости (включают основные + pytest)
pip install -r tests/requirements.txt
```

**Важно:** `tests/requirements.txt` включает все основные зависимости через `-r ../requirements.txt`, поэтому тесты могут импортировать модули проекта.

## Запуск тестов

### Python тесты (pytest)

#### Все тесты
```bash
# Из корня проекта
pytest

# С подробным выводом
pytest -v

# С покрытием кода
pytest --cov=plugins --cov=app
```

#### Конкретный тест
```bash
# По пути к файлу
pytest plugins/utilities/core/condition_parser/tests/test_baseline.py

# Конкретная функция
pytest plugins/utilities/core/condition_parser/tests/test_baseline.py::test_basic_comparison_operators

# С маркером
pytest -m unit
pytest -m integration
```

#### Фильтрация тестов
```bash
# Только unit-тесты
pytest -m unit

# Только integration-тесты
pytest -m integration

# По имени файла/функции
pytest -k "condition_parser"
pytest -k "test_basic"
```

#### Отладка
```bash
# Остановиться на первой ошибке
pytest -x

# Показать print() вывод
pytest -s

# Подробный traceback
pytest --tb=long

# Запустить только последние упавшие тесты
pytest --lf
```

## Типы тестов

### Unit-тесты (`tests/unit/` или рядом с кодом)

- Изолированные тесты модулей без внешних зависимостей
- Все зависимости заменены моками
- Быстрые и простые в отладке

**Пример:**
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

### Integration-тесты (`tests/integration/`)

- Тесты взаимодействия компонентов через DI-контейнер
- Используют реальные зависимости (через DI)
- Могут использовать тестовую БД

**Пример:**
```python
# tests/integration/test_di_container.py
import pytest

@pytest.mark.asyncio
async def test_di_resolves_dependencies(initialized_di_container):
    db_manager = initialized_di_container.get_utility("database_manager")
    assert db_manager is not None
```

## Доступные фикстуры (Python тесты)

См. `tests/conftest.py` для полного списка фикстур:

- `logger` - Logger для тестов
- `di_container` - DI-контейнер (без инициализации)
- `initialized_di_container` - DI-контейнер с инициализированными плагинами
- `test_database_url` - URL для тестовой БД (SQLite в памяти)
- `test_database_engine` - SQLAlchemy engine для тестовой БД
- `test_database_session` - SQLAlchemy session для тестовой БД
- `temp_dir` - Временная директория для тестов
- `project_root` - Корень проекта

## Определение корня проекта

**Не нужно вручную определять корень проекта в тестах!**

Корень проекта автоматически добавляется в `sys.path` через `pythonpath = ["."]` в `pyproject.toml`. Это происходит ДО загрузки всех `conftest.py` файлов, поэтому все тесты могут использовать абсолютные импорты.

Если нужно получить путь к корню проекта в тесте, используйте фикстуру `project_root`:

```python
def test_something(project_root):
    config_path = project_root / "config" / "settings.yaml"
    assert config_path.exists()
```

## Маркеры (pytest)

- `@pytest.mark.unit` - Unit-тесты
- `@pytest.mark.integration` - Integration-тесты
- `@pytest.mark.asyncio` - Асинхронные тесты

## CI/CD

### GitHub Actions

Тесты автоматически запускаются в CI:

1. **Python тесты** - через pytest в workflow

```yaml
# Установка зависимостей
- name: Установка зависимостей
  run: |
    pip install -r requirements.txt
    pip install -r tests/requirements.txt

# Запуск тестов
- name: Запуск тестов
  run: |
    pytest -v --tb=short -rA
```

## Проблемы и решения

### Тест не запускается

**Проблема:** `ModuleNotFoundError: No module named 'plugins'`

**Решение:** Убедитесь, что запускаете тесты через `pytest`, а не напрямую через Python:
```bash
# ✅ Правильно
pytest plugins/utilities/core/condition_parser/tests/test_baseline.py

# ❌ Неправильно
python plugins/utilities/core/condition_parser/tests/test_baseline.py
```

### Фикстура не найдена

**Проблема:** `fixture 'logger' not found`

**Решение:** Убедитесь, что в локальном `conftest.py` правильно импортируется фикстура:
```python
from tests.conftest import logger  # noqa: F401
```

### Тесты не находятся

**Проблема:** `pytest` не находит тесты

**Решение:** Проверьте, что файл называется `test_*.py` или `*_test.py` и функции начинаются с `test_*`.

