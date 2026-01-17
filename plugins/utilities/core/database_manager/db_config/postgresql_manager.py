import socket

import psycopg2


class PostgreSQLManager:
    """Менеджер для управления PostgreSQL базой данных (подключение к внешнему серверу)."""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Настройки PostgreSQL
        self.postgresql_host = None
        self.postgresql_port = None
        self.postgresql_username = None
        self.postgresql_password = None
        self.postgresql_database = None
        self.engine = None
        self.session_factory = None
        
        # Инициализируем сразу
        self._initialize()
        
    def _initialize(self):
        """Инициализация подключения к PostgreSQL."""
        try:
            # Получаем настройки
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            postgresql_config = database_configs.get('postgresql', {})
            
            # Настраиваем параметры подключения
            self.postgresql_host = postgresql_config.get('host', 'postgres')
            self.postgresql_port = postgresql_config.get('port', 5432)
            self.postgresql_username = postgresql_config.get('username', 'postgres')
            self.postgresql_password = postgresql_config.get('password', None)
            self.postgresql_database = postgresql_config.get('database', 'core_db')
            
            # Получаем настройки retry из конфига
            connection_retry = postgresql_config.get('connection_retry', {})
            max_retries = connection_retry.get('max_retries', 3)
            retry_interval = connection_retry.get('retry_interval', 1)
            
            # Проверяем доступность PostgreSQL
            if not self._wait_for_postgresql(max_retries=max_retries, retry_interval=retry_interval):
                raise Exception(f"PostgreSQL недоступен по адресу {self.postgresql_host}:{self.postgresql_port}")
            
            # Создаем базу данных если нужно
            self.create_database()
            
            # Создаём engine
            connection_pool = postgresql_config.get('connection_pool', {})
            self.engine, self.session_factory = self.create_engine(connection_pool)
            
            self.logger.info(f"[PostgreSQL] Подключение установлено: {self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}")
            
        except Exception as e:
            self.logger.error(f"[PostgreSQL] Ошибка инициализации: {e}")
            raise Exception(f"Не удалось инициализировать PostgreSQL: {e}") from e
    
    def _wait_for_postgresql(self, max_retries=3, retry_interval=1):
        """Ожидает доступности PostgreSQL с повторными попытками."""
        import time
        
        for attempt in range(max_retries):
            if self.is_port_available():
                return True
            
            if attempt < max_retries - 1:
                self.logger.info(f"[PostgreSQL] Ожидание доступности... (попытка {attempt + 1}/{max_retries})")
                time.sleep(retry_interval)
        
        return False
    
    def is_port_available(self):
        """Проверяет доступность порта PostgreSQL через socket."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # Таймаут 1 секунда
            try:
                result = sock.connect_ex((self.postgresql_host, self.postgresql_port))
                sock.close()
                is_available = result == 0  # True если порт доступен
                if not is_available:
                    self.logger.debug(f"[PostgreSQL] Порт {self.postgresql_host}:{self.postgresql_port} недоступен (код: {result})")
                return is_available
            except Exception as e:
                sock.close()
                self.logger.debug(f"[PostgreSQL] Ошибка проверки порта {self.postgresql_host}:{self.postgresql_port}: {e}")
                return False
        except Exception as e:
            self.logger.debug(f"[PostgreSQL] Ошибка создания socket: {e}")
            return False
    
    def get_connection(self, database=None):
        """Создает подключение к PostgreSQL."""
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
            self.logger.warning(f"[PostgreSQL] Ошибка подключения: {e}")
            return None
    
    def is_running(self):
        """Проверяет запущен ли PostgreSQL на нужном порту."""
        try:
            # Проверяем подключение к PostgreSQL
            conn = self.get_connection()
            if conn is None:
                return False
            
            conn.close()
            return True
        except Exception as e:
            self.logger.warning(f"[PostgreSQL] Ошибка проверки статуса: {e}")
            return False
    
    def create_database(self):
        """Создает базу данных если она не существует."""
        try:
            self.logger.info(f"[PostgreSQL] Проверка базы данных {self.postgresql_database}...")
            
            # Подключаемся к системной базе postgres
            conn = self.get_connection('postgres')
            if conn is None:
                self.logger.error("[PostgreSQL] Не удалось подключиться к системной базе")
                raise Exception("PostgreSQL недоступен")
            
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Проверяем существует ли база
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.postgresql_database,))
            if not cursor.fetchone():
                # Создаем базу
                cursor.execute(f'CREATE DATABASE "{self.postgresql_database}"')
                self.logger.info(f"[PostgreSQL] База данных {self.postgresql_database} создана")
            else:
                self.logger.info(f"[PostgreSQL] База данных {self.postgresql_database} уже существует")
            
            cursor.close()
            conn.close()
        except Exception as e:
            self.logger.error(f"[PostgreSQL] Ошибка создания базы данных: {e}")
            raise Exception(f"Не удалось создать базу данных: {e}") from e
    
    def create_engine(self, connection_pool_config):
        """Создаёт engine для PostgreSQL."""
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            
            # Для PostgreSQL используем настройки пула соединений
            pool_size = connection_pool_config.get('pool_size', 30)
            max_overflow = connection_pool_config.get('max_overflow', 0)

            # Получаем настройки engine из конфига
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            postgresql_config = database_configs.get('postgresql', {})
            engine_config = postgresql_config.get('engine_settings', {})
            session_config = engine_config.get('session_settings', {})
            
            # Параметры engine
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
            
            self.logger.info(f"[PostgreSQL] Engine создан: pool_size={pool_size}, max_overflow={max_overflow}")
            return self.engine, self.session_factory
            
        except Exception as e:
            self.logger.error(f"[PostgreSQL] Ошибка создания engine: {e}")
            raise Exception(f"Не удалось создать PostgreSQL engine: {e}") from e
    
    def get_database_url(self):
        """Возвращает URL для подключения к PostgreSQL."""
        if self.postgresql_password:
            return f"postgresql://{self.postgresql_username}:{self.postgresql_password}@{self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}"
        else:
            return f"postgresql://{self.postgresql_username}@{self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}"
    
    def get_engine(self):
        """Возвращает engine PostgreSQL."""
        return self.engine
    
    def get_session_factory(self):
        """Возвращает фабрику сессий PostgreSQL."""
        return self.session_factory
    
    def get_config(self) -> dict:
        """
        Возвращает конфигурацию подключения к PostgreSQL
        """
        return {
            'host': self.postgresql_host,
            'port': self.postgresql_port,
            'username': self.postgresql_username,
            'password': self.postgresql_password,
            'database': self.postgresql_database
        }