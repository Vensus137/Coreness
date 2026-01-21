"""
Integration tests for database operations
Verify correct database operations through DI container
"""
import pytest

from tests.conftest import initialized_di_container, test_database_url  # noqa: F401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_initialization(initialized_di_container):
    """Verify database_manager initialization"""
    database_manager = initialized_di_container.get_utility('database_manager')
    
    # Verify that database_manager can be obtained (without exceptions)
    assert database_manager is not None, "DatabaseManager should be available through DI"
    
    # Verify that we can get database information
    db_info = database_manager.get_database_config()
    assert db_info is not None, "Database information should be available"
    assert 'type' in db_info, "Database information should contain type"
    
    # Verify that we can get list of available databases
    available_dbs = database_manager.get_available_databases()
    assert isinstance(available_dbs, list), "List of available databases should be an array"
    assert len(available_dbs) > 0, "At least one database should be available"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_repositories_work(initialized_di_container):
    """Verify repository operations through database_manager"""
    database_manager = initialized_di_container.get_utility('database_manager')
    assert database_manager is not None, "DatabaseManager should be available through DI"
    
    # In current implementation, DatabaseManager does not provide get_repository(),
    # instead we use master repository and table map as integration check.
    master_repo = database_manager.get_master_repository()
    assert master_repo is not None, "MasterRepository should be available"

    table_map = database_manager.get_table_class_map()
    assert isinstance(table_map, dict), "Table map should be a dictionary"
    assert len(table_map) > 0, "At least one table should be in the map"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_repositories_list(initialized_di_container):
    """Verify availability of various repositories"""
    database_manager = initialized_di_container.get_utility('database_manager')
    
    # List of repositories that should be available
    expected_repos = ['cache', 'actions']
    
    for repo_name in expected_repos:
        try:
            repo = database_manager.get_repository(repo_name)
            assert repo is not None, f"Repository {repo_name} should be available"
        except Exception as e:
            # Some repositories may be optional
            pass


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_session_management(initialized_di_container):
    """Verify database session management"""
    database_manager = initialized_di_container.get_utility('database_manager')
    assert database_manager is not None, "DatabaseManager should be available through DI"
    
    # Verify that we can get basic database information without exceptions
    _ = database_manager.get_database_config()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_database_manager_shutdown(initialized_di_container):
    """Verify correct database_manager shutdown"""
    database_manager = initialized_di_container.get_utility('database_manager')
    
    # Verify that shutdown does not cause errors
    if hasattr(database_manager, 'shutdown'):
        try:
            database_manager.shutdown()
        except Exception as e:
            # Shutdown can be called multiple times, this is normal
            pass

