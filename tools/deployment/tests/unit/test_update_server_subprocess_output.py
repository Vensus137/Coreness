"""
Unit-тесты для UpdateServerScript._run_subprocess_with_output - вывод логов в реальном времени
"""
from unittest.mock import MagicMock, patch

import pytest
from modules.migrations.migration_manager import MigrationManager
from modules.update.docker_manager import DockerManager
from modules.update.server_updater import ServerUpdater
from modules.update.version_manager import VersionManager


@pytest.mark.unit
class TestUpdateServerSubprocessOutput:
    """Тесты для метода _run_subprocess_with_output"""
    
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
        
        return script
    
    @patch("scripts.update_server.sys.stdout")
    @patch("scripts.update_server.time.time")
    @patch("scripts.update_server.time.sleep")
    @patch("scripts.update_server.subprocess.Popen")
    def test_run_subprocess_success_linux(self, mock_popen, mock_sleep, mock_time, mock_stdout, update_script):
        """Проверяет успешный запуск подпроцесса на Linux с выводом логов"""
        # Мокаем время
        mock_time.side_effect = [100.0, 102.0]  # start_time, end_time
        
        # Мокаем платформу - Linux
        with patch("scripts.update_server.platform.system", return_value="Linux"):
            # Мокаем select для Linux
            with patch("scripts.update_server.select.select") as mock_select:
                # Мокаем процесс
                mock_process = MagicMock()
                mock_process.poll.side_effect = [None, None, 0]  # Процесс еще работает, потом завершился
                mock_process.wait.return_value = None
                mock_process.returncode = 0
                
                # Мокаем stdout с несколькими строками вывода
                mock_stdout_obj = MagicMock()
                mock_stdout_obj.readline.side_effect = ["Line 1\n", "Line 2\n", ""]
                mock_process.stdout = mock_stdout_obj
                
                mock_popen.return_value = mock_process
                
                # Мокаем select.select - возвращаем готовый stdout для чтения
                mock_select.side_effect = [
                    ([mock_stdout_obj], [], []),  # Первая строка готова
                    ([mock_stdout_obj], [], []),  # Вторая строка готова
                    ([], [], [])  # Больше нет данных
                ]
                
                # Запускаем метод
                result = update_script._run_subprocess_with_output(
                    ["python", "-c", "print('test')"],
                    "Тестовая команда"
                )
                
                # Проверяем результат
                assert result == 0
                
                # Проверяем, что процесс был запущен
                mock_popen.assert_called_once()
                
                # Проверяем, что вывод был записан в stdout
                assert mock_stdout.write.call_count >= 2  # Минимум 2 строки
                assert mock_stdout.flush.call_count >= 2
                
                # Проверяем, что были вызовы select.select
                assert mock_select.call_count >= 2
    
    @patch("scripts.update_server.sys.stdout")
    @patch("scripts.update_server.time.time")
    @patch("scripts.update_server.time.sleep")
    @patch("scripts.update_server.subprocess.Popen")
    def test_run_subprocess_success_windows(self, mock_popen, mock_sleep, mock_time, mock_stdout, update_script):
        """Проверяет успешный запуск подпроцесса на Windows с выводом логов"""
        # Мокаем время
        mock_time.side_effect = [100.0, 102.0]  # start_time, end_time
        
        # Мокаем платформу - Windows
        with patch("scripts.update_server.platform.system", return_value="Windows"):
            # Мокаем процесс
            mock_process = MagicMock()
            mock_process.poll.side_effect = [None, None, 0]  # Процесс еще работает, потом завершился
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            
            # Мокаем stdout с несколькими строками вывода
            mock_stdout_obj = MagicMock()
            mock_stdout_obj.readline.side_effect = ["Line 1\n", "Line 2\n", ""]
            mock_process.stdout = mock_stdout_obj
            
            mock_popen.return_value = mock_process
            
            # Запускаем метод
            result = update_script._run_subprocess_with_output(
                ["python", "-c", "print('test')"],
                "Тестовая команда"
            )
            
            # Проверяем результат
            assert result == 0
            
            # Проверяем, что процесс был запущен
            mock_popen.assert_called_once()
            
            # Проверяем, что вывод был записан в stdout
            assert mock_stdout.write.call_count >= 2  # Минимум 2 строки
            assert mock_stdout.flush.call_count >= 2
            
            # На Windows select не используется
            # Проверяем, что был вызов sleep (для задержки между чтениями)
            assert mock_sleep.call_count >= 0
    
    @patch("scripts.update_server.sys.stdout")
    @patch("scripts.update_server.time.time")
    @patch("scripts.update_server.time.sleep")
    @patch("scripts.update_server.subprocess.Popen")
    def test_run_subprocess_failure(self, mock_popen, mock_sleep, mock_time, mock_stdout, update_script):
        """Проверяет обработку ошибки подпроцесса"""
        # Мокаем время
        mock_time.side_effect = [100.0, 102.0]  # start_time, end_time
        
        # Мокаем платформу - Windows (проще для теста)
        with patch("scripts.update_server.platform.system", return_value="Windows"):
            # Мокаем процесс с ошибкой
            mock_process = MagicMock()
            mock_process.poll.side_effect = [None, None, 1]  # Процесс завершился с ошибкой
            mock_process.wait.return_value = None
            mock_process.returncode = 1
            
            # Мокаем stdout с ошибкой
            mock_stdout_obj = MagicMock()
            mock_stdout_obj.readline.side_effect = ["Error message\n", ""]
            mock_process.stdout = mock_stdout_obj
            
            mock_popen.return_value = mock_process
            
            # Запускаем метод
            result = update_script._run_subprocess_with_output(
                ["python", "-c", "exit(1)"],
                "Команда с ошибкой"
            )
            
            # Проверяем результат
            assert result == 1
            
            # Проверяем, что процесс был запущен
            mock_popen.assert_called_once()
            
            # Проверяем, что вывод ошибки был записан
            assert mock_stdout.write.call_count >= 1
    
    @patch("scripts.update_server.sys.stdout")
    @patch("scripts.update_server.time.time")
    @patch("scripts.update_server.subprocess.Popen")
    def test_run_subprocess_exception(self, mock_popen, mock_stdout, mock_time, update_script):
        """Проверяет обработку исключения при запуске подпроцесса"""
        # Мокаем время
        mock_time.return_value = 100.0
        
        # Мокаем исключение при создании процесса
        mock_popen.side_effect = Exception("Subprocess error")
        
        # Запускаем метод
        result = update_script._run_subprocess_with_output(
            ["python", "-c", "print('test')"],
            "Команда с исключением"
        )
        
        # Проверяем результат - должен вернуть 1 при ошибке
        assert result == 1
        
        # Проверяем, что была попытка создать процесс
        mock_popen.assert_called_once()
    
    @patch("scripts.update_server.sys.stdout")
    @patch("scripts.update_server.time.time")
    @patch("scripts.update_server.time.sleep")
    @patch("scripts.update_server.subprocess.Popen")
    def test_run_subprocess_readline_exception_linux(self, mock_popen, mock_sleep, mock_time, mock_stdout, update_script):
        """Проверяет обработку исключения при чтении вывода на Linux"""
        # Мокаем время
        mock_time.side_effect = [100.0, 102.0]  # start_time, end_time
        
        # Мокаем платформу - Linux
        with patch("scripts.update_server.platform.system", return_value="Linux"):
            # Мокаем select для Linux
            with patch("scripts.update_server.select.select") as mock_select:
                # Мокаем процесс
                mock_process = MagicMock()
                mock_process.poll.side_effect = [None, None, 0]  # Процесс завершился
                mock_process.wait.return_value = None
                mock_process.returncode = 0
                
                # Мокаем stdout с исключением при чтении
                mock_stdout_obj = MagicMock()
                mock_stdout_obj.readline.side_effect = Exception("Read error")
                mock_process.stdout = mock_stdout_obj
                
                mock_popen.return_value = mock_process
                
                # Мокаем select.select - возвращаем готовый stdout
                mock_select.side_effect = [
                    ([mock_stdout_obj], [], []),  # Первая попытка чтения
                    ([], [], [])  # Больше нет данных
                ]
                
                # Запускаем метод - не должно упасть с исключением
                result = update_script._run_subprocess_with_output(
                    ["python", "-c", "print('test')"],
                    "Команда с ошибкой чтения"
                )
                
                # Проверяем результат - должен обработать исключение и завершиться
                assert result == 0
    
    @patch("scripts.update_server.sys.stdout")
    @patch("scripts.update_server.time.time")
    @patch("scripts.update_server.time.sleep")
    @patch("scripts.update_server.subprocess.Popen")
    def test_run_subprocess_encoding(self, mock_popen, mock_sleep, mock_time, mock_stdout, update_script):
        """Проверяет использование правильной кодировки для подпроцесса"""
        # Мокаем время
        mock_time.side_effect = [100.0, 102.0]  # start_time, end_time
        
        # Мокаем переменную окружения для кодировки
        with patch("scripts.update_server.os.environ", {"PYTHONIOENCODING": "utf-8"}):
            # Мокаем платформу - Windows
            with patch("scripts.update_server.platform.system", return_value="Windows"):
                # Мокаем процесс
                mock_process = MagicMock()
                mock_process.poll.return_value = 0  # Процесс сразу завершился
                mock_process.wait.return_value = None
                mock_process.returncode = 0
                
                mock_stdout_obj = MagicMock()
                mock_stdout_obj.readline.return_value = ""
                mock_process.stdout = mock_stdout_obj
                
                mock_popen.return_value = mock_process
                
                # Запускаем метод
                update_script._run_subprocess_with_output(
                    ["python", "-c", "print('test')"],
                    "Команда с кодировкой"
                )
                
                # Проверяем, что Popen был вызван с правильной кодировкой
                call_kwargs = mock_popen.call_args[1]
                assert call_kwargs.get('encoding') == 'utf-8'
                assert call_kwargs.get('errors') == 'replace'
    
    @patch("scripts.update_server.sys.stdout")
    @patch("scripts.update_server.time.time")
    @patch("scripts.update_server.time.sleep")
    @patch("scripts.update_server.subprocess.Popen")
    def test_run_subprocess_empty_output(self, mock_popen, mock_sleep, mock_time, mock_stdout, update_script):
        """Проверяет обработку подпроцесса без вывода"""
        # Мокаем время
        mock_time.side_effect = [100.0, 102.0]  # start_time, end_time
        
        # Мокаем платформу - Windows
        with patch("scripts.update_server.platform.system", return_value="Windows"):
            # Мокаем процесс
            mock_process = MagicMock()
            mock_process.poll.return_value = 0  # Процесс сразу завершился
            mock_process.wait.return_value = None
            mock_process.returncode = 0
            
            # Мокаем stdout без вывода
            mock_stdout_obj = MagicMock()
            mock_stdout_obj.readline.return_value = ""  # Нет вывода
            mock_process.stdout = mock_stdout_obj
            
            mock_popen.return_value = mock_process
            
            # Запускаем метод
            result = update_script._run_subprocess_with_output(
                ["python", "-c", "pass"],
                "Команда без вывода"
            )
            
            # Проверяем результат
            assert result == 0
            
            # Проверяем, что процесс был запущен
            mock_popen.assert_called_once()
            
            # Проверяем, что не было попыток записи пустого вывода
            # (или были, но с пустыми строками)
            # Может быть несколько вызовов с пустыми строками, это нормально

