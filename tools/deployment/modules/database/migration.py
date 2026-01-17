"""
Основной модуль для универсальной миграции БД
Координирует все модули для выполнения миграции
"""

from pathlib import Path
from typing import Optional

from sqlalchemy import inspect

from .connection import DatabaseConnection
from .index_operations import IndexOperations
from .json_validator import JSONValidator
from .metadata import TableMetadataCache
from .sequence_sync import SequenceSync
from .table_operations import TableOperations


class UniversalMigration:
    """Класс для выполнения универсальной миграции БД"""
    
    def __init__(self, db_connection: DatabaseConnection, logger, formatter):
        """
        Инициализация универсальной миграции
        """
        self.db_connection = db_connection
        self.logger = logger
        self.formatter = formatter
        
        # Инициализируем все модули
        self.metadata_cache = TableMetadataCache(
            db_connection.db_service,
            logger,
            formatter
        )
        
        # Получаем конфигурацию БД один раз
        db_config = db_connection.get_database_config()
        db_type = db_config.get('type')
        
        self.table_ops = TableOperations(
            db_connection.db_service,
            db_connection.engine,
            db_type,
            self.metadata_cache,
            logger,
            formatter
        )
        
        self.index_ops = IndexOperations(
            db_connection.engine,
            db_type,
            logger,
            formatter
        )
        
        self.json_validator = JSONValidator(
            db_connection.db_service,
            self.metadata_cache,
            logger,
            formatter
        )
        
        self.sequence_sync = SequenceSync(
            db_connection.db_service,
            db_connection.engine,
            db_type,
            self.metadata_cache,
            logger,
            formatter
        )
        
        # Сохраняем db_type для использования в методах
        self._db_type = db_type
    
    def migrate_database(self, target_table: Optional[str] = None, backup_path: Optional[str] = None) -> bool:
        """
        Выполняет миграцию базы данных
        """
        try:
            engine = self.db_connection.engine
            inspector = inspect(engine)
            existing_tables = set(self.metadata_cache.get_existing_tables())
            # Бэкап создается на уровне выше (в migration_manager) перед вызовом миграции
            table_class_map = self.metadata_cache.get_table_class_map()
            
            # Для PostgreSQL: удаляем все view перед миграцией, чтобы избежать проблем с зависимостями
            if self._db_type == 'postgresql':
                try:
                    db_service = self.db_connection.db_service
                    self.formatter.print_info("Удаление view перед миграцией...")
                    db_service.drop_all_views()
                    self.formatter.print_success("View удалены")
                except Exception as e:
                    self.formatter.print_warning(f"Не удалось удалить view перед миграцией: {e}")
                    # Продолжаем миграцию, возможно view не существуют
            
            # Определяем какие таблицы мигрировать
            if target_table:
                if target_table not in table_class_map:
                    self.formatter.print_error(f"Неизвестная таблица: {target_table}. Доступные: {list(table_class_map.keys())}")
                    return False
                tables_to_migrate = {target_table: table_class_map[target_table]}
            else:
                tables_to_migrate = table_class_map
            
            # Для SQLite исключаем таблицу vector_storage (она только для PostgreSQL с pgvector)
            if self._db_type == 'sqlite':
                tables_to_migrate = {
                    name: cls for name, cls in tables_to_migrate.items()
                    if name != 'vector_storage'
                }
                if 'vector_storage' in table_class_map:
                    self.formatter.print_info("Таблица vector_storage пропущена (только для PostgreSQL)")
            
            for table_name, table_class in tables_to_migrate.items():
                self.formatter.print_section(f"Миграция таблицы {table_name}")
                
                if table_name not in existing_tables:
                    self.formatter.print_info(f"Таблица {table_name} не найдена, создаю...")
                    try:
                        # Создаем таблицу
                        if not self.table_ops.create_table(table_class):
                            raise Exception(f"Не удалось создать таблицу {table_name}")
                        
                        # Индексы уже созданы вместе с таблицей
                        self.formatter.print_success(f"Индексы для {table_name} созданы автоматически")
                        continue
                        
                    except Exception as e:
                        self.formatter.print_error(f"Ошибка создания таблицы {table_name}: {e}")
                        raise
                else:
                    self.formatter.print_success(f"Таблица {table_name} существует")
                
                db_cols = self.metadata_cache.get_db_columns(table_name)
                model_cols = self.metadata_cache.get_model_columns(table_class)
                need_recreate = False
                
                # Проверка совпадения колонок и типов
                if db_cols == model_cols:
                    self.formatter.print_success(f"Структура таблицы {table_name} совпадает с моделью")
                    self.formatter.print_success("Добавление/удаление колонок не требуется")
                    # Пересоздаём индексы даже если миграция не требуется
                    self.index_ops.recreate_indexes(table_class)
                    continue
                
                # Добавление недостающих колонок
                with engine.connect() as conn:
                    from sqlalchemy import text
                    
                    cols_to_add = [col for col in model_cols if col not in db_cols]
                    cols_to_remove = [col for col in db_cols if col not in model_cols]
                    
                    if not cols_to_add and not cols_to_remove:
                        self.formatter.print_success("Все колонки присутствуют, добавление/удаление не требуется")
                    else:
                        if cols_to_add:
                            self.formatter.print_info(f"Найдено {len(cols_to_add)} колонок для добавления")
                        if cols_to_remove:
                            self.formatter.print_info(f"Найдено {len(cols_to_remove)} колонок для удаления")
                    
                    for col, col_info in model_cols.items():
                        if col not in db_cols:
                            self.formatter.print_info(f"Добавляю колонку {col} в {table_name}")
                            col_type = col_info.get('type') if isinstance(col_info, dict) else col_info
                            nullable = col_info.get('nullable', True) if isinstance(col_info, dict) else True
                            
                            # Получаем информацию о колонке из модели для определения дефолта
                            column_obj = getattr(table_class, col, None)
                            has_default = False
                            default_value = None
                            
                            if column_obj:
                                # Проверяем, есть ли дефолт в модели
                                if hasattr(column_obj, 'default') and column_obj.default is not None:
                                    if hasattr(column_obj.default, 'arg'):
                                        # Для callable дефолтов (например, dtf_now_local)
                                        if callable(column_obj.default.arg):
                                            # Для TIMESTAMP/DATETIME используем CURRENT_TIMESTAMP
                                            col_type_str = str(col_type).upper()
                                            if 'TIMESTAMP' in col_type_str or 'DATETIME' in col_type_str:
                                                has_default = True
                                                default_value = "CURRENT_TIMESTAMP"
                                        else:
                                            # Для обычных дефолтов
                                            has_default = True
                                            default_value = column_obj.default.arg
                                    else:
                                        has_default = True
                                        default_value = column_obj.default
                            
                            # Проверяем, есть ли данные в таблице
                            row_count_result = conn.execute(text(f'SELECT COUNT(*) FROM {table_name}'))
                            row_count = row_count_result.scalar()
                            
                            if not nullable and row_count > 0:
                                # NOT NULL колонка в таблице с данными - добавляем в два этапа
                                # 1. Добавляем как NULL (или с DEFAULT)
                                if has_default and default_value:
                                    if default_value == "CURRENT_TIMESTAMP":
                                        # Для TIMESTAMP используем DEFAULT CURRENT_TIMESTAMP
                                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type} DEFAULT CURRENT_TIMESTAMP'))
                                    else:
                                        # Для других типов
                                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type} DEFAULT {default_value}'))
                                else:
                                    # Без дефолта - добавляем как NULL
                                    conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type}'))
                                conn.commit()
                                
                                # 2. Заполняем существующие записи
                                if has_default and default_value == "CURRENT_TIMESTAMP":
                                    # Для TIMESTAMP заполняем текущим временем
                                    conn.execute(text(f'UPDATE {table_name} SET {col} = CURRENT_TIMESTAMP WHERE {col} IS NULL'))
                                elif has_default and default_value:
                                    # Для других типов заполняем дефолтным значением
                                    conn.execute(text(f'UPDATE {table_name} SET {col} = {default_value} WHERE {col} IS NULL'))
                                else:
                                    # Если нет дефолта, используем дефолт по типу из TYPE_DEFAULTS
                                    from .constants import TYPE_DEFAULTS
                                    col_type_str = str(col_type).upper()
                                    type_default = None
                                    for type_name, default_val in TYPE_DEFAULTS.items():
                                        if type_name in col_type_str:
                                            type_default = default_val
                                            break
                                    
                                    if type_default is not None:
                                        if isinstance(type_default, str):
                                            conn.execute(text(f"UPDATE {table_name} SET {col} = '{type_default}' WHERE {col} IS NULL"))
                                        else:
                                            conn.execute(text(f'UPDATE {table_name} SET {col} = {type_default} WHERE {col} IS NULL'))
                                    else:
                                        # Если не нашли дефолт по типу, используем CURRENT_TIMESTAMP для TIMESTAMP
                                        if 'TIMESTAMP' in col_type_str or 'DATETIME' in col_type_str:
                                            conn.execute(text(f'UPDATE {table_name} SET {col} = CURRENT_TIMESTAMP WHERE {col} IS NULL'))
                                
                                # 3. Устанавливаем NOT NULL
                                conn.execute(text(f'ALTER TABLE {table_name} ALTER COLUMN {col} SET NOT NULL'))
                                conn.commit()
                                
                                # 4. Удаляем DEFAULT (если был установлен) - оставляем только NOT NULL
                                if has_default and default_value == "CURRENT_TIMESTAMP":
                                    # Для TIMESTAMP оставляем DEFAULT, так как это полезно для новых записей
                                    pass
                                elif has_default:
                                    conn.execute(text(f'ALTER TABLE {table_name} ALTER COLUMN {col} DROP DEFAULT'))
                                    conn.commit()
                            else:
                                # NULL колонка или таблица пустая - добавляем сразу с нужными параметрами
                                nullable_str = "" if nullable else " NOT NULL"
                                default_str = ""
                                if has_default and default_value:
                                    if default_value == "CURRENT_TIMESTAMP":
                                        default_str = " DEFAULT CURRENT_TIMESTAMP"
                                    else:
                                        default_str = f" DEFAULT {default_value}"
                                conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type}{nullable_str}{default_str}'))
                    
                    # Удаление лишних колонок
                    for col in db_cols:
                        if col not in model_cols:
                            # Проверяем, является ли колонка частью PK в текущей БД
                            pk_constraint = inspector.get_pk_constraint(table_name)
                            pk_columns = pk_constraint['constrained_columns'] if pk_constraint else []
                            
                            if col in pk_columns:
                                self.formatter.print_warning(f"Колонка {col} является PK, требуется перезаливка таблицы {table_name}")
                                need_recreate = True
                                break  # Прерываем цикл удаления колонок
                            
                            # Проверяем, есть ли индексы, ссылающиеся на эту колонку
                            indexes_using_column = []
                            existing_indexes = inspector.get_indexes(table_name)
                            for idx in existing_indexes:
                                if col in idx['column_names']:
                                    indexes_using_column.append(idx['name'])
                            
                            if indexes_using_column:
                                self.formatter.print_warning(f"Колонка {col} используется в индексах: {', '.join(indexes_using_column)}")
                                self.formatter.print_warning(f"Требуется перезаливка таблицы {table_name} для удаления колонки с индексами")
                                need_recreate = True
                                break  # Прерываем цикл удаления колонок
                            
                            if self.table_ops.can_drop_column():
                                self.formatter.print_warning(f"Удаляю колонку {col} из {table_name}")
                                conn.execute(text(f'ALTER TABLE {table_name} DROP COLUMN {col}'))
                                conn.commit()
                                self.formatter.print_success(f"Колонка {col} удалена из {table_name}")
                            else:
                                self.formatter.print_warning(f"SQLite не поддерживает DROP COLUMN, требуется перезаливка таблицы {table_name}")
                                need_recreate = True
                
                # Проверяем изменения constraints (UNIQUE, etc.)
                constraint_changes = self.metadata_cache.check_constraint_changes(
                    table_name,
                    table_class,
                    self._db_type
                )
                if constraint_changes:
                    self.formatter.print_info("Найдены изменения constraints, требуется перезаливка")
                    need_recreate = True
                
                # Несовпадение типов и nullable
                type_mismatches = []
                nullable_mismatches = []
                for col in model_cols:
                    if col in db_cols:
                        # Проверяем тип
                        db_type = db_cols[col].get('type') if isinstance(db_cols[col], dict) else db_cols[col]
                        model_type = model_cols[col].get('type') if isinstance(model_cols[col], dict) else model_cols[col]
                        if str(db_type) != str(model_type):
                            type_mismatches.append((col, db_type, model_type))
                        
                        # Проверяем nullable
                        db_nullable = db_cols[col].get('nullable', True) if isinstance(db_cols[col], dict) else True
                        model_nullable = model_cols[col].get('nullable', True) if isinstance(model_cols[col], dict) else True
                        if db_nullable != model_nullable:
                            nullable_mismatches.append((col, db_nullable, model_nullable))
                
                if type_mismatches or nullable_mismatches:
                    if type_mismatches:
                        self.formatter.print_info(f"Найдено {len(type_mismatches)} несовпадений типов колонок")
                        
                        # Определяем стратегию миграции
                        json_migrations, other_migrations = self.json_validator.determine_migration_strategy(
                            table_name,
                            type_mismatches
                        )
                        
                        # Все миграции теперь через пересоздание таблицы
                        if json_migrations or other_migrations:
                            all_migrations = json_migrations + other_migrations
                            self.formatter.print_info(f"Найдено {len(all_migrations)} несовпадений типов, требуется перезаливка")
                            for col, db_type, model_type in all_migrations:
                                self.formatter.print_warning(f"Несовпадение типа колонки {col} ({db_type} -> {model_type})")
                            need_recreate = True
                    
                    if nullable_mismatches:
                        self.formatter.print_info(f"Найдено {len(nullable_mismatches)} несовпадений nullable колонок, требуется перезаливка")
                        for col, db_nullable, model_nullable in nullable_mismatches:
                            db_nullable_str = "NULL" if db_nullable else "NOT NULL"
                            model_nullable_str = "NULL" if model_nullable else "NOT NULL"
                            self.formatter.print_warning(f"Несовпадение nullable колонки {col} ({db_nullable_str} -> {model_nullable_str})")
                        need_recreate = True
                    
                    if not type_mismatches and not nullable_mismatches:
                        self.formatter.print_success("Все типы колонок совпадают")
                else:
                    self.formatter.print_success("Все типы колонок совпадают")
                
                if need_recreate:
                    self.formatter.print_info(f"Пересоздаю таблицу {table_name} с данными...")
                    try:
                        self.table_ops.recreate_table_with_data(table_class)
                        self.formatter.print_success(f"Таблица {table_name} успешно пересоздана с данными")
                        
                        # После пересоздания таблицы с CASCADE нужно восстановить FK constraints в зависимых таблицах
                        if self._db_type == 'postgresql':
                            self.formatter.print_info(f"Восстанавливаю FK constraints в зависимых таблицах для {table_name}...")
                            self.index_ops.restore_foreign_keys_in_dependent_tables(table_name, table_class_map)
                    except Exception as e:
                        self.formatter.print_error(f"Ошибка пересоздания таблицы {table_name}: {e}")
                        raise
                else:
                    self.formatter.print_success(f"Пересоздание таблицы {table_name} не требуется")
                
                # Пересоздаём индексы
                self.formatter.print_info(f"Пересоздаю индексы для таблицы {table_name}...")
                try:
                    self.index_ops.recreate_indexes(table_class)
                except Exception as e:
                    self.formatter.print_error(f"Ошибка пересоздания индексов для {table_name}: {e}")
                    raise
            
            # Очищаем временные таблицы
            self.formatter.print_info("Очищаю временные таблицы...")
            self.cleanup_temp_tables()
            
            # Синхронизируем sequence для PostgreSQL
            if self._db_type == 'postgresql':
                self.formatter.print_info("Синхронизирую sequence...")
                self.sequence_sync.sync_postgresql_sequences()
                
                # Пересоздаём view после миграции с актуальной структурой таблиц
                try:
                    db_service = self.db_connection.db_service
                    self.formatter.print_info("Пересоздание view после миграции...")
                    db_service.create_all_views()
                    self.formatter.print_success("View пересозданы")
                except Exception as e:
                    self.formatter.print_warning(f"Не удалось пересоздать view после миграции: {e}")
                    # Не критично, view можно пересоздать вручную или при следующем запуске
            
            self.formatter.print_success("\n🎉 Миграция завершена успешно!")
            
            # Удаляем бэкап после успешной миграции (если был передан путь)
            if backup_path:
                try:
                    backup_file = Path(backup_path)
                    if backup_file.is_file():
                        # Удаляем файл бэкапа
                        backup_file.unlink()
                        self.formatter.print_success(f"Удалён бэкап базы: {backup_path}")
                    else:
                        self.logger.warning(f"Файл бэкапа не найден для удаления: {backup_path}")
                except Exception as e:
                    self.logger.warning(f"Не удалось удалить бэкап базы {backup_path}: {e}")
            
            return True
            
        except Exception as e:
            self.formatter.print_error(f"Ошибка миграции: {e}")
            # Восстановление из бэкапа выполняется на уровне выше (в migration_manager)
            raise
    
    def cleanup_temp_tables(self):
        """Очищает временные таблицы, оставшиеся после неудачных миграций"""
        try:
            inspector = inspect(self.db_connection.engine)
            existing_tables = inspector.get_table_names()
            
            temp_tables = [table for table in existing_tables if table.endswith('_tmp')]
            
            if temp_tables:
                self.formatter.print_info(f"Очищаю временные таблицы: {', '.join(temp_tables)}")
                
                with self.db_connection.engine.begin() as conn:
                    from sqlalchemy import text
                    for temp_table in temp_tables:
                        try:
                            conn.execute(text(f'DROP TABLE IF EXISTS {temp_table}'))
                            self.formatter.print_success(f"Удалена временная таблица: {temp_table}")
                        except Exception as e:
                            self.formatter.print_warning(f"Не удалось удалить {temp_table}: {e}")
            else:
                self.formatter.print_success("Временные таблицы не найдены")
                
        except Exception as e:
            self.logger.warning(f"Ошибка при очистке временных таблиц: {e}")

