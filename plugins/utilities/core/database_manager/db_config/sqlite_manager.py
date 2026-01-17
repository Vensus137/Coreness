import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


class SQLiteManager:
    """Менеджер для управления SQLite базой данных."""
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Настройки SQLite
        self.database_url = None
        self.engine = None
        self.session_factory = None
        
        # Инициализируем сразу
        self._initialize()
    
    def _initialize(self):
        """Инициализация SQLite."""
        try:
            # Получаем настройки
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            sqlite_config = database_configs.get('sqlite', {})
            
            # Настраиваем параметры
            self.database_url = sqlite_config.get('database_url', 'sqlite:///data/core.db')
            
            # Создаём директорию
            self.ensure_database_directory()
            
            # Создаём engine
            self.engine, self.session_factory = self.create_engine()
            
            self.logger.info("SQLite инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации SQLite: {e}")
            raise Exception(f"Не удалось инициализировать SQLite: {e}") from e
    
    def ensure_database_directory(self):
        """Создаёт директорию для базы данных, если её нет."""
        try:
            # Для SQLite - директория файла базы данных
            db_path = self.database_url[10:]  # Убираем 'sqlite:///'
            db_dir = os.path.dirname(db_path)
            
            # Создаём директорию, если она не существует
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
                self.logger.info(f"Создана директория для базы данных: {db_dir}")
                
        except Exception as e:
            self.logger.error(f"Ошибка при создании директории для базы данных: {e}")
            # Не прерываем инициализацию - возможно, директория уже существует
    
    def create_engine(self):
        """Создаёт engine для SQLite с настройками пула."""
        try:
            # Получаем настройки пула
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            sqlite_config = database_configs.get('sqlite', {})
            pool_config = sqlite_config.get('connection_pool', {})
            engine_config = sqlite_config.get('engine_settings', {})
            
            # Параметры пула
            # SQLite использует SingletonThreadPool, который не поддерживает max_overflow, pool_pre_ping, pool_recycle, pool_reset_on_return
            pool_size = pool_config.get('pool_size', 5)
            connect_timeout = pool_config.get('connect_timeout', 1)
            
            # Параметры engine
            echo = engine_config.get('echo', False)
            future = engine_config.get('future', True)
            isolation_level = engine_config.get('isolation_level', None)
            
            # SQLite engine kwargs (только поддерживаемые параметры)
            engine_kwargs = {
                'echo': echo,
                'future': future,
                'pool_size': pool_size,
                'connect_args': {
                    'timeout': connect_timeout,
                    # SQLite оптимизации из конфига
                    'isolation_level': isolation_level,
                }
            }
            
            self.engine = create_engine(self.database_url, **engine_kwargs)
            
            # Добавляем SQLite оптимизации через event listener
            self._setup_sqlite_optimizations()
            
            self.session_factory = sessionmaker(
                bind=self.engine,
                autoflush=False, 
                autocommit=False,
                future=True
            )
            
            self.logger.info(f"SQLite engine создан с пулом: size={pool_size}")
            return self.engine, self.session_factory
            
        except Exception as e:
            self.logger.error(f"Ошибка создания SQLite engine: {e}")
            raise Exception(f"Не удалось создать SQLite engine: {e}") from e
    
    def get_database_url(self):
        """Возвращает URL для подключения к SQLite."""
        return self.database_url
    
    def get_engine(self):
        """Возвращает engine SQLite."""
        return self.engine
    
    def get_session_factory(self):
        """Возвращает фабрику сессий SQLite."""
        return self.session_factory
    
    def get_config(self) -> dict:
        """
        Возвращает конфигурацию SQLite
        """
        # Извлекаем путь из URL (убираем префикс 'sqlite:///')
        db_path = None
        if self.database_url:
            if self.database_url.startswith('sqlite:///'):
                db_path = self.database_url[10:]  # Убираем 'sqlite:///'
            else:
                db_path = self.database_url.replace('sqlite:///', '')
        
        return {
            'database_url': self.database_url,
            'db_path': db_path
        }
    
    def _setup_sqlite_optimizations(self):
        """Настраивает SQLite оптимизации через PRAGMA команды из конфига."""
        try:
            # Получаем настройки PRAGMA из конфига
            settings = self.settings_manager.get_plugin_settings("database_manager")
            database_configs = settings.get('database', {})
            sqlite_config = database_configs.get('sqlite', {})
            pragma_settings = sqlite_config.get('pragma_settings', {})
            
            # Дефолтные значения если не указаны в конфиге
            default_pragma = {
                'journal_mode': 'WAL',
                'cache_size': 2000,
                'synchronous': 'NORMAL',
                'temp_store': 'MEMORY',
                'busy_timeout': 30000,
                'foreign_keys': True
            }
            
            # Объединяем с дефолтными настройками
            pragma_config = {**default_pragma, **pragma_settings}
            
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                """Устанавливает PRAGMA настройки для каждого подключения."""
                cursor = dbapi_connection.cursor()
                
                # Применяем настройки из конфига
                for pragma_name, pragma_value in pragma_config.items():
                    if pragma_name == 'foreign_keys':
                        # Для boolean значений
                        value = 'ON' if pragma_value else 'OFF'
                        cursor.execute(f"PRAGMA {pragma_name} = {value}")
                    else:
                        # Для остальных значений
                        cursor.execute(f"PRAGMA {pragma_name} = {pragma_value}")
                
                cursor.close()
            
            # Логируем примененные настройки
            applied_settings = ', '.join([f"{k}={v}" for k, v in pragma_config.items()])
            self.logger.info(f"SQLite оптимизации настроены: {applied_settings}")
            
        except Exception as e:
            self.logger.warning(f"Не удалось настроить SQLite оптимизации: {e}")
    