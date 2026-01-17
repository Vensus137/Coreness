"""
Базовые фикстуры для всех тестов
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator, AsyncGenerator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Отключаем создание __pycache__ файлов для всех тестов
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'


def _find_project_root(start_path: Path) -> Path:
    """
    Надежно определяет корень проекта
    """
    # Сначала проверяем переменную окружения
    env_root = os.environ.get('PROJECT_ROOT')
    if env_root and Path(env_root).exists():
        return Path(env_root)
    
    # Ищем по ключевым файлам/папкам
    current = start_path.resolve()
    if current.is_file():
        current = current.parent
    
    while current != current.parent:
        if (current / "main.py").exists() and \
           (current / "plugins").exists() and \
           (current / "app").exists():
            return current
        current = current.parent
    
    # Fallback
    if start_path.name == "tests" or "tests" in start_path.parts:
        return start_path.parent if start_path.is_dir() else start_path.parent.parent
    
    return start_path.parent if start_path.is_file() else start_path


# Определяем корень проекта для фикстуры project_root
# Корень проекта уже добавлен в sys.path через pythonpath = ["."] в pyproject.toml
PROJECT_ROOT = _find_project_root(Path(__file__))

from plugins.utilities.foundation.logger.logger import Logger
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager
from app.di_container import DIContainer


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для async тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Возвращает корень проекта"""
    return PROJECT_ROOT


@pytest.fixture
def logger() -> Logger:
    """Создает logger для тестов (scope="function" - для каждого теста)"""
    return Logger()


@pytest.fixture(scope="session")
def module_logger() -> Logger:
    """Создает logger один раз на всю сессию тестов (максимальная оптимизация)"""
    return Logger()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Создает временную директорию для тестов"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config_dir(temp_dir: Path) -> Path:
    """Создает тестовую директорию для конфигов"""
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def test_database_url(temp_dir: Path) -> str:
    """Создает URL для тестовой БД (SQLite в памяти)"""
    return "sqlite:///:memory:"


@pytest.fixture
def test_database_engine(test_database_url: str):
    """Создает engine для тестовой БД"""
    engine = create_engine(test_database_url, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture
def test_database_session(test_database_engine):
    """Создает сессию для тестовой БД"""
    Session = sessionmaker(bind=test_database_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def plugins_manager(module_logger: Logger) -> PluginsManager:
    """Создает PluginsManager один раз на всю сессию тестов (максимальная оптимизация)"""
    return PluginsManager(logger=module_logger.get_logger("plugins_manager"))


@pytest.fixture(scope="session")
def settings_manager(module_logger: Logger, plugins_manager: PluginsManager) -> SettingsManager:
    """Создает SettingsManager один раз на всю сессию тестов (максимальная оптимизация)"""
    return SettingsManager(
        logger=module_logger.get_logger("settings_manager"),
        plugins_manager=plugins_manager
    )


@pytest.fixture
def di_container(module_logger: Logger, plugins_manager: PluginsManager, settings_manager: SettingsManager) -> DIContainer:
    """Создает DI-контейнер для теста.

    Используем scope по умолчанию (function), чтобы не тащить состояние shutdown
    между тестами и максимально приблизиться к поведению Application, которое
    создает контейнер при старте процесса.
    """
    return DIContainer(
        logger=module_logger,
        plugins_manager=plugins_manager,
        settings_manager=settings_manager
    )


@pytest.fixture
async def initialized_di_container(
    di_container: DIContainer,
    module_logger: Logger,
    plugins_manager: PluginsManager,
    settings_manager: SettingsManager,
) -> AsyncGenerator[DIContainer, None]:
    """
    Создает и инициализирует DI-контейнер со всеми плагинами.

    Важно: после shutdown DI-контейнера его внутренние кеши очищаются, поэтому перед
    каждой инициализацией мы повторно регистрируем foundation-утилиты (logger,
    plugins_manager, settings_manager) так же, как это делает Application.
    """
    # Гарантируем, что foundation-утилиты присутствуют в контейнере перед инициализацией
    di_container._utilities['logger'] = module_logger
    di_container._utilities['plugins_manager'] = plugins_manager
    di_container._utilities['settings_manager'] = settings_manager

    di_container.initialize_all_plugins()
    yield di_container
    # Cleanup при необходимости
    di_container.shutdown()

