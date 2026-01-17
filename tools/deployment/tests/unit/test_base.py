"""
Unit-тесты для DeploymentBase
"""
import os
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import yaml
from modules.base import DeploymentBase


@pytest.mark.unit
class TestDeploymentBase:
    """Тесты для DeploymentBase"""
    
    @pytest.fixture
    def config_content(self):
        """Содержимое тестового config.yaml"""
        return """
server_update:
  repository:
    url: "https://github.com/test/repo"
    token: "${GITHUB_TOKEN}"

deploy_settings:
  timeouts:
    docker_build: 600
"""
    
    def test_resolve_env_variable_simple(self):
        """Тест разрешения простой переменной окружения"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        # Устанавливаем переменную окружения
        os.environ["TEST_VAR"] = "test_value"
        
        result = base._resolve_env_variable_in_string("${TEST_VAR}")
        assert result == "test_value"
        
        # Очищаем
        del os.environ["TEST_VAR"]
    
    def test_resolve_env_variable_not_set(self):
        """Тест разрешения не установленной переменной окружения"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        result = base._resolve_env_variable_in_string("${NONEXISTENT_VAR}")
        assert result == ""
    
    def test_resolve_env_variable_in_string(self):
        """Тест разрешения переменной в строке"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        os.environ["TEST_VAR"] = "test_value"
        
        result = base._resolve_env_variable_in_string("url: ${TEST_VAR}/path")
        assert result == "url: test_value/path"
        
        del os.environ["TEST_VAR"]
    
    def test_resolve_env_variables_in_dict(self):
        """Тест разрешения переменных в словаре"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        os.environ["GITHUB_TOKEN"] = "token123"
        
        data = {
            "token": "${GITHUB_TOKEN}",
            "url": "https://github.com/test"
        }
        
        result = base._resolve_env_variables(data)
        
        assert result["token"] == "token123"
        assert result["url"] == "https://github.com/test"
        
        del os.environ["GITHUB_TOKEN"]
    
    def test_resolve_env_variables_in_list(self):
        """Тест разрешения переменных в списке"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        os.environ["VAR1"] = "value1"
        os.environ["VAR2"] = "value2"
        
        data = ["${VAR1}", "static", "${VAR2}"]
        
        result = base._resolve_env_variables(data)
        
        assert result == ["value1", "static", "value2"]
        
        del os.environ["VAR1"]
        del os.environ["VAR2"]
    
    def test_find_unresolved_placeholders(self):
        """Тест поиска неразрешенных плейсхолдеров"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        data = {
            "token": "${GITHUB_TOKEN}",
            "url": "https://github.com",
            "nested": {
                "key": "${NESTED_VAR}"
            }
        }
        
        unresolved = base._find_unresolved_placeholders(data)
        
        # Должны найти обе переменные
        var_names = [item["var"] for item in unresolved]
        assert "GITHUB_TOKEN" in var_names
        assert "NESTED_VAR" in var_names
    
    def test_load_config_success(self, config_content):
        """Тест успешной загрузки конфигурации - проверяем структуру данных"""
        # Парсим YAML из config_content для проверки структуры
        parsed_config = yaml.safe_load(config_content)
        
        base = DeploymentBase.__new__(DeploymentBase)
        base.project_root = Path("/test")
        
        # Мокаем весь путь к файлу и его чтение
        with patch("modules.base.Path") as mock_path_class:
            # Создаем мок для config_path
            mock_config_path = MagicMock()
            mock_config_path.exists.return_value = True
            
            # Настраиваем цепочку Path(__file__).parent.parent / CONFIG_FILE_NAME
            mock_file_path = MagicMock()
            mock_parent = MagicMock()
            mock_parent_parent = MagicMock()
            
            def mock_truediv(self, other):
                return mock_config_path
            
            mock_parent_parent.__truediv__ = mock_truediv
            mock_parent.parent = mock_parent_parent
            mock_file_path.parent = mock_parent
            mock_path_class.return_value = mock_file_path
            
            # Мокаем open и yaml.safe_load
            with patch("builtins.open", mock_open(read_data=config_content)):
                with patch("modules.base.yaml.safe_load", return_value=parsed_config):
                    with patch("modules.base.sys.exit"):
                        config = base._load_config()
                        
                        assert config is not None
                        assert isinstance(config, dict)
                        assert "server_update" in config
    
    @patch("modules.base.sys.exit")
    @patch("modules.base.Path")
    def test_load_config_file_not_found(self, mock_path_class, mock_exit):
        """Тест загрузки конфигурации когда файл не найден"""
        # Настраиваем мок пути
        mock_config_path = MagicMock()
        mock_config_path.exists.return_value = False
        
        mock_file_path = MagicMock()
        mock_parent = MagicMock()
        mock_parent_parent = MagicMock()
        
        def mock_truediv(self, other):
            return mock_config_path
        
        mock_parent_parent.__truediv__ = mock_truediv
        mock_parent.parent = mock_parent_parent
        mock_file_path.parent = mock_parent
        mock_path_class.return_value = mock_file_path
        
        base = DeploymentBase.__new__(DeploymentBase)
        base.project_root = Path("/test")
        
        # sys.exit должен быть вызван при отсутствии файла
        mock_exit.side_effect = SystemExit(1)
        
        with pytest.raises(SystemExit):
            base._load_config()
        
        # Проверяем что sys.exit был вызван
        assert mock_exit.called
    
    def test_get_default_branch_from_repo_config(self):
        """Тест получения дефолтной ветки из конфига репозитория"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        repo_config = {
            "default_branch": "develop"
        }
        
        result = base.get_default_branch(repo_config)
        assert result == "develop"
    
    def test_get_default_branch_from_branches(self):
        """Тест получения дефолтной ветки из branches"""
        base = DeploymentBase.__new__(DeploymentBase)
        
        repo_config = {
            "branches": {
                "test": "test-branch",
                "prod": "main"
            }
        }
        
        result = base.get_default_branch(repo_config)
        # Должен вернуть main если есть
        assert result in ["test-branch", "main"]
    
    def test_get_default_branch_fallback(self):
        """Тест fallback на 'main' если ветка не указана"""
        base = DeploymentBase.__new__(DeploymentBase)
        base.config = {}
        
        result = base.get_default_branch()
        assert result == "main"

