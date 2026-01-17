from typing import Optional

from .db_config.postgresql_manager import PostgreSQLManager
from .db_config.sqlite_manager import SQLiteManager
from .models import Base
from .modules.backup_operations import BackupOperations
from .modules.data_preparer import DataPreparer
from .modules.view_operations import ViewOperations


class DatabaseManager:
    # Доступные базы данных
    AVAILABLE_DATABASES = ['sqlite', 'postgresql']
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.data_converter = kwargs['data_converter']

        # Сохраняем kwargs для передачи в менеджеры
        self._kwargs = kwargs

        # Инициализируем внутренний data_preparer вместо внешней зависимости
        self.data_preparer = DataPreparer(**kwargs)

        # Добавляем data_preparer в kwargs для передачи в репозитории
        self._kwargs['data_preparer'] = self.data_preparer
        
        # Переменные для хранения текущего менеджера
        self.current_manager = None
        self.engine = None
        self.session_factory = None
        
        # ViewOperations будет создан после инициализации подключения
        self.view_ops = None
        
        # BackupOperations будет создан после инициализации подключения
        self.backup_ops = None
        
        # Инициализируем подключение к базе данных
        self._initialize_database_connection()

    def shutdown(self):
        """Корректное завершение database_manager"""
        try:
            # Закрываем все соединения из пула SQLAlchemy
            if hasattr(self, 'engine') and self.engine is not None:
                self.engine.dispose()
                self.logger.info("Соединения из пула закрыты")
        except Exception as e:
            self.logger.warning(f"Ошибка при закрытии соединений: {e}")
    
    def _shutdown_application(self, reason: str):
        """Останавливает все приложение при критической ошибке базы данных."""
        self.logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА БАЗЫ ДАННЫХ: {reason}")
        self.logger.critical("Приложение не может работать без базы данных. Запускаем graceful shutdown...")
        
        # Импортируем os для принудительного завершения
        import os
        
        # Логируем критическую ошибку
        self.logger.critical("=== ПРИЛОЖЕНИЕ ОСТАНОВЛЕНО ИЗ-ЗА ОШИБКИ БАЗЫ ДАННЫХ ===")
        
        # Принудительное завершение процесса
        os._exit(1)

    def get_master_repository(self):
        """Получить мастер-репозиторий - единую точку входа для всех операций с БД"""
        if not hasattr(self, '_master_repository'):
            from .repositories.master import MasterRepository
            self._master_repository = MasterRepository(self)
        return self._master_repository

    def create_all(self):
        """Создаёт все таблицы в БД согласно моделям и view для PostgreSQL."""
        try:
            # Для SQLite исключаем таблицу vector_storage (она только для PostgreSQL с pgvector)
            if self.db_type == 'sqlite':
                # Получаем все таблицы кроме vector_storage
                tables_to_create = [
                    table for table in Base.metadata.tables.values()
                    if table.name != 'vector_storage'
                ]
                Base.metadata.create_all(self.engine, tables=tables_to_create)
                self.logger.info("Все таблицы успешно созданы (vector_storage пропущена для SQLite).")
            else:
                # Для PostgreSQL создаем все таблицы включая vector_storage
                Base.metadata.create_all(self.engine)
                self.logger.info("Все таблицы успешно созданы.")
            
            # Создаём view для PostgreSQL (для SQLite игнорируется)
            self.create_all_views()
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании таблиц: {e}")
            self._shutdown_application(f"Критическая ошибка создания таблиц: {e}")
    
    def drop_all_views(self) -> bool:
        """
        Удаляет все системные view для PostgreSQL (для SQLite игнорируется)
        """
        if not self.view_ops:
            return True
        
        return self.view_ops.drop_all_views()
    
    def create_all_views(self) -> bool:
        """
        Создаёт все view для PostgreSQL (для SQLite игнорируется)
        """
        if not self.view_ops:
            return True
        
        return self.view_ops.create_all_views()
    
    def get_table_class_map(self):
        """Получает карту таблиц: имя таблицы -> класс модели."""
        table_class_map = {}
        for table_name, _table in Base.metadata.tables.items():
            # Находим соответствующую модель
            for model_class in Base.registry._class_registry.values():
                if hasattr(model_class, '__tablename__') and model_class.__tablename__ == table_name:
                    table_class_map[table_name] = model_class
                    break
        return table_class_map

    def get_available_databases(self):
        """Возвращает список доступных баз данных"""
        return self.AVAILABLE_DATABASES.copy()

    def get_database_config(self) -> dict:
        """
        Возвращает полную конфигурацию текущей базы данных
        Включает: type, url и параметры подключения (host, port, username, password, database для PostgreSQL или db_path для SQLite)
        """
        config = self.current_manager.get_config()
        config['type'] = self.db_type
        config['url'] = self.current_manager.get_database_url()
        return config
    
    def _initialize_database_connection(self):
        """Инициализирует подключение к базе данных."""
        # Получаем настройки
        settings = self.settings_manager.get_plugin_settings("database_manager")
        self.db_type = settings.get('database_preset', 'sqlite')
        
        # Создаем менеджер для нужной базы данных
        self.current_manager = self._create_database_manager(self.db_type)
        
        # Получаем engine и session_factory от текущего менеджера
        self.engine = self.current_manager.get_engine()
        self.session_factory = self.current_manager.get_session_factory()
        
        # Инициализируем ViewOperations для PostgreSQL
        if self.db_type == 'postgresql':
            self.view_ops = ViewOperations(self.engine, self.db_type, self.logger)
        else:
            self.view_ops = None
        
        # Инициализируем BackupOperations
        self.backup_ops = BackupOperations(
            logger=self.logger,
            db_config=self.get_database_config(),
            engine=self.engine,
            settings_manager=self.settings_manager
        )
        
        # Создаём таблицы при инициализации
        self.create_all()
    
    def _create_database_manager(self, db_type: str):
        """Создает менеджер для указанного типа базы данных."""
        if db_type == 'postgresql':
            return PostgreSQLManager(**self._kwargs)
        else:
            return SQLiteManager(**self._kwargs)
    
    async def create_backup(self, backup_filename: Optional[str] = None) -> Optional[str]:
        """Создает бэкап базы данных в формате plain SQL + gzip для PostgreSQL или .bak.gz для SQLite"""
        return await self.backup_ops.create_backup(backup_filename)
    
    async def restore_backup(self, backup_filename: Optional[str] = None) -> bool:
        """Восстанавливает базу данных из бэкапа"""
        return await self.backup_ops.restore_backup(backup_filename)