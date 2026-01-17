"""
Фикстуры для тестов системы деплоя
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Корень проекта уже добавлен в sys.path через pythonpath = ["."] в pyproject.toml
# Импортируем общие фикстуры из базового conftest
from tests.conftest import temp_dir  # noqa: F401
from tests.utils import find_project_root

# ВАЖНО: Модули deployment используют импорты вида "from modules.base import ..."
# Эти импорты выполняются при ЗАГРУЗКЕ модуля (до инициализации DeploymentBase),
# поэтому нужно добавить tools/deployment в sys.path ДО импорта модулей в тестах
# Добавляем в конец, чтобы не конфликтовать с импортами из tests/
project_root = find_project_root(Path(__file__))
deployment_dir = project_root / "tools" / "deployment"
if str(deployment_dir) not in sys.path:
    sys.path.append(str(deployment_dir))


@pytest.fixture(scope="session")
def mock_logger():
    """Создает мок логгера один раз на всю сессию тестов (максимальная оптимизация)"""
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture(scope="session")
def sample_config():
    """Возвращает пример конфигурации для тестов один раз на всю сессию (максимальная оптимизация)"""
    return {
        "deployment_presets": {
            "core_files": {
                "include": ["app/", "tools/", "main.py"]
            },
            "exclusions": {
                "exclude": ["resources/", "logs/"]
            }
        },
        "deploy_settings": {
            "timeouts": {
                "docker_build": 600,
                "docker_stop": 60,
                "api_request": 30
            }
        },
        "git_settings": {
            "branch_prefix": "deploy/",
            "mr_title_template": "Deploy {version}",
            "mr_description_template": "Deploy {version}"
        },
        "migration_settings": {
            "migrations_dir": "tools/deployment/migrations",
            "require_confirmation": True,
            "auto_backup": True,
            "backup_dir": "data/backups"
        }
    }


@pytest.fixture(scope="session")
def project_root():
    """Возвращает корень проекта deployment (tools/deployment) один раз на всю сессию (максимальная оптимизация)"""
    return find_project_root(Path(__file__)) / "tools" / "deployment"

