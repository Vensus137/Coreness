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
        
        # Проверяем циклические зависимости
        self._check_circular_dependencies()

    def _scan_plugins_recursively(self, root_dir: str, plugin_type: str, target_cache: Dict[str, Dict]):
        """
        Рекурсивно сканирует директорию и загружает информацию о плагинах
        :param root_dir: корневая директория для сканирования
        :param plugin_type: тип плагина ("utilities" или "services")
        :param target_cache: кеш для сохранения информации о плагинах
        """
        if not os.path.exists(root_dir):
            self.logger.warning(f"Директория {plugin_type} не найдена: {root_dir}")
            return

        self._scan_directory_recursively(root_dir, plugin_type, target_cache, "")
        self.logger.info(f"Загружено {plugin_type}: {len(target_cache)}")

    def _scan_directory_recursively(self, directory: str, plugin_type: str, target_cache: Dict[str, Dict], relative_path: str):
        """
        Рекурсивно сканирует директорию на предмет плагинов
        :param directory: текущая директория для сканирования
        :param plugin_type: тип плагина ("utilities" или "services")
        :param target_cache: кеш для сохранения информации
        :param relative_path: относительный путь от корня типа плагинов
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
        :param plugin_path: относительный путь к папке плагина от корня проекта
        :param plugin_name: имя папки плагина
        :param plugin_type: тип плагина ("utilities" или "services")
        :param target_cache: кеш для сохранения информации
        :param relative_path: относительный путь от корня типа плагинов
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
                'dependencies': config.get('dependencies', {}).get('utilities', []),
                'settings': config.get('settings', {}),
                'features': config.get('features', []),
                'singleton': config.get('singleton', False),
                'edition': config.get('edition', 'base')  # По умолчанию "base"
            }
            
            # Добавляем все поля из конфига
            plugin_info['interface'] = config.get('interface', {})
            plugin_info['actions'] = config.get('actions', {})
            
            # Проверяем обязательные поля для разных типов
            if plugin_type == "utilities":
                if not plugin_info['interface']:
                    self.logger.warning(f"Утилита {plugin_name} не имеет секции interface")
            elif plugin_type == "services":
                if not plugin_info['actions']:
                    self.logger.warning(f"Сервис {plugin_name} не имеет секции actions")
            
            target_cache[plugin_info['name']] = plugin_info
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфига {plugin_type[:-1]} {plugin_name}: {e}")

    def _load_plugins_info(self, plugin_type: str, plugins_subdir: str, target_cache: Dict[str, Dict]):
        """
        Универсальный метод для загрузки информации о плагинах (утилитах или сервисах)
        :param plugin_type: тип плагина ("utilities" или "services")
        :param plugins_subdir: подпапка для данного типа плагинов
        :param target_cache: кеш для сохранения информации о плагинах
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

    def _check_circular_dependencies(self):
        """Проверяет наличие циклических зависимостей в графе"""
        def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in self._dependency_graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        visited = set()
        for node in self._dependency_graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    self.logger.error(f"Обнаружена циклическая зависимость для: {node}")
                    raise ValueError(f"Циклическая зависимость обнаружена для: {node}")

    # === Публичные методы ===

    def get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        """
        Универсальный метод для получения информации о любом плагине (утилите или сервисе)
        :param plugin_name: имя плагина
        :return: информация о плагине или None
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
        :param plugin_name: имя плагина
        :return: "utilities", "services" или None
        """
        plugin_info = self.get_plugin_info(plugin_name)
        return plugin_info.get('type') if plugin_info else None

    def get_all_plugins_info(self) -> Dict[str, Dict]:
        """
        Получить информацию о всех плагинах (утилиты + сервисы)
        :return: словарь {имя_плагина: информация_о_плагине}
        """
        all_plugins = {}
        all_plugins.update(self._utilities_info)
        all_plugins.update(self._services_info)
        return all_plugins

    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, Dict]:
        """
        Получить все плагины определенного типа
        :param plugin_type: "utilities" или "services"
        :return: словарь с плагинами указанного типа
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
        Универсальный метод для получения зависимостей любого плагина
        :param plugin_name: имя плагина
        :return: список зависимостей
        """
        plugin_info = self.get_plugin_info(plugin_name)
        if plugin_info:
            return plugin_info.get('dependencies', [])
        return []

    def get_dependency_order(self) -> List[str]:
        """Получить порядок инициализации утилит с учетом зависимостей (топологическая сортировка)"""
        def topological_sort(graph: Dict[str, Set[str]]) -> List[str]:
            result = []
            visited = set()
            temp_visited = set()
            
            def visit(node: str):
                if node in temp_visited:
                    raise ValueError(f"Циклическая зависимость обнаружена для: {node}")
                if node in visited:
                    return
                
                temp_visited.add(node)
                
                for neighbor in graph.get(node, set()):
                    visit(neighbor)
                
                temp_visited.remove(node)
                visited.add(node)
                result.append(node)
            
            for node in graph:
                if node not in visited:
                    visit(node)
            
            return result
        
        # Создаем граф только для утилит (сервисы инициализируются после утилит)
        utilities_graph = {name: deps for name, deps in self._dependency_graph.items() 
                          if name in self._utilities_info}
        
        return topological_sort(utilities_graph)

    def get_all_dependencies(self) -> Dict[str, List[str]]:
        """Получить все зависимости (утилиты + сервисы)"""
        all_deps = {}
        
        # Добавляем зависимости утилит
        for utility_name, utility_info in self._utilities_info.items():
            all_deps[utility_name] = utility_info.get('dependencies', [])
        
        # Добавляем зависимости сервисов
        for service_name, service_info in self._services_info.items():
            all_deps[service_name] = service_info.get('dependencies', [])
        
        return all_deps

    def check_circular_dependencies(self) -> bool:
        """Проверить наличие циклических зависимостей"""
        try:
            self._check_circular_dependencies()
            return True
        except ValueError:
            return False

    def reload(self):
        """Перезагрузить информацию о плагинах"""
        self.logger.info("Перезагрузка информации о плагинах...")
        self._load_utilities_and_services_info() 