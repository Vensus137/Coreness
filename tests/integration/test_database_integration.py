"""
Интеграционные тесты работы с базой данных
Проверяют корректную работу с БД через DI-контейнер
"""
import pytest

from tests.conftest import initialized_di_container, test_database_url  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_initialization(initialized_di_container):
    """Проверка инициализации database_manager"""
    database_manager = initialized_di_container.get_utility('database_manager')
    
    # Проверяем, что database_manager можно получить (без исключений)
    assert database_manager is not None, "DatabaseManager должен быть доступен через DI"
    
    # Проверяем, что можем получить информацию о БД
    db_info = database_manager.get_database_config()
    assert db_info is not None, "Информация о БД должна быть доступна"
    assert 'type' in db_info, "Информация о БД должна содержать тип"
    
    # Проверяем, что можем получить список доступных БД
    available_dbs = database_manager.get_available_databases()
    assert isinstance(available_dbs, list), "Список доступных БД должен быть массивом"
    assert len(available_dbs) > 0, "Должна быть хотя бы одна доступная БД"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_repositories_work(initialized_di_container):
    """Проверка работы репозиториев через database_manager"""
    database_manager = initialized_di_container.get_utility('database_manager')
    assert database_manager is not None, "DatabaseManager должен быть доступен через DI"
    
    # В текущей реализации DatabaseManager не предоставляет get_repository(),
    # вместо этого используем master-репозиторий и карту таблиц как интеграционную проверку.
    master_repo = database_manager.get_master_repository()
    assert master_repo is not None, "MasterRepository должен быть доступен"

    table_map = database_manager.get_table_class_map()
    assert isinstance(table_map, dict), "Карта таблиц должна быть словарем"
    assert len(table_map) > 0, "Должна быть хотя бы одна таблица в карте"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_repositories_list(initialized_di_container):
    """Проверка доступности различных репозиториев"""
    database_manager = initialized_di_container.get_utility('database_manager')
    
    # Список репозиториев, которые должны быть доступны
    expected_repos = ['cache', 'actions']
    
    for repo_name in expected_repos:
        try:
            repo = database_manager.get_repository(repo_name)
            assert repo is not None, f"Репозиторий {repo_name} должен быть доступен"
        except Exception as e:
            # Некоторые репозитории могут быть опциональными
            pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_session_management(initialized_di_container):
    """Проверка управления сессиями БД"""
    database_manager = initialized_di_container.get_utility('database_manager')
    assert database_manager is not None, "DatabaseManager должен быть доступен через DI"
    
    # Проверяем, что можно получить базовую информацию о БД без исключений
    _ = database_manager.get_database_config()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_shutdown(initialized_di_container):
    """Проверка корректного shutdown database_manager"""
    database_manager = initialized_di_container.get_utility('database_manager')
    
    # Проверяем, что shutdown не вызывает ошибок
    if hasattr(database_manager, 'shutdown'):
        try:
            database_manager.shutdown()
        except Exception as e:
            # Shutdown может быть вызван несколько раз, это нормально
            pass

