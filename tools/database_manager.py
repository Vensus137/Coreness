import os
import sys

# Добавляем корневую директорию проекта в путь
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

# Переходим в корневую директорию проекта для корректной работы DI-контейнера
os.chdir(project_root)

# Загружаем переменные окружения из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv не установлен. Переменные окружения могут быть не загружены.")

import argparse

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

# Импорты для работы с DI-контейнером
from app.di_container import DIContainer
from plugins.utilities.foundation.logger.logger import Logger
from plugins.utilities.foundation.plugins_manager.plugins_manager import \
    PluginsManager


def get_table_class_map(db_service):
    """Получает карту таблиц из database_service."""
    return db_service.get_table_class_map()

def get_table_class(table_name, db_service):
    """Получает класс модели по имени таблицы."""
    table_class_map = get_table_class_map(db_service)
    cls = table_class_map.get(table_name)
    if not cls:
        print(f"Неизвестная таблица: {table_name}. Доступные: {list(table_class_map.keys())}")
        sys.exit(1)
    return cls

def recreate_table(db_service, table_class):
    engine = db_service.engine
    table = table_class.__table__
    print(f"Удаляю таблицу {table.name}...")
    table.drop(engine, checkfirst=True)
    print(f"Создаю таблицу {table.name}...")
    table.create(engine, checkfirst=True)
    print(f"Таблица {table.name} успешно пересоздана.")

def recreate_indexes(db_service, table_class):
    engine = db_service.engine
    table = table_class.__table__
    inspector = inspect(engine)
    # Получаем существующие индексы
    existing_indexes = {idx['name'] for idx in inspector.get_indexes(table.name)}
    # Индексы, определённые в модели
    model_indexes = [idx for idx in table.indexes]
    # Удаляем существующие индексы
    with engine.connect() as conn:
        for idx in existing_indexes:
            if idx == 'sqlite_autoindex_' + table.name + '_1':
                continue  # Не трогаем PK
            try:
                print(f"Удаляю индекс {idx}...")
                conn.execute(text(f'DROP INDEX IF EXISTS "{idx}"'))
            except OperationalError as e:
                print(f"Ошибка при удалении индекса {idx}: {e}")
        # Создаём индексы из модели
        for idx in model_indexes:
            print(f"Создаю индекс {idx.name}...")
            try:
                idx.create(conn, checkfirst=True)
            except Exception as e:
                print(f"Ошибка при создании индекса {idx.name}: {e}")
    print(f"Индексы для таблицы {table.name} успешно пересозданы.")

def drop_table(db_service, table_name):
    """Удаляет таблицу по имени."""
    engine = db_service.engine
    inspector = inspect(engine)
    
    if table_name not in inspector.get_table_names():
        print(f"Таблица {table_name} не найдена.")
        return False
    
    try:
        with engine.connect() as conn:
            print(f"Удаляю таблицу {table_name}...")
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
            conn.commit()
        print(f"Таблица {table_name} успешно удалена.")
        return True
    except Exception as e:
        print(f"Ошибка при удалении таблицы {table_name}: {e}")
        return False

def backup_database(db_path):
    import shutil
    backup_path = db_path + ".bak"
    shutil.copy2(db_path, backup_path)
    return backup_path

def restore_database(backup_path, db_path):
    import shutil
    shutil.copy2(backup_path, db_path)

def get_db_columns(engine, table_name):
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return {col['name']: col['type'] for col in columns}

def get_model_columns(table_class):
    return {col.name: col.type for col in table_class.__table__.columns}

def can_drop_column(engine):
    # SQLite >= 3.35 поддерживает DROP COLUMN
    with engine.connect() as conn:
        version = conn.execute(text('select sqlite_version()')).scalar()
    major, minor, *_ = map(int, version.split('.'))
    return (major, minor) >= (3, 35)

def recreate_table_with_data(db_service, table_class, logger):
    engine = db_service.engine
    table = table_class.__table__
    tmp_table_name = table.name + "_tmp"
    # Создаём временную таблицу
    tmp_table = table.tometadata(table.metadata, name=tmp_table_name)
    tmp_table.create(engine, checkfirst=True)
    # Переносим данные с преобразованием типов
    inspector = inspect(engine)
    old_columns = inspector.get_columns(table.name)
    new_columns = [c.name for c in tmp_table.columns]
    common_columns = [c for c in new_columns if c in [col['name'] for col in old_columns]]
    select_cols = ', '.join(common_columns)
    insert_cols = ', '.join(common_columns)
    try:
        with engine.begin() as conn:
            rows = conn.execute(text(f'SELECT {select_cols} FROM {table.name}')).fetchall()
            for row in rows:
                values = []
                for i, col in enumerate(common_columns):
                    try:
                        values.append(row[i])
                    except Exception as e:
                        logger.warning(f"Ошибка преобразования значения {col}: {e}")
                        values.append(None)
                placeholders = ', '.join([':{}'.format(c) for c in common_columns])
                conn.execute(text(f'INSERT INTO {tmp_table_name} ({insert_cols}) VALUES ({placeholders})'), dict(zip(common_columns, values)))
            conn.execute(text(f'DROP TABLE {table.name}'))
            conn.execute(text(f'ALTER TABLE {tmp_table_name} RENAME TO {table.name}'))
    except Exception as e:
        logger.error(f"Ошибка при перезаливке таблицы {table.name}: {e}")
        raise

