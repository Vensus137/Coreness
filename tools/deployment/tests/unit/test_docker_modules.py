"""
Unit-тесты для новых модулей Docker (после рефакторинга)
Тесты для docker_checker, compose_manager, image_manager, container_manager
"""

from unittest.mock import MagicMock, patch

import pytest
from modules.update.compose_manager import ComposeManager
from modules.update.container_manager import ContainerManager
from modules.update.docker_checker import DockerChecker
from modules.update.image_manager import ImageManager


@pytest.mark.unit
class TestDockerChecker:
    """Тесты для DockerChecker"""
    
    @pytest.fixture
    def docker_checker(self, mock_logger, sample_config):
        """Создает экземпляр DockerChecker"""
        return DockerChecker(mock_logger, sample_config)
    
    @patch("modules.update.docker_checker.subprocess.run")
    def test_check_docker_success(self, mock_subprocess, docker_checker):
        """Проверяет успешную проверку Docker"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Docker version 20.10.0"
        mock_subprocess.return_value = mock_result
        
        result = docker_checker.check_docker()
        
        assert result is True
        docker_checker.logger.info.assert_called()
    
    @patch("modules.update.docker_checker.subprocess.run")
    def test_check_docker_failure(self, mock_subprocess, docker_checker):
        """Проверяет обработку отсутствия Docker"""
        mock_subprocess.side_effect = FileNotFoundError()
        
        result = docker_checker.check_docker()
        
        assert result is False
        docker_checker.logger.error.assert_called()
    
    @patch("modules.update.docker_checker.subprocess.run")
    def test_check_docker_compose_new_syntax(self, mock_subprocess, docker_checker):
        """Проверяет обнаружение docker compose (новый синтаксис)"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Docker Compose version v2.0.0"
        mock_subprocess.return_value = mock_result
        
        result = docker_checker.check_docker_compose()
        
        assert result is True
    
    @patch("modules.update.docker_checker.subprocess.run")
    def test_get_compose_command_new_syntax(self, mock_subprocess, docker_checker):
        """Проверяет получение команды docker compose (новый синтаксис)"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        result = docker_checker.get_compose_command()
        
        assert result == ['docker', 'compose']
    
    @patch("modules.update.docker_checker.subprocess.run")
    def test_get_compose_command_old_syntax(self, mock_subprocess, docker_checker):
        """Проверяет fallback на docker-compose (старый синтаксис)"""
        # Первый вызов (docker compose) падает, второй (docker-compose) успешен
        mock_subprocess.side_effect = [
            FileNotFoundError(),  # docker compose не найден
            MagicMock(returncode=0)  # docker-compose найден
        ]
        
        result = docker_checker.get_compose_command()
        
        assert result == ['docker-compose']


@pytest.mark.unit
class TestComposeManager:
    """Тесты для ComposeManager"""
    
    @pytest.fixture
    def compose_manager(self, mock_logger, sample_config, project_root):
        """Создает экземпляр ComposeManager"""
        from modules.update.compose_config_manager import ComposeConfigManager
        compose_config_manager = ComposeConfigManager(sample_config, mock_logger)
        manager = ComposeManager(project_root, mock_logger, sample_config, compose_config_manager)
        manager.set_compose_command(['docker', 'compose'])
        return manager
    
    def test_get_compose_file_test(self, compose_manager, project_root, tmp_path):
        """Проверяет получение compose файла для test окружения"""
        # Создаем глобальный файл для тестирования
        global_config_path = tmp_path / ".docker-compose" / "docker-compose.test.yml"
        global_config_path.parent.mkdir(parents=True)
        global_config_path.write_text("version: '3'")
        
        with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
            with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_config_path):
                compose_file = compose_manager.get_compose_file("test")
                
                assert compose_file is not None
                assert compose_file == global_config_path
    
    def test_get_compose_file_prod(self, compose_manager, project_root, tmp_path):
        """Проверяет получение compose файла для prod окружения"""
        # Создаем глобальный файл для тестирования
        global_config_path = tmp_path / ".docker-compose" / "docker-compose.prod.yml"
        global_config_path.parent.mkdir(parents=True)
        global_config_path.write_text("version: '3'")
        
        with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
            with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_config_path):
                compose_file = compose_manager.get_compose_file("prod")
                
                assert compose_file is not None
                assert compose_file == global_config_path
    
    def test_get_compose_file_not_found(self, compose_manager, project_root):
        """Проверяет что метод возвращает None если глобальные файлы не найдены"""
        with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=False):
            result = compose_manager.get_compose_file("test")
            
            # Если глобальные файлы не существуют, должен вернуться None
            assert result is None
    
    @patch("modules.update.compose_manager.subprocess.run")
    @patch("modules.update.compose_manager.yaml.safe_load")
    def test_get_image_name_from_config(self, mock_yaml, mock_subprocess, compose_manager, project_root):
        """Проверяет получение имени образа из compose конфига"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "services:\n  app:\n    image: my-app:latest"
        mock_subprocess.return_value = mock_result
        
        mock_yaml.return_value = {
            'services': {
                'app': {
                    'image': 'my-app:latest'
                }
            }
        }
        
        compose_file = project_root / "docker" / "docker-compose.yml"
        image_name = compose_manager.get_image_name(compose_file)
        
        assert image_name == "my-app"
    
    @patch("modules.update.compose_manager.subprocess.run")
    @patch("modules.update.compose_manager.yaml.safe_load")
    def test_get_image_name_generated(self, mock_yaml, mock_subprocess, compose_manager, project_root):
        """Проверяет генерацию имени образа если image не указан"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        mock_yaml.return_value = {
            'services': {
                'app': {}
            }
        }
        
        compose_file = project_root / "docker" / "docker-compose.yml"
        image_name = compose_manager.get_image_name(compose_file)
        
        # Должно быть сгенерировано имя на основе project_root и service name
        assert image_name is not None
        assert 'app' in image_name.lower()
    
    @patch("modules.update.compose_manager.subprocess.run")
    @patch("modules.update.compose_manager.yaml.safe_load")
    @patch("builtins.open", create=True)
    def test_get_container_name_test_environment(self, mock_open, mock_yaml, mock_subprocess, compose_manager, project_root, tmp_path):
        """Проверяет получение container_name для test окружения"""
        # Создаем глобальные файлы для тестирования
        global_base = tmp_path / ".docker-compose" / "docker-compose.yml"
        global_test = tmp_path / ".docker-compose" / "docker-compose.test.yml"
        global_base.parent.mkdir(parents=True)
        global_base.write_text("version: '3'")
        global_test.write_text("version: '3'")
        
        with patch.object(compose_manager.compose_config_manager, "get_base_config_path", return_value=global_base):
            with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
                with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_test):
                    # Мокаем чтение файла окружения
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value = mock_file
                    mock_file.__exit__.return_value = None
                    mock_open.return_value = mock_file
                    
                    # Мокаем docker-compose config
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = "services:\n  app-test:\n    container_name: app-test"
                    mock_subprocess.return_value = mock_result
                    
                    # yaml.safe_load вызывается дважды:
                    # 1. Для парсинга вывода docker-compose config (строка)
                    # 2. Для чтения файла окружения (docker-compose.test.yml) - файловый объект
                    call_count = [0]
                    def yaml_side_effect(content):
                        call_count[0] += 1
                        # Первый вызов - вывод docker-compose config (строка)
                        if call_count[0] == 1:
                            return {
                                'services': {
                                    'app-test': {
                                        'container_name': 'app-test'
                                    }
                                }
                            }
                        # Второй вызов - файл окружения (файловый объект)
                        else:
                            return {
                                'services': {
                                    'app-test': {}
                                }
                            }
                    mock_yaml.side_effect = yaml_side_effect
                    
                    # Проверяем что compose_command установлен
                    assert compose_manager.compose_command is not None, "compose_command должен быть установлен"
                    
                    container_name = compose_manager.get_container_name("test")
                    
                    assert container_name == "app-test"
    
    @patch("modules.update.compose_manager.subprocess.run")
    @patch("modules.update.compose_manager.yaml.safe_load")
    @patch("builtins.open", create=True)
    def test_get_container_name_prod_environment(self, mock_open, mock_yaml, mock_subprocess, compose_manager, project_root, tmp_path):
        """Проверяет получение container_name для prod окружения"""
        # Создаем глобальные файлы для тестирования
        global_base = tmp_path / ".docker-compose" / "docker-compose.yml"
        global_prod = tmp_path / ".docker-compose" / "docker-compose.prod.yml"
        global_base.parent.mkdir(parents=True)
        global_base.write_text("version: '3'")
        global_prod.write_text("version: '3'")
        
        with patch.object(compose_manager.compose_config_manager, "get_base_config_path", return_value=global_base):
            with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
                with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_prod):
                    # Мокаем чтение файла окружения
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value = mock_file
                    mock_file.__exit__.return_value = None
                    mock_open.return_value = mock_file
                    
                    # Мокаем docker-compose config
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = "services:\n  app:\n    container_name: app"
                    mock_subprocess.return_value = mock_result
                    
                    # yaml.safe_load вызывается дважды:
                    # 1. Для парсинга вывода docker-compose config (строка)
                    # 2. Для чтения файла окружения (docker-compose.prod.yml) - файловый объект
                    call_count = [0]
                    def yaml_side_effect(content):
                        call_count[0] += 1
                        if call_count[0] == 1:  # Первый вызов - вывод docker-compose config
                            return {
                                'services': {
                                    'core': {
                                        'container_name': 'app'
                                    }
                                }
                            }
                        else:  # Второй вызов - файл окружения
                            return {
                                'services': {
                                    'core': {}
                                }
                            }
                    mock_yaml.side_effect = yaml_side_effect
                    
                    container_name = compose_manager.get_container_name("prod")
                    
                    assert container_name == "app"
    
    @patch("modules.update.compose_manager.subprocess.run")
    @patch("modules.update.compose_manager.yaml.safe_load")
    @patch("builtins.open", create=True)
    def test_get_container_name_custom_environment(self, mock_open, mock_yaml, mock_subprocess, compose_manager, project_root, tmp_path):
        """Проверяет получение container_name для кастомного окружения (coreness)"""
        # Создаем глобальные файлы для тестирования
        global_base = tmp_path / ".docker-compose" / "docker-compose.yml"
        global_coreness = tmp_path / ".docker-compose" / "docker-compose.coreness.yml"
        global_base.parent.mkdir(parents=True)
        global_base.write_text("version: '3'")
        global_coreness.write_text("version: '3'")
        
        with patch.object(compose_manager.compose_config_manager, "get_base_config_path", return_value=global_base):
            with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
                with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_coreness):
                    # Мокаем чтение файла окружения
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value = mock_file
                    mock_file.__exit__.return_value = None
                    mock_open.return_value = mock_file
                    
                    # Мокаем docker-compose config
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = "services:\n  coreness:\n    container_name: app-coreness"
                    mock_subprocess.return_value = mock_result
                    
                    # yaml.safe_load вызывается дважды:
                    # 1. Для парсинга вывода docker-compose config (строка)
                    # 2. Для чтения файла окружения (docker-compose.coreness.yml) - файловый объект
                    call_count = [0]
                    def yaml_side_effect(content):
                        call_count[0] += 1
                        if call_count[0] == 1:  # Первый вызов - вывод docker-compose config
                            return {
                                'services': {
                                    'coreness': {
                                        'container_name': 'app-coreness'
                                    }
                                }
                            }
                        else:  # Второй вызов - файл окружения
                            return {
                                'services': {
                                    'coreness': {}
                                }
                            }
                    mock_yaml.side_effect = yaml_side_effect
                    
                    container_name = compose_manager.get_container_name("coreness")
                    
                    assert container_name == "app-coreness"
    
    @patch("modules.update.compose_manager.yaml.safe_load")
    @patch("builtins.open", create=True)
    def test_get_postgres_service_name_test_environment(self, mock_open, mock_yaml, compose_manager, project_root, tmp_path):
        """Проверяет получение имени сервиса PostgreSQL для test окружения"""
        # Создаем глобальные файлы для тестирования
        global_base = tmp_path / ".docker-compose" / "docker-compose.yml"
        global_test = tmp_path / ".docker-compose" / "docker-compose.test.yml"
        global_base.parent.mkdir(parents=True)
        
        # Базовый файл с сервисом postgres
        global_base.write_text("""
