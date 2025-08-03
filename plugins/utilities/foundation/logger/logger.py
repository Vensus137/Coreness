import logging
import os
import sys
from logging.handlers import RotatingFileHandler
# Новый импорт для поиска bot.yaml
from pathlib import Path

import yaml


class Logger:
    """Системный логгер для проекта"""
    
    def __init__(self):
        """Инициализация логгера"""
        # Путь к глобальному settings.yaml
        self.settings_path = Path('config/settings.yaml')
    
    def _load_global_logger_settings(self) -> dict:
        """Чтение секции logger из config/settings.yaml"""
        if not self.settings_path.exists():
            return {}
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return config.get('logger', {}) if config else {}
        except Exception:
            return {}

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

        # Извлекаем значения и дефолты
        level = local_config.get('level', {}).get('default', 'INFO')
        file_enabled = local_config.get('file_enabled', {}).get('default', True)
        file_path = local_config.get('file_path', {}).get('default', 'logs/bot.log')
        max_file_size_mb = local_config.get('max_file_size_mb', {}).get('default', 10)
        backup_count = local_config.get('backup_count', {}).get('default', 5)
        # console_enabled теперь может быть переопределён глобально
        local_console_enabled = local_config.get('console_enabled', {}).get('default', False)

        # Проверяем глобальную настройку из settings.yaml
        global_logger_settings = self._load_global_logger_settings()
        global_console_enabled = global_logger_settings.get('console_logging_enabled', None)
        if global_console_enabled is not None:
            console_enabled = bool(global_console_enabled)
        else:
            console_enabled = local_console_enabled

        return {
            'level': level,
            'file_enabled': file_enabled,
            'file_path': file_path,
            'max_file_size_mb': max_file_size_mb,
            'backup_count': backup_count,
            'console_enabled': console_enabled
        }

    def setup_logger(self, name: str = "logger") -> logging.Logger:
        """Настройка основного логгера"""
        # Настройка основного логгера
        config = self._load_logging_config()
        level = config.get('level', 'INFO').upper()
        file_enabled = config.get('file_enabled', True)
        file_path = config.get('file_path', 'logs/bot.log')
        max_file_size_mb = config.get('max_file_size_mb', 10)
        backup_count = config.get('backup_count', 5)
        console_enabled = config.get('console_enabled', True)

        # Создаем логгер
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)  # Всегда DEBUG, фильтруем на хендлерах

        # Очищаем существующие обработчики
        logger.handlers.clear()

        # Создаем форматтер
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S")

        # Создаем обработчик для файла
        if file_enabled:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file_handler = RotatingFileHandler(
                file_path,
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(getattr(logging, level))
            logger.addHandler(file_handler)

        # Создаем обработчик для консоли
        if console_enabled:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.DEBUG)
            logger.addHandler(console_handler)

        return logger

    def get_logger(self, name: str) -> logging.Logger:
        """Получение и настройка логгера для модуля"""
        return self.setup_logger(name)
    
    # Методы для совместимости с logging.Logger (для использования в DI)
    def info(self, message: str):
        """Логирование информационного сообщения"""
        logger = self.get_logger("logger")
        logger.info(message)
    
    def debug(self, message: str):
        """Логирование отладочного сообщения"""
        logger = self.get_logger("logger")
        logger.debug(message)
    
    def warning(self, message: str):
        """Логирование предупреждения"""
        logger = self.get_logger("logger")
        logger.warning(message)
    
    def error(self, message: str):
        """Логирование ошибки"""
        logger = self.get_logger("logger")
        logger.error(message)
    
    def critical(self, message: str):
        """Логирование критической ошибки"""
        logger = self.get_logger("logger")
        logger.critical(message)