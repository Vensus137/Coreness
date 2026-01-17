#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт миграции данных из SQLite в PostgreSQL
Переносит все данные из data/core.db в PostgreSQL базу данных
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, insert, text
from sqlalchemy.orm import sessionmaker

# Добавляем корень проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Настраиваем кодировку
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Импорты из проекта (после добавления project_root в sys.path)
from app.di_container import DIContainer  # noqa: E402
from plugins.utilities.core.database_manager.models import Base  # noqa: E402
from plugins.utilities.foundation.logger.logger import Logger  # noqa: E402
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager  # noqa: E402
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager  # noqa: E402


# Цвета для вывода
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Порядок миграции таблиц (с учетом FK зависимостей)
MIGRATION_ORDER = [
    'tenant',              # Нет зависимостей
    'id_sequence',         # Нет зависимостей
    'tenant_storage',      # → tenant
    'user_storage',        # → tenant
    'tenant_user',         # → tenant
    'bot',                 # → tenant
    'bot_command',         # → bot
    'scenario',            # → tenant
    'scenario_trigger',    # → scenario
    'scenario_step',       # → scenario
    'scenario_step_transition',  # → scenario_step
    'invoice',             # → tenant
]

# Размер батча для вставки данных
BATCH_SIZE = 1000


class SQLiteToPostgreSQLMigrator:
    """Класс для миграции данных из SQLite в PostgreSQL"""
    
    def __init__(self):
        """Инициализация мигратора"""
        self.logger = Logger()
        self.log = self.logger.get_logger("migration")
        
        # Инициализируем DI-контейнер для PostgreSQL
        self._init_di_container()
        
        # Подключаемся к базам данных
        self._connect_to_sqlite()
        self._connect_to_postgresql()
        
        # Получаем карту таблиц
        self.table_class_map = self.db_service.get_table_class_map()
    
    def _init_di_container(self):
        """Инициализирует DI-контейнер для доступа к PostgreSQL"""
        self.log.info("Инициализация DI-контейнера...")
        
        plugins_manager = PluginsManager(logger=self.logger)
        settings_manager = SettingsManager(logger=self.logger, plugins_manager=plugins_manager)
        
        # Проверяем, запущены ли мы в Docker
        is_inside_docker = os.path.exists('/.dockerenv')
        
        if is_inside_docker:
            # В Docker - используем настройки из конфига как есть (host будет именем сервиса)
            postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
            postgres_port = os.getenv('POSTGRES_PORT', '5432')
        else:
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
        
        # Переопределяем настройки в settings_manager перед созданием DI-контейнера
        original_get_plugin_settings = settings_manager.get_plugin_settings
        
        def patched_get_plugin_settings(self_ref, plugin_name: str):
            settings = original_get_plugin_settings(plugin_name)
            if plugin_name == 'database_manager':
                settings = settings.copy()
                if 'database' not in settings:
                    settings['database'] = {}
                if 'postgresql' not in settings['database']:
                    settings['database']['postgresql'] = {}
                # Переопределяем настройки подключения
                settings['database']['postgresql']['host'] = postgres_host
                settings['database']['postgresql']['port'] = int(postgres_port)
                settings['database']['postgresql']['username'] = postgres_user
                if postgres_password:
                    settings['database']['postgresql']['password'] = postgres_password
                settings['database']['postgresql']['database'] = postgres_db
            return settings
        
        # Временно патчим метод для переопределения настроек
        import types
        settings_manager.get_plugin_settings = types.MethodType(patched_get_plugin_settings, settings_manager)
        
        # Логируем применяемые настройки (только на хосте)
        if not is_inside_docker:
            self.log.info(f"Настройки PostgreSQL переопределены для хоста: {postgres_host}:{postgres_port}")
        
        self.di_container = DIContainer(
            logger=self.logger,
            plugins_manager=plugins_manager,
            settings_manager=settings_manager
        )
        
        # Получаем database_manager
        self.db_service = self.di_container.get_utility_on_demand("database_manager")
        if not self.db_service:
            raise RuntimeError("Не удалось получить database_manager из DI-контейнера")
        
        self.log.info(f"DI-контейнер инициализирован (PostgreSQL: {postgres_host}:{postgres_port}/{postgres_db})")
    
    def _connect_to_sqlite(self):
        """Подключается к SQLite базе данных"""
        sqlite_path = project_root / "data" / "core.db"
        
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite база данных не найдена: {sqlite_path}")
        
        sqlite_url = f"sqlite:///{sqlite_path}"
        self.sqlite_engine = create_engine(sqlite_url, echo=False)
        self.sqlite_session_factory = sessionmaker(bind=self.sqlite_engine)
        
        self.log.info(f"Подключено к SQLite: {sqlite_path}")
    
    def _connect_to_postgresql(self):
        """Подключается к PostgreSQL базе данных"""
        # Проверяем, что текущая БД - PostgreSQL
        db_info = self.db_service.get_database_info()
        if db_info.get('type') != 'postgresql':
            raise RuntimeError(f"Текущая БД не PostgreSQL, а {db_info.get('type')}")
        
        self.pg_engine = self.db_service.engine
        self.pg_session_factory = self.db_service.session_factory
        
        self.log.info(f"Подключено к PostgreSQL: {db_info.get('url')}")
    
    def _clear_postgresql_database(self):
        """Очищает PostgreSQL базу данных"""
        self.print_info("Очищаю целевую БД (PostgreSQL)...")
        
        try:
            with self.pg_engine.begin() as conn:
                # Удаляем все объекты в схеме public
                conn.execute(text('DROP SCHEMA public CASCADE'))
                conn.execute(text('CREATE SCHEMA public'))
                conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
                conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
            
            self.print_success("Целевая БД очищена")
        except Exception as e:
            self.print_error(f"Ошибка очистки БД: {e}")
            raise
    
    def _create_postgresql_schema(self):
        """Создает схему в PostgreSQL"""
        self.print_info("Создаю схему в PostgreSQL...")
        
        try:
            Base.metadata.create_all(self.pg_engine)
            self.print_success("Схема создана")
        except Exception as e:
            self.print_error(f"Ошибка создания схемы: {e}")
            raise
    
    def _get_table_count(self, table_name: str, engine) -> int:
        """Получает количество записей в таблице"""
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar() or 0
    
    def _get_existing_parent_ids(self, parent_table_name: str) -> set:
        """Получает множество существующих ID из родительской таблицы в PostgreSQL"""
        try:
            with self.pg_engine.connect() as conn:
                result = conn.execute(text(f"SELECT id FROM {parent_table_name}"))
                return {row[0] for row in result}
        except Exception as e:
            self.logger.warning(f"Ошибка получения ID из {parent_table_name}: {e}")
            return set()
    
    def _get_foreign_key_relations(self, table_class) -> list:
        """Получает список FK связей для таблицы: [(column_name, referenced_table_name, referenced_column_name)]"""
        fk_relations = []
        for column in table_class.__table__.columns:
            for fk in column.foreign_keys:
                # fk.column.table.name - имя таблицы, на которую ссылается FK
                # fk.column.name - имя колонки в родительской таблице
                fk_relations.append((column.name, fk.column.table.name, fk.column.name))
        return fk_relations
    
    def _migrate_table(self, table_name: str) -> bool:
        """Мигрирует данные одной таблицы"""
        if table_name not in self.table_class_map:
            self.print_warning(f"Таблица {table_name} не найдена в моделях, пропускаю")
            return True
        
        table_class = self.table_class_map[table_name]
        
        # Получаем количество записей
        source_count = self._get_table_count(table_name, self.sqlite_engine)
        
        if source_count == 0:
            self.print_info(f"Таблица {table_name} пуста, пропускаю")
            return True
        
        self.print_info(f"Мигрирую таблицу {table_name} ({source_count} записей)...")
        
        try:
            # Получаем все записи из SQLite
            with self.sqlite_session_factory() as sqlite_session:
                records = sqlite_session.query(table_class).all()
            
            if not records:
                return True
            
            # Проверяем FK связи и получаем существующие ID родительских таблиц
            fk_relations = self._get_foreign_key_relations(table_class)
            parent_ids_map = {}
            for fk_column, parent_table, _parent_column in fk_relations:
                parent_ids_map[fk_column] = self._get_existing_parent_ids(parent_table)
                if not parent_ids_map[fk_column]:
                    self.print_warning(f"  Родительская таблица {parent_table} пуста, все записи будут пропущены")
            
            # Фильтруем записи по FK - оставляем только те, у которых есть родительские записи
            filtered_records = []
            skipped_count = 0
            for record in records:
                skip = False
                for fk_column, _parent_table, _parent_column in fk_relations:
                    fk_value = getattr(record, fk_column)
                    if fk_value is not None and fk_value not in parent_ids_map[fk_column]:
                        skip = True
                        skipped_count += 1
                        break
                if not skip:
                    filtered_records.append(record)
            
            if skipped_count > 0:
                self.print_warning(f"  Пропущено {skipped_count} записей из-за отсутствия родительских записей")
            
            if not filtered_records:
                self.print_warning(f"  Нет записей для миграции после фильтрации")
                return True
            
            # Вставляем батчами в PostgreSQL
            with self.pg_session_factory() as pg_session:
                inserted = 0
                for i in range(0, len(filtered_records), BATCH_SIZE):
                    batch = filtered_records[i:i + BATCH_SIZE]
                    
                    # Конвертируем записи в словари для вставки
                    batch_data = []
                    for record in batch:
                        record_dict = {}
                        for column in table_class.__table__.columns:
                            value = getattr(record, column.name)
                            # Значения уже из БД, просто передаем как есть
                            record_dict[column.name] = value
                        batch_data.append(record_dict)
                    
                    # Вставляем батч используя insert()
                    if batch_data:
                        pg_session.execute(insert(table_class), batch_data)
                        pg_session.commit()
                    
                    inserted += len(batch)
                    progress = (inserted / len(filtered_records)) * 100
                    self.print_info(f"  Прогресс: {progress:.1f}% ({inserted}/{len(filtered_records)})", end='\r')
                
                self.print_info("")  # Новая строка после прогресса
            
            # Проверяем количество записей в целевой БД
            target_count = self._get_table_count(table_name, self.pg_engine)
            
            if skipped_count > 0:
                expected_count = source_count - skipped_count
                if target_count == expected_count:
                    self.print_success(f"Таблица {table_name} мигрирована: {target_count} записей (пропущено {skipped_count})")
                    return True
                else:
                    self.print_warning(f"Несовпадение количества записей в {table_name}: ожидалось {expected_count}, получено {target_count}")
                    return False
            else:
                if target_count == source_count:
                    self.print_success(f"Таблица {table_name} мигрирована: {target_count} записей")
                    return True
                else:
                    self.print_warning(f"Несовпадение количества записей в {table_name}: {source_count} → {target_count}")
                    return False
                
        except Exception as e:
            self.print_error(f"Ошибка миграции таблицы {table_name}: {e}")
            raise
    
    def _sync_sequences(self):
        """Синхронизирует sequences в PostgreSQL"""
        self.print_info("Синхронизирую sequences...")
        
        try:
            with self.pg_engine.begin() as conn:
                # Получаем все таблицы с автоинкрементом
                for table_name, table_class in self.table_class_map.items():
                    # Проверяем, есть ли автоинкрементное поле id
                    if hasattr(table_class, 'id'):
                        id_column = table_class.id
                        if hasattr(id_column, 'property') and hasattr(id_column.property, 'columns'):
                            # Получаем максимальный ID
                            result = conn.execute(text(f"SELECT MAX(id) FROM {table_name}"))
                            max_id = result.scalar() or 0
                            
                            if max_id > 0:
                                sequence_name = f"{table_name}_id_seq"
                                # Синхронизируем sequence с максимальным ID
                                conn.execute(text(f"SELECT setval('{sequence_name}', {max_id})"))
                                self.print_success(f"Sequence {sequence_name} установлен на {max_id}")
            
            return True
            
        except Exception as e:
            self.print_error(f"Ошибка синхронизации sequences: {e}")
            return False
    
    def _validate_migration(self) -> bool:
        """Валидирует миграцию - сравнивает количество записей"""
        self.print_info("Валидирую миграцию...")
        
        all_ok = True
        for table_name in MIGRATION_ORDER:
            if table_name not in self.table_class_map:
                continue
            
            source_count = self._get_table_count(table_name, self.sqlite_engine)
            target_count = self._get_table_count(table_name, self.pg_engine)
            
            if source_count == target_count:
                self.print_success(f"  {table_name}: {source_count} записей ✓")
            else:
                self.print_error(f"  {table_name}: {source_count} → {target_count} ✗")
                all_ok = False
        
        return all_ok
    
    def migrate(self, clear_target: bool = True) -> bool:
        """Выполняет полную миграцию данных"""
        try:
            self.print_separator("МИГРАЦИЯ ДАННЫХ SQLite → PostgreSQL")
            
            # 1. Очистка целевой БД
            if clear_target:
                self._clear_postgresql_database()
            
            # 2. Создание схемы
            self._create_postgresql_schema()
            
            # 3. Миграция данных по порядку
            self.print_separator("МИГРАЦИЯ ДАННЫХ")
            for table_name in MIGRATION_ORDER:
                if not self._migrate_table(table_name):
                    self.print_error(f"Ошибка миграции таблицы {table_name}")
                    return False
            
            # 4. Синхронизация sequences
            self.print_separator("СИНХРОНИЗАЦИЯ SEQUENCES")
            self._sync_sequences()
            
            # 5. Валидация
            self.print_separator("ВАЛИДАЦИЯ")
            if not self._validate_migration():
                self.print_warning("Валидация показала несовпадения, но миграция завершена")
            
            self.print_separator("МИГРАЦИЯ ЗАВЕРШЕНА")
            self.print_success("✅ Миграция данных завершена успешно!")
            
            return True
            
        except Exception as e:
            self.print_error(f"❌ Ошибка миграции: {e}")
            raise
    
    def print_info(self, message: str, end: str = '\n'):
        """Выводит информационное сообщение"""
        print(f"{Colors.CYAN}ℹ️ {message}{Colors.END}", end=end)
    
    def print_success(self, message: str):
        """Выводит сообщение об успехе"""
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    
    def print_warning(self, message: str):
        """Выводит предупреждение"""
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.END}")
    
    def print_error(self, message: str):
        """Выводит ошибку"""
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    
    def print_separator(self, title: str = None):
        """Выводит разделитель"""
        if title:
            print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
            print(f"{Colors.BOLD}{title:^60}{Colors.END}")
            print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        else:
            print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")
    
    def cleanup(self):
        """Очищает ресурсы"""
        if hasattr(self, 'sqlite_engine'):
            self.sqlite_engine.dispose()
        if hasattr(self, 'di_container'):
            try:
                self.di_container.shutdown()
            except Exception:
                pass


def main():
    """Главная функция"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{'МИГРАЦИЯ SQLite → PostgreSQL':^60}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    # Подтверждение
    print(f"{Colors.YELLOW}⚠️ ВНИМАНИЕ:{Colors.END}")
    print(f"{Colors.CYAN}Этот скрипт:{Colors.END}")
    print(f"  1. Очистит целевую БД (PostgreSQL)")
    print(f"  2. Перенесет все данные из SQLite (data/core.db) в PostgreSQL")
    print(f"  3. Синхронизирует sequences")
    print()
    
    confirm = input(f"{Colors.YELLOW}Продолжить? (y/N): {Colors.END}").strip().lower()
    if confirm != 'y':
        print(f"{Colors.CYAN}Миграция отменена{Colors.END}")
        return
    
    migrator = None
    try:
        migrator = SQLiteToPostgreSQLMigrator()
        migrator.migrate(clear_target=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Миграция прервана пользователем{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Критическая ошибка: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
    finally:
        if migrator:
            migrator.cleanup()


if __name__ == '__main__':
    main()

