from typing import Optional

from .db_config.postgresql_manager import PostgreSQLManager
from .db_config.sqlite_manager import SQLiteManager
from .models import Base
from .modules.backup_operations import BackupOperations
from .modules.data_preparer import DataPreparer
from .modules.view_operations import ViewOperations


class DatabaseManager:
    # Available databases
    AVAILABLE_DATABASES = ['sqlite', 'postgresql']
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.data_converter = kwargs['data_converter']

        # Save kwargs for passing to managers
        self._kwargs = kwargs

        # Initialize internal data_preparer instead of external dependency
        self.data_preparer = DataPreparer(**kwargs)

        # Add data_preparer to kwargs for passing to repositories
        self._kwargs['data_preparer'] = self.data_preparer
        
        # Variables for storing current manager
        self.current_manager = None
        self.engine = None
        self.session_factory = None
        
        # ViewOperations will be created after connection initialization
        self.view_ops = None
        
        # BackupOperations will be created after connection initialization
        self.backup_ops = None
        
        # Initialize database connection
        self._initialize_database_connection()

    def shutdown(self):
        """Correct shutdown of database_manager"""
        try:
            # Close all connections from SQLAlchemy pool
            if hasattr(self, 'engine') and self.engine is not None:
                self.engine.dispose()
                self.logger.info("Connections from pool closed")
        except Exception as e:
            self.logger.warning(f"Error closing connections: {e}")
    
    def _shutdown_application(self, reason: str):
        """Stops entire application on critical database error."""
        self.logger.critical(f"CRITICAL DATABASE ERROR: {reason}")
        self.logger.critical("Application cannot work without database. Starting graceful shutdown...")
        
        # Import os for forced termination
        import os
        
        # Log critical error
        self.logger.critical("=== APPLICATION STOPPED DUE TO DATABASE ERROR ===")
        
        # Force process termination
        os._exit(1)

    def get_master_repository(self):
        """Get master repository - single entry point for all DB operations"""
        if not hasattr(self, '_master_repository'):
            from .repositories.master import MasterRepository
            self._master_repository = MasterRepository(self)
        return self._master_repository

    def create_all(self):
        """Creates all tables in DB according to models and views for PostgreSQL."""
        try:
            # For SQLite exclude vector_storage table (it's only for PostgreSQL with pgvector)
            if self.db_type == 'sqlite':
                # Get all tables except vector_storage
                tables_to_create = [
                    table for table in Base.metadata.tables.values()
                    if table.name != 'vector_storage'
                ]
                Base.metadata.create_all(self.engine, tables=tables_to_create)
                self.logger.info("All tables successfully created (vector_storage skipped for SQLite).")
            else:
                # For PostgreSQL create all tables including vector_storage
                Base.metadata.create_all(self.engine)
                self.logger.info("All tables successfully created.")
            
            # Create views for PostgreSQL (ignored for SQLite)
            self.create_all_views()
            
        except Exception as e:
            self.logger.error(f"Error creating tables: {e}")
            self._shutdown_application(f"Critical error creating tables: {e}")
    
    def drop_all_views(self) -> bool:
        """
        Drops all system views for PostgreSQL (ignored for SQLite)
        """
        if not self.view_ops:
            return True
        
        return self.view_ops.drop_all_views()
    
    def create_all_views(self) -> bool:
        """
        Creates all views for PostgreSQL (ignored for SQLite)
        """
        if not self.view_ops:
            return True
        
        return self.view_ops.create_all_views()
    
    def get_table_class_map(self):
        """Gets table map: table name -> model class."""
        table_class_map = {}
        for table_name, _table in Base.metadata.tables.items():
            # Find corresponding model
            for model_class in Base.registry._class_registry.values():
                if hasattr(model_class, '__tablename__') and model_class.__tablename__ == table_name:
                    table_class_map[table_name] = model_class
                    break
        return table_class_map

    def get_available_databases(self):
        """Returns list of available databases"""
        return self.AVAILABLE_DATABASES.copy()

    def get_database_config(self) -> dict:
        """
        Returns full configuration of current database
        Includes: type, url and connection parameters (host, port, username, password, database for PostgreSQL or db_path for SQLite)
        """
        config = self.current_manager.get_config()
        config['type'] = self.db_type
        config['url'] = self.current_manager.get_database_url()
        return config
    
    def _initialize_database_connection(self):
        """Initializes database connection."""
        # Get settings
        settings = self.settings_manager.get_plugin_settings("database_manager")
        self.db_type = settings.get('database_preset', 'sqlite')
        
        # Create manager for required database
        self.current_manager = self._create_database_manager(self.db_type)
        
        # Get engine and session_factory from current manager
        self.engine = self.current_manager.get_engine()
        self.session_factory = self.current_manager.get_session_factory()
        
        # Initialize ViewOperations for PostgreSQL
        if self.db_type == 'postgresql':
            self.view_ops = ViewOperations(self.engine, self.db_type, self.logger)
        else:
            self.view_ops = None
        
        # Initialize BackupOperations
        self.backup_ops = BackupOperations(
            logger=self.logger,
            db_config=self.get_database_config(),
            engine=self.engine,
            settings_manager=self.settings_manager
        )
        
        # Create tables on initialization
        self.create_all()
    
    def _create_database_manager(self, db_type: str):
        """Creates manager for specified database type."""
        if db_type == 'postgresql':
            return PostgreSQLManager(**self._kwargs)
        else:
            return SQLiteManager(**self._kwargs)
    
    async def create_backup(self, backup_filename: Optional[str] = None) -> Optional[str]:
        """Creates database backup in plain SQL + gzip format for PostgreSQL or .bak.gz for SQLite"""
        return await self.backup_ops.create_backup(backup_filename)
    
    async def restore_backup(self, backup_filename: Optional[str] = None) -> bool:
        """Restores database from backup"""
        return await self.backup_ops.restore_backup(backup_filename)