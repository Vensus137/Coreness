"""
Unit-тесты для UpdateServerScript._run_migrations - запуск миграции в подпроцессе
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from modules.migrations.migration_manager import MigrationManager
from modules.update.docker_manager import DockerManager
from modules.update.server_updater import ServerUpdater
from modules.update.version_manager import VersionManager
from scripts.update_server import UpdateServerScript


@pytest.mark.unit
class TestUpdateServerMigrations:
    """Тесты для запуска миграций в подпроцессе"""
    
    @pytest.fixture
    def update_script(self, sample_config, mock_logger, project_root):
        """Создает экземпляр UpdateServerScript"""
        from scripts.update_server import UpdateServerScript
        
        script = UpdateServerScript.__new__(UpdateServerScript)
        script.base = MagicMock()
        script.base.get_project_root.return_value = project_root
        script.base.get_config.return_value = sample_config
        script.project_root = project_root
        script.config = sample_config
        script.logger = mock_logger
        script.formatter = MagicMock()
        
        # Инициализируем менеджеры
        from modules.update.compose_config_manager import ComposeConfigManager
        script.version_manager = VersionManager(project_root, mock_logger)
        script.server_updater = ServerUpdater(sample_config, project_root, mock_logger)
        script.docker_manager = DockerManager(project_root, mock_logger, sample_config)
        script.migration_manager = MigrationManager(sample_config, project_root, mock_logger, script.formatter)
        script.compose_config_manager = ComposeConfigManager(sample_config, mock_logger)
        
        script.environment = "test"
        script.new_version = "1.0.0"
        script.backup_path = None
        
        return script
    
    @patch.object(UpdateServerScript, '_run_subprocess_with_output')
    @patch.object(UpdateServerScript, '_is_container_running')
    @patch("modules.utils.user_input.confirm")
    def test_run_migrations_success(self, mock_confirm, mock_is_running, mock_run_subprocess, update_script, project_root):
        """Проверяет успешный запуск миграции в подпроцессе"""
        mock_confirm.return_value = True
        mock_is_running.return_value = False  # Контейнер не запущен, используем fallback на хосте
        mock_run_subprocess.return_value = 0  # Успешный код возврата
        
        # Мокаем get_container_name чтобы возвращал значение
        with patch.object(update_script.docker_manager.compose_manager, 'get_container_name', return_value='app-test'):
            # Мокаем путь к deployment_manager.py
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(update_script, 'project_root', project_root):
                    result = update_script._run_migrations()
                    
                    assert result is True
                    # Проверяем, что подпроцесс был запущен
                    mock_run_subprocess.assert_called_once()
                    # Проверяем параметры команды
                    call_args = mock_run_subprocess.call_args[0][0]
                    assert sys.executable in call_args
                    assert "--migrate-only" in call_args
                    assert "--version" in call_args
                    assert "1.0.0" in call_args
                    assert "--environment" in call_args
                    assert "test" in call_args
    
    @patch.object(UpdateServerScript, '_run_subprocess_with_output')
    @patch.object(UpdateServerScript, '_is_container_running')
    @patch("modules.utils.user_input.confirm")
    def test_run_migrations_with_backup(self, mock_confirm, mock_is_running, mock_run_subprocess, update_script, project_root):
        """Проверяет запуск миграции с бэкапом БД"""
        mock_confirm.return_value = True
        mock_is_running.return_value = False  # Контейнер не запущен, используем fallback на хосте
        mock_run_subprocess.return_value = 0  # Успешный код возврата
        db_backup_path = "/path/to/backup"
        
        # Мокаем get_container_name чтобы возвращал значение
        with patch.object(update_script.docker_manager.compose_manager, 'get_container_name', return_value='app-test'):
            # Мокаем путь к deployment_manager.py
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(update_script, 'project_root', project_root):
                    result = update_script._run_migrations(db_backup_path)
                    
                    assert result is True
                    # Проверяем, что --db-backup был добавлен в команду
                    call_args = mock_run_subprocess.call_args[0][0]
                    assert "--db-backup" in call_args
                    assert db_backup_path in call_args
    
    @patch("scripts.update_server.subprocess.Popen")
    @patch("modules.utils.user_input.confirm")
    def test_run_migrations_user_cancelled(self, mock_confirm, mock_popen, update_script):
        """Проверяет отмену миграции пользователем"""
        mock_confirm.return_value = False
        
        result = update_script._run_migrations()
        
        assert result is True  # Отмена не считается ошибкой
        # Подпроцесс не должен запускаться
        mock_popen.assert_not_called()
    
    @patch.object(UpdateServerScript, '_run_subprocess_with_output')
    @patch.object(UpdateServerScript, '_is_container_running')
    @patch("modules.utils.user_input.confirm")
    def test_run_migrations_process_failure(self, mock_confirm, mock_is_running, mock_run_subprocess, update_script, project_root):
        """Проверяет обработку ошибки подпроцесса"""
        mock_confirm.return_value = True
        mock_is_running.return_value = False  # Контейнер не запущен, используем fallback на хосте
        mock_run_subprocess.return_value = 1  # Ошибка подпроцесса
        db_backup_path = "/path/to/backup"
        
        # Мокаем get_container_name чтобы возвращал значение
        with patch.object(update_script.docker_manager.compose_manager, 'get_container_name', return_value='app-test'):
            # Мокаем путь к deployment_manager.py
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(update_script, 'project_root', project_root):
                    with patch.object(update_script.migration_manager, 'restore_database', return_value=True) as mock_restore:
                        result = update_script._run_migrations(db_backup_path)
                        
                        assert result is False
                        # Должно быть восстановление из бэкапа (без параметров, так как используется последний бэкап)
                        mock_restore.assert_called_once()
    
    @patch.object(UpdateServerScript, '_run_subprocess_with_output')
    @patch("modules.utils.user_input.confirm")
    def test_run_migrations_script_not_found(self, mock_confirm, mock_run_subprocess, update_script, project_root):
        """Проверяет обработку случая, когда скрипт не найден"""
        mock_confirm.return_value = True
        
        # Мокаем путь к deployment_manager.py - файл не существует
        with patch.object(Path, 'exists', return_value=False):
            with patch.object(update_script, 'project_root', project_root):
                result = update_script._run_migrations()
                
                assert result is False
                # Подпроцесс не должен запускаться
                mock_run_subprocess.assert_not_called()
    
    @patch.object(UpdateServerScript, '_run_subprocess_with_output')
    @patch.object(UpdateServerScript, '_is_container_running')
    @patch("modules.utils.user_input.confirm")
    def test_run_migrations_exception(self, mock_confirm, mock_is_running, mock_run_subprocess, update_script, project_root):
        """Проверяет обработку исключения при запуске подпроцесса"""
        mock_confirm.return_value = True
        mock_is_running.return_value = False  # Контейнер не запущен, используем fallback на хосте
        db_backup_path = "/path/to/backup"
        
        # Мокаем исключение при запуске подпроцесса
        mock_run_subprocess.side_effect = Exception("Subprocess error")
        
        # Мокаем get_container_name чтобы возвращал значение
        with patch.object(update_script.docker_manager.compose_manager, 'get_container_name', return_value='app-test'):
            # Мокаем путь к deployment_manager.py
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(update_script, 'project_root', project_root):
                    with patch.object(update_script.migration_manager, 'restore_database', return_value=True) as mock_restore:
                        result = update_script._run_migrations(db_backup_path)
                        
                        assert result is False
                        # Должно быть восстановление из бэкапа (без параметров, так как используется последний бэкап)
                        mock_restore.assert_called_once()
    
    @patch.object(UpdateServerScript, '_run_subprocess_with_output')
    @patch.object(UpdateServerScript, '_is_container_running')
    @patch("modules.utils.user_input.confirm")
    def test_run_migrations_no_confirmation_required(self, mock_confirm, mock_is_running, mock_run_subprocess, update_script, project_root):
        """Проверяет запуск миграции без подтверждения"""
        # Отключаем требование подтверждения
        update_script.migration_manager.require_confirmation = False
        mock_is_running.return_value = False  # Контейнер не запущен, используем fallback на хосте
        mock_run_subprocess.return_value = 0  # Успешный код возврата
        
        # Мокаем get_container_name чтобы возвращал значение
        with patch.object(update_script.docker_manager.compose_manager, 'get_container_name', return_value='app-test'):
            # Мокаем путь к deployment_manager.py
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(update_script, 'project_root', project_root):
                    result = update_script._run_migrations()
                    
                    assert result is True
                    # confirm не должен вызываться
                    mock_confirm.assert_not_called()
                    # Подпроцесс должен запуститься
                    mock_run_subprocess.assert_called_once()

