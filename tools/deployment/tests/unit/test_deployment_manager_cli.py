"""
Unit-тесты для DeploymentManager - CLI параметры и run_migration_only
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from modules.ui.output import get_formatter


@pytest.mark.unit
class TestDeploymentManagerCLI:
    """Тесты для CLI параметров и run_migration_only"""
    
    @pytest.fixture
    def deployment_manager(self, sample_config, mock_logger, project_root):
        """Создает экземпляр DeploymentManager"""
        import sys
        
        # Добавляем путь к deployment для импорта
        deployment_dir = Path(__file__).parent.parent.parent
        if str(deployment_dir) not in sys.path:
            sys.path.insert(0, str(deployment_dir))
        
        from deployment_manager import DeploymentManager
        
        manager = DeploymentManager.__new__(DeploymentManager)
        manager.base = MagicMock()
        manager.base.get_project_root.return_value = project_root
        manager.base.get_config.return_value = sample_config
        manager.project_root = project_root
        manager.config = sample_config
        manager.formatter = get_formatter()
        
        return manager
    
    def test_run_migration_only_success(self, deployment_manager, mock_logger):
        """Проверяет успешный запуск миграции через run_migration_only"""
        version = "1.0.0"
        environment = "test"
        
        with patch("modules.migrations.migration_manager.MigrationManager") as mock_migration_manager_class:
            mock_migration_manager = MagicMock()
            mock_migration_manager.run_all_migrations = MagicMock(return_value=True)
            mock_migration_manager_class.return_value = mock_migration_manager
            
            result = deployment_manager.run_migration_only(version, environment)
            
            assert result is True
            mock_migration_manager.run_all_migrations.assert_called_once_with(version, None)
    
    def test_run_migration_only_with_backup(self, deployment_manager, mock_logger):
        """Проверяет запуск миграции с бэкапом БД"""
        version = "1.0.0"
        environment = "test"
        db_backup_path = "/path/to/backup"
        
        with patch("modules.migrations.migration_manager.MigrationManager") as mock_migration_manager_class:
            mock_migration_manager = MagicMock()
            mock_migration_manager.run_all_migrations = MagicMock(return_value=True)
            mock_migration_manager_class.return_value = mock_migration_manager
            
            result = deployment_manager.run_migration_only(version, environment, db_backup_path)
            
            assert result is True
            mock_migration_manager.run_all_migrations.assert_called_once_with(version, db_backup_path)
    
    def test_run_migration_only_failure(self, deployment_manager, mock_logger):
        """Проверяет обработку ошибки миграции"""
        version = "1.0.0"
        environment = "test"
        db_backup_path = "/path/to/backup"
        
        with patch("modules.migrations.migration_manager.MigrationManager") as mock_migration_manager_class:
            mock_migration_manager = MagicMock()
            mock_migration_manager.run_all_migrations = MagicMock(return_value=False)
            mock_migration_manager_class.return_value = mock_migration_manager
            
            result = deployment_manager.run_migration_only(version, environment, db_backup_path)
            
            assert result is False
            mock_migration_manager.run_all_migrations.assert_called_once_with(version, db_backup_path)
    
    def test_run_migration_only_exception_with_restore(self, deployment_manager, mock_logger):
        """Проверяет восстановление из бэкапа при исключении"""
        version = "1.0.0"
        environment = "test"
        db_backup_path = "/path/to/backup"
        
        with patch("modules.migrations.migration_manager.MigrationManager") as mock_migration_manager_class:
            mock_migration_manager = MagicMock()
            mock_migration_manager.run_all_migrations = MagicMock(side_effect=Exception("Migration error"))
            mock_migration_manager.restore_database = MagicMock(return_value=True)
            mock_migration_manager_class.return_value = mock_migration_manager
            
            result = deployment_manager.run_migration_only(version, environment, db_backup_path)
            
            assert result is False
            # Проверяем, что restore_database был вызван (без параметров, так как используется последний бэкап)
            mock_migration_manager.restore_database.assert_called_once()
    
    def test_run_migration_only_exception_without_backup(self, deployment_manager, mock_logger):
        """Проверяет обработку исключения без бэкапа"""
        version = "1.0.0"
        environment = "test"
        
        with patch("modules.migrations.migration_manager.MigrationManager") as mock_migration_manager_class:
            mock_migration_manager = MagicMock()
            mock_migration_manager.run_all_migrations = MagicMock(side_effect=Exception("Migration error"))
            mock_migration_manager.restore_database = MagicMock()
            mock_migration_manager_class.return_value = mock_migration_manager
            
            result = deployment_manager.run_migration_only(version, environment)
            
            assert result is False
            # Без бэкапа restore_database не должен вызываться
            mock_migration_manager.restore_database.assert_not_called()
    
    @patch("os.execv")
    @patch("time.sleep")
    @patch("deployment_manager.Path")
    def test_restart_self_success(self, mock_path_class, mock_sleep, mock_execv, deployment_manager):
        """Проверяет успешный перезапуск утилиты"""
        # Мокаем Path(__file__)
        mock_file_path = MagicMock()
        mock_file_path.resolve.return_value = MagicMock()
        mock_file_path.resolve.return_value.__str__ = lambda x: "/path/to/deployment_manager.py"
        mock_path_class.return_value = mock_file_path
        
        deployment_manager._restart_self()
        
        # Проверяем, что os.execv был вызван с правильными параметрами
        mock_execv.assert_called_once()
        args = mock_execv.call_args[0]
        assert args[0] == sys.executable
        assert args[1][0] == sys.executable
        assert "deployment_manager.py" in str(args[1][1])
    
    @patch("os.execv")
    @patch("deployment_manager.Path")
    def test_restart_self_script_not_found(self, mock_path_class, mock_execv, deployment_manager):
        """Проверяет обработку случая, когда скрипт не найден"""
        # В реальной реализации проверка существования не выполняется,
        # но мы можем проверить, что метод не падает с исключением
        # Мокаем Path(__file__)
        mock_file_path = MagicMock()
        mock_resolved = MagicMock()
        mock_resolved.exists.return_value = False
        mock_file_path.resolve.return_value = mock_resolved
        mock_path_class.return_value = mock_file_path
        
        # Мокаем os.execv чтобы он не выполнялся реально
        mock_execv.side_effect = FileNotFoundError("Script not found")
        
        # Метод должен обработать исключение и не упасть
        deployment_manager._restart_self()
        
        # os.execv должен был быть вызван (но упал с FileNotFoundError)
        mock_execv.assert_called_once()
    
    @patch("os.execv")
    @patch("deployment_manager.Path")
    def test_restart_self_exception(self, mock_path_class, mock_execv, deployment_manager):
        """Проверяет обработку исключения при перезапуске"""
        mock_execv.side_effect = Exception("Exec error")
        
        # Мокаем Path(__file__)
        mock_file_path = MagicMock()
        mock_file_path.resolve.return_value = MagicMock()
        mock_file_path.resolve.return_value.exists.return_value = True
        mock_file_path.resolve.return_value.__str__ = lambda x: "/path/to/deployment_manager.py"
        mock_path_class.return_value = mock_file_path
        
        # Не должно упасть с исключением
        deployment_manager._restart_self()
        
        # os.execv должен был быть вызван (но упал)
        mock_execv.assert_called_once()

