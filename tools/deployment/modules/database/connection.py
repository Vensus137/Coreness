"""
Модуль для подключения к базе данных через DI-контейнер ядра
"""

from pathlib import Path
from typing import Optional


class DatabaseConnection:
    """Класс для управления подключением к БД через DI-контейнер ядра"""
    
    def __init__(self, project_root: Path, logger, formatter):
        """
        Инициализация подключения к БД
        """
        self.project_root = project_root
        self.logger = logger
        self.formatter = formatter
        
        self._di_container = None
        self._db_service = None
        self._db_type = None
        self._db_path = None
        self._db_exists = False
    
    def _initialize_di_container(self):
        """Инициализирует DI-контейнер ядра"""
        if self._di_container is not None:
            return
        
        try:
            self.logger.info("Инициализация DI-контейнера ядра...")
            
            # Импортируем необходимые модули ядра
            from app.di_container import DIContainer
            from plugins.utilities.foundation.logger.logger import Logger
            from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager
            from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager
            
            # Создаем logger для ядра
            core_logger = Logger()
            
            # Создаем plugins_manager
            plugins_manager = PluginsManager(logger=core_logger)
            
            # Создаем settings_manager
            settings_manager = SettingsManager(logger=core_logger, plugins_manager=plugins_manager)
            
            # Переопределяем настройки PostgreSQL для запуска на хосте (не в контейнере)
            # Используем переменные окружения или автоматическое определение
            self._patch_postgresql_settings(settings_manager)
            
            # Создаем DI-контейнер
            self._di_container = DIContainer(
                logger=core_logger,
                plugins_manager=plugins_manager,
                settings_manager=settings_manager
            )
            
            # НЕ инициализируем все плагины - используем get_utility_on_demand для ленивой загрузки
            # Это создаст только нужные зависимости для database_manager, а не весь план запуска приложения
            self.logger.info("DI-контейнер ядра создан (плагины будут загружаться по требованию)")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации DI-контейнера: {e}")
            raise
    
    def _patch_postgresql_settings(self, settings_manager):
        """
        Патчит settings_manager для переопределения настроек PostgreSQL при запуске на хосте
        Использует тот же подход, что и sqlite_to_postgresql_migration.py
        """
        import os
        import types
        
        # Проверяем, запущены ли мы в Docker
        is_inside_docker = os.path.exists('/.dockerenv')
        
        if is_inside_docker:
            # В Docker - используем настройки из конфига как есть
            return
        
        # На хосте - переопределяем настройки для подключения через localhost
        postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        postgres_port = os.getenv('POSTGRES_PORT', None)  # Определим автоматически если не указан
        
        # Автоматически определяем порт по окружению
        if postgres_port is None:
            environment = os.getenv('ENVIRONMENT', '')
            if environment == 'test':
                postgres_port = '5433'  # Test окружение использует порт 5433
            else:
                postgres_port = '5432'  # Prod использует порт 5432
        
        postgres_user = os.getenv('POSTGRES_USER', 'postgres')
        postgres_password = os.getenv('POSTGRES_PASSWORD', '')
        postgres_db = os.getenv('POSTGRES_DB', 'core_db')
        
        # Патчим метод get_plugin_settings
        original_get_plugin_settings = settings_manager.get_plugin_settings
        
        def patched_get_plugin_settings(self_ref, plugin_name: str):
            settings = original_get_plugin_settings(plugin_name)
            if plugin_name == 'database_manager':
                settings = settings.copy()
                if 'database' not in settings:
                    settings['database'] = {}
                if 'postgresql' not in settings['database']:
                    settings['database']['postgresql'] = {}
                # Переопределяем настройки подключения для хоста
                settings['database']['postgresql']['host'] = postgres_host
                settings['database']['postgresql']['port'] = int(postgres_port)
                settings['database']['postgresql']['username'] = postgres_user
                if postgres_password:
                    settings['database']['postgresql']['password'] = postgres_password
                settings['database']['postgresql']['database'] = postgres_db
            return settings
        
        # Временно патчим метод для переопределения настроек
        settings_manager.get_plugin_settings = types.MethodType(patched_get_plugin_settings, settings_manager)
        
        self.logger.info(f"Настройки PostgreSQL переопределены для хоста: {postgres_host}:{postgres_port}")
    
    def get_db_service(self):
        """Получает database_manager из DI-контейнера"""
        if self._db_service is None:
            self._initialize_di_container()
            
            self._db_service = self._di_container.get_utility_on_demand("database_manager")
            if not self._db_service:
                raise RuntimeError("Не удалось получить database_manager из DI-контейнера")
            
            # Инициализируем информацию о БД
            self._initialize_database_info()
        
        return self._db_service
    
    def _initialize_database_info(self):
        """Инициализирует информацию о базе данных"""
        if self._db_service is None:
            return
        
        # Получаем информацию о базе данных
        db_config = self._db_service.get_database_config()
        self._db_type = db_config.get('type', 'unknown')
        
        # Для SQLite получаем путь к файлу
        if self._db_type == 'sqlite':
            self._db_path = self._db_service.engine.url.database
            import os
            self._db_exists = os.path.exists(self._db_path) if self._db_path else False
        else:
            # Для PostgreSQL проверяем подключение
            try:
                from sqlalchemy import text
                with self._db_service.engine.connect() as conn:
                    conn.execute(text('SELECT 1'))
                self._db_exists = True
            except Exception:
                self._db_exists = False
        
        # Отключаем SQLAlchemy echo для PostgreSQL
        if self._db_type == 'postgresql':
            self._db_service.engine.echo = False
            self._db_service.engine.echo_pool = False
    
    @property
    def db_service(self):
        """Возвращает database_service"""
        return self.get_db_service()
    
    @property
    def engine(self):
        """Возвращает SQLAlchemy engine"""
        return self.get_db_service().engine
    
    @property
    def db_type(self) -> str:
        """Возвращает тип БД (sqlite/postgresql)"""
        if self._db_type is None:
            self.get_db_service()
        return self._db_type
    
    @property
    def db_path(self) -> Optional[str]:
        """Возвращает путь к файлу БД (для SQLite)"""
        if self._db_path is None:
            self.get_db_service()
        return self._db_path
    
    @property
    def db_exists(self) -> bool:
        """Возвращает True если БД существует"""
        if self._db_type is None:
            self.get_db_service()
        return self._db_exists
    
    def get_database_config(self) -> dict:
        """
        Возвращает конфигурацию текущей базы данных
        """
        return self.get_db_service().get_database_config()
    
    def cleanup(self):
        """Очищает ресурсы"""
        if self._di_container:
            try:
                self._di_container.shutdown()
            except Exception as e:
                self.logger.warning(f"Ошибка завершения DI-контейнера: {e}")