services:
  postgres:
    image: postgres:18
""")
        
        # Файл окружения с сервисом postgres-test, который extends базовый postgres
        test_file_content = """
services:
  postgres-test:
    extends:
      file: docker-compose.yml
      service: postgres
"""
        global_test.write_text(test_file_content)
        
        with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
            with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_test):
                with patch.object(compose_manager.compose_config_manager, "get_base_config_path", return_value=global_base):
                    # Мокаем чтение файла окружения
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value.read.return_value = test_file_content
                    mock_file.__exit__.return_value = None
                    mock_open.return_value = mock_file
                    
                    # Мокаем yaml.safe_load для чтения файла окружения
                    mock_yaml.return_value = {
                        'services': {
                            'postgres-test': {
                                'extends': {
                                    'file': 'docker-compose.yml',
                                    'service': 'postgres'
                                }
                            }
                        }
                    }
                    
                    service_name = compose_manager.get_postgres_service_name("test")
                    
                    assert service_name == "postgres-test"
    
    @patch("modules.update.compose_manager.subprocess.run")
    @patch("modules.update.compose_manager.yaml.safe_load")
    @patch("builtins.open", create=True)
    def test_get_postgres_service_name_prod_environment(self, mock_open, mock_yaml, mock_subprocess, compose_manager, project_root, tmp_path):
        """Проверяет получение имени сервиса PostgreSQL для prod окружения"""
        # Создаем глобальные файлы для тестирования
        global_base = tmp_path / ".docker-compose" / "docker-compose.yml"
        global_prod = tmp_path / ".docker-compose" / "docker-compose.prod.yml"
        global_base.parent.mkdir(parents=True)
        
        # Базовый файл с сервисом postgres
        global_base.write_text("""
