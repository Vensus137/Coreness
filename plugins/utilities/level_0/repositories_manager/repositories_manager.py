import os
from pathlib import Path
from typing import Dict, Optional

import yaml


class RepositoriesManager:
    """Менеджер репозиториев для работы с базой данных"""

    @staticmethod
    def _find_project_root(start_path: Path) -> Path:
        """Надежно определяет корень проекта"""
        # Сначала проверяем переменную окружения
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and Path(env_root).exists():
            return Path(env_root)
        
        # Ищем по ключевым файлам/папкам
        current = start_path
        while current != current.parent:
            # Проверяем наличие ключевых файлов проекта
            if (current / "main.py").exists() and \
               (current / "plugins").exists() and \
               (current / "app").exists():
                return current
            current = current.parent
        
        # Если не найден - используем fallback
        return start_path.parent.parent.parent.parent

    def __init__(self, repositories_dir: str = "repositories", **kwargs):
        self.logger = kwargs['logger']
        self.repositories_dir = repositories_dir
        
        # Кеш для информации о репозиториях
        self._repositories_info: Dict[str, Dict] = {}
        self._repositories_path: Optional[str] = None

        # Устанавливаем корень проекта надежным способом
        self.project_root = self._find_project_root(Path(__file__))

        # Загружаем информацию о репозиториях
        self._load_repositories_info()

    def _load_repositories_info(self):
        """Загружает информацию о всех репозиториях"""
        self.logger.info("Загрузка информации о репозиториях...")
        self._repositories_info.clear()

        # Ищем папку репозиториев в проекте
        self._repositories_path = self._find_repositories_directory()
        if not self._repositories_path:
            self.logger.warning(f"Папка репозиториев '{self.repositories_dir}' не найдена в проекте")
            return

        # Сканируем директорию репозиториев
        self._scan_repositories_directory(self._repositories_path)
        
        self.logger.info(f"Загружено репозиториев: {len(self._repositories_info)}")

    def _find_repositories_directory(self) -> Optional[str]:
        """Умный поиск папки репозиториев в проекте"""
        # Список возможных путей для поиска
        search_paths = [
            # Прямой путь (если указан полный путь)
            os.path.join(self.project_root, self.repositories_dir),
            # Поиск в plugins/utilities/core/database_service/
            os.path.join(self.project_root, "plugins", "utilities", "core", "database_service", self.repositories_dir),
            # Поиск в plugins/utilities/
            os.path.join(self.project_root, "plugins", "utilities", self.repositories_dir),
            # Поиск в plugins/
            os.path.join(self.project_root, "plugins", self.repositories_dir),
            # Поиск в корне проекта
            os.path.join(self.project_root, self.repositories_dir),
        ]
        
        # Добавляем поиск по всему проекту, если не найден в стандартных местах
        if not any(os.path.exists(path) for path in search_paths):
    
            found_path = self._search_directory_recursively(self.project_root, self.repositories_dir)
            if found_path:
                search_paths.append(found_path)
        
        # Проверяем все пути
        for path in search_paths:
            if os.path.exists(path) and os.path.isdir(path):
                return path
        
        return None

    def _search_directory_recursively(self, root_dir: str, target_dir: str, max_depth: int = 5) -> Optional[str]:
        """Рекурсивный поиск папки в проекте"""
        def search_recursive(current_dir: str, depth: int) -> Optional[str]:
            if depth > max_depth:
                return None
            
            try:
                for item in os.listdir(current_dir):
                    item_path = os.path.join(current_dir, item)
                    
                    if os.path.isdir(item_path):
                        # Проверяем, не является ли это папкой репозиториев
                        if item == target_dir:
                            return item_path
                        
                        # Исключаем системные папки
                        if item in ['.git', '__pycache__', 'venv', 'node_modules', '.vscode']:
                            continue
                        
                        # Рекурсивно ищем глубже
                        result = search_recursive(item_path, depth + 1)
                        if result:
                            return result
                            
            except (PermissionError, OSError):
                pass
            
            return None
        
        return search_recursive(root_dir, 0)

    def _scan_repositories_directory(self, directory: str):
        """Сканирует директорию репозиториев"""
        for item_name in os.listdir(directory):
            item_path = os.path.join(directory, item_name)
            
            if os.path.isdir(item_path):
                # Проверяем, есть ли .yaml файл в этой папке
                yaml_files = [f for f in os.listdir(item_path) if f.endswith('.yaml')]
                
                if yaml_files:
                    # Берем первый .yaml файл (обычно один на репозиторий)
                    yaml_file = yaml_files[0]
                    self._load_repository_info(item_path, item_name, yaml_file)

    def _load_repository_info(self, repository_path: str, repository_name: str, yaml_file: str):
        """Загружает информацию о репозитории"""
        try:
            yaml_path = os.path.join(repository_path, yaml_file)
            
            with open(yaml_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file) or {}
            
            # Создаем структуру информации о репозитории
            repository_info = {
                'name': config.get('name', repository_name),
                'description': config.get('description', ''),
                'path': repository_path,
                'yaml_file': yaml_file,
                'python_file': f"{repository_name}.py",
                'dependencies': config.get('dependencies', {}).get('utilities', []),
                'table': config.get('table', {}),
                'interface': config.get('interface', {}),
                'features': config.get('features', [])
            }
            
            self._repositories_info[repository_info['name']] = repository_info
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки репозитория {repository_name}: {e}")

    def get_repository_info(self, name: str) -> Optional[Dict]:
        """Получить информацию о репозитории по имени"""
        return self._repositories_info.get(name)

    def get_all_repositories_info(self) -> Dict[str, Dict]:
        """Получить информацию о всех репозиториях"""
        return self._repositories_info.copy()

    def get_table_info(self, name: str) -> Optional[Dict]:
        """Получить информацию о таблице репозитория"""
        repo_info = self._repositories_info.get(name)
        if repo_info:
            return repo_info.get('table')
        return None

    def get_repositories_directory(self) -> Optional[str]:
        """Получить путь к найденной папке репозиториев"""
        return self._repositories_path

    def reload(self):
        """Перезагрузить информацию о репозиториях"""
        self.logger.info("Перезагрузка информации о репозиториях...")
        self._repositories_path = None  # Сбрасываем кеш пути
        self._load_repositories_info() 