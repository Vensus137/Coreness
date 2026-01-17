"""
Integration-тесты для GitHub API (с моками)
"""
from unittest.mock import MagicMock, patch

import pytest
from modules.deploy.github_api import GitHubAPIClient, MergeRequestManager


@pytest.mark.integration
class TestGitHubAPIClient:
    """Тесты для GitHubAPIClient"""
    
    @pytest.fixture
    def api_client(self, sample_config, mock_logger):
        """Создает экземпляр GitHubAPIClient"""
        return GitHubAPIClient(sample_config, mock_logger)
    
    def test_parse_repo_url_github(self, api_client):
        """Тест парсинга URL GitHub репозитория"""
        url = "https://github.com/owner/repo"
        result = api_client.parse_repo_url(url)
        
        assert result == ("owner", "repo")
    
    def test_parse_repo_url_non_github(self, api_client):
        """Тест парсинга не-GitHub URL"""
        url = "https://gitlab.com/owner/repo"
        result = api_client.parse_repo_url(url)
        
        assert result is None
    
    def test_build_api_url(self, api_client):
        """Тест построения API URL"""
        url = api_client.build_api_url("pulls", "owner", "repo")
        
        assert "api.github.com" in url
        assert "owner" in url
        assert "repo" in url
        assert "pulls" in url
    
    def test_get_headers(self, api_client):
        """Тест получения заголовков для API"""
        headers = api_client.get_headers("token123")
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "token token123"
        assert "Accept" in headers


@pytest.mark.integration
class TestMergeRequestManager:
    """Тесты для MergeRequestManager"""
    
    @pytest.fixture
    def mr_manager(self, sample_config, mock_logger):
        """Создает экземпляр MergeRequestManager"""
        return MergeRequestManager(sample_config, mock_logger)
    
    @patch("modules.deploy.github_api.requests.get")
    def test_check_existing_mr_found(self, mock_get, mr_manager):
        """Тест проверки существующего MR когда он найден"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "head": {"ref": "deploy/1.0.0"},
                "state": "open",
                "html_url": "https://github.com/test/repo/pull/1",
                "title": "Test MR",
                "merged": False
            },
            {
                "head": {"ref": "other-branch"},
                "state": "closed",
                "html_url": "https://github.com/test/repo/pull/2",
                "title": "Other MR",
                "merged": False
            }
        ]
        mock_get.return_value = mock_response
        
        repo_config = {
            "url": "https://github.com/owner/repo",
            "token": "token"
        }
        
        result = mr_manager.check_existing(repo_config, "deploy/1.0.0")
        
        # Проверяем что запрос был сделан
        assert mock_get.called
        assert result["exists"] is True
        assert result["status"] == "open"
        assert result["url"] == "https://github.com/test/repo/pull/1"
    
    @patch("modules.deploy.github_api.requests.get")
    def test_check_existing_mr_not_found(self, mock_get, mr_manager):
        """Тест проверки существующего MR когда он не найден"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        repo_config = {
            "url": "https://github.com/owner/repo",
            "token": "token"
        }
        
        result = mr_manager.check_existing(repo_config, "deploy/1.0.0")
        
        assert result["exists"] is False
    
    @patch("modules.deploy.github_api.requests.post")
    @patch("modules.deploy.github_api.requests.get")
    def test_create_mr_success(self, mock_get, mock_post, mr_manager):
        """Тест успешного создания MR"""
        # Мок для проверки существующих MR (пустой список)
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = []
        mock_get.return_value = mock_get_response
        
        # Мок для создания MR
        mock_post_response = MagicMock()
        mock_post_response.status_code = 201
        mock_post_response.json.return_value = {
            "html_url": "https://github.com/test/repo/pull/1"
        }
        mock_post.return_value = mock_post_response
        
        repo_config = {
            "url": "https://github.com/owner/repo",
            "token": "token"
        }
        
        result = mr_manager.create(
            repo_config=repo_config,
            branch_name="deploy/1.0.0",
            version="1.0.0",
            date="2024-01-01",
            repo_name="test_repo"
        )
        
        assert result is True
        mock_post.assert_called_once()
    
    @patch("modules.deploy.github_api.requests.post")
    def test_create_mr_already_exists(self, mock_post, mr_manager):
        """Тест создания MR когда он уже существует"""
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"message": "Pull request already exists"}
        mock_post.return_value = mock_response
        
        repo_config = {
            "url": "https://github.com/owner/repo",
            "token": "token"
        }
        
        result = mr_manager.create(
            repo_config=repo_config,
            branch_name="deploy/1.0.0",
            version="1.0.0",
            date="2024-01-01",
            repo_name="test_repo"
        )
        
        # Должен вернуть True (MR уже существует - это не ошибка)
        assert result is True
    
    @patch("modules.deploy.github_api.requests.get")
    def test_check_branch_exists_via_api_found(self, mock_get, mr_manager):
        """Тест проверки существования ветки через API когда она найдена"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        repo_config = {
            "url": "https://github.com/owner/repo",
            "token": "token"
        }
        
        result = mr_manager.check_branch_exists_via_api(repo_config, "deploy/1.0.0")
        
        assert result is True
    
    @patch("modules.deploy.github_api.requests.get")
    def test_check_branch_exists_via_api_not_found(self, mock_get, mr_manager):
        """Тест проверки существования ветки через API когда она не найдена"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        repo_config = {
            "url": "https://github.com/owner/repo",
            "token": "token"
        }
        
        result = mr_manager.check_branch_exists_via_api(repo_config, "deploy/1.0.0")
        
        assert result is False

