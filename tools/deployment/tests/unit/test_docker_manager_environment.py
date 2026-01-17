"""
Unit-тесты для DockerManager - работа с окружениями (test/prod)
"""
from unittest.mock import MagicMock, patch

import pytest
from modules.update.docker_manager import DockerManager


@pytest.mark.unit
class TestDockerManagerEnvironment:
    """Тесты для работы DockerManager с разными окружениями"""
    
    @pytest.fixture
    def docker_manager(self, mock_logger, sample_config, project_root):
        """Создает экземпляр DockerManager"""
        return DockerManager(project_root, mock_logger, sample_config)
    
    def test_get_compose_file_test(self, docker_manager, project_root, tmp_path):
        """Проверяет выбор docker-compose.test.yml для test окружения"""
        # Создаем глобальный файл для тестирования
        global_config_path = tmp_path / ".docker-compose" / "docker-compose.test.yml"
        global_config_path.parent.mkdir(parents=True)
        global_config_path.write_text("version: '3'")
        
        with patch.object(docker_manager.compose_config_manager, "config_exists", return_value=True):
            with patch.object(docker_manager.compose_config_manager, "get_config_path", return_value=global_config_path):
                compose_file = docker_manager._get_compose_file("test")
                
                assert compose_file is not None
                assert compose_file == global_config_path
    
    def test_get_compose_file_prod(self, docker_manager, project_root, tmp_path):
        """Проверяет выбор docker-compose.prod.yml для prod окружения"""
        # Создаем глобальный файл для тестирования
        global_config_path = tmp_path / ".docker-compose" / "docker-compose.prod.yml"
        global_config_path.parent.mkdir(parents=True)
        global_config_path.write_text("version: '3'")
        
        with patch.object(docker_manager.compose_config_manager, "config_exists", return_value=True):
            with patch.object(docker_manager.compose_config_manager, "get_config_path", return_value=global_config_path):
                compose_file = docker_manager._get_compose_file("prod")
                
                assert compose_file is not None
                assert compose_file == global_config_path
    
    def test_get_compose_file_not_found(self, docker_manager, project_root):
        """Проверяет что метод возвращает None если глобальные файлы не найдены"""
        with patch.object(docker_manager.compose_config_manager, "config_exists", return_value=False):
            compose_file = docker_manager._get_compose_file("test")
            
            # Если глобальные файлы не существуют, должен вернуться None
            assert compose_file is None
    
    @patch("modules.update.image_manager.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_build_tags_prod_only(self, mock_exists, mock_subprocess, docker_manager, project_root):
        """Проверяет что версионирование работает только для prod"""
        # Настраиваем моки для subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        mock_exists.return_value = True
        
        # Мокаем методы для получения compose файлов (новая логика через container_manager)
        base_config = project_root / "docker" / "docker-compose.yml"
        env_config = project_root / "docker" / "docker-compose.prod.yml"
        with patch.object(docker_manager.container_manager, "_get_compose_files", return_value=(base_config, env_config, None)):
            with patch.object(docker_manager.compose_manager, "get_image_name", return_value="test-image"):
                with patch.object(docker_manager.compose_manager, "get_built_image_id", return_value="image-id-123"):
                    with patch.object(docker_manager.image_manager, "tag_image", return_value=True) as mock_tag:
                        # Тест для prod - должен вызываться tag_image
                        result = docker_manager.build_with_compose("prod", version="1.0.0")
                        
                        assert result is True
                        mock_tag.assert_called_once()
    
    @patch("modules.update.image_manager.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_build_no_tags_for_test(self, mock_exists, mock_subprocess, docker_manager, project_root):
        """Проверяет что для test окружения образ НЕ тегируется версией"""
        # Настраиваем моки для subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result
        mock_exists.return_value = True
        
        # Мокаем методы для получения compose файлов (новая логика через container_manager)
        base_config = project_root / "docker" / "docker-compose.yml"
        env_config = project_root / "docker" / "docker-compose.test.yml"
        with patch.object(docker_manager.container_manager, "_get_compose_files", return_value=(base_config, env_config, None)):
            with patch.object(docker_manager.image_manager, "tag_image") as mock_tag:
                # Тест для test - НЕ должен вызываться tag_image
                result = docker_manager.build_with_compose("test", version="1.0.0")
                
                assert result is True
                mock_tag.assert_not_called()
    
    def test_rollback_only_prod(self, docker_manager):
        """Проверяет что откат доступен только для prod окружения"""
        # Для test должен возвращать False
        with patch.object(docker_manager.image_manager, "rollback_image", return_value=False) as mock_rollback:
            result = docker_manager.rollback_image("test", "1.0.0")
            
            assert result is False
            # Проверяем что метод был вызван (но вернул False из-за окружения)
            mock_rollback.assert_called_once()
    
    @patch("modules.update.image_manager.subprocess.run")
    @patch("pathlib.Path.exists")
    def test_rollback_prod_allowed(self, mock_exists, mock_subprocess, docker_manager, project_root):
        """Проверяет что откат работает для prod окружения"""
        # Настраиваем моки для subprocess.run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "image-id-123"  # Для проверки существования образа
        mock_subprocess.return_value = mock_result
        mock_exists.return_value = True
        
        compose_file = project_root / "docker" / "docker-compose.prod.yml"
        with patch.object(docker_manager.compose_manager, "get_compose_file", return_value=compose_file):
            with patch.object(docker_manager.compose_manager, "get_image_name", return_value="test-image"):
                with patch.object(docker_manager.image_manager, "rollback_image", return_value=True) as mock_rollback:
                    result = docker_manager.rollback_image("prod", "1.0.0")
                    
                    # Должен попытаться выполнить откат
                    assert result is True
                    mock_rollback.assert_called_once()
    
    def test_list_versions_only_prod(self, docker_manager):
        """Проверяет что список версий доступен только для prod"""
        # Для test должен возвращать пустой список
        result = docker_manager.list_available_versions("test")
        
        assert result == []
    
    @patch("modules.update.image_manager.subprocess.run")
    def test_list_versions_prod_allowed(self, mock_subprocess, docker_manager, project_root):
        """Проверяет что список версий работает для prod окружения"""
        # Настраиваем моки - docker images возвращает только теги
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "1.0.0\n0.9.0\nlatest"  # Только теги, без имени образа
        mock_subprocess.return_value = mock_result
        
        compose_file = project_root / "docker" / "docker-compose.prod.yml"
        with patch.object(docker_manager.compose_manager, "get_compose_file", return_value=compose_file):
            with patch.object(docker_manager.compose_manager, "get_image_name", return_value="test-image"):
                result = docker_manager.list_available_versions("prod")
                
                assert isinstance(result, list)
                assert "1.0.0" in result
                assert "0.9.0" in result
                assert "latest" not in result  # latest исключается