services:
  postgres:
    image: postgres:18
""")
        
        # Файл prod может не иметь специфичного сервиса PostgreSQL
        global_prod.write_text("""
services:
  app:
    image: app:latest
""")
        
        with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
            with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_prod):
                with patch.object(compose_manager.compose_config_manager, "get_base_config_path", return_value=global_base):
                    # Мокаем чтение файла окружения (нет postgres сервиса)
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value.read.return_value = global_prod.read_text()
                    mock_file.__exit__.return_value = None
                    mock_open.return_value = mock_file
                    
                    # Мокаем yaml.safe_load для чтения файла окружения
                    mock_yaml.return_value = {
                        'services': {
                            'app': {}
                        }
                    }
                    
                    # Мокаем docker compose config для fallback
                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = "services:\n  postgres:\n    image: postgres:18"
                    mock_subprocess.return_value = mock_result
                    
                    # Мокаем yaml.safe_load для объединенного конфига
                    def yaml_side_effect(content):
                        if isinstance(content, str) and 'services:' in content:
                            # Это вывод docker compose config
                            return {
                                'services': {
                                    'postgres': {
                                        'image': 'postgres:18'
                                    }
                                }
                            }
                        else:
                            # Это чтение файла окружения
                            return {
                                'services': {
                                    'app': {}
                                }
                            }
                    
                    mock_yaml.side_effect = yaml_side_effect
                    
                    service_name = compose_manager.get_postgres_service_name("prod")
                    
                    assert service_name == "postgres"
    
    @patch("modules.update.compose_manager.yaml.safe_load")
    @patch("builtins.open", create=True)
    def test_get_postgres_service_name_direct_postgres_service(self, mock_open, mock_yaml, compose_manager, project_root, tmp_path):
        """Проверяет получение имени сервиса PostgreSQL, если в файле окружения есть сервис с именем postgres-*"""
        # Создаем глобальные файлы для тестирования
        global_base = tmp_path / ".docker-compose" / "docker-compose.yml"
        global_test = tmp_path / ".docker-compose" / "docker-compose.test.yml"
        global_base.parent.mkdir(parents=True)
        
        global_base.write_text("version: '3'")
        
        # Файл окружения с сервисом postgres-test без extends
        test_file_content = """