def migrate_database(db_service, logger, db_path):
    engine = db_service.engine
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    backup_path = backup_database(db_path)
    table_class_map = get_table_class_map(db_service)
    try:
        for table_name, table_class in table_class_map.items():
            logger.info(f"\n=== Миграция таблицы {table_name} ===")
            if table_name not in existing_tables:
                logger.info(f"Таблица {table_name} не найдена, создаю...")
                table_class.__table__.create(engine, checkfirst=True)
                continue
            db_cols = get_db_columns(engine, table_name)
            model_cols = get_model_columns(table_class)
            need_recreate = False
            # Проверка совпадения колонок и типов
            if db_cols == model_cols:
                logger.info(f"Структура таблицы {table_name} совпадает, миграция не требуется.")
                # Пересоздаём индексы даже если миграция не требуется
                recreate_indexes(db_service, table_class)
                continue
            # Добавление недостающих колонок
            with engine.connect() as conn:
                for col, col_type in model_cols.items():
                    if col not in db_cols:
                        logger.info(f"Добавляю колонку {col} в {table_name}")
                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type}'))
                # Удаление лишних колонок
                for col in db_cols:
                    if col not in model_cols:
                        if can_drop_column(engine):
                            logger.info(f"Удаляю колонку {col} из {table_name}")
                            conn.execute(text(f'ALTER TABLE {table_name} DROP COLUMN {col}'))
                        else:
                            logger.info(f"SQLite не поддерживает DROP COLUMN, требуется перезаливка таблицы {table_name}")
                            need_recreate = True
            # Несовпадение типов
            for col in model_cols:
                if col in db_cols and str(db_cols[col]) != str(model_cols[col]):
                    logger.info(f"Несовпадение типа колонки {col} ({db_cols[col]} -> {model_cols[col]}), требуется перезаливка")
                    need_recreate = True
            if need_recreate:
                recreate_table_with_data(db_service, table_class, logger)
            # Пересоздаём индексы
            recreate_indexes(db_service, table_class)
    except Exception as e:
        logger.error(f"Ошибка миграции: {e}. Восстанавливаю базу из бэкапа...")
        restore_database(backup_path, db_path)
        raise
    logger.info("\nМиграция завершена успешно!")
    # --- Удаляем .bak после успешной миграции ---
    if os.path.exists(backup_path):
        try:
            os.remove(backup_path)
            logger.info(f"Удалён бэкап базы: {backup_path}")
        except Exception as e:
            logger.warning(f"Не удалось удалить бэкап базы {backup_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Менеджер базы данных: пересоздание таблиц, индексов, миграции")
    group_target = parser.add_mutually_exclusive_group(required=True)
    group_target.add_argument('table', nargs='?', help="Имя таблицы (actions, users) или имя таблицы для удаления")
    group_target.add_argument('--all', action='store_true', help="Применить ко всем таблицам")
    group_mode = parser.add_mutually_exclusive_group(required=True)
    group_mode.add_argument('--recreate-tables', action='store_true', help="Пересоздать таблицу (drop/create)")
    group_mode.add_argument('--recreate-indexes', action='store_true', help="Пересоздать только индексы")
    group_mode.add_argument('--migrate', action='store_true', help="Миграция схемы и данных (умная)")
    group_mode.add_argument('--drop-table', action='store_true', help="Удалить таблицу по имени")
    args = parser.parse_args()

    # Инициализация DI-контейнера
    logger = Logger()
    plugins_manager = PluginsManager(logger=logger)
    di_container = DIContainer(logger=logger, plugins_manager=plugins_manager)
    
    try:
        # Инициализация всех плагинов через DI-контейнер
        di_container.initialize_all_plugins()
        
        # Получение необходимых утилит и сервисов
        db_service = di_container.get_utility("database_service")
        if not db_service:
            print("❌ Ошибка: не удалось получить database_service из DI-контейнера")
            sys.exit(1)
        
        # Получение пути к базе данных
        db_path = db_service.engine.url.database
        db_dir = os.path.dirname(db_path)
        
        # Создаем директорию для базы данных, если её нет
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"📁 Создана директория для базы данных: {db_dir}")
        
        # Проверяем существование базы данных
        db_exists = os.path.exists(db_path)
        if not db_exists:
            print(f"🗄 База данных не найдена: {db_path}")
            print("🔄 Создаю новую базу данных...")
            
            # Создаем все таблицы в новой базе
            table_class_map = get_table_class_map(db_service)
            for table_name, table_class in table_class_map.items():
                print(f"📋 Создаю таблицу: {table_name}")
                table_class.__table__.create(db_service.engine, checkfirst=True)
            
            print("✅ База данных создана успешно!")
            
            # Если это миграция, то база уже создана и готова
            if args.migrate:
                print("✅ Миграция завершена (создана новая база данных)")
                return
        else:
            print(f"🗄 База данных найдена: {db_path}")

        if args.drop_table:
            if not args.table:
                print("❌ Для удаления таблицы необходимо указать имя таблицы")
                sys.exit(1)
            drop_table(db_service, args.table)
            return

        if args.migrate:
            migrate_database(db_service, logger, db_path)
            return

        if args.all:
            table_class_map = get_table_class_map(db_service)
            table_classes = list(table_class_map.values())
        else:
            table_classes = [get_table_class(args.table, db_service)]

        for table_class in table_classes:
            if args.recreate_tables:
                recreate_table(db_service, table_class)
            elif args.recreate_indexes:
                recreate_indexes(db_service, table_class)
            else:
                print("Не выбран режим работы.")
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        sys.exit(1)
    finally:
        # Корректное завершение DI-контейнера
        di_container.shutdown()

if __name__ == '__main__':
    main()
