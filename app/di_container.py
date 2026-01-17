import importlib.util
from typing import Any, Dict, List, Optional, Type


class DIContainer:
    """DI-контейнер для управления зависимостями плагинов"""
    
    def __init__(self, logger: Any, plugins_manager: Any, settings_manager: Any = None):
        self.logger = logger
        self.plugins_manager = plugins_manager
        self.settings_manager = settings_manager
        
        # Кеши для экземпляров и классов
        self._utilities: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._utilities_classes: Dict[str, Type] = {}
        self._services_classes: Dict[str, Type] = {}
        
        # Регистрируем переданные утилиты как уже инициализированные
        self._utilities['logger'] = logger
        self._utilities['plugins_manager'] = plugins_manager
        self._utilities['settings_manager'] = settings_manager
        
        # Флаги инициализации
        self._utilities_initialized = False
        self._services_initialized = False
    
    def initialize_all_plugins(self):
        """Инициализация всех плагинов по плану из SettingsManager"""
        self.logger.info("Начинаем инициализацию всех плагинов...")
        
        # Проверяем доступность SettingsManager
        if self.settings_manager is None:
            self.logger.error("SettingsManager не передан в DIContainer")
            return
        
        # Получаем план запуска из SettingsManager
        startup_plan = self.settings_manager.get_startup_plan()
        
        if not startup_plan:
            self.logger.error("SettingsManager не смог построить план запуска")
            return
        
        self.logger.info(f"План запуска: {startup_plan['total_services']} сервисов, {startup_plan['total_utilities']} утилит")
        
        # Инициализируем утилиты в правильном порядке
        self._initialize_utilities_from_plan(startup_plan['dependency_order'])
        
        # Инициализируем сервисы
        self._initialize_services_from_plan(startup_plan['enabled_services'])
        
        self.logger.info("Все плагины успешно инициализированы")
    
    def get_startup_plan(self) -> Optional[Dict[str, Any]]:
        """Получить план запуска из SettingsManager"""
        return self.settings_manager.get_startup_plan()
    
    def _initialize_utilities_from_plan(self, dependency_order: List[str]):
        """Инициализация утилит по плану из SettingsManager"""
        if self._utilities_initialized:
            return
        
        for utility_name in dependency_order:
            self._register_utility_from_manager(utility_name)
        
        self._utilities_initialized = True
        self.logger.info(f"Инициализировано утилит: {len(self._utilities)}")
    
    def _initialize_services_from_plan(self, enabled_services: List[str]):
        """Инициализация сервисов по плану из SettingsManager"""
        if self._services_initialized:
            return
        
        for service_name in enabled_services:
            self._register_service_from_manager(service_name)
        
        self._services_initialized = True
        self.logger.info(f"Инициализировано сервисов: {len(self._services)}")
    
    def _register_utility_from_manager(self, utility_name: str):
        """Регистрация утилиты из PluginsManager"""
        utility_info = self.plugins_manager.get_plugin_info(utility_name)
        if not utility_info:
            self.logger.error(f"Информация об утилите {utility_name} не найдена")
            return
        
        try:
            # Загружаем класс утилиты
            utility_class = self._load_plugin_class(utility_info)
            if not utility_class:
                return
            
            # Проверяем, является ли утилита singleton
            is_singleton = utility_info.get('singleton', False)
            
            if is_singleton:
                # Создаем экземпляр сразу для singleton
                instance = self._create_utility_instance(utility_name, utility_class)
                self._utilities[utility_name] = instance
            else:
                # Сохраняем только класс для non-singleton
                self._utilities_classes[utility_name] = utility_class
                
        except Exception as e:
            self.logger.error(f"Ошибка регистрации утилиты {utility_name}: {e}")
    
    def _register_service_from_manager(self, service_name: str):
        """Регистрация сервиса из PluginsManager"""
        service_info = self.plugins_manager.get_plugin_info(service_name)
        if not service_info:
            self.logger.error(f"Информация о сервисе {service_name} не найдена")
            return
        
        try:
            # Загружаем класс сервиса
            service_class = self._load_plugin_class(service_info)
            if not service_class:
                return
            
            # Проверяем, является ли сервис singleton
            is_singleton = service_info.get('singleton', False)
            
            if is_singleton:
                # Создаем экземпляр сразу для singleton
                instance = self._create_service_instance(service_name, service_class)
                self._services[service_name] = instance
            else:
                # Сохраняем только класс для non-singleton
                self._services_classes[service_name] = service_class
                
        except Exception as e:
            self.logger.error(f"Ошибка регистрации сервиса {service_name}: {e}")
    
    def _load_plugin_class(self, plugin_info: Dict) -> Optional[Type]:
        """Загрузка класса плагина из файла"""
        plugin_path = plugin_info['path']
        plugin_name = plugin_info['name']
        
        # Определяем имя файла с классом (обычно это имя папки + .py)
        class_file_name = f"{plugin_name}.py"
        class_file_path = f"{plugin_path}/{class_file_name}"
        
        # Если файл с именем папки не найден, ищем другие .py файлы
        if not self._file_exists(class_file_path):
            # Ищем любой .py файл в папке плагина
            py_files = self._find_py_files(plugin_path)
            if not py_files:
                self.logger.error(f"Не найдены .py файлы в папке плагина: {plugin_path}")
                return None
            class_file_path = py_files[0]  # Берем первый найденный .py файл
        
        try:
            # Загружаем модуль с правильной установкой __package__
            module_name = f"plugin_{plugin_name}"
            spec = importlib.util.spec_from_file_location(module_name, class_file_path)
            module = importlib.util.module_from_spec(spec)
            
            # Устанавливаем __package__ для корректной работы относительных импортов
            # Приводим путь к универсальному виду (заменяем все разделители на '/')
            universal_path = plugin_path.replace('\\', '/')
            # Заменяем '/' на '.' для создания имени пакета
            module.__package__ = universal_path.replace('/', '.')
            
            spec.loader.exec_module(module)
            
            # Ищем класс с именем, соответствующим имени плагина
            class_name = self._get_class_name_from_module(module, plugin_name)
            if class_name:
                # Если найден класс, возвращаем его
                plugin_class = getattr(module, class_name)
                return plugin_class
            else:
                # Если класс не найден, возвращаем сам модуль (для модулей с функциями)
                return module
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки класса для плагина {plugin_name}: {e}")
            return None
    
    def _file_exists(self, file_path: str) -> bool:
        """Проверка существования файла"""
        import os
        return os.path.exists(file_path)
    
    def _find_py_files(self, directory: str) -> List[str]:
        """Поиск .py файлов в директории"""
        import os
        py_files = []
        for file in os.listdir(directory):
            if file.endswith('.py') and not file.startswith('__'):
                py_files.append(os.path.join(directory, file))
        return py_files
    
    def _get_class_name_from_module(self, module: Any, plugin_name: str) -> Optional[str]:
        """Поиск имени класса в модуле или возврат самого модуля"""
        
        # Сначала ищем класс с именем, соответствующим имени плагина
        class_name = plugin_name.replace('_', '').title()  # logger -> Logger
        if hasattr(module, class_name):
            attr = getattr(module, class_name)
            if isinstance(attr, type):
                return class_name
        
        # Если не найден, ищем классы, которые могут быть основными
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and not attr_name.startswith('_'):
                # Проверяем, что это не встроенный класс, не typing.Any и не другие типы
                # И что класс определен в этом же модуле (не импортирован)
                if (not attr.__module__.startswith('builtins') and 
                    attr is not type and 
                    not attr.__module__.startswith('typing') and
                    attr_name not in ['Any', 'Dict', 'List', 'Optional', 'Type', 'Path'] and
                    not attr.__module__.startswith('pathlib') and
                    attr.__module__ == module.__name__):  # Класс должен быть определен в этом модуле
                    return attr_name
        
        # Если класс не найден, возвращаем None (будем использовать сам модуль)
        return None
    
    def _create_utility_instance(self, utility_name: str, utility_class: Type, use_on_demand: bool = False) -> Any:
        """Создание экземпляра утилиты с инъекцией зависимостей"""
        
        # Проверяем, является ли это модулем (не классом)
        if hasattr(utility_class, '__file__'):
            # Это модуль, возвращаем его как есть
            return utility_class
        
        # Получаем ВСЕ зависимости утилиты (обязательные + опциональные)
        dependencies = self.plugins_manager.get_plugin_dependencies(utility_name)
        
        # Создаем словарь зависимостей для передачи в конструктор
        deps_dict = {}
        missing_deps = []
        
        for dep_name in dependencies:
            # Выбираем метод получения зависимости в зависимости от флага
            if use_on_demand:
                dep_instance = self.get_utility_on_demand(dep_name)
            else:
                dep_instance = self.get_utility(dep_name)
                
            if dep_instance:
                # Если это логгер, создаем именованный логгер для утилиты
                if dep_name == 'logger' and utility_name != 'logger':
                    deps_dict[dep_name] = dep_instance.get_logger(utility_name)
                else:
                    deps_dict[dep_name] = dep_instance
            else:
                missing_deps.append(dep_name)
                self.logger.warning(f"Зависимость {dep_name} для утилиты {utility_name} не найдена - будет пропущена")
        
        # Логируем информацию о зависимостях (только если есть проблемы)
        if missing_deps:
            pass
        
        # Создаем экземпляр с зависимостями
        try:
            if deps_dict:
                # Передаем зависимости как именованные аргументы
                # Конструктор сам извлечет нужные зависимости из kwargs
                instance = utility_class(**deps_dict)
            else:
                # Если зависимостей нет, создаем без аргументов
                instance = utility_class()
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Ошибка создания экземпляра утилиты {utility_name}: {e}")
            raise
    
    def _create_service_instance(self, service_name: str, service_class: Type) -> Any:
        """Создание экземпляра сервиса с инъекцией зависимостей"""
        
        # Получаем ВСЕ зависимости сервиса (обязательные + опциональные)
        dependencies = self.plugins_manager.get_plugin_dependencies(service_name)
        
        # Создаем словарь зависимостей для передачи в конструктор
        deps_dict = {}
        missing_deps = []
        
        for dep_name in dependencies:
            # Сервисы могут зависеть от утилит
            dep_instance = self.get_utility(dep_name)
            if dep_instance:
                # Если это логгер, создаем именованный логгер для сервиса
                if dep_name == 'logger':
                    deps_dict[dep_name] = dep_instance.get_logger(service_name)
                else:
                    deps_dict[dep_name] = dep_instance
            else:
                missing_deps.append(dep_name)
                self.logger.warning(f"Зависимость {dep_name} для сервиса {service_name} не найдена - будет пропущена")
        
        # Логируем информацию о зависимостях (только если есть проблемы)
        if missing_deps:
            pass
        
        # Создаем экземпляр с зависимостями
        try:
            if deps_dict:
                # Передаем зависимости как именованные аргументы
                # Конструктор сам извлечет нужные зависимости из kwargs
                instance = service_class(**deps_dict)
            else:
                # Если зависимостей нет, создаем без аргументов
                instance = service_class()
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Ошибка создания экземпляра сервиса {service_name}: {e}")
            raise
    
    def get_utility(self, name: str) -> Optional[Any]:
        """Получить утилиту по имени"""
        if name in self._utilities:
            return self._utilities[name]
        
        if name in self._utilities_classes:
            # Создаем экземпляр для non-singleton
            utility_class = self._utilities_classes[name]
            instance = self._create_utility_instance(name, utility_class)
            return instance
        
        return None
    
    def get_utility_on_demand(self, name: str) -> Optional[Any]:
        """Получить утилиту по требованию, даже если она не в плане запуска"""
        
        # Сначала пробуем стандартный метод
        utility = self.get_utility(name)
        if utility:
            return utility
        
        # Если не найдена - загружаем из PluginsManager
        utility_info = self.plugins_manager.get_plugin_info(name)
        if not utility_info:
            self.logger.warning(f"Утилита {name} не найдена в PluginsManager")
            return None
        
        try:
            # Загружаем класс утилиты
            utility_class = self._load_plugin_class(utility_info)
            if not utility_class:
                self.logger.error(f"Не удалось загрузить класс утилиты {name}")
                return None
            
            # Создаем экземпляр с флагом on_demand
            instance = self._create_utility_instance(name, utility_class, use_on_demand=True)
            
            # Регистрируем для будущего использования
            is_singleton = utility_info.get('singleton', False)
            if is_singleton:
                self._utilities[name] = instance
                self.logger.info(f"Утилита {name} создана и зарегистрирована как singleton")
            else:
                self._utilities_classes[name] = utility_class
                self.logger.info(f"Класс утилиты {name} зарегистрирован для создания по требованию")
            
            return instance
            
        except Exception as e:
            self.logger.error(f"Ошибка создания утилиты {name}: {e}")
            return None
    
    def get_service(self, name: str) -> Optional[Any]:
        """Получить сервис по имени"""
        if name in self._services:
            return self._services[name]
        
        if name in self._services_classes:
            # Создаем экземпляр для non-singleton
            service_class = self._services_classes[name]
            instance = self._create_service_instance(name, service_class)
            return instance
        
        return None
    
    def get_all_utilities(self) -> Dict[str, Any]:
        """Получить все зарегистрированные утилиты"""
        return self._utilities.copy()
    
    def get_all_services(self) -> Dict[str, Any]:
        """Получить все зарегистрированные сервисы (singleton + non-singleton)"""
        all_services = self._services.copy()  # singleton сервисы
        
        # Добавляем non-singleton сервисы, создавая экземпляры
        for service_name, service_class in self._services_classes.items():
            try:
                instance = self._create_service_instance(service_name, service_class)
                all_services[service_name] = instance
            except Exception as e:
                self.logger.error(f"Ошибка создания экземпляра сервиса {service_name}: {e}")
        
        return all_services
    
    def shutdown(self):
        """Корректное завершение контейнера"""
        self.logger.info("Shutdown DI-контейнера...")
        
        # Вызываем shutdown у всех утилит, если у них есть такой метод
        # Плагины останавливают свои внутренние фоновые задачи (пулинг, task processors, cache cleanup и т.д.)
        for utility_name, utility_instance in self._utilities.items():
            if hasattr(utility_instance, 'shutdown'):
                try:
                    self.logger.info(f"Shutdown утилиты {utility_name}")
                    utility_instance.shutdown()
                except Exception as e:
                    self.logger.error(f"Ошибка shutdown утилиты {utility_name}: {e}")
        
        # Вызываем shutdown у всех сервисов, если у них есть такой метод
        for service_name, service_instance in self._services.items():
            if hasattr(service_instance, 'shutdown'):
                try:
                    service_instance.shutdown()
                except Exception as e:
                    self.logger.error(f"Ошибка shutdown сервиса {service_name}: {e}")
        
        # Очищаем кеши
        self._utilities.clear()
        self._services.clear()
        self._utilities_classes.clear()
        self._services_classes.clear()
        
        self.logger.info("DI-контейнер завершен") 