services:
  postgres-test:
    image: postgres:18
"""
        global_test.write_text(test_file_content)
        
        with patch.object(compose_manager.compose_config_manager, "config_exists", return_value=True):
            with patch.object(compose_manager.compose_config_manager, "get_config_path", return_value=global_test):
                with patch.object(compose_manager.compose_config_manager, "get_base_config_path", return_value=global_base):
                    # Мокаем чтение файла окружения
                    mock_file = MagicMock()
                    mock_file.__enter__.return_value.read.return_value = test_file_content
                    mock_file.__exit__.return_value = None
                    mock_open.return_value = mock_file
                    
                    # Мокаем yaml.safe_load для чтения файла окружения
                    mock_yaml.return_value = {
                        'services': {
                            'postgres-test': {
                                'image': 'postgres:18'
                            }
                        }
                    }
                    
                    service_name = compose_manager.get_postgres_service_name("test")
                    
                    assert service_name == "postgres-test"
    
    @patch("modules.update.compose_manager.subprocess.run")
    @patch("modules.update.compose_manager.yaml.safe_load")
    @patch("pathlib.Path.exists")
    def test_get_container_name_no_container_name(self, mock_exists, mock_yaml, mock_subprocess, compose_manager, project_root):
        """Проверяет возврат None если container_name не указан"""
        # Мокаем существование файлов
        def exists_side_effect(path):
            if 'docker-compose.test.yml' in str(path):
                return True
            if 'docker-compose.yml' in str(path):
                return True
            return False
        mock_exists.side_effect = exists_side_effect
        
        # Мокаем чтение файла окружения
        with patch("builtins.open", create=True) as mock_open:
            mock_file_content = "services:\n  app-test:\n    image: app-test:latest\n"
            mock_file = MagicMock()
            mock_file.__enter__.return_value.read.return_value = mock_file_content
            mock_file.__exit__.return_value = None
            mock_open.return_value = mock_file
            
            # Мокаем docker-compose config
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "services:\n  app-test:\n    image: app-test:latest"
            mock_subprocess.return_value = mock_result
            
            mock_yaml.return_value = {
                'services': {
                    'app-test': {
                        'image': 'app-test:latest'
                        # container_name отсутствует
                    }
                }
            }
            
            container_name = compose_manager.get_container_name("test")
            
            assert container_name is None
    
    @patch("pathlib.Path.exists")
    def test_get_container_name_file_not_found(self, mock_exists, compose_manager):
        """Проверяет возврат None если файл окружения не найден"""
        mock_exists.return_value = False
        
        container_name = compose_manager.get_container_name("unknown")
        
        assert container_name is None


@pytest.mark.unit
class TestImageManager:
    """Тесты для ImageManager"""
    
    @pytest.fixture
    def image_manager(self, mock_logger, sample_config, project_root):
        """Создает экземпляр ImageManager"""
        compose_manager = ComposeManager(project_root, mock_logger, sample_config)
        compose_manager.set_compose_command(['docker', 'compose'])
        return ImageManager(project_root, mock_logger, sample_config, compose_manager)
    
    @patch("modules.update.image_manager.subprocess.run")
    def test_list_images_with_info(self, mock_subprocess, image_manager, project_root):
        """Проверяет получение списка образов с информацией"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "my-app:1.0.0|100MB|2024-01-01\nmy-app:0.9.0|90MB|2023-12-01"
        mock_subprocess.return_value = mock_result
        
        with patch.object(image_manager.compose_manager, "get_compose_file", return_value=project_root / "docker" / "docker-compose.prod.yml"):
            with patch.object(image_manager.compose_manager, "get_image_name", return_value="my-app"):
                images = image_manager.list_images_with_info("prod")
                
                assert len(images) == 2
                assert images[0]['version'] == '1.0.0'
                assert images[0]['size'] == '100MB'
                assert 'latest' not in [img['version'] for img in images]
    
    @patch("modules.update.image_manager.subprocess.run")
    def test_cleanup_old_images_dangling(self, mock_subprocess, image_manager):
        """Проверяет очистку dangling images"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Total reclaimed space: 100MB"
        mock_subprocess.return_value = mock_result
        
        result = image_manager.cleanup_old_images("prod", keep_versions=5)
        
        assert result["dangling_removed"] == 1
        assert result["space_freed"] > 0
    
    def test_list_available_versions_only_prod(self, image_manager):
        """Проверяет что список версий доступен только для prod"""
        result = image_manager.list_available_versions("test")
        
        assert result == []


@pytest.mark.unit
class TestContainerManager:
    """Тесты для ContainerManager"""
    
    @pytest.fixture
    def container_manager(self, mock_logger, sample_config, project_root):
        """Создает экземпляр ContainerManager"""
        from modules.update.compose_config_manager import ComposeConfigManager
        compose_manager = ComposeManager(project_root, mock_logger, sample_config)
        compose_manager.set_compose_command(['docker', 'compose'])
        compose_config_manager = ComposeConfigManager(sample_config, mock_logger)
        return ContainerManager(project_root, mock_logger, sample_config, compose_manager, compose_config_manager)
    
    @patch("modules.update.container_manager.subprocess.run")
    def test_restart_with_compose(self, mock_subprocess, container_manager, project_root, tmp_path):
        """Проверяет перезапуск контейнеров"""
        # Мокаем оба вызова subprocess.run (down и up)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Создаем реальные файлы для тестирования
        global_config_dir = tmp_path / ".docker-compose"
        global_config_dir.mkdir()
        base_config = global_config_dir / "docker-compose.yml"
        env_config = global_config_dir / "docker-compose.test.yml"
        base_config.write_text("version: '3'")
        env_config.write_text("version: '3'")
        
        # Мокаем _get_compose_files и _get_services_for_environment
        with patch.object(container_manager, "_get_compose_files", return_value=(base_config, env_config, None)):
            with patch.object(container_manager, "_get_services_for_environment", return_value=["postgres-test", "app-test"]):
                result = container_manager.restart_with_compose("test", ['docker', 'compose'])
                
                assert result is True
                assert mock_subprocess.call_count >= 2  # stop и up
    
    @patch("modules.update.container_manager.subprocess.run")
    def test_stop_with_compose(self, mock_subprocess, container_manager, project_root, tmp_path):
        """Проверяет остановку контейнеров"""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        
        # Создаем реальные файлы для тестирования
        global_config_dir = tmp_path / ".docker-compose"
        global_config_dir.mkdir()
        base_config = global_config_dir / "docker-compose.yml"
        env_config = global_config_dir / "docker-compose.test.yml"
        base_config.write_text("version: '3'")
        env_config.write_text("version: '3'")
        
        # Мокаем _get_compose_files напрямую - это проще и надежнее
        with patch.object(container_manager, "_get_compose_files", return_value=(base_config, env_config, None)):
            result = container_manager.stop_with_compose("test", ['docker', 'compose'])
            
            assert result is True
            mock_subprocess.assert_called_once()
    
    @patch("modules.update.container_manager.subprocess.run")
    def test_get_services_for_environment_test(self, mock_subprocess, container_manager, project_root, tmp_path):
        """Проверяет что для test окружения возвращаются только сервисы из файла окружения"""
        # Создаем compose файлы
        global_config_dir = tmp_path / ".docker-compose"
        global_config_dir.mkdir()
        base_config = global_config_dir / "docker-compose.yml"
        env_config = global_config_dir / "docker-compose.test.yml"
        
        # Базовый файл содержит postgres и app
        base_config.write_text("""
