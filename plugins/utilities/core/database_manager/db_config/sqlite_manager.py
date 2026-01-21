import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


class SQLiteManager:
    """Manager for managing SQLite database."""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # SQLite settings
        self.database_url = None
        self.engine = None
        self.session_factory = None
        
        # Initialize immediately
        self._initialize()
    
    def _initialize(self):
        """SQLite initialization."""
        try:
            # Get settings
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            sqlite_config = database_configs.get('sqlite', {})
            
            # Configure parameters
            self.database_url = sqlite_config.get('database_url', 'sqlite:///data/core.db')
            
            # Create directory
            self.ensure_database_directory()
            
            # Create engine
            self.engine, self.session_factory = self.create_engine()
            
            self.logger.info("SQLite initialized")
            
        except Exception as e:
            self.logger.error(f"SQLite initialization error: {e}")
            raise Exception(f"Failed to initialize SQLite: {e}") from e
    
    def ensure_database_directory(self):
        """Creates database directory if it doesn't exist."""
        try:
            # For SQLite - database file directory
            db_path = self.database_url[10:]  # Remove 'sqlite:///'
            db_dir = os.path.dirname(db_path)
            
            # Create directory if it doesn't exist
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info(f"Database directory created: {db_dir}")
                
        except Exception as e:
            self.logger.error(f"Error creating database directory: {e}")
            # Don't interrupt initialization - directory may already exist
    
    def create_engine(self):
        """Creates SQLite engine with pool settings."""
        try:
            # Get pool settings
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            sqlite_config = database_configs.get('sqlite', {})
            pool_config = sqlite_config.get('connection_pool', {})
            engine_config = sqlite_config.get('engine_settings', {})
            
            # Pool parameters
            # SQLite uses SingletonThreadPool, which doesn't support max_overflow, pool_pre_ping, pool_recycle, pool_reset_on_return
            pool_size = pool_config.get('pool_size', 5)
            connect_timeout = pool_config.get('connect_timeout', 1)
            
            # Engine parameters
            echo = engine_config.get('echo', False)
            future = engine_config.get('future', True)
            isolation_level = engine_config.get('isolation_level', None)
            
            # SQLite engine kwargs (only supported parameters)
            engine_kwargs = {
                'echo': echo,
                'future': future,
                'pool_size': pool_size,
                'connect_args': {
                    'timeout': connect_timeout,
                    # SQLite optimizations from config
                    'isolation_level': isolation_level,
                }
            }
            
            self.engine = create_engine(self.database_url, **engine_kwargs)
            
            # Add SQLite optimizations via event listener
            self._setup_sqlite_optimizations()
            
            self.session_factory = sessionmaker(
                bind=self.engine,
                autoflush=False, 
                autocommit=False,
                future=True
            )
            
            self.logger.info(f"SQLite engine created with pool: size={pool_size}")
            return self.engine, self.session_factory
            
        except Exception as e:
            self.logger.error(f"Error creating SQLite engine: {e}")
            raise Exception(f"Failed to create SQLite engine: {e}") from e
    
    def get_database_url(self):
        """Returns URL for connecting to SQLite."""
        return self.database_url
    
    def get_engine(self):
        """Returns SQLite engine."""
        return self.engine
    
    def get_session_factory(self):
        """Returns SQLite session factory."""
        return self.session_factory
    
    def get_config(self) -> dict:
        """
        Returns SQLite configuration
        """
        # Extract path from URL (remove 'sqlite:///' prefix)
        db_path = None
        if self.database_url:
            if self.database_url.startswith('sqlite:///'):
                db_path = self.database_url[10:]  # Remove 'sqlite:///'
            else:
                db_path = self.database_url.replace('sqlite:///', '')
        
        return {
            'database_url': self.database_url,
            'db_path': db_path
        }
    
    def _setup_sqlite_optimizations(self):
        """Configures SQLite optimizations via PRAGMA commands from config."""
        try:
            # Get PRAGMA settings from config
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            sqlite_config = database_configs.get('sqlite', {})
            pragma_settings = sqlite_config.get('pragma_settings', {})
            
            # Default values if not specified in config
            default_pragma = {
                'journal_mode': 'WAL',
                'cache_size': 2000,
                'synchronous': 'NORMAL',
                'temp_store': 'MEMORY',
                'busy_timeout': 30000,
                'foreign_keys': True
            }
            
            # Merge with default settings
            pragma_config = {**default_pragma, **pragma_settings}
            
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                """Sets PRAGMA settings for each connection."""
                cursor = dbapi_connection.cursor()
                
                # Apply settings from config
                for pragma_name, pragma_value in pragma_config.items():
                    if pragma_name == 'foreign_keys':
                        # For boolean values
                        value = 'ON' if pragma_value else 'OFF'
                        cursor.execute(f"PRAGMA {pragma_name} = {value}")
                    else:
                        # For other values
                        cursor.execute(f"PRAGMA {pragma_name} = {pragma_value}")
                
                cursor.close()
            
            # Log applied settings
            applied_settings = ', '.join([f"{k}={v}" for k, v in pragma_config.items()])
            self.logger.info(f"SQLite optimizations configured: {applied_settings}")
            
        except Exception as e:
            self.logger.warning(f"Failed to configure SQLite optimizations: {e}")
    