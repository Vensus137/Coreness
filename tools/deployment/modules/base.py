"""
Базовый модуль инициализации системы деплоя
Централизованное управление project_root, config, env
"""

import os
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

import yaml
from dotenv import load_dotenv

# Определяем директорию deployment для корректных импортов
_deployment_dir = Path(__file__).parent.parent

# Константы конфигурации
CONFIG_FILE_NAME = "config.yaml"
ENV_FILE_NAME = ".env"


class DeploymentBase:
    """Базовый класс для инициализации системы деплоя"""
    
    _instance: Optional['DeploymentBase'] = None
    _initialized: bool = False
    
    def __new__(cls):
        """Singleton паттерн - один экземпляр на все приложение"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация базовых параметров (выполняется один раз)"""
        if self._initialized:
            return
        
        # Добавляем директорию deployment в sys.path для корректных импортов модулей
        if str(_deployment_dir) not in sys.path:
            sys.path.insert(0, str(_deployment_dir))
        
        # Определяем корень проекта
        self.project_root = self._find_project_root()
        
        # Добавляем корень проекта в sys.path (один раз)
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))
        
        # Загружаем переменные окружения (один раз)
        self._load_environment()
        
        # Инициализируем логгер (до загрузки конфига для логирования процесса)
        from modules.utils.console_logger import ConsoleLogger
        self.logger = ConsoleLogger("deployment_base")
        
        # Загружаем конфигурацию (один раз)
        self.config = self._load_config()
        
        # Проверяем, что все переменные окружения разрешены корректно
        self._validate_resolved_env_vars()
        
        self._initialized = True
        self.logger.info(f"Система деплоя инициализирована. Корень проекта: {self.project_root}")
    
    @staticmethod
    def _find_project_root() -> Path:
        """Надежно определяет корень проекта"""
        # Сначала проверяем переменную окружения
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and Path(env_root).exists():
            return Path(env_root)
        
        # Определяем стартовую точку (файл, который вызвал инициализацию)
        # Берем самый глубокий вызов в стеке, который не из этой библиотеки
        sys._getframe()  # для будущего использования стека вызовов
        start_path = Path(__file__).parent.parent.parent  # tools/deployment
        
        # Ищем корень проекта по ключевым файлам/папкам
        current = start_path
        while current != current.parent:
            # Проверяем наличие ключевых файлов проекта
            if (current / "main.py").exists() and \
               (current / "plugins").exists() and \
               (current / "app").exists():
                return current
            current = current.parent
        
        # Fallback - используем папку на уровень выше от tools/deployment
        return start_path.parent
    
    def _load_environment(self):
        """Загружает переменные окружения из .env файла"""
        try:
            env_file = self.project_root / ENV_FILE_NAME
            if env_file.exists():
                load_dotenv(env_file)
            else:
                # Пробуем загрузить без указания пути (dotenv сам найдет)
                load_dotenv()
        except Exception:
            # Не критично, продолжаем работу (logger еще не инициализирован)
            pass
    
    def _load_config(self) -> dict:
        """Загружает конфигурацию из config.yaml и разрешает переменные окружения"""
        config_path = Path(__file__).parent.parent / CONFIG_FILE_NAME
        
        try:
            if not config_path.exists():
                raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError("Конфигурационный файл пуст")
            
            # Разрешаем переменные окружения в конфиге
            config = self._resolve_env_variables(config)
            
            return config
            
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"❌ Ошибка парсинга YAML: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            sys.exit(1)
    
    def _resolve_env_variables(self, data: Any) -> Any:
        """
        Рекурсивно обрабатывает переменные окружения в формате ${VARIABLE}
        Аналогично settings_manager для унификации
        """
        if isinstance(data, dict):
            return {key: self._resolve_env_variables(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._resolve_env_variables(item) for item in data]
        elif isinstance(data, str):
            return self._resolve_env_variable_in_string(data)
        else:
            return data
    
    def _resolve_env_variable_in_string(self, value: str) -> str:
        """
        Заменяет переменные окружения в строке формата ${VARIABLE}
        Сохраняет информацию о неразрешенных переменных для последующей валидации
        """
        if not isinstance(value, str):
            return value
        
        # Проверяем, является ли вся строка переменной окружения
        if value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            resolved = os.getenv(env_var, '')
            # Сохраняем информацию о неразрешенной переменной
            if not resolved:
                if not hasattr(self, '_unresolved_vars'):
                    self._unresolved_vars = []
                self._unresolved_vars.append({
                    'var': env_var,
                    'value': value,
                    'path': None  # Будет заполнено при валидации
                })
            return resolved
        
        # Проверяем, содержит ли строка переменные окружения
        pattern = r'\$\{([^}]+)\}'
        
        def replace_env_var(match):
            env_var = match.group(1)
            resolved = os.getenv(env_var, '')
            # Сохраняем информацию о неразрешенной переменной
            if not resolved:
                if not hasattr(self, '_unresolved_vars'):
                    self._unresolved_vars = []
                self._unresolved_vars.append({
                    'var': env_var,
                    'value': match.group(0),
                    'path': None  # Будет заполнено при валидации
                })
            return resolved
        
        return re.sub(pattern, replace_env_var, value)
    
    def _find_unresolved_placeholders(self, data: Any, path: str = "") -> List[dict]:
        """
        Рекурсивно ищет все неразрешенные плейсхолдеры ${...} в данных
        Возвращает список словарей с информацией о неразрешенных переменных
        """
        unresolved = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                unresolved.extend(self._find_unresolved_placeholders(value, current_path))
        elif isinstance(data, list):
            for i, item in enumerate(data):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                unresolved.extend(self._find_unresolved_placeholders(item, current_path))
        elif isinstance(data, str):
            # Проверяем, содержит ли строка плейсхолдеры
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, data)
            for var_name in matches:
                unresolved.append({
                    'var': var_name,
                    'value': f"${{{var_name}}}",
                    'path': path
                })
        
        return unresolved
    
    def _validate_resolved_env_vars(self):
        """
        Универсальная проверка всех неразрешенных плейсхолдеров ${...} в конфиге
        Вызывается после инициализации logger для логирования предупреждений
        """
        unresolved = self._find_unresolved_placeholders(self.config)
        
        if unresolved:
            # Группируем по имени переменной для более читаемого вывода
            vars_by_name = {}
            for item in unresolved:
                var_name = item['var']
                if var_name not in vars_by_name:
                    vars_by_name[var_name] = []
                vars_by_name[var_name].append(item)
            
            for var_name, occurrences in vars_by_name.items():
                paths = [occ['path'] for occ in occurrences if occ['path']]
                if paths:
                    paths_str = ", ".join(paths[:3])  # Показываем первые 3 пути
                    if len(paths) > 3:
                        paths_str += f" и еще {len(paths) - 3}"
                    self.logger.warning(
                        f"Переменная окружения {var_name} не установлена "
                        f"(используется в: {paths_str})"
                    )
                else:
                    self.logger.warning(f"Переменная окружения {var_name} не установлена")
    
    def get_project_root(self) -> Path:
        """Возвращает корень проекта"""
        return self.project_root
    
    def get_config(self) -> dict:
        """Возвращает конфигурацию"""
        return self.config
    
    def get_global_settings(self) -> dict:
        """Получает глобальные настройки из config/settings.yaml"""
        settings_path = self.project_root / "config" / "settings.yaml"
        try:
            if settings_path.exists():
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = yaml.safe_load(f)
                    return settings.get('global', {})
        except Exception as e:
            self.logger.warning(f"Не удалось загрузить глобальные настройки: {e}")
        return {}
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Получает переменную окружения"""
        return os.getenv(key, default)
    
    def get_default_branch(self, repo_config: Optional[dict] = None) -> str:
        """
        Получает дефолтную ветку из конфига репозитория или общих настроек
        Если не указана - возвращает 'main' как fallback
        """
        # Сначала проверяем конфиг конкретного репозитория
        if repo_config:
            default_branch = repo_config.get('default_branch')
            if default_branch:
                return default_branch
            
            # Пробуем получить из branches (первая ветка или 'main')
            branches = repo_config.get('branches', {})
            if branches:
                # Берем первую доступную ветку или ищем 'main'/'master'
                for branch in branches.values():
                    if branch in ['main', 'master']:
                        return branch
                # Если не нашли стандартные - берем первую
                return list(branches.values())[0]
        
        # Проверяем общие настройки git
        git_settings = self.config.get('git_settings', {})
        default_branch = git_settings.get('default_branch')
        if default_branch:
            return default_branch
        
        # Fallback - стандартная ветка
        return 'main'


# Глобальный экземпляр для удобного доступа
_base = None

def get_base() -> DeploymentBase:
    """Получает или создает базовый экземпляр"""
    global _base
    if _base is None:
        _base = DeploymentBase()
    return _base