services:
  postgres:
    image: postgres:18
  app:
    image: app:latest
""")
        
        # Файл окружения содержит postgres-test и app-test
        env_config.write_text("""
services:
  postgres-test:
    extends:
      file: docker-compose.yml
      service: postgres
  app-test:
    extends:
      file: docker-compose.yml
      service: app
""")
        
        # Мокаем subprocess.run для docker compose config --services
        # Docker Compose вернет все сервисы (включая базовые), но мы отфильтруем только из env_config
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Docker Compose может вернуть все сервисы, включая базовые
        mock_result.stdout = "postgres\napp\npostgres-test\napp-test\n"
        mock_subprocess.return_value = mock_result
        
        # Мокаем _get_compose_files
        with patch.object(container_manager, "_get_compose_files", return_value=(base_config, env_config, None)):
            services = container_manager._get_services_for_environment("test", ['docker', 'compose'], [])
            
            # Проверяем, что вернулись только сервисы из файла окружения
            assert "postgres-test" in services
            assert "app-test" in services
            # Проверяем, что НЕ вернулись сервисы из базового файла (отфильтрованы)
            assert "postgres" not in services
            assert "app" not in services
            assert len(services) == 2
            
            # Проверяем, что docker compose config был вызван со всеми файлами
            assert mock_subprocess.called
            call_args = mock_subprocess.call_args[0][0]
            # Должны быть оба файла: базовый и окружения
            assert str(base_config) in call_args or base_config.name in str(call_args)
            assert str(env_config) in call_args or env_config.name in str(call_args)
    
    @patch("modules.update.container_manager.subprocess.run")
    def test_get_services_for_environment_prod(self, mock_subprocess, container_manager, project_root, tmp_path):
        """Проверяет что для prod окружения возвращаются только сервисы из файла окружения"""
        # Создаем compose файлы
        global_config_dir = tmp_path / ".docker-compose"
        global_config_dir.mkdir()
        base_config = global_config_dir / "docker-compose.yml"
        env_config = global_config_dir / "docker-compose.prod.yml"
        
        # Базовый файл содержит postgres и app
        base_config.write_text("""
