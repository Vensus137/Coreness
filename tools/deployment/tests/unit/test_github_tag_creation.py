"""
Unit-тесты для создания тегов версий через GitHub API
"""
from unittest.mock import MagicMock, patch

import pytest
import requests
from modules.deploy.github_api import MergeRequestManager


@pytest.mark.unit
class TestGitHubTagCreation:
    """Тесты для создания тегов версий"""
    
    @pytest.fixture
    def mr_manager(self, mock_logger, sample_config):
        """Создает экземпляр MergeRequestManager"""
        return MergeRequestManager(sample_config, mock_logger)
    
    @pytest.fixture
    def repo_config(self):
        """Конфигурация репозитория для тестов"""
        return {
            "url": "https://github.com/testuser/testrepo",
            "token": "test_token"
        }
    
    @patch('modules.deploy.github_api.requests.get')
    @patch('modules.deploy.github_api.requests.post')
    def test_create_tag_success(self, mock_post, mock_get, mr_manager, repo_config):
        """Проверяет успешное создание тега"""
        # Мокаем проверку существования тега (404 - тег не существует)
        mock_get.side_effect = [
            MagicMock(status_code=404),  # Тег не существует
            MagicMock(status_code=200, json=lambda: {"commit": {"sha": "abc123"}})  # Информация о ветке
        ]
        
        # Мокаем создание тега (201 - успешно создан)
        mock_post.return_value = MagicMock(status_code=201)
        
        result = mr_manager.create_tag(repo_config, "1.0.0", "deploy/1.0.0")
        
        assert result is True
        assert mock_post.called
        call_args = mock_post.call_args
        assert call_args[1]['json']['ref'] == "refs/tags/v1.0.0"
        assert call_args[1]['json']['sha'] == "abc123"
    
    @patch('modules.deploy.github_api.requests.get')
    def test_create_tag_already_exists(self, mock_get, mr_manager, repo_config):
        """Проверяет поведение когда тег уже существует"""
        # Мокаем проверку существования тега (200 - тег существует)
        mock_get.return_value = MagicMock(status_code=200)
        
        result = mr_manager.create_tag(repo_config, "1.0.0", "deploy/1.0.0")
        
        assert result is True
        # POST не должен вызываться
        assert not hasattr(mock_get, 'post') or not mock_get.post.called
    
    @patch('modules.deploy.github_api.requests.get')
    @patch('modules.deploy.github_api.requests.post')
    def test_create_tag_with_v_prefix(self, mock_post, mock_get, mr_manager, repo_config):
        """Проверяет создание тега с префиксом v"""
        mock_get.side_effect = [
            MagicMock(status_code=404),
            MagicMock(status_code=200, json=lambda: {"commit": {"sha": "abc123"}})
        ]
        mock_post.return_value = MagicMock(status_code=201)
        
        result = mr_manager.create_tag(repo_config, "v1.0.0", "deploy/1.0.0")
        
        assert result is True
        call_args = mock_post.call_args
        assert call_args[1]['json']['ref'] == "refs/tags/v1.0.0"
    
    @patch('modules.deploy.github_api.requests.get')
    def test_create_tag_branch_not_found(self, mock_get, mr_manager, repo_config):
        """Проверяет поведение когда ветка не найдена"""
        mock_get.side_effect = [
            MagicMock(status_code=404),  # Тег не существует
            MagicMock(status_code=404)   # Ветка не найдена
        ]
        
        result = mr_manager.create_tag(repo_config, "1.0.0", "deploy/1.0.0")
        
        assert result is False
    
    @patch('modules.deploy.github_api.requests.get')
    @patch('modules.deploy.github_api.requests.post')
    def test_create_tag_api_error(self, mock_post, mock_get, mr_manager, repo_config):
        """Проверяет обработку ошибки API при создании тега"""
        mock_get.side_effect = [
            MagicMock(status_code=404),
            MagicMock(status_code=200, json=lambda: {"commit": {"sha": "abc123"}})
        ]
        # Мокаем ошибку при создании тега
        mock_post.return_value = MagicMock(status_code=500, text="Internal Server Error")
        
        result = mr_manager.create_tag(repo_config, "1.0.0", "deploy/1.0.0")
        
        assert result is False
    
    @patch('modules.deploy.github_api.requests.get')
    @patch('modules.deploy.github_api.requests.post')
    def test_create_tag_network_error(self, mock_post, mock_get, mr_manager, repo_config):
        """Проверяет обработку сетевой ошибки"""
        mock_get.side_effect = requests.RequestException("Network error")
        
        result = mr_manager.create_tag(repo_config, "1.0.0", "deploy/1.0.0")
        
        assert result is False
    
    def test_create_tag_invalid_repo_url(self, mr_manager):
        """Проверяет поведение с невалидным URL репозитория"""
        repo_config = {
            "url": "invalid_url",
            "token": "test_token"
        }
        
        result = mr_manager.create_tag(repo_config, "1.0.0", "deploy/1.0.0")
        
        assert result is False

