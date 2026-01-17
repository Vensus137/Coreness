"""
Unit-тесты для MigrationManager.run_all_migrations
"""
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestMigrationManagerRunAll:
    """Тесты для метода run_all_migrations"""
    
    @pytest.fixture
    def migration_manager(self, sample_config, mock_logger, project_root):
        """Создает экземпляр MigrationManager"""
        from modules.migrations.migration_manager import MigrationManager
        from modules.ui.output import get_formatter
        
        manager = MigrationManager(sample_config, project_root, mock_logger, get_formatter())
        return manager
    
    def test_run_all_migrations_success_both(self, migration_manager):
        """Проверяет успешный запуск обеих миграций (универсальной и специфической)"""
        version = "1.0.0"
        
        with patch.object(migration_manager, 'check_specific_migration_needed', return_value=True):
            with patch.object(migration_manager, 'run_universal_migration', return_value=True):
                with patch.object(migration_manager, 'run_specific_migration', return_value=True):
                    result = migration_manager.run_all_migrations(version)
                    
                    assert result is True
                    migration_manager.run_universal_migration.assert_called_once()
                    migration_manager.run_specific_migration.assert_called_once_with(version)
    
    def test_run_all_migrations_success_universal_only(self, migration_manager):
        """Проверяет успешный запуск только универсальной миграции (специфической нет)"""
        version = "1.0.0"
        
        with patch.object(migration_manager, 'check_specific_migration_needed', return_value=False):
            with patch.object(migration_manager, 'run_universal_migration', return_value=True):
                result = migration_manager.run_all_migrations(version)
                
                assert result is True
                migration_manager.run_universal_migration.assert_called_once()
                # run_specific_migration не должен вызываться
                assert not hasattr(migration_manager.run_specific_migration, 'call_count') or \
                       migration_manager.run_specific_migration.call_count == 0
    
    def test_run_all_migrations_universal_failure(self, migration_manager):
        """Проверяет обработку ошибки универсальной миграции"""
        version = "1.0.0"
        db_backup_path = "/path/to/backup"
        
        with patch.object(migration_manager, 'check_specific_migration_needed', return_value=True):
            with patch.object(migration_manager, 'run_universal_migration', return_value=False):
                with patch.object(migration_manager, 'restore_database', return_value=True) as mock_restore:
                    result = migration_manager.run_all_migrations(version, db_backup_path)
                    
                    assert result is False
                    migration_manager.run_universal_migration.assert_called_once()
                    # Специфическая миграция не должна запускаться при ошибке универсальной
                    assert not hasattr(migration_manager.run_specific_migration, 'call_count') or \
                           migration_manager.run_specific_migration.call_count == 0
                    # Должно быть восстановление из бэкапа (без параметров, так как используется последний бэкап)
                    mock_restore.assert_called_once()
    
    def test_run_all_migrations_specific_failure(self, migration_manager):
        """Проверяет обработку ошибки специфической миграции"""
        version = "1.0.0"
        db_backup_path = "/path/to/backup"
        
        with patch.object(migration_manager, 'check_specific_migration_needed', return_value=True):
            with patch.object(migration_manager, 'run_universal_migration', return_value=True):
                with patch.object(migration_manager, 'run_specific_migration', return_value=False):
                    with patch.object(migration_manager, 'restore_database', return_value=True) as mock_restore:
                        result = migration_manager.run_all_migrations(version, db_backup_path)
                        
                        assert result is False
                        migration_manager.run_universal_migration.assert_called_once()
                        migration_manager.run_specific_migration.assert_called_once_with(version)
                        # Должно быть восстановление из бэкапа (без параметров, так как используется последний бэкап)
                        mock_restore.assert_called_once()
    
    def test_run_all_migrations_universal_failure_no_backup(self, migration_manager):
        """Проверяет обработку ошибки без бэкапа"""
        version = "1.0.0"
        
        with patch.object(migration_manager, 'check_specific_migration_needed', return_value=True):
            with patch.object(migration_manager, 'run_universal_migration', return_value=False):
                with patch.object(migration_manager, 'restore_database') as mock_restore:
                    result = migration_manager.run_all_migrations(version)
                    
                    assert result is False
                    # Без бэкапа restore_database не должен вызываться
                    mock_restore.assert_not_called()
    
    def test_run_all_migrations_exception(self, migration_manager):
        """Проверяет обработку исключения при миграции"""
        version = "1.0.0"
        db_backup_path = "/path/to/backup"
        
        with patch.object(migration_manager, 'check_specific_migration_needed', side_effect=Exception("Error")):
            with patch.object(migration_manager, 'restore_database', return_value=True) as mock_restore:
                result = migration_manager.run_all_migrations(version, db_backup_path)
                
                assert result is False
                # Должно быть восстановление из бэкапа при исключении (без параметров, так как используется последний бэкап)
                mock_restore.assert_called_once()
    
    def test_run_all_migrations_exception_no_backup(self, migration_manager):
        """Проверяет обработку исключения без бэкапа"""
        version = "1.0.0"
        
        with patch.object(migration_manager, 'check_specific_migration_needed', side_effect=Exception("Error")):
            with patch.object(migration_manager, 'restore_database') as mock_restore:
                result = migration_manager.run_all_migrations(version)
                
                assert result is False
                # Без бэкапа restore_database не должен вызываться
                mock_restore.assert_not_called()

