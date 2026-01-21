import socket

import psycopg2


class PostgreSQLManager:
    """Manager for managing PostgreSQL database (connection to external server)."""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # PostgreSQL settings
        self.postgresql_host = None
        self.postgresql_port = None
        self.postgresql_username = None
        self.postgresql_password = None
        self.postgresql_database = None
        self.engine = None
        self.session_factory = None
        
        # Initialize immediately
        self._initialize()
        
    def _initialize(self):
        """PostgreSQL connection initialization."""
        try:
            # Get settings
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            postgresql_config = database_configs.get('postgresql', {})
            
            # Configure connection parameters
            self.postgresql_host = postgresql_config.get('host', 'postgres')
            self.postgresql_port = postgresql_config.get('port', 5432)
            self.postgresql_username = postgresql_config.get('username', 'postgres')
            self.postgresql_password = postgresql_config.get('password', None)
            self.postgresql_database = postgresql_config.get('database', 'core_db')
            
            # Get retry settings from config
            connection_retry = postgresql_config.get('connection_retry', {})
            max_retries = connection_retry.get('max_retries', 3)
            retry_interval = connection_retry.get('retry_interval', 1)
            
            # Check PostgreSQL availability
            if not self._wait_for_postgresql(max_retries=max_retries, retry_interval=retry_interval):
                raise Exception(f"PostgreSQL unavailable at {self.postgresql_host}:{self.postgresql_port}")
            
            # Create database if needed
            self.create_database()
            
            # Create engine
            connection_pool = postgresql_config.get('connection_pool', {})
            self.engine, self.session_factory = self.create_engine(connection_pool)
            
            self.logger.info(f"[PostgreSQL] Connection established: {self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}")
            
        except Exception as e:
            self.logger.error(f"[PostgreSQL] Initialization error: {e}")
            raise Exception(f"Failed to initialize PostgreSQL: {e}") from e
    
    def _wait_for_postgresql(self, max_retries=3, retry_interval=1):
        """Waits for PostgreSQL availability with retries."""
        import time
        
        for attempt in range(max_retries):
            if self.is_port_available():
                return True
            
            if attempt < max_retries - 1:
                self.logger.info(f"[PostgreSQL] Waiting for availability... (attempt {attempt + 1}/{max_retries})")
                time.sleep(retry_interval)
        
        return False
    
    def is_port_available(self):
        """Checks PostgreSQL port availability via socket."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # 1 second timeout
            try:
                result = sock.connect_ex((self.postgresql_host, self.postgresql_port))
                sock.close()
                is_available = result == 0  # True if port is available
                if not is_available:
                    self.logger.debug(f"[PostgreSQL] Port {self.postgresql_host}:{self.postgresql_port} unavailable (code: {result})")
                return is_available
            except Exception as e:
                sock.close()
                self.logger.debug(f"[PostgreSQL] Error checking port {self.postgresql_host}:{self.postgresql_port}: {e}")
                return False
        except Exception as e:
            self.logger.debug(f"[PostgreSQL] Error creating socket: {e}")
            return False
    
    def get_connection(self, database=None):
        """Creates connection to PostgreSQL."""
        try:
            db_name = database or self.postgresql_database
            return psycopg2.connect(
                host=self.postgresql_host,
                port=self.postgresql_port,
                user=self.postgresql_username,
                password=self.postgresql_password,
                database=db_name,
                connect_timeout=2
            )
        except psycopg2.OperationalError as e:
            self.logger.warning(f"[PostgreSQL] Connection error: {e}")
            return None
    
    def is_running(self):
        """Checks if PostgreSQL is running on required port."""
        try:
            # Check PostgreSQL connection
            conn = self.get_connection()
            if conn is None:
                return False
            
            conn.close()
            return True
        except Exception as e:
            self.logger.warning(f"[PostgreSQL] Status check error: {e}")
            return False
    
    def create_database(self):
        """Creates database if it doesn't exist."""
        try:
            self.logger.info(f"[PostgreSQL] Checking database {self.postgresql_database}...")
            
            # Connect to system database postgres
            conn = self.get_connection('postgres')
            if conn is None:
                self.logger.error("[PostgreSQL] Failed to connect to system database")
                raise Exception("PostgreSQL unavailable")
            
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.postgresql_database,))
            if not cursor.fetchone():
                # Create database
                cursor.execute(f'CREATE DATABASE "{self.postgresql_database}"')
                self.logger.info(f"[PostgreSQL] Database {self.postgresql_database} created")
            else:
                self.logger.info(f"[PostgreSQL] Database {self.postgresql_database} already exists")
            
            cursor.close()
            conn.close()
        except Exception as e:
            self.logger.error(f"[PostgreSQL] Error creating database: {e}")
            raise Exception(f"Failed to create database: {e}") from e
    
    def create_engine(self, connection_pool_config):
        """Creates engine for PostgreSQL."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            # For PostgreSQL use connection pool settings
            pool_size = connection_pool_config.get('pool_size', 30)
            max_overflow = connection_pool_config.get('max_overflow', 0)

            # Get engine settings from config
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            postgresql_config = database_configs.get('postgresql', {})
            engine_config = postgresql_config.get('engine_settings', {})
            session_config = engine_config.get('session_settings', {})
            
            # Engine parameters
            echo = engine_config.get('echo', False)
            echo_pool = engine_config.get('echo_pool', False)
            future = engine_config.get('future', True)
            connect_args = engine_config.get('connect_args', {})

            engine_kwargs = {
                'echo': echo,
                'echo_pool': echo_pool,
                'future': future,
                'pool_size': pool_size,
                'max_overflow': max_overflow,
                'pool_pre_ping': connection_pool_config.get('pool_pre_ping', True),
                'pool_recycle': connection_pool_config.get('pool_recycle', 600),
                'connect_args': {
                    'options': connect_args.get('options', '-c client_encoding=utf8'),
                    'connect_timeout': connection_pool_config.get('connect_timeout', 2)
                }
            }
            
            self.engine = create_engine(self.get_database_url(), **engine_kwargs)
            self.session_factory = sessionmaker(
                bind=self.engine, 
                autoflush=session_config.get('autoflush', False),
                autocommit=session_config.get('autocommit', False),
                future=session_config.get('future', True)
            )
            
            self.logger.info(f"[PostgreSQL] Engine created: pool_size={pool_size}, max_overflow={max_overflow}")
            return self.engine, self.session_factory
            
        except Exception as e:
            self.logger.error(f"[PostgreSQL] Error creating engine: {e}")
            raise Exception(f"Failed to create PostgreSQL engine: {e}") from e
    
    def get_database_url(self):
        """Returns URL for connecting to PostgreSQL."""
        if self.postgresql_password:
            return f"postgresql://{self.postgresql_username}:{self.postgresql_password}@{self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}"
        else:
            return f"postgresql://{self.postgresql_username}@{self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}"
    
    def get_engine(self):
        """Returns PostgreSQL engine."""
        return self.engine
    
    def get_session_factory(self):
        """Returns PostgreSQL session factory."""
        return self.session_factory
    
    def get_config(self) -> dict:
        """
        Returns PostgreSQL connection configuration
        """
        return {
            'host': self.postgresql_host,
            'port': self.postgresql_port,
            'username': self.postgresql_username,
            'password': self.postgresql_password,
            'database': self.postgresql_database
        }