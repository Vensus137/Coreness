import logging
import os
import sys
from logging.handlers import RotatingFileHandler

# Новый импорт для поиска bot.yaml
from pathlib import Path

import yaml

# Импортируем форматтеры
from .formatters import ColoredFormatter, TimezoneFormatter


class Logger:
    """Системный логгер для проекта"""
    
    def __init__(self):
        """Инициализация логгера"""
        # Определяем корень проекта
        self.project_root = self._find_project_root(Path(__file__))
        
        # Путь к глобальным настройкам
        self.global_settings_path = self.project_root / 'config' / 'settings.yaml'
        
        # Загружаем настройки логгера
        self.settings = self._load_logger_settings()
        
        # Кэшируем основной логгер
        self._main_logger = None
    
    @staticmethod
    def _find_project_root(start_path: Path) -> Path:
        """Надежно определяет корень проекта"""
        # Сначала проверяем переменную окружения
        env_root = os.environ.get('PROJECT_ROOT')
        if env_root and os.path.exists(env_root):
            return Path(env_root)
        
        # Ищем корень проекта по наличию config/settings.yaml
        current_path = start_path.resolve()
        while current_path != current_path.parent:
            config_file = current_path / 'config' / 'settings.yaml'
            if config_file.exists():
                return current_path
            current_path = current_path.parent
        
        # Если не найден, возвращаем текущую директорию
        return Path.cwd()
    
    # --- Вспомогательные преобразования для безопасного слияния настроек ---
    def _to_bool(self, value, fallback: bool) -> bool:
        if value is None:
            return fallback
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", ""}:
                return False
        return fallback

    def _to_int(self, value, fallback: int) -> int:
        try:
            return int(value) if value is not None else fallback
        except Exception:
            return fallback

    def _to_str(self, value, fallback: str) -> str:
        try:
            return str(value) if value is not None else fallback
        except Exception:
            return fallback
    
    def _load_logger_settings(self) -> dict:
        """Чтение секции logger из глобальных настроек"""
        # Загружаем глобальные настройки
        global_settings = {}
        if self.global_settings_path.exists():
            try:
                with open(self.global_settings_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                    global_settings = config.get('logger', {})
            except Exception:
                pass
        
        return global_settings

    def _deep_merge(self, base_dict: dict, override_dict: dict) -> dict:
        """Глубокое слияние словарей: override_dict перекрывает base_dict"""
        result = base_dict.copy()
        
        for key, value in override_dict.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Рекурсивно мерджим вложенные словари
                result[key] = self._deep_merge(result[key], value)
            else:
                # Перекрываем значение
                result[key] = value
        
        return result

    def _load_logging_config(self) -> dict:
        """Загрузка конфига логирования"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

        if not os.path.exists(config_path):
            local_config = {}
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    config = yaml.safe_load(file)
                local_config = config.get('settings', {}) if config else {}
            except Exception:
                local_config = {}

        # Извлекаем значения и дефолты из локального конфига (plugins/.../config.yaml)
        level = local_config.get('level', {}).get('default', 'DEBUG')
        file_enabled = local_config.get('file_enabled', {}).get('default', True)
        file_path = local_config.get('file_path', {}).get('default', 'logs/core.log')
        max_file_size_mb = local_config.get('max_file_size_mb', {}).get('default', 10)
        backup_count = local_config.get('backup_count', {}).get('default', 5)
        local_console_enabled = local_config.get('console_enabled', {}).get('default', True)
        timezone = local_config.get('timezone', {}).get('default', 'Europe/Moscow')

        # Глобальные переопределения из настроек пресета (приоритет над локальными)
        global_logger_settings = self._load_logger_settings()

        # console_enabled: приоритет console_enabled, затем локальный
        if 'console_enabled' in global_logger_settings:
            console_enabled = self._to_bool(global_logger_settings.get('console_enabled'), local_console_enabled)
        else:
            console_enabled = local_console_enabled

        # Прочие поля: берём глобальные, если указаны, с аккуратным приведением типа
        file_enabled = self._to_bool(global_logger_settings.get('file_enabled', file_enabled), file_enabled)
        level = self._to_str(global_logger_settings.get('level', level), level)
        file_path = self._to_str(global_logger_settings.get('file_path', file_path), file_path)
        max_file_size_mb = self._to_int(global_logger_settings.get('max_file_size_mb', max_file_size_mb), max_file_size_mb)
        backup_count = self._to_int(global_logger_settings.get('backup_count', backup_count), backup_count)
        timezone = self._to_str(global_logger_settings.get('timezone', timezone), timezone)

        return {
            'level': level,
            'file_enabled': file_enabled,
            'file_path': file_path,
            'max_file_size_mb': max_file_size_mb,
            'backup_count': backup_count,
            'console_enabled': console_enabled,
            'timezone': timezone
        }

    def setup_logger(self, name: str = "logger") -> logging.Logger:
        """Настройка основного логгера"""
        # Настройка основного логгера
        config = self._load_logging_config()
        level = config.get('level', 'DEBUG').upper()
        file_enabled = config.get('file_enabled', True)
        file_path = config.get('file_path', 'logs/core.log')
        max_file_size_mb = config.get('max_file_size_mb', 10)
        backup_count = config.get('backup_count', 5)
        buffer_size = config.get('buffer_size', 8192)
        console_enabled = config.get('console_enabled', True)

        # Создаем логгер
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Всегда DEBUG, фильтруем на хендлерах

        # Очищаем существующие обработчики
        logger.handlers.clear()

        # Получаем настройку timezone
        timezone = config.get('timezone', 'Europe/Moscow')
        
        # Создаем форматтеры
        # Для файла - форматтер с правильной таймзоной (без цветов)
        file_formatter = TimezoneFormatter('%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S", timezone=timezone)
        
        # Для консоли - цветной форматтер с умным форматированием
        console_formatter = ColoredFormatter(
            '%(asctime)s %(levelname)s %(name)s: %(message)s',
            datefmt="%Y-%m-%d %H:%M:%S",
            use_colors=True,
            smart_format=True,
            timezone=timezone
        )

        # Создаем обработчик для файла
        if file_enabled:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Создаем файловый handler с буферизацией
            if buffer_size > 0:
                # Используем BufferingHandler для буферизации
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
                # Включаем буферизацию на уровне операционной системы
                import io
                buffered_handler = logging.StreamHandler(
                    io.TextIOWrapper(
                        io.BufferedWriter(
                            io.FileIO(file_path, 'ab'),
                            buffer_size=buffer_size
                        ),
                        encoding='utf-8'
                    )
                )
                file_handler = buffered_handler
            else:
                # Обычный handler без буферизации
                file_handler = RotatingFileHandler(
                    file_path,
                    maxBytes=max_file_size_mb * 1024 * 1024,
                    backupCount=backup_count,
                    encoding='utf-8'
                )
            
            file_handler.setLevel(getattr(logging, level))
            file_handler.setFormatter(file_formatter)  # Без цветов
            logger.addHandler(file_handler)

        # Создаем обработчик для консоли
        if console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)  # С цветами
            console_handler.setLevel(getattr(logging, level))  # Используем тот же уровень, что и для файла
            logger.addHandler(console_handler)

        return logger

    def get_logger(self, name: str) -> 'Logger':
        """Получение логгера для модуля"""
        # Создаем новый экземпляр нашего класса Logger
        logger_instance = Logger()
        # Используем тот же внутренний логгер с новым именем
        logger_instance._main_logger = self.setup_logger(name)
        # Устанавливаем правильное имя логгера
        logger_instance.set_logger_name(name)
        return logger_instance
    
    def _get_main_logger(self) -> logging.Logger:
        """Получение кэшированного основного логгера"""
        if self._main_logger is None:
            self._main_logger = self.setup_logger("logger")
        return self._main_logger
    
    def set_logger_name(self, new_name: str):
        """Изменить имя основного логгера"""
        if self._main_logger is None:
            self._main_logger = self.setup_logger("logger")
        self._main_logger.name = new_name
    
    # Методы для совместимости с logging.Logger (для использования в DI)
    def info(self, message: str):
        """Логирование информационного сообщения"""
        self._get_main_logger().info(message)
    
    def debug(self, message: str):
        """Логирование отладочного сообщения"""
        self._get_main_logger().debug(message)
    
    def warning(self, message: str):
        """Логирование предупреждения"""
        self._get_main_logger().warning(message)
    
    def error(self, message: str):
        """Логирование ошибки"""
        self._get_main_logger().error(message)
    
    def critical(self, message: str):
        """Логирование критической ошибки"""
        self._get_main_logger().critical(message)