services:
  postgres:
    image: postgres:18
  app:
    image: app:latest
""")
        
        # Файл окружения содержит postgres и app (для prod они без постфикса)
        env_config.write_text("""
services:
  postgres:
    extends:
      file: docker-compose.yml
      service: postgres
  app:
    extends:
      file: docker-compose.yml
      service: app
""")
        
        # Мокаем subprocess.run для docker compose config --services
        # Docker Compose вернет все сервисы, но мы отфильтруем только из env_config
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "postgres\napp\n"
        mock_subprocess.return_value = mock_result
        
        # Мокаем _get_compose_files
        with patch.object(container_manager, "_get_compose_files", return_value=(base_config, env_config, None)):
            services = container_manager._get_services_for_environment("prod", ['docker', 'compose'], [])
            
            # Проверяем, что вернулись только сервисы из файла окружения
            assert "postgres" in services
            assert "app" in services
            assert len(services) == 2
            
            # Проверяем, что docker compose config был вызван со всеми файлами
            assert mock_subprocess.called
            call_args = mock_subprocess.call_args[0][0]
            # Должны быть оба файла: базовый и окружения
            assert str(base_config) in call_args or base_config.name in str(call_args)
            assert str(env_config) in call_args or env_config.name in str(call_args)
    
    @patch("modules.update.container_manager.subprocess.run")
    def test_get_services_for_environment_filters_by_env_file(self, mock_subprocess, container_manager, project_root, tmp_path):
        """Проверяет что используются все файлы для разрешения extends, но результат фильтруется по файлу окружения"""
        # Создаем compose файлы
        global_config_dir = tmp_path / ".docker-compose"
        global_config_dir.mkdir()
        base_config = global_config_dir / "docker-compose.yml"
        env_config = global_config_dir / "docker-compose.test.yml"
        
        base_config.write_text("services:\n  postgres:\n    image: postgres:18\n  app:\n    image: app:latest\n")
        env_config.write_text("services:\n  postgres-test:\n    extends:\n      file: docker-compose.yml\n      service: postgres\n  app-test:\n    extends:\n      file: docker-compose.yml\n      service: app\n")
        
        # Мокаем subprocess.run - docker compose config вернет все сервисы (включая базовые)
        mock_result = MagicMock()
        mock_result.returncode = 0
        # Docker Compose вернет все сервисы, но мы отфильтруем только из env_config
        mock_result.stdout = "postgres\napp\npostgres-test\napp-test\n"
        mock_subprocess.return_value = mock_result
        
        # Мокаем _get_compose_files
        with patch.object(container_manager, "_get_compose_files", return_value=(base_config, env_config, None)):
            services = container_manager._get_services_for_environment("test", ['docker', 'compose'], [])
            
            # Проверяем, что subprocess.run был вызван со всеми файлами (для разрешения extends)
            assert mock_subprocess.called
            call_args = mock_subprocess.call_args[0][0]  # Первый аргумент - команда
            
            # Проверяем, что в команде есть оба файла: базовый и окружения
            assert '-f' in call_args
            f_indices = [i for i, arg in enumerate(call_args) if arg == '-f']
            # Должно быть минимум 2 файла: базовый и окружения
            assert len(f_indices) >= 2
            # Проверяем, что в команде есть оба файла
            assert str(base_config) in call_args or base_config.name in str(call_args)
            assert str(env_config) in call_args or env_config.name in str(call_args)
            
            # Проверяем, что результат отфильтрован: только сервисы из env_config
            assert "postgres-test" in services
            assert "app-test" in services
            assert "postgres" not in services
            assert "app" not in services
            assert len(services) == 2


@pytest.mark.unit
class TestDockerManagerIntegration:
    """Интеграционные тесты для DockerManager (фасада)"""
    
    @pytest.fixture
    def docker_manager(self, mock_logger, sample_config, project_root):
        """Создает экземпляр DockerManager"""
        from modules.update.docker_manager import DockerManager
        return DockerManager(project_root, mock_logger, sample_config)
    
    def test_docker_manager_initialization(self, docker_manager):
        """Проверяет корректную инициализацию DockerManager"""
        assert docker_manager.checker is not None
        assert docker_manager.compose_manager is not None
        assert docker_manager.image_manager is not None
        assert docker_manager.container_manager is not None
    
    def test_docker_manager_delegates_to_checker(self, docker_manager):
        """Проверяет что DockerManager делегирует проверку Docker"""
        with patch.object(docker_manager.checker, "check_docker", return_value=True) as mock_check:
            result = docker_manager.check_docker()
            
            assert result is True
            mock_check.assert_called_once()
    
    def test_docker_manager_delegates_to_image_manager(self, docker_manager):
        """Проверяет что DockerManager делегирует работу с образами"""
        with patch.object(docker_manager.image_manager, "list_available_versions", return_value=["1.0.0", "0.9.0"]) as mock_list:
            result = docker_manager.list_available_versions("prod")
            
            assert result == ["1.0.0", "0.9.0"]
            mock_list.assert_called_once_with("prod")

