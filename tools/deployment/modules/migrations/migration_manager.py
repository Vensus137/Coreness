"""
Модуль для управления миграциями БД
Универсальные и специфические миграции
"""

import datetime
import gzip
import importlib.util
import os
import subprocess
from pathlib import Path
from typing import Optional

# Импорты будут работать через базовый модуль
from modules.utils.version_utils import get_clean_version


class MigrationManager:
    """Класс для управления миграциями БД"""
    
    def __init__(self, config: dict, project_root: Path, logger, formatter):
        """Инициализация менеджера миграций"""
        self.config = config
        self.project_root = project_root
        self.logger = logger
        self.formatter = formatter
        self.migrations_dir = Path(project_root) / config.get('migration_settings', {}).get('migrations_dir', 'tools/deployment/migrations')
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройки миграций
        self.migration_settings = config.get('migration_settings', {})
        self.require_confirmation = self.migration_settings.get('require_confirmation', True)
        self.auto_backup = self.migration_settings.get('auto_backup', True)
        
        # Подключение к БД и универсальная миграция
        self._db_connection = None
        self._universal_migration = None
        
        # ComposeManager для получения имен контейнеров (ленивая инициализация)
        self._compose_manager = None
    
    def _get_db_connection(self):
        """Получает подключение к БД"""
        if self._db_connection is None:
            from modules.database.connection import DatabaseConnection
            self._db_connection = DatabaseConnection(
                self.project_root,
                self.logger,
                self.formatter
            )
        return self._db_connection
    
    def _get_universal_migration(self):
        """Получает экземпляр универсальной миграции"""
        if self._universal_migration is None:
            from modules.database.migration import UniversalMigration
            db_connection = self._get_db_connection()
            self._universal_migration = UniversalMigration(
                db_connection,
                self.logger,
                self.formatter
            )
        return self._universal_migration
    
    def run_universal_migration(self, backup_path: Optional[str] = None) -> bool:
        """
        Запускает универсальную миграцию через новые модули
        """
        try:
            self.logger.info("Запуск универсальной миграции")
            
            # Получаем все JSON миграции для проверки
            universal_migration = self._get_universal_migration()
            json_migrations = self._get_all_json_migrations()
            
            # Проверяем невалидные JSON перед миграцией
            if not universal_migration.json_validator.check_and_fix_invalid_json(json_migrations):
                self.formatter.print_warning("Миграция отменена из-за невалидных JSON данных")
                return False
            
            # Запускаем миграцию, передаем путь к бэкапу для удаления после успешной миграции
            success = universal_migration.migrate_database(backup_path=backup_path)
            
            if success:
                self.logger.info("Универсальная миграция завершена успешно")
            else:
                self.logger.error("Универсальная миграция завершилась с ошибкой")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Ошибка универсальной миграции: {e}")
            return False
    
    def _get_all_json_migrations(self):
        """Получает все JSON миграции для всех таблиц"""
        try:
            universal_migration = self._get_universal_migration()
            metadata_cache = universal_migration.metadata_cache
            
            all_json_migrations = []
            all_tables = metadata_cache.get_table_class_map()
            
            for table_name, table_class in all_tables.items():
                # Получаем типы колонок из БД и модели
                db_cols = metadata_cache.get_db_columns(table_name)
                model_cols = metadata_cache.get_model_columns(table_class)
                
                # Находим несовпадения типов
                type_mismatches = []
                for col_name in model_cols:
                    if col_name in db_cols:
                        # Проверяем тип
                        db_type = db_cols[col_name].get('type') if isinstance(db_cols[col_name], dict) else db_cols[col_name]
                        model_type = model_cols[col_name].get('type') if isinstance(model_cols[col_name], dict) else model_cols[col_name]
                        if str(db_type) != str(model_type):
                            # Получаем объект колонки из модели
                            col_obj = getattr(table_class, col_name)
                            type_mismatches.append((col_obj, db_type, model_type))
                
                if type_mismatches:
                    # Определяем JSON миграции для этой таблицы
                    json_migrations, _ = universal_migration.json_validator.determine_migration_strategy(
                        table_name,
                        type_mismatches
                    )
                    all_json_migrations.extend(json_migrations)
            
            return all_json_migrations
            
        except Exception as e:
            self.logger.warning(f"Ошибка получения JSON миграций: {e}")
            return []
    
    def check_specific_migration_needed(self, version: str) -> bool:
        """
        Проверяет необходимость специфической миграции для версии
        
        Использует чистую версию (без суффикса) для поиска миграций
        """
        clean_version = get_clean_version(version)
        version_migration_dir = self.migrations_dir / f"v{clean_version}"
        migration_file = version_migration_dir / "migration.py"
        
        if migration_file.exists():
            self.logger.info(f"Найдена специфическая миграция для версии {clean_version} (из {version})")
            return True
        
        return False
    
    def run_specific_migration(self, version: str) -> bool:
        """
        Запускает версионированную миграцию
        
        Использует чистую версию (без суффикса) для поиска миграций
        """
        try:
            clean_version = get_clean_version(version)
            version_migration_dir = self.migrations_dir / f"v{clean_version}"
            migration_file = version_migration_dir / "migration.py"
            
            if not migration_file.exists():
                self.logger.warning(f"Специфическая миграция для версии {clean_version} (из {version}) не найдена")
                return False
            
            self.logger.info(f"Запуск специфической миграции для версии {clean_version} (из {version})")
            
            # Загружаем модуль миграции
            spec = importlib.util.spec_from_file_location("migration", migration_file)
            if spec is None or spec.loader is None:
                self.logger.error("Не удалось загрузить модуль миграции")
                return False
            
            migration_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration_module)
            
            # Проверяем наличие функции migrate
            if not hasattr(migration_module, 'migrate'):
                self.logger.error("Функция migrate не найдена в модуле миграции")
                return False
            
            # Получаем db_service для передачи в специфическую миграцию
            db_connection = self._get_db_connection()
            db_service = db_connection.db_service
            
            # Запускаем миграцию (передаем db_service вместо старого db_manager)
            success = migration_module.migrate(db_service, self.logger)
            
            if success:
                self.logger.info(f"Специфическая миграция для версии {version} завершена успешно")
            else:
                self.logger.error(f"Специфическая миграция для версии {version} завершилась с ошибкой")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Ошибка специфической миграции для версии {version}: {e}")
            return False
    
    def run_all_migrations(self, version: str, db_backup_path: Optional[str] = None) -> bool:
        """
        Запускает все миграции (универсальную и специфическую) для указанной версии
        """
        try:
            # Проверяем специфическую миграцию для текущей версии
            has_specific = self.check_specific_migration_needed(version)
            
            # Сначала универсальная миграция (всегда запускаем)
            self.logger.info("Шаг 1: Универсальная миграция")
            if not self.run_universal_migration():
                self.logger.error("Ошибка универсальной миграции")
                if db_backup_path:
                    self.logger.info("Восстанавливаем БД из последнего бэкапа...")
                    self.restore_database()
                return False
            self.logger.info("Универсальная миграция завершена")
            
            # Затем специфическая миграция (если есть для этой версии)
            if has_specific:
                self.logger.info(f"Шаг 2: Специфическая миграция для версии {version}")
                if not self.run_specific_migration(version):
                    self.logger.error("Ошибка специфической миграции")
                    if db_backup_path:
                        self.logger.info("Восстанавливаем БД из последнего бэкапа...")
                        self.restore_database()
                    return False
                self.logger.info(f"Специфическая миграция для версии {version} завершена")
            else:
                self.logger.info(f"Специфическая миграция для версии {version} не найдена (пропускаем)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка миграций: {e}")
            if db_backup_path:
                self.logger.info("Восстанавливаем БД из последнего бэкапа...")
                self.restore_database()
            return False
    
    def _get_compose_manager(self):
        """Получает ComposeManager для работы с docker-compose файлами"""
        if self._compose_manager is None:
            from modules.update.compose_config_manager import ComposeConfigManager
            from modules.update.compose_manager import ComposeManager
            from modules.update.docker_checker import DockerChecker
            
            compose_config_manager = ComposeConfigManager(self.config, self.logger)
            self._compose_manager = ComposeManager(
                self.project_root,
                self.logger,
                self.config,
                compose_config_manager
            )
            # Устанавливаем команду docker-compose
            docker_checker = DockerChecker(self.logger, self.config)
            compose_command = docker_checker.get_compose_command()
            if compose_command:
                self._compose_manager.set_compose_command(compose_command)
        return self._compose_manager
    
    def _get_app_container_name(self) -> Optional[str]:
        """Определяет имя контейнера app по окружению из docker-compose файлов"""
        try:
            environment = os.getenv('ENVIRONMENT', '').lower()
            if not environment:
                return None
            
            compose_manager = self._get_compose_manager()
            container_name = compose_manager.get_container_name(environment)
            return container_name
        except Exception as e:
            self.logger.warning(f"Не удалось определить имя контейнера из docker-compose файлов: {e}")
            return None
    
    def _is_container_running(self, container_name: str) -> bool:
        """Проверяет, запущен ли Docker контейнер"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--format', '{{.Names}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return container_name in result.stdout
            return False
        except Exception:
            return False
    
    def _create_backup_via_docker_exec(self, db_config: dict, backup_dir: str) -> Optional[str]:
        """Создает бэкап PostgreSQL через docker exec (для запуска на хосте)"""
        try:
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Определяем имя контейнера app
            container_name = self._get_app_container_name()
            if not container_name:
                self.logger.error("Не удалось определить имя контейнера app")
                return None
            
            if not self._is_container_running(container_name):
                self.logger.error(f"Контейнер {container_name} не запущен")
                return None
            
            # Определяем имя сервиса PostgreSQL в Docker сети из docker-compose файлов
            environment = os.getenv('ENVIRONMENT', '').lower()
            
            compose_manager = self._get_compose_manager()
            postgres_service_host = compose_manager.get_postgres_service_name(environment)
            
            if not postgres_service_host:
                self.logger.error(f"Не удалось определить имя сервиса PostgreSQL для окружения {environment}")
                return None
            
            # Формируем имя файла бэкапа
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"postgresql_backup_{timestamp}.sql.gz"
            backup_path = os.path.join(backup_dir, backup_filename)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Команда через docker exec
            cmd = [
                'docker', 'exec',
                container_name,
                'pg_dump',
                '-h', postgres_service_host,
                '-p', '5432',
                '-U', postgresql_username,
                '-d', postgresql_database,
                '--no-password'
            ]
            
            env = os.environ.copy()
            if postgresql_password:
                env['PGPASSWORD'] = postgresql_password
            
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False
            )
            
            with gzip.open(backup_path, 'wb') as f_out:
                while True:
                    chunk = process.stdout.read(8192)
                    if not chunk:
                        break
                    f_out.write(chunk)
            
            process.wait()
            
            if process.returncode == 0:
                self.logger.info(f"Бэкап PostgreSQL создан через docker exec: {backup_path}")
                return backup_path
            else:
                error_msg = process.stderr.read().decode('utf-8') if process.stderr else "Неизвестная ошибка"
                self.logger.error(f"Ошибка создания бэкапа PostgreSQL через docker exec: {error_msg}")
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return None
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа PostgreSQL через docker exec: {e}")
            return None
    
    def _find_latest_backup_file(self, backup_dir: str, db_type: str) -> Optional[str]:
        """Находит последний файл бэкапа в директории для указанного типа БД"""
        try:
            if not os.path.exists(backup_dir):
                return None
            
            # Определяем расширение файла в зависимости от типа БД
            if db_type == 'sqlite':
                extension = '.bak.gz'
            elif db_type == 'postgresql':
                extension = '.sql.gz'
            else:
                return None
            
            # Ищем все файлы бэкапа с нужным расширением
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.endswith(extension):
                    file_path = os.path.join(backup_dir, filename)
                    mtime = os.path.getmtime(file_path)
                    backup_files.append((file_path, mtime))
            
            if not backup_files:
                return None
            
            # Сортируем по времени модификации (последний = самый новый)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            return backup_files[0][0]
            
        except Exception as e:
            self.logger.warning(f"Ошибка поиска последнего бэкапа: {e}")
            return None
    
    def _restore_backup_via_docker_exec(self, db_config: dict, backup_file_path: str) -> bool:
        """Восстанавливает PostgreSQL из бэкапа через docker exec (для запуска на хосте)"""
        try:
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Определяем имя контейнера app
            container_name = self._get_app_container_name()
            if not container_name:
                self.logger.error("Не удалось определить имя контейнера app")
                return False
            
            if not self._is_container_running(container_name):
                self.logger.error(f"Контейнер {container_name} не запущен")
                return False
            
            # Определяем имя сервиса PostgreSQL в Docker сети из docker-compose файлов
            environment = os.getenv('ENVIRONMENT', '').lower()
            
            compose_manager = self._get_compose_manager()
            postgres_service_host = compose_manager.get_postgres_service_name(environment)
            
            if not postgres_service_host:
                self.logger.error(f"Не удалось определить имя сервиса PostgreSQL для окружения {environment}")
                return False
            
            # Копируем файл бэкапа в контейнер
            temp_backup_path = f"/tmp/{os.path.basename(backup_file_path)}"
            copy_cmd = ['docker', 'cp', backup_file_path, f"{container_name}:{temp_backup_path}"]
            
            copy_result = subprocess.run(
                copy_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if copy_result.returncode != 0:
                self.logger.error(f"Не удалось скопировать файл бэкапа в контейнер: {copy_result.stderr}")
                return False
            
            try:
                # Сначала очищаем БД
                clear_cmd = ['docker', 'exec']
                if postgresql_password:
                    clear_cmd.extend(['-e', f'PGPASSWORD={postgresql_password}'])
                clear_cmd.extend([
                    container_name,
                    'psql',
                    '-h', postgres_service_host,
                    '-p', '5432',
                    '-U', postgresql_username,
                    '-d', postgresql_database,
                    '--no-password',
                    '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
                ])
                
                clear_result = subprocess.run(
                    clear_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if clear_result.returncode != 0:
                    self.logger.warning(f"Не удалось очистить БД перед восстановлением: {clear_result.stderr}")
                
                # Восстанавливаем из бэкапа
                if backup_file_path.endswith('.gz'):
                    # Распаковываем и передаем в psql
                    # Используем bash -c с передачей переменной окружения PGPASSWORD через -e
                    restore_cmd = ['docker', 'exec', '-i']
                    if postgresql_password:
                        restore_cmd.extend(['-e', f'PGPASSWORD={postgresql_password}'])
                    restore_cmd.extend([
                        container_name,
                        'bash', '-c',
                        f'gunzip -c {temp_backup_path} | psql -h {postgres_service_host} -p 5432 -U {postgresql_username} -d {postgresql_database} --no-password'
                    ])
                else:
                    # Передаем файл напрямую
                    restore_cmd = ['docker', 'exec', '-i']
                    if postgresql_password:
                        restore_cmd.extend(['-e', f'PGPASSWORD={postgresql_password}'])
                    restore_cmd.extend([
                        container_name,
                        'psql',
                        '-h', postgres_service_host,
                        '-p', '5432',
                        '-U', postgresql_username,
                        '-d', postgresql_database,
                        '--no-password',
                        '-f', temp_backup_path
                    ])
                
                restore_result = subprocess.run(
                    restore_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # Восстановление может занять время
                )
                
                if restore_result.returncode == 0:
                    self.logger.info(f"БД PostgreSQL восстановлена через docker exec из {backup_file_path}")
                    return True
                else:
                    error_msg = restore_result.stderr if restore_result.stderr else restore_result.stdout
                    self.logger.error(f"Ошибка восстановления PostgreSQL через docker exec: {error_msg}")
                    return False
                    
            finally:
                # Удаляем временный файл из контейнера
                cleanup_cmd = ['docker', 'exec', container_name, 'rm', '-f', temp_backup_path]
                subprocess.run(cleanup_cmd, capture_output=True, timeout=5)
                
        except Exception as e:
            self.logger.error(f"Ошибка восстановления PostgreSQL через docker exec: {e}")
            return False
    
    def backup_database(self) -> Optional[str]:
        """Создает бэкап БД перед миграцией"""
        import asyncio
        try:
            self.logger.info("Создание бэкапа БД...")
            
            # Проверяем, запущены ли мы в Docker
            is_inside_docker = os.path.exists('/.dockerenv')
            
            # Используем database_manager из DI-контейнера
            db_connection = self._get_db_connection()
            database_manager = db_connection.get_db_service()
            db_config = db_connection.get_database_config()
            db_type = db_config.get('type')
            
            # Для PostgreSQL на хосте пробуем использовать docker exec если pg_dump недоступен
            if db_type == 'postgresql' and not is_inside_docker:
                try:
                    # Пробуем создать бэкап через database_manager
                    backup_path = asyncio.run(database_manager.create_backup())
                    if backup_path:
                        self.logger.info(f"Бэкап БД создан: {backup_path}")
                        return backup_path
                    else:
                        # Если вернулся None, значит pg_dump не найден, пробуем через docker exec
                        # Получаем backup_dir из глобальных настроек
                        from modules.base import get_base
                        base = get_base()
                        global_settings = base.get_global_settings()
                        backup_dir = global_settings.get('backup_dir', 'data/backups')
                        backup_path = self._create_backup_via_docker_exec(db_config, str(self.project_root / backup_dir))
                        if backup_path:
                            return backup_path
                        # Если и через docker exec не получилось, возвращаем None
                        self.logger.error("Не удалось создать бэкап ни напрямую, ни через docker exec")
                        return None
                except Exception as e:
                    # Если не получилось (например, pg_dump не найден), пробуем через docker exec
                    self.logger.info(f"Не удалось создать бэкап напрямую ({e}), пробуем через docker exec...")
                    # Получаем backup_dir из глобальных настроек
                    from modules.base import get_base
                    base = get_base()
                    global_settings = base.get_global_settings()
                    backup_dir = global_settings.get('backup_dir', 'data/backups')
                    backup_path = self._create_backup_via_docker_exec(db_config, str(self.project_root / backup_dir))
                    if backup_path:
                        return backup_path
                    # Если и через docker exec не получилось, возвращаем None
                    self.logger.error("Не удалось создать бэкап ни напрямую, ни через docker exec")
                    return None
            
            # Для SQLite или для PostgreSQL внутри Docker используем стандартный метод
            backup_path = asyncio.run(database_manager.create_backup())
            
            if backup_path:
                self.logger.info(f"Бэкап БД создан: {backup_path}")
                return backup_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа БД: {e}")
            return None
    
    def restore_database(self, backup_filename: Optional[str] = None) -> bool:
        """Восстанавливает БД из бэкапа"""
        import asyncio
        try:
            # Проверяем, запущены ли мы в Docker
            is_inside_docker = os.path.exists('/.dockerenv')
            
            # Используем database_manager из DI-контейнера
            db_connection = self._get_db_connection()
            database_manager = db_connection.get_db_service()
            db_config = db_connection.get_database_config()
            db_type = db_config.get('type')
            
            # Для PostgreSQL на хосте пробуем использовать docker exec если psql недоступен
            if db_type == 'postgresql' and not is_inside_docker:
                try:
                    # Пробуем восстановить через database_manager
                    if backup_filename:
                        success = asyncio.run(database_manager.restore_backup(backup_filename=backup_filename))
                    else:
                        success = asyncio.run(database_manager.restore_backup())
                    
                    if success:
                        self.logger.info("БД успешно восстановлена из бэкапа")
                        return True
                    else:
                        # Если не получилось (например, psql не найден), пробуем через docker exec
                        # Получаем backup_dir из глобальных настроек
                        from modules.base import get_base
                        base = get_base()
                        global_settings = base.get_global_settings()
                        backup_dir = global_settings.get('backup_dir', 'data/backups')
                        backup_path = str(self.project_root / backup_dir)
                        
                        if backup_filename:
                            # Если указано имя файла, используем его
                            backup_file_path = os.path.join(backup_path, backup_filename)
                        else:
                            # Иначе находим последний бэкап
                            backup_file_path = self._find_latest_backup_file(backup_path, db_type)
                        
                        if not backup_file_path or not os.path.exists(backup_file_path):
                            self.logger.error(f"Файл бэкапа не найден: {backup_file_path}")
                            return False
                        
                        success = self._restore_backup_via_docker_exec(db_config, backup_file_path)
                        if success:
                            return True
                        self.logger.error("Не удалось восстановить бэкап ни напрямую, ни через docker exec")
                        return False
                except Exception as e:
                    # Если не получилось (например, psql не найден), пробуем через docker exec
                    self.logger.info(f"Не удалось восстановить бэкап напрямую ({e}), пробуем через docker exec...")
                    # Получаем backup_dir из глобальных настроек
                    from modules.base import get_base
                    base = get_base()
                    global_settings = base.get_global_settings()
                    backup_dir = global_settings.get('backup_dir', 'data/backups')
                    backup_path = str(self.project_root / backup_dir)
                    
                    if backup_filename:
                        backup_file_path = os.path.join(backup_path, backup_filename)
                    else:
                        backup_file_path = self._find_latest_backup_file(backup_path, db_type)
                    
                    if not backup_file_path or not os.path.exists(backup_file_path):
                        self.logger.error(f"Файл бэкапа не найден: {backup_file_path}")
                        return False
                    
                    success = self._restore_backup_via_docker_exec(db_config, backup_file_path)
                    if success:
                        return True
                    self.logger.error("Не удалось восстановить бэкап ни напрямую, ни через docker exec")
                    return False
            
            # Для SQLite или для PostgreSQL внутри Docker используем стандартный метод
            if backup_filename:
                self.logger.info(f"Восстановление БД из бэкапа: {backup_filename}")
                success = asyncio.run(database_manager.restore_backup(backup_filename=backup_filename))
            else:
                self.logger.info("Восстановление БД из последнего бэкапа...")
                success = asyncio.run(database_manager.restore_backup())
            
            if success:
                self.logger.info("БД успешно восстановлена из бэкапа")
            return success
            
        except Exception as e:
            self.logger.error(f"Ошибка восстановления БД: {e}")
            return False

