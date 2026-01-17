"""
Unit-тесты для VersionManager
"""
from unittest.mock import MagicMock, patch

import pytest
from modules.update.version_manager import VersionManager


@pytest.mark.unit
class TestVersionManager:
    """Тесты для VersionManager"""
    
    @pytest.fixture
    def version_manager(self, project_root, mock_logger):
        """Создает экземпляр VersionManager"""
        return VersionManager(project_root, mock_logger)
    
    def test_read_version_file_not_exists(self, version_manager, temp_dir):
        """Тест чтения версии когда файл не существует"""
        version_manager.version_file = temp_dir / "nonexistent" / ".version"
        result = version_manager.read_version()
        assert result is None
    
    def test_write_and_read_version(self, version_manager, temp_dir):
        """Тест записи и чтения версии"""
        version_manager.version_file = temp_dir / ".version"
        version_manager.version_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Записываем версию
        assert version_manager.write_version("1.2.3") is True
        
        # Читаем версию
        result = version_manager.read_version()
        assert result == "1.2.3"
    
    def test_compare_versions_old_less_than_new(self, version_manager):
        """Тест сравнения версий: старая меньше новой"""
        result = version_manager.compare_versions("1.0.0", "1.0.1")
        assert result == -1
    
    def test_compare_versions_old_greater_than_new(self, version_manager):
        """Тест сравнения версий: старая больше новой"""
        result = version_manager.compare_versions("1.0.1", "1.0.0")
        assert result == 1
    
    def test_compare_versions_equal(self, version_manager):
        """Тест сравнения версий: версии равны"""
        result = version_manager.compare_versions("1.0.0", "1.0.0")
        assert result == 0
    
    def test_compare_versions_different_length(self, version_manager):
        """Тест сравнения версий разной длины"""
        # "1.0" дополняется до "1.0.0"
        result = version_manager.compare_versions("1.0", "1.0.1")
        assert result == -1
        
        result = version_manager.compare_versions("1.0.1", "1.0")
        assert result == 1
    
    def test_compare_versions_major_difference(self, version_manager):
        """Тест сравнения версий с разницей в major версии"""
        result = version_manager.compare_versions("1.0.0", "2.0.0")
        assert result == -1
    
    def test_needs_migration_different_versions(self, version_manager):
        """Тест необходимости миграции при разных версиях"""
        assert version_manager.needs_migration("1.0.0", "1.0.1") is True
        assert version_manager.needs_migration("1.0.0", "2.0.0") is True
    
    def test_needs_migration_same_versions(self, version_manager):
        """Тест необходимости миграции при одинаковых версиях"""
        assert version_manager.needs_migration("1.0.0", "1.0.0") is False
    
    def test_needs_migration_none_versions(self, version_manager):
        """Тест необходимости миграции когда версии None"""
        assert version_manager.needs_migration(None, "1.0.0") is False
        assert version_manager.needs_migration("1.0.0", None) is False
        assert version_manager.needs_migration(None, None) is False
    
    @patch("modules.update.version_manager.Repo")
    def test_get_version_from_repo_with_v_prefix(self, mock_repo_class, version_manager, temp_dir):
        """Тест получения версии из репозитория с префиксом 'v'"""
        # Настраиваем мок репозитория
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Мок коммита
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.commit.return_value = mock_commit
        
        # Мок тега
        mock_tag = MagicMock()
        mock_tag.name = "v1.2.3"
        mock_tag.commit.hexsha = "abc123"
        mock_tag.commit.committed_datetime = None
        mock_repo.tags = [mock_tag]
        
        result = version_manager.get_version_from_repo(temp_dir, "main")
        
        # Проверяем что префикс 'v' убран
        assert result == "1.2.3"
    
    @patch("modules.update.version_manager.Repo")
    def test_get_version_from_repo_without_v_prefix(self, mock_repo_class, version_manager, temp_dir):
        """Тест получения версии из репозитория без префикса 'v'"""
        # Настраиваем мок репозитория
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Мок коммита
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.commit.return_value = mock_commit
        
        # Мок тега без префикса 'v'
        mock_tag = MagicMock()
        mock_tag.name = "1.2.3"
        mock_tag.commit.hexsha = "abc123"
        mock_tag.commit.committed_datetime = None
        mock_repo.tags = [mock_tag]
        
        result = version_manager.get_version_from_repo(temp_dir, "main")
        
        # Версия должна остаться без изменений
        assert result == "1.2.3"
    
    @patch("modules.update.version_manager.Repo")
    def test_get_version_from_repo_no_tags(self, mock_repo_class, version_manager, temp_dir):
        """Тест получения версии когда нет тегов"""
        # Настраиваем мок репозитория
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        
        # Мок коммита
        mock_commit = MagicMock()
        mock_commit.hexsha = "abc123"
        mock_repo.commit.return_value = mock_commit
        
        # Нет тегов
        mock_repo.tags = []
        
        result = version_manager.get_version_from_repo(temp_dir, "main")
        
        # Должен вернуть None
        assert result is None

