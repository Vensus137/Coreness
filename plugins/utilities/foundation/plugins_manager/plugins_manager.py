import os
from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml


class PluginsManager:
    """Менеджер утилит и сервисов с поддержкой зависимостей и DI"""

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
            if (current / "plugins").exists() and \
               (current / "app").exists():
                return current
            current = current.parent
        
        # Если не найден - используем fallback
        return start_path.parent.parent.parent.parent

    def __init__(self, plugins_dir: str = "plugins", utilities_dir: str = "utilities", services_dir: str = "services", **kwargs):
        self.logger = kwargs['logger']
        self.plugins_dir = plugins_dir
        self.utilities_dir = utilities_dir
        self.services_dir = services_dir
        
        # Кеш для информации о утилитах и зависимостях
        self._utilities_info: Dict[str, Dict] = {}
        self._services_info: Dict[str, Dict] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

        # Устанавливаем корень проекта надежным способом
        self.project_root = self._find_project_root(Path(__file__))

        # Загружаем информацию о всех утилитах и сервисах
        self._load_utilities_and_services_info()

    def _load_utilities_and_services_info(self):
        """Загружает информацию о всех утилитах и сервисах для системы DI"""
        self.logger.info("Загрузка информации о утилитах и сервисах...")
        self._utilities_info.clear()
        self._services_info.clear()
        self._dependency_graph.clear()

        # Загружаем информацию о утилитах (рекурсивно)
        utilities_dir = os.path.join(self.project_root, self.plugins_dir, self.utilities_dir)
        self._scan_plugins_recursively(utilities_dir, "utilities", self._utilities_info)
        
        # Загружаем информацию о сервисах (рекурсивно)
        services_dir = os.path.join(self.project_root, self.plugins_dir, self.services_dir)
        self._scan_plugins_recursively(services_dir, "services", self._services_info)
        
        # Строим граф зависимостей
        self._build_dependency_graph()
        
    def _scan_plugins_recursively(self, root_dir: str, plugin_type: str, target_cache: Dict[str, Dict]):
        """
        Рекурсивно сканирует директорию и загружает информацию о плагинах
        """
        if not os.path.exists(root_dir):
            self.logger.warning(f"Директория {plugin_type} не найдена: {root_dir}")
            return

        self._scan_directory_recursively(root_dir, plugin_type, target_cache, "")
        self.logger.info(f"Загружено {plugin_type}: {len(target_cache)}")

    def _scan_directory_recursively(self, directory: str, plugin_type: str, target_cache: Dict[str, Dict], relative_path: str):
        """
        Рекурсивно сканирует директорию на предмет плагинов
        """
        for item_name in os.listdir(directory):
            item_path = os.path.join(directory, item_name)
            
            if os.path.isdir(item_path):
                # Проверяем, есть ли config.yaml в этой папке
                config_path = os.path.join(item_path, 'config.yaml')
                
                if os.path.exists(config_path):
                    # Нашли плагин!
                    # Формируем относительный путь от корня проекта
                    relative_plugin_path = os.path.relpath(item_path, self.project_root)
                    self._load_plugin_info(relative_plugin_path, item_name, plugin_type, target_cache, relative_path)
                else:
                    # Это подпапка, продолжаем рекурсию
                    new_relative_path = os.path.join(relative_path, item_name) if relative_path else item_name
                    self._scan_directory_recursively(item_path, plugin_type, target_cache, new_relative_path)

    def _load_plugin_info(self, plugin_path: str, plugin_name: str, plugin_type: str, target_cache: Dict[str, Dict], relative_path: str):
        """
        Загружает информацию о конкретном плагине
        """
        # Формируем полный путь для чтения config.yaml
        full_plugin_path = os.path.join(self.project_root, plugin_path)
        config_path = os.path.join(full_plugin_path, 'config.yaml')
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            
            # Проверяем, включен ли плагин (по умолчанию включен)
            enabled = config.get('enabled', True)
            if not enabled:
                self.logger.info(f"Плагин {plugin_name} отключен в конфигурации, пропускаем")
                return
            
            plugin_info = {
                'name': config.get('name', plugin_name),
                'description': config.get('description', ''),
                'type': plugin_type,
                'path': plugin_path,
                'config_path': config_path,
                'relative_path': relative_path,
                'dependencies': config.get('dependencies', []),
                'optional_dependencies': config.get('optional_dependencies', []),
                'settings': config.get('settings', {}),
                'features': config.get('features', []),
                'singleton': config.get('singleton', False)
            }
            
            # Добавляем все поля из конфига
            plugin_info['methods'] = config.get('methods', {})
            plugin_info['actions'] = config.get('actions', {})
            
            # Проверяем обязательные поля для разных типов
            if plugin_type == "utilities":
                if not plugin_info['methods']:
                    self.logger.warning(f"Утилита {plugin_name} не имеет секции methods")
                # actions для утилит опциональны
            elif plugin_type == "services":
                if not plugin_info['actions']:
                    self.logger.warning(f"Сервис {plugin_name} не имеет секции actions")
                # methods для сервисов больше не обязательны
            
            target_cache[plugin_info['name']] = plugin_info
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфига {plugin_type[:-1]} {plugin_name}: {e}")

    def _load_plugins_info(self, plugin_type: str, plugins_subdir: str, target_cache: Dict[str, Dict]):
        """
        Универсальный метод для загрузки информации о плагинах (утилитах или сервисах)
        """
        plugins_dir = os.path.join(self.project_root, self.plugins_dir, plugins_subdir)
        self._scan_plugins_recursively(plugins_dir, plugin_type, target_cache)

    def _scan_plugins_in_directory(self, directory: str, plugin_type: str, target_cache: Dict[str, Dict], level: str = None):
        """
        Сканирует директорию и загружает информацию о плагинах (устаревший метод)
        """
        self.logger.warning("Метод _scan_plugins_in_directory устарел, используйте _scan_plugins_recursively")
        self._scan_directory_recursively(directory, plugin_type, target_cache, "")

    def _load_utilities_info(self):
        """Загружает информацию о всех утилитах из plugins/utilities/ (устаревший метод)"""
        self.logger.warning("Метод _load_utilities_info устарел, используйте _scan_plugins_recursively")
        utilities_dir = os.path.join(self.project_root, self.plugins_dir, self.utilities_dir)
        self._scan_plugins_recursively(utilities_dir, "utilities", self._utilities_info)

    def _load_services_info(self):
        """Загружает информацию о всех сервисах из plugins/services/ (устаревший метод)"""
        self.logger.warning("Метод _load_services_info устарел, используйте _scan_plugins_recursively")
        services_dir = os.path.join(self.project_root, self.plugins_dir, self.services_dir)
        self._scan_plugins_recursively(services_dir, "services", self._services_info)

    def _build_dependency_graph(self):
        """Строит граф зависимостей для проверки циклических зависимостей"""
        # Добавляем все утилиты и сервисы в граф
        for utility_name in self._utilities_info:
            self._dependency_graph[utility_name] = set()
        
        for service_name in self._services_info:
            self._dependency_graph[service_name] = set()
        
        # Добавляем зависимости утилит
        for utility_name, utility_info in self._utilities_info.items():
            for dep in utility_info['dependencies']:
                if dep in self._utilities_info:
                    self._dependency_graph[utility_name].add(dep)
                else:
                    self.logger.warning(f"Утилита {utility_name} зависит от несуществующей утилиты: {dep}")
        
        # Добавляем зависимости сервисов
        for service_name, service_info in self._services_info.items():
            for dep in service_info['dependencies']:
                if dep in self._utilities_info:
                    self._dependency_graph[service_name].add(dep)
                else:
                    self.logger.warning(f"Сервис {service_name} зависит от несуществующей утилиты: {dep}")


    # === Публичные методы ===

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        """
        Универсальный метод для получения информации о любом плагине (утилите или сервисе)
        """
        # Сначала пробуем найти как утилиту
        plugin_info = self._utilities_info.get(plugin_name)
        if plugin_info:
            return plugin_info
        
        # Если не найдена как утилита, пробуем как сервис
        plugin_info = self._services_info.get(plugin_name)
        if plugin_info:
            return plugin_info
        
        return None

    def get_plugin_type(self, plugin_name: str) -> Optional[str]:
        """
        Получить тип плагина (утилита или сервис)
        """
        plugin_info = self.get_plugin_info(plugin_name)
        return plugin_info.get('type') if plugin_info else None

    def get_all_plugins_info(self) -> Dict[str, Dict]:
        """
        Получить информацию о всех плагинах (утилиты + сервисы)
        """
        all_plugins = {}
        all_plugins.update(self._utilities_info)
        all_plugins.update(self._services_info)
        return all_plugins

    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, Dict]:
        """
        Получить все плагины определенного типа
        """
        if plugin_type == "utilities":
            return self._utilities_info.copy()
        elif plugin_type == "services":
            return self._services_info.copy()
        else:
            self.logger.warning(f"Неизвестный тип плагина: {plugin_type}")
            return {}

    def get_plugin_dependencies(self, plugin_name: str) -> List[str]:
        """
        Получить ВСЕ зависимости плагина (обязательные + опциональные)
        """
        mandatory = self.get_plugin_mandatory_dependencies(plugin_name)
        optional = self.get_plugin_optional_dependencies(plugin_name)
        return mandatory + optional
    
    def get_plugin_mandatory_dependencies(self, plugin_name: str) -> List[str]:
        """
        Получить только обязательные зависимости плагина
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            return []
        
        return plugin_info.get('dependencies', [])
    
    def get_plugin_optional_dependencies(self, plugin_name: str) -> List[str]:
        """
        Получить только опциональные зависимости плагина
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if not plugin_info:
            return []
        
        return plugin_info.get('optional_dependencies', [])

    def reload(self):
        """Перезагрузить информацию о плагинах"""
        self.logger.info("Перезагрузка информации о плагинах...")
        self._load_utilities_and_services_info() 