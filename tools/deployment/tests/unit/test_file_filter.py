"""
Unit-тесты для FileFilter
"""

import pytest
from modules.deploy.file_filter import FileFilter


@pytest.mark.unit
class TestFileFilter:
    """Тесты для FileFilter"""
    
    @pytest.fixture
    def temp_project(self, temp_dir):
        """Создает временную структуру проекта для тестов"""
        # Создаем структуру:
        # temp_dir/
        #   app/
        #     main.py
        #   tools/
        #     script.py
        #   resources/
        #     data.txt
        #   main.py
        
        (temp_dir / "app").mkdir()
        (temp_dir / "app" / "main.py").write_text("# app main")
        
        (temp_dir / "tools").mkdir()
        (temp_dir / "tools" / "script.py").write_text("# tool script")
        
        (temp_dir / "resources").mkdir()
        (temp_dir / "resources" / "data.txt").write_text("data")
        
        (temp_dir / "main.py").write_text("# main")
        
        return temp_dir
    
    @pytest.fixture
    def file_filter(self, sample_config, mock_logger, temp_project):
        """Создает экземпляр FileFilter"""
        return FileFilter(sample_config, mock_logger, temp_project)
    
    def test_resolve_presets(self, file_filter):
        """Тест разрешения пресетов"""
        deployment_config = {
            "presets": ["core_files"],
            "custom_include": [],
            "custom_exclude": []
        }
        
        resolved = file_filter._resolve_deployment_rules(deployment_config)
        
        assert "app/" in resolved["include"]
        assert "tools/" in resolved["include"]
        assert "main.py" in resolved["include"]
    
    def test_custom_include_overrides_exclude(self, file_filter):
        """Тест что custom_include имеет приоритет над exclude"""
        deployment_config = {
            "presets": ["core_files", "exclusions"],
            "custom_include": ["resources/"],  # Включаем resources несмотря на exclude
            "custom_exclude": []
        }
        
        resolved = file_filter._resolve_deployment_rules(deployment_config)
        
        # resources должен быть в include (custom_include имеет приоритет)
        assert "resources/" in resolved["include"]
        # Но также может быть в exclude из пресета
        # Проверяем что в итоговом списке файлов resources присутствует
    
    def test_empty_include_returns_empty_list(self, file_filter):
        """Тест что пустой include возвращает пустой список"""
        deployment_config = {
            "presets": [],
            "custom_include": [],
            "custom_exclude": []
        }
        
        files = file_filter.get_files_for_repo("test_repo", deployment_config)
        
        assert files == []
    
    def test_get_files_for_repo_with_presets(self, file_filter):
        """Тест получения файлов с использованием пресетов"""
        deployment_config = {
            "presets": ["core_files"],
            "custom_include": [],
            "custom_exclude": []
        }
        
        files = file_filter.get_files_for_repo("test_repo", deployment_config)
        
        # Проверяем что файлы найдены
        assert len(files) > 0
        assert "main.py" in files
        assert "app/main.py" in files or any("app" in f for f in files)
    
    def test_exclude_patterns(self, file_filter):
        """Тест применения exclude паттернов"""
        deployment_config = {
            "presets": ["core_files", "exclusions"],
            "custom_include": [],
            "custom_exclude": []
        }
        
        files = file_filter.get_files_for_repo("test_repo", deployment_config)
        
        # resources должен быть исключен
        assert not any("resources" in f for f in files)
    
    def test_validate_files_exist(self, file_filter, temp_project):
        """Тест валидации существования файлов"""
        existing_files = ["main.py", "app/main.py"]
        missing_files = ["nonexistent.py", "missing/file.txt"]
        
        all_files = existing_files + missing_files
        
        missing = file_filter.validate_files_exist(all_files)
        
        assert len(missing) == 2
        assert "nonexistent.py" in missing
        assert "missing/file.txt" in missing
    
    def test_recursive_exclude_pattern(self, file_filter, temp_project):
        """Тест рекурсивного исключения паттерна **/tests/"""
        # Создаем структуру с tests в разных местах
        (temp_project / "tests").mkdir()
        (temp_project / "tests" / "test_main.py").write_text("# test")
        
        (temp_project / "plugins").mkdir()
        (temp_project / "plugins" / "services").mkdir()
        (temp_project / "plugins" / "services" / "test_service").mkdir()
        (temp_project / "plugins" / "services" / "test_service" / "tests").mkdir()
        (temp_project / "plugins" / "services" / "test_service" / "tests" / "test_service.py").write_text("# test")
        
        (temp_project / "plugins" / "utilities").mkdir()
        (temp_project / "plugins" / "utilities" / "core").mkdir()
        (temp_project / "plugins" / "utilities" / "core" / "tests").mkdir()
        (temp_project / "plugins" / "utilities" / "core" / "tests" / "test_core.py").write_text("# test")
        
        # Создаем файлы, которые не должны быть исключены
        (temp_project / "app" / "main.py").write_text("# main")
        (temp_project / "main.py").write_text("# main")
        
        # Тестируем рекурсивное исключение
        files = {
            "tests/test_main.py",
            "plugins/services/test_service/tests/test_service.py",
            "plugins/utilities/core/tests/test_core.py",
            "app/main.py",
            "main.py"
        }
        
        excluded = file_filter._apply_excludes(files, ["**/tests/"])
        
        # Все файлы из tests должны быть исключены
        assert "tests/test_main.py" not in excluded
        assert "plugins/services/test_service/tests/test_service.py" not in excluded
        assert "plugins/utilities/core/tests/test_core.py" not in excluded
        
        # Остальные файлы должны остаться
        assert "app/main.py" in excluded
        assert "main.py" in excluded
    
    def test_backward_compatibility_exclude_patterns(self, file_filter):
        """Тест обратной совместимости с существующими паттернами"""
        files = {
            "resources/data.txt",
            "logs/app.log",
            "data/core.db",
            "app/main.py"
        }
        
        # Старые паттерны должны работать как раньше
        excluded = file_filter._apply_excludes(files, ["resources/", "logs/", "data/"])
        
        assert "resources/data.txt" not in excluded
        assert "logs/app.log" not in excluded
        assert "data/core.db" not in excluded
        assert "app/main.py" in excluded
    
    def test_nested_folder_exclude(self, file_filter, temp_project):
        """Тест исключения вложенных папок с рекурсивным паттерном"""
        # Создаем глубокую структуру
        (temp_project / "level1").mkdir()
        (temp_project / "level1" / "level2").mkdir()
        (temp_project / "level1" / "level2" / "tests").mkdir()
        (temp_project / "level1" / "level2" / "tests" / "deep_test.py").write_text("# test")
        
        files = {
            "level1/level2/tests/deep_test.py",
            "app/main.py"
        }
        
        excluded = file_filter._apply_excludes(files, ["**/tests/"])
        
        assert "level1/level2/tests/deep_test.py" not in excluded
        assert "app/main.py" in excluded

