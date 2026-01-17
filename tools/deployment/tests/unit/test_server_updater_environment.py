"""
Unit-тесты для ServerUpdater - работа с окружениями (test/prod)
"""
from unittest.mock import MagicMock, patch

import pytest
from modules.update.server_updater import ServerUpdater


@pytest.mark.unit
class TestServerUpdaterEnvironment:
    """Тесты для работы ServerUpdater с разными окружениями"""
    
    @pytest.fixture
    def server_updater(self, sample_config, mock_logger, project_root):
        """Создает экземпляр ServerUpdater"""
        return ServerUpdater(sample_config, project_root, mock_logger)
    
    def test_get_branch_for_test_environment(self, server_updater):
        """Проверяет выбор правильной ветки для test окружения"""
        # Настраиваем конфиг с ветками и токеном
        server_updater.server_config = {
            "repository": {
                "url": "https://github.com/test/repo",
                "token": "test-token",
                "branches": {
                    "test": "test-branch",
                    "prod": "prod-branch"
                }
            }
        }
        
        # Мокаем клонирование
        with patch("modules.update.server_updater.Repo.clone_from") as mock_clone:
            mock_repo = MagicMock()
            mock_clone.return_value = mock_repo
            
            repo_path = server_updater.clone_repository("test")
            
            # Проверяем что использовалась правильная ветка
            assert repo_path is not None
            mock_repo.git.checkout.assert_called_once_with("test-branch")
    
    def test_get_branch_for_prod_environment(self, server_updater):
        """Проверяет выбор правильной ветки для prod окружения"""
        # Настраиваем конфиг с ветками и токеном
        server_updater.server_config = {
            "repository": {
                "url": "https://github.com/test/repo",
                "token": "test-token",
                "branches": {
                    "test": "test-branch",
                    "prod": "prod-branch"
                }
            }
        }
        
        # Мокаем клонирование
        with patch("modules.update.server_updater.Repo.clone_from") as mock_clone:
            mock_repo = MagicMock()
            mock_clone.return_value = mock_repo
            
            repo_path = server_updater.clone_repository("prod")
            
            # Проверяем что использовалась правильная ветка
            assert repo_path is not None
            mock_repo.git.checkout.assert_called_once_with("prod-branch")
    
    def test_get_branch_with_explicit_branch(self, server_updater):
        """Проверяет использование явно указанной ветки"""
        # Настраиваем конфиг с токеном
        server_updater.server_config = {
            "repository": {
                "url": "https://github.com/test/repo",
                "token": "test-token",
                "branches": {
                    "test": "test-branch",
                    "prod": "prod-branch"
                }
            }
        }
        
        # Мокаем клонирование
        with patch("modules.update.server_updater.Repo.clone_from") as mock_clone:
            mock_repo = MagicMock()
            mock_clone.return_value = mock_repo
            
            # Явно указываем ветку
            repo_path = server_updater.clone_repository("test", branch="custom-branch")
            
            # Проверяем что использовалась явно указанная ветка
            assert repo_path is not None
            mock_repo.git.checkout.assert_called_once_with("custom-branch")
    
    def test_get_branch_missing_environment(self, server_updater):
        """Проверяет обработку отсутствия ветки для окружения"""
        # Настраиваем конфиг без ветки для test
        server_updater.server_config = {
            "repository": {
                "url": "https://github.com/test/repo",
                "branches": {
                    "prod": "prod-branch"
                }
            }
        }
        
        # Должен вернуть None и залогировать ошибку
        repo_path = server_updater.clone_repository("test")
        
        assert repo_path is None
        server_updater.logger.error.assert_called()
    
    def test_get_branch_missing_repo_config(self, server_updater):
        """Проверяет обработку отсутствия конфигурации репозитория"""
        # Настраиваем конфиг без repository
        server_updater.server_config = {}
        
        # Должен вернуть None
        repo_path = server_updater.clone_repository("test")
        
        assert repo_path is None
        server_updater.logger.error.assert_called()

