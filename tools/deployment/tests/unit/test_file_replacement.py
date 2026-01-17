"""
Unit-тесты для подмены файлов при деплое
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from modules.deploy.file_manager import FileCopier


@pytest.mark.unit
class TestFileReplacement:
    """Тесты для подмены файлов в FileCopier"""
    
    @pytest.fixture
    def temp_project(self, temp_dir):
        """Создает временную структуру проекта для тестов"""
        project_root = temp_dir / "project"
        project_root.mkdir()
        
        # Создаем оригинальные файлы
        (project_root / "config").mkdir()
        (project_root / "config" / "settings.yaml").write_text("original_settings: dev")
        
        (project_root / "config" / "tenant").mkdir()
        (project_root / "config" / "tenant" / "tenant_1").mkdir()
        (project_root / "config" / "tenant" / "tenant_1" / "tg_bot.yaml").write_text("token: dev_token")
        
        # Создаем файлы для подмены
        (project_root / "dev").mkdir()
        (project_root / "dev" / "file_replacement").mkdir()
        (project_root / "dev" / "file_replacement" / "settings.yaml").write_text("original_settings: default")
        (project_root / "dev" / "file_replacement" / "tg_bot.yaml").write_text("token: default_token")
        
        return project_root
    
    @pytest.fixture
    def mock_repo(self, temp_dir):
        """Создает мок Git репозитория"""
        repo_dir = temp_dir / "repo"
        repo_dir.mkdir()
        repo = MagicMock()
        repo.working_dir = str(repo_dir)
        return repo
    
    @pytest.fixture
    def file_copier(self, mock_logger, temp_project):
        """Создает экземпляр FileCopier"""
        return FileCopier(temp_project, mock_logger)
    
    def test_copy_files_without_replacement(self, file_copier, mock_repo):
        """Проверяет копирование файлов без подмены"""
        files_to_deploy = ["config/settings.yaml"]
        deployment_config = {}
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        assert len(result) == 1
        assert "config/settings.yaml" in result
        
        # Проверяем, что скопирован оригинальный файл
        copied_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert copied_file.exists()
        assert copied_file.read_text() == "original_settings: dev"
    
    def test_copy_files_with_replacement(self, file_copier, mock_repo):
        """Проверяет копирование файлов с подменой"""
        files_to_deploy = ["config/settings.yaml"]
        deployment_config = {
            "file_replacements": {
                "config/settings.yaml": "dev/file_replacement/settings.yaml"
            }
        }
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        assert len(result) == 1
        assert "config/settings.yaml" in result
        
        # Проверяем, что скопирован файл-замена
        copied_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert copied_file.exists()
        assert copied_file.read_text() == "original_settings: default"
    
    def test_copy_files_multiple_replacements(self, file_copier, mock_repo):
        """Проверяет копирование нескольких файлов с подменой"""
        files_to_deploy = [
            "config/settings.yaml",
            "config/tenant/tenant_1/tg_bot.yaml"
        ]
        deployment_config = {
            "file_replacements": {
                "config/settings.yaml": "dev/file_replacement/settings.yaml",
                "config/tenant/tenant_1/tg_bot.yaml": "dev/file_replacement/tg_bot.yaml"
            }
        }
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        assert len(result) == 2
        
        # Проверяем первый файл
        settings_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert settings_file.read_text() == "original_settings: default"
        
        # Проверяем второй файл
        tg_bot_file = Path(mock_repo.working_dir) / "config" / "tenant" / "tenant_1" / "tg_bot.yaml"
        assert tg_bot_file.read_text() == "token: default_token"
    
    def test_copy_files_replacement_source_not_found(self, file_copier, mock_repo, mock_logger):
        """Проверяет поведение когда файл-источник для подмены не найден"""
        files_to_deploy = ["config/settings.yaml"]
        deployment_config = {
            "file_replacements": {
                "config/settings.yaml": "dev/file_replacement/nonexistent.yaml"
            }
        }
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        assert len(result) == 1
        
        # Должен использоваться оригинальный файл
        copied_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert copied_file.exists()
        assert copied_file.read_text() == "original_settings: dev"
        
        # Должно быть предупреждение в логах
        assert any("Файл-источник для подмены не найден" in str(call) for call in mock_logger.warning.call_args_list)
    
    def test_copy_files_partial_replacement(self, file_copier, mock_repo):
        """Проверяет копирование когда подменяется только часть файлов"""
        files_to_deploy = [
            "config/settings.yaml",
            "config/tenant/tenant_1/tg_bot.yaml"
        ]
        deployment_config = {
            "file_replacements": {
                "config/settings.yaml": "dev/file_replacement/settings.yaml"
                # tg_bot.yaml не подменяется
            }
        }
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        assert len(result) == 2
        
        # Первый файл подменен
        settings_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert settings_file.read_text() == "original_settings: default"
        
        # Второй файл оригинальный
        tg_bot_file = Path(mock_repo.working_dir) / "config" / "tenant" / "tenant_1" / "tg_bot.yaml"
        assert tg_bot_file.read_text() == "token: dev_token"
    
    def test_copy_files_no_deployment_config(self, file_copier, mock_repo):
        """Проверяет что метод работает без deployment_config"""
        files_to_deploy = ["config/settings.yaml"]
        
        result = file_copier.copy_files(mock_repo, files_to_deploy)
        
        assert len(result) == 1
        copied_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert copied_file.exists()
        assert copied_file.read_text() == "original_settings: dev"
    
    def test_copy_files_add_new_file_not_in_list(self, file_copier, mock_repo):
        """Проверяет добавление файла, которого нет в files_to_deploy"""
        files_to_deploy = ["config/settings.yaml"]  # Этот файл есть в списке
        
        # Добавляем файл, которого нет в files_to_deploy
        deployment_config = {
            "file_replacements": {
                "config/new_file.yaml": "dev/file_replacement/settings.yaml"  # Новый файл
            }
        }
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        # Должны быть скопированы оба файла
        assert len(result) == 2
        assert "config/settings.yaml" in result
        assert "config/new_file.yaml" in result
        
        # Проверяем, что новый файл добавлен
        new_file = Path(mock_repo.working_dir) / "config" / "new_file.yaml"
        assert new_file.exists()
        assert new_file.read_text() == "original_settings: default"
    
    def test_copy_files_add_multiple_new_files(self, file_copier, mock_repo):
        """Проверяет добавление нескольких новых файлов"""
        files_to_deploy = []  # Пустой список
        
        deployment_config = {
            "file_replacements": {
                "config/settings.yaml": "dev/file_replacement/settings.yaml",
                "config/tenant/tenant_1/tg_bot.yaml": "dev/file_replacement/tg_bot.yaml"
            }
        }
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        # Оба файла должны быть добавлены
        assert len(result) == 2
        assert "config/settings.yaml" in result
        assert "config/tenant/tenant_1/tg_bot.yaml" in result
        
        # Проверяем содержимое
        settings_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert settings_file.read_text() == "original_settings: default"
        
        tg_bot_file = Path(mock_repo.working_dir) / "config" / "tenant" / "tenant_1" / "tg_bot.yaml"
        assert tg_bot_file.read_text() == "token: default_token"
    
    def test_copy_files_mixed_replacement_and_addition(self, file_copier, mock_repo):
        """Проверяет смешанный режим: замена существующих и добавление новых"""
        files_to_deploy = ["config/settings.yaml"]  # Один файл в списке
        
        deployment_config = {
            "file_replacements": {
                "config/settings.yaml": "dev/file_replacement/settings.yaml",  # Замена существующего
                "config/new_config.yaml": "dev/file_replacement/tg_bot.yaml"   # Добавление нового
            }
        }
        
        result = file_copier.copy_files(mock_repo, files_to_deploy, deployment_config)
        
        assert len(result) == 2
        
        # Существующий файл заменен
        settings_file = Path(mock_repo.working_dir) / "config" / "settings.yaml"
        assert settings_file.read_text() == "original_settings: default"
        
        # Новый файл добавлен
        new_config_file = Path(mock_repo.working_dir) / "config" / "new_config.yaml"
        assert new_config_file.exists()
        assert new_config_file.read_text() == "token: default_token"

