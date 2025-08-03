import datetime
import os
from pathlib import Path
from typing import Any, Dict

import yaml


class SettingsManager:
    """Менеджер настроек бота и глобальных параметров"""

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

    def __init__(self, config_dir: str = "config", **kwargs):
        self.logger = kwargs['logger']
        self.plugins_manager = kwargs['plugins_manager']
        self.config_dir = config_dir
        
        # Кеш для настроек
        self._cache: Dict[str, Any] = {}
        
        # Время запуска приложения (будем получать по требованию)
        self._startup_time = None

        # Устанавливаем корень проекта надежным способом
        self.project_root = self._find_project_root(Path(__file__))

        # Загружаем настройки
        self._load_settings()

    def _load_settings(self):
        """Загрузка всех настроек"""
        self.logger.info("Загрузка настроек...")
        self._cache.clear()

        # Загружаем настройки бота
        self._cache['bot_config'] = self._load_yaml_file('bot.yaml')

        # Загружаем settings.yaml
        self._cache['settings'] = self._load_yaml_file('settings.yaml')

        self.logger.info("Настройки загружены")

    def _load_yaml_file(self, relative_path: str) -> dict:
        """Загружает YAML файл по относительному пути от config_dir"""
        file_path = os.path.join(self.project_root, self.config_dir, relative_path)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        return {}

    # === Публичные методы ===

    def get_startup_time(self):
        """Получить время запуска приложения"""
        if self._startup_time is None:
            self._startup_time = self._get_local_time()
        return self._startup_time

    def get_bot_config(self) -> dict:
        """Получить настройки бота"""
        return self._cache.get('bot_config', {})

    def get_settings_section(self, section: str) -> dict:
        """Получить секцию из settings.yaml по имени (например, 'logger', 'bot_docs')."""
        settings = self._cache.get('settings', {})
        return settings.get(section, {})

    def get_all_settings(self) -> dict:
        """Получить все настройки из settings.yaml"""
        return self._cache.get('settings', {}).copy()

    def get_plugin_settings(self, plugin_name: str) -> dict:
        """
        Универсальный метод для получения настроек любого плагина (утилиты или сервиса)
        с учётом приоритета: глобальные из settings.yaml > локальные из config.yaml плагина
        :param plugin_name: имя утилиты или сервиса
        :return: dict с итоговыми настройками
        """
        # Получаем информацию о плагине из plugins_manager
        plugin_info = self.plugins_manager.get_plugin_info(plugin_name)
        if not plugin_info:
            self.logger.warning(f"Плагин {plugin_name} не найден")
            return {}
        
        plugin_type = plugin_info.get('type', 'unknown')
        
        # Глобальные настройки из settings.yaml
        global_settings = self.get_settings_section(plugin_name)
        
        # Локальные настройки из config.yaml плагина
        local_settings = plugin_info.get('settings', {})
        
        # Собираем итоговый dict с приоритетом: глобальные > локальные
        all_keys = set(global_settings.keys()) | set(local_settings.keys())
        merged = {}
        for key in all_keys:
            global_val = global_settings.get(key, None)
            local_val = local_settings.get(key, None)
            
            # Если локальный параметр — dict с default, берём default
            if isinstance(local_val, dict) and 'default' in local_val:
                local_val = local_val['default']
            
            # Приоритет: глобальные > локальные
            merged[key] = global_val if global_val is not None else local_val
        
        return merged

    def reload(self):
        """Перезагрузить настройки бота и глобальные параметры"""
        self.logger.info("Перезагрузка настроек...")
        self._load_settings()
    
    def _get_local_time(self) -> datetime.datetime:
        """Получить текущее локальное время без зависимости от datetime_formatter"""
        import datetime
        from zoneinfo import ZoneInfo

        # Получаем настройки timezone из datetime_formatter (если доступен)
        # или используем значение по умолчанию
        timezone_name = "Europe/Moscow"  # значение по умолчанию
        
        try:
            # Пытаемся получить настройки datetime_formatter
            datetime_settings = self.get_plugin_settings("datetime_formatter")
            timezone_name = datetime_settings.get('timezone', timezone_name)
        except Exception:
            # Если не удалось получить настройки, используем значение по умолчанию
            pass
        
        # Создаем timezone и получаем локальное время
        tz = ZoneInfo(timezone_name)
        return datetime.datetime.now(tz).replace(tzinfo=None) 