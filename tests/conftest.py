"""
Base fixtures for all tests
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

# Disable __pycache__ file creation for all tests
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'


def _find_project_root(start_path: Path) -> Path:
    """
    Reliably determines project root
    """
    # First check environment variable
    env_root = os.environ.get('PROJECT_ROOT')
    if env_root and Path(env_root).exists():
        return Path(env_root)
    
    # Search by key files/folders
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


# Determine project root for project_root fixture
# Project root is already added to sys.path via pythonpath = ["."] in pyproject.toml
PROJECT_ROOT = _find_project_root(Path(__file__))

from plugins.utilities.foundation.logger.logger import Logger
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager
from app.di_container import DIContainer


@pytest.fixture(scope="session")
def event_loop():
    """Creates event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns project root"""
    return PROJECT_ROOT


@pytest.fixture
def logger() -> Logger:
    """Creates logger for tests (scope="function" - for each test)"""
    return Logger()


@pytest.fixture(scope="session")
def module_logger() -> Logger:
    """Creates logger once per test session (maximum optimization)"""
    return Logger()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Creates temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_config_dir(temp_dir: Path) -> Path:
    """Creates test directory for configs"""
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def test_database_url(temp_dir: Path) -> str:
    """Creates URL for test DB (SQLite in memory)"""
    return "sqlite:///:memory:"


@pytest.fixture
def test_database_engine(test_database_url: str):
    """Creates engine for test DB"""
    engine = create_engine(test_database_url, echo=False)
    yield engine
    engine.dispose()


@pytest.fixture
def test_database_session(test_database_engine):
    """Creates session for test DB"""
    Session = sessionmaker(bind=test_database_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="session")
def plugins_manager(module_logger: Logger) -> PluginsManager:
    """Creates PluginsManager once per test session (maximum optimization)"""
    return PluginsManager(logger=module_logger.get_logger("plugins_manager"))


@pytest.fixture(scope="session")
def settings_manager(module_logger: Logger, plugins_manager: PluginsManager) -> SettingsManager:
    """Creates SettingsManager once per test session (maximum optimization)"""
    return SettingsManager(
        logger=module_logger.get_logger("settings_manager"),
        plugins_manager=plugins_manager
    )


@pytest.fixture
def di_container(module_logger: Logger, plugins_manager: PluginsManager, settings_manager: SettingsManager) -> DIContainer:
    """Creates DI container for test.

    Use default scope (function) to avoid carrying shutdown state
    between tests and to closely match Application behavior, which
    creates container at process startup.
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
    Creates and initializes DI container with all plugins.

    Important: after DI container shutdown, its internal caches are cleared, so before
    each initialization we re-register foundation utilities (logger,
    plugins_manager, settings_manager) the same way Application does.
    """
    # Ensure foundation utilities are present in container before initialization
    di_container._utilities['logger'] = module_logger
    di_container._utilities['plugins_manager'] = plugins_manager
    di_container._utilities['settings_manager'] = settings_manager

    di_container.initialize_all_plugins()
    yield di_container
    # Cleanup if needed
    di_container.shutdown()

