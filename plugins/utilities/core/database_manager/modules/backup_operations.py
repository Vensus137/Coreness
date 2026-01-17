"""
Модуль для операций с бэкапами базы данных
Создание и восстановление бэкапов для SQLite и PostgreSQL
"""

import datetime
import gzip
import os
import shutil
import subprocess
from typing import Optional


class BackupOperations:
    """Класс для операций с бэкапами базы данных"""
    
    def __init__(self, logger, db_config, engine, settings_manager):
        """
        Инициализация операций с бэкапами
        """
        self.logger = logger
        self.db_config = db_config
        self.engine = engine
        self.settings_manager = settings_manager
    
    def _get_backup_dir(self) -> str:
        """Получает директорию бэкапов из глобальных настроек"""
        global_settings = self.settings_manager.get_global_settings()
        return global_settings.get('backup_dir', 'data/backups')
    
    async def create_backup(self, backup_filename: Optional[str] = None) -> Optional[str]:
        """Создает бэкап базы данных в формате plain SQL + gzip для PostgreSQL или .bak.gz для SQLite"""
        try:
            backup_dir = self._get_backup_dir()
            db_type = self.db_config.get('type')
            
            if db_type == 'sqlite':
                return await self._create_sqlite_backup(backup_dir, self.db_config, backup_filename)
            elif db_type == 'postgresql':
                return await self._create_postgresql_backup(backup_dir, self.db_config, backup_filename)
            else:
                self.logger.error(f"Неподдерживаемый тип БД для бэкапа: {db_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа: {e}")
            return None
    
    async def restore_backup(self, backup_filename: Optional[str] = None) -> bool:
        """Восстанавливает базу данных из бэкапа"""
        try:
            backup_dir = self._get_backup_dir()
            db_type = self.db_config.get('type')
            
            # Если имя файла не указано, находим последний бэкап
            if backup_filename is None:
                backup_filename = self._find_latest_backup(backup_dir, db_type)
                if backup_filename is None:
                    self.logger.error("Не найден бэкап для восстановления")
                    return False
            
            backup_path = os.path.join(backup_dir, backup_filename)
            
            if db_type == 'sqlite':
                return await self._restore_sqlite_backup(backup_path, self.db_config)
            elif db_type == 'postgresql':
                return await self._restore_postgresql_backup(backup_path, self.db_config)
            else:
                self.logger.error(f"Неподдерживаемый тип БД для восстановления: {db_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Ошибка восстановления бэкапа: {e}")
            return False
    
    def _find_latest_backup(self, backup_dir: str, db_type: str) -> Optional[str]:
        """Находит последний бэкап в директории для указанного типа БД"""
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
            
            # Находим все файлы бэкапов с нужным расширением
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.endswith(extension):
                    file_path = os.path.join(backup_dir, filename)
                    if os.path.isfile(file_path):
                        backup_files.append((filename, os.path.getmtime(file_path)))
            
            if not backup_files:
                return None
            
            # Сортируем по времени модификации (последний = самый новый)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            return backup_files[0][0]
            
        except Exception as e:
            self.logger.warning(f"Ошибка поиска последнего бэкапа: {e}")
            return None
    
    async def _create_sqlite_backup(self, backup_dir: str, db_config: dict, backup_filename: Optional[str] = None) -> Optional[str]:
        """Создает бэкап SQLite в формате .bak.gz"""
        try:
            db_path = db_config.get('db_path')
            
            if not db_path or not os.path.exists(db_path):
                self.logger.warning(f"Файл БД SQLite не найден: {db_path}")
                return None
            
            # Формируем имя файла бэкапа
            if backup_filename:
                # Если имя указано, добавляем расширение если его нет
                if not backup_filename.endswith('.bak.gz'):
                    backup_filename = f"{backup_filename}.bak.gz"
            else:
                # Генерируем автоматически с timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                db_filename = os.path.basename(db_path) if db_path else "core.db"
                backup_filename = f"{db_filename}_{timestamp}.bak.gz"
            
            backup_path = os.path.join(backup_dir, backup_filename)
            # Создаем директорию если нужно (включая поддиректории из пути в имени файла)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Читаем файл БД и сжимаем его
            with open(db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            self.logger.info(f"Бэкап SQLite создан: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа SQLite: {e}")
            return None
    
    async def _create_postgresql_backup(self, backup_dir: str, db_config: dict, backup_filename: Optional[str] = None) -> Optional[str]:
        """Создает бэкап PostgreSQL в формате plain SQL + gzip"""
        backup_path = None
        try:
            # Получаем параметры подключения из конфигурации
            postgresql_host = db_config.get('host')
            postgresql_port = db_config.get('port')
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Формируем имя файла бэкапа
            if backup_filename:
                # Если имя указано, добавляем расширение если его нет
                if not backup_filename.endswith('.sql.gz'):
                    backup_filename = f"{backup_filename}.sql.gz"
            else:
                # Генерируем автоматически с timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"postgresql_backup_{timestamp}.sql.gz"
            
            backup_path = os.path.join(backup_dir, backup_filename)
            # Создаем директорию если нужно (включая поддиректории из пути в имени файла)
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            
            # Команда для создания дампа
            cmd = [
                'pg_dump',
                '-h', str(postgresql_host),
                '-p', str(postgresql_port),
                '-U', postgresql_username,
                '-d', postgresql_database,
                '--no-password'
            ]
            
            # Устанавливаем пароль через переменную окружения
            env = os.environ.copy()
            if postgresql_password:
                env['PGPASSWORD'] = postgresql_password
            
            # Запускаем pg_dump и сжимаем вывод через gzip
            process = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False  # Работаем с бинарными данными для gzip
            )
            
            # Сжимаем вывод и сохраняем в файл
            with gzip.open(backup_path, 'wb') as f_out:
                while True:
                    chunk = process.stdout.read(8192)
                    if not chunk:
                        break
                    f_out.write(chunk)
            
            # Ждем завершения процесса
            process.wait()
            
            if process.returncode == 0:
                self.logger.info(f"Бэкап PostgreSQL создан: {backup_path}")
                return backup_path
            else:
                error_msg = process.stderr.read().decode('utf-8') if process.stderr else "Неизвестная ошибка"
                self.logger.error(f"Ошибка создания бэкапа PostgreSQL: {error_msg}")
                # Удаляем частично созданный файл при ошибке
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return None
                
        except FileNotFoundError:
            self.logger.error("pg_dump не найден, создание бэкапа PostgreSQL невозможно")
            return None
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа PostgreSQL: {e}")
            # Удаляем частично созданный файл при ошибке
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
            return None
    
    async def _restore_sqlite_backup(self, backup_path: str, db_config: dict) -> bool:
        """Восстанавливает SQLite из бэкапа"""
        try:
            # Проверяем существование файла бэкапа
            if not os.path.exists(backup_path):
                self.logger.error(f"Файл бэкапа не найден: {backup_path}")
                return False
            
            db_path = db_config.get('db_path')
            if not db_path:
                self.logger.error("Путь к файлу БД SQLite не определен")
                return False
            
            # Закрываем все соединения с БД перед восстановлением
            try:
                self.engine.dispose()
            except Exception as e:
                self.logger.warning(f"Ошибка при закрытии соединений: {e}")
            
            # Создаем директорию для БД, если её нет
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Удаляем существующий файл БД, если он есть
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    # Если файл заблокирован, пробуем еще раз после небольшой задержки
                    import time
                    time.sleep(0.1)
                    os.remove(db_path)
            
            # Распаковываем и копируем файл
            if backup_path.endswith('.gz'):
                # Распаковываем gzip
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(db_path, 'wb') as f_out:
                        f_out.writelines(f_in)
            else:
                # Просто копируем файл
                shutil.copy2(backup_path, db_path)
            
            self.logger.info(f"БД SQLite восстановлена из {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка восстановления бэкапа SQLite: {e}")
            return False
    
    async def _restore_postgresql_backup(self, backup_path: str, db_config: dict) -> bool:
        """Восстанавливает PostgreSQL из бэкапа"""
        try:
            # Проверяем существование файла бэкапа
            if not os.path.exists(backup_path):
                self.logger.error(f"Файл бэкапа не найден: {backup_path}")
                return False
            
            # Получаем параметры подключения из конфигурации
            postgresql_host = db_config.get('host')
            postgresql_port = db_config.get('port')
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Сначала очищаем БД для чистого восстановления
            if not await self._clear_postgresql_database(db_config):
                self.logger.warning("Не удалось очистить БД перед восстановлением, продолжаем...")
            
            # Команда для восстановления
            cmd = [
                'psql',
                '-h', str(postgresql_host),
                '-p', str(postgresql_port),
                '-U', postgresql_username,
                '-d', postgresql_database,
                '--quiet',
                '--no-password'
            ]
            
            # Устанавливаем пароль через переменную окружения
            env = os.environ.copy()
            if postgresql_password:
                env['PGPASSWORD'] = postgresql_password
            
            # Распаковываем gzip если нужно и передаем в psql
            if backup_path.endswith('.gz'):
                # Распаковываем и передаем в psql
                with gzip.open(backup_path, 'rb') as f_in:
                    process = subprocess.Popen(
                        cmd,
                        env=env,
                        stdin=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=False
                    )
                    process.stdin.write(f_in.read())
                    process.stdin.close()
                    process.wait()
            else:
                # Передаем файл напрямую
                with open(backup_path, 'rb') as f_in:
                    process = subprocess.Popen(
                        cmd,
                        env=env,
                        stdin=f_in,
                        stderr=subprocess.PIPE,
                        text=False
                    )
                    process.wait()
            
            if process.returncode == 0:
                self.logger.info(f"БД PostgreSQL восстановлена из {backup_path}")
                return True
            else:
                error_msg = process.stderr.read().decode('utf-8') if process.stderr else "Неизвестная ошибка"
                self.logger.error(f"Ошибка восстановления PostgreSQL: {error_msg}")
                return False
                
        except FileNotFoundError:
            self.logger.error("psql не найден, восстановление PostgreSQL невозможно")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка восстановления бэкапа PostgreSQL: {e}")
            return False
    
    async def _clear_postgresql_database(self, db_config: dict) -> bool:
        """Очищает PostgreSQL базу данных перед восстановлением"""
        try:
            postgresql_host = db_config.get('host')
            postgresql_port = db_config.get('port')
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Команда для очистки БД
            cmd = [
                'psql',
                '-h', str(postgresql_host),
                '-p', str(postgresql_port),
                '-U', postgresql_username,
                '-d', postgresql_database,
                '--no-password',
                '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
            ]
            
            # Устанавливаем пароль через переменную окружения
            env = os.environ.copy()
            if postgresql_password:
                env['PGPASSWORD'] = postgresql_password
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return result.returncode == 0
                
        except FileNotFoundError:
            self.logger.warning("psql не найден, очистка БД пропущена")
            return False
        except Exception as e:
            self.logger.warning(f"Ошибка очистки БД: {e}")
            return False

