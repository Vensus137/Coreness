"""
Модуль для операций с таблицами БД
Создание, пересоздание, удаление таблиц
"""

import json
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from .metadata import TableMetadataCache


class TableOperations:
    """Класс для операций с таблицами"""
    
    def __init__(self, db_service, engine, db_type: str, metadata_cache: TableMetadataCache, logger, formatter, translator):
        self.db_service = db_service
        self.engine = engine
        self.db_type = db_type
        self.metadata_cache = metadata_cache
        self.logger = logger
        self.formatter = formatter
        self.translator = translator
    
    def create_table(self, table_class: Any) -> bool:
        """Создает таблицу из модели"""
        try:
            table = table_class.__table__
            self.formatter.print_info(self.translator.get("database.creating_table", name=table.name))
            table.create(self.engine, checkfirst=True)
            
            # Проверяем, что таблица действительно создалась
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            if table.name in existing_tables:
                self.formatter.print_success(self.translator.get("database.table_created", name=table.name))
                return True
            else:
                self.formatter.print_error(self.translator.get("database.table_not_created", name=table.name))
                return False
                
        except Exception as e:
            self.formatter.print_error(self.translator.get("database.table_create_failed") + f" {table_class.__table__.name}: {e}")
            raise
    
    def recreate_table(self, table_class: Any) -> bool:
        """Пересоздает таблицу (drop/create)"""
        try:
            table = table_class.__table__
            self.formatter.print_warning(self.translator.get("database.dropping_table", name=table.name))
            table.drop(self.engine, checkfirst=True)
            self.formatter.print_info(self.translator.get("database.creating_table", name=table.name))
            table.create(self.engine, checkfirst=True)
            self.formatter.print_success(self.translator.get("database.table_recreated_msg", name=table.name))
            return True
        except Exception as e:
            self.formatter.print_error(self.translator.get("database.error_recreate_table", name=table_class.__table__.name, error=str(e)))
            raise
    
    def recreate_table_with_data(self, table_class: Any) -> bool:
        """Пересоздает таблицу с сохранением данных"""
        try:
            table = table_class.__table__
            tmp_table_name = table.name + "_tmp"
            
            # Создаём временную таблицу через SQLAlchemy для совместимости с разными БД
            # Создаем таблицу С Foreign Keys (как в модели) - корректную структуру сразу
            # Используем тот же MetaData, где все таблицы уже есть (для корректной работы Foreign Keys)
            tmp_table = table.to_metadata(table.metadata, name=tmp_table_name)
            
            # Удаляем только индексы (они будут пересозданы позже)
            # Foreign Keys оставляем - они нужны для проверки целостности при вставке
            tmp_table.indexes.clear()
            
            # UNIQUE constraints остаются в колонках (через unique=True), 
            # SQLAlchemy автоматически создаст их при создании таблицы
            
            # Создаем временную таблицу через SQLAlchemy с Foreign Keys
            tmp_table.create(self.engine, checkfirst=True)
            
            # Получаем информацию о колонках для переноса данных
            inspector = inspect(self.engine)
            old_columns = inspector.get_columns(table.name)
            # Используем колонки из временной таблицы (они уже соответствуют модели)
            new_columns = [col.name for col in tmp_table.columns]
            
            # Получаем колонки с unique=True из модели для обработки ошибок
            unique_columns = {col.name for col in table.columns if col.unique}
            
            # Исключаем только autoincrement поля из копирования
            # чтобы избежать конфликтов с sequence
            autoincrement_fields = self.metadata_cache.get_autoincrement_fields_cached(table.name)
            autoincrement_columns = [field['column_name'] for field in autoincrement_fields]
            old_column_names = [col['name'] for col in old_columns]
            common_columns = [c for c in new_columns if c in old_column_names and c not in autoincrement_columns]
            
            select_cols = ', '.join(common_columns)
            insert_cols = ', '.join(common_columns)
            
            # Получаем дефолтные значения из кэша
            column_defaults = {}
            for col in common_columns:
                column_defaults[col] = self.metadata_cache.get_column_default_cached(table.name, col)
            
            # Статистика для пропущенных записей
            skipped_records = 0
            unique_violations_by_column = {}
            fk_violations_by_column = {}  # Нарушения Foreign Keys по колонкам
            
            # Получаем Foreign Key колонки из модели для обработки ошибок
            fk_columns = {}
            for column in table.columns:
                for fk in column.foreign_keys:
                    fk_columns[column.name] = {
                        'target_table': fk.column.table.name,
                        'target_column': fk.column.name
                    }
            
            # Временная таблица создана С Foreign Keys - они будут проверяться при вставке
            # Для SQLite временно отключаем Foreign Key проверку при вставке, чтобы избежать ошибок
            # при наличии orphaned records (записей, ссылающихся на несуществующие записи)
            with self.engine.begin() as conn:
                # Для SQLite временно отключаем Foreign Keys при вставке
                if self.db_type == 'sqlite':
                    conn.execute(text('PRAGMA foreign_keys = OFF'))
                
                rows = conn.execute(text(f'SELECT {select_cols} FROM {table.name}')).fetchall()
                for row in rows:
                    values = []
                    for i, _col in enumerate(common_columns):
                        value = row[i]
                        
                        # Если значение - dict или list, сериализуем в JSON строку
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value, ensure_ascii=False)
                        
                        values.append(value)
                    
                    placeholders = ', '.join([':{}'.format(c) for c in common_columns])
                    try:
                        conn.execute(text(f'INSERT INTO {tmp_table_name} ({insert_cols}) VALUES ({placeholders})'), dict(zip(common_columns, values, strict=True)))
                    except IntegrityError as e:
                        # Отлавливаем нарушения UNIQUE constraint или Foreign Key
                        skipped_records += 1
                        error_msg = str(e).lower()
                        
                        # Проверяем, это UNIQUE или Foreign Key нарушение
                        is_unique_violation = False
                        is_fk_violation = False
                        
                        # Проверяем UNIQUE constraints
                        for col_name in unique_columns:
                            if col_name.lower() in error_msg or f'"{col_name}"' in error_msg:
                                unique_violations_by_column[col_name] = unique_violations_by_column.get(col_name, 0) + 1
                                is_unique_violation = True
                                break
                        
                        # Проверяем Foreign Key violations
                        if not is_unique_violation:
                            for col_name in fk_columns:
                                if col_name.lower() in error_msg or f'"{col_name}"' in error_msg or 'foreign key' in error_msg:
                                    fk_violations_by_column[col_name] = fk_violations_by_column.get(col_name, 0) + 1
                                    is_fk_violation = True
                                    break
                        
                        # Если не удалось определить тип нарушения
                        if not is_unique_violation and not is_fk_violation:
                            if 'unique' in error_msg:
                                unique_violations_by_column['unknown'] = unique_violations_by_column.get('unknown', 0) + 1
                            elif 'foreign key' in error_msg or 'references' in error_msg:
                                fk_violations_by_column['unknown'] = fk_violations_by_column.get('unknown', 0) + 1
                            else:
                                unique_violations_by_column['unknown'] = unique_violations_by_column.get('unknown', 0) + 1
                        
                        # Логируем как warning, но не прерываем миграцию
                        violation_type = "UNIQUE constraint" if is_unique_violation else ("Foreign Key" if is_fk_violation else "constraint")
                        self.logger.warning(self.translator.get("database.skipped_row_violation", violation_type=violation_type, error=str(e)))
                
                # Для SQLite Foreign Keys уже отключены для вставки, оставляем отключенными
                # для DROP TABLE (иначе не удастся удалить таблицу, на которую ссылаются другие таблицы)
                
                try:
                    # Для PostgreSQL используем CASCADE для удаления зависимых объектов
                    # CASCADE удалит FK constraints в зависимых таблицах, но не сами таблицы
                    if self.db_type == 'postgresql':
                        conn.execute(text(f'DROP TABLE {table.name} CASCADE'))
                    else:
                        conn.execute(text(f'DROP TABLE {table.name}'))
                    conn.execute(text(f'ALTER TABLE {tmp_table_name} RENAME TO {table.name}'))
                finally:
                    # Включаем Foreign Keys обратно для SQLite (были отключены для вставки и DROP TABLE)
                    if self.db_type == 'sqlite':
                        conn.execute(text('PRAGMA foreign_keys = ON'))
                
                # Foreign Keys уже есть в таблице, ничего восстанавливать не нужно
                # НО: после CASCADE FK constraints в зависимых таблицах удалены
                # Они будут восстановлены при миграции зависимых таблиц (когда дойдем до них)
                
                # Переименовываем constraint и sequence если они остались с именами _tmp
                # Только для PostgreSQL (SQLite не поддерживает эти операции)
                if self.db_type == 'postgresql':
                    # Проверяем и переименовываем constraint
                    constraint_result = conn.execute(text(f"""
                        SELECT constraint_name FROM information_schema.table_constraints 
                        WHERE table_name = '{table.name}' AND constraint_type = 'PRIMARY KEY'
                    """)).fetchone()
                    
                    if constraint_result and constraint_result[0].endswith('_tmp_pkey1'):
                        conn.execute(text(f'ALTER TABLE {table.name} RENAME CONSTRAINT {constraint_result[0]} TO {table.name}_pkey'))
                    
                    # Проверяем и переименовываем sequence
                    sequence_result = conn.execute(text(f"""
                        SELECT sequence_name FROM information_schema.sequences 
                        WHERE sequence_name = '{tmp_table_name}_id_seq'
                    """)).fetchone()
                    
                    if sequence_result:
                        conn.execute(text(f'ALTER SEQUENCE {tmp_table_name}_id_seq RENAME TO {table.name}_id_seq'))
                else:
                    # Для SQLite эти операции не нужны
                    self.formatter.print_info(self.translator.get("database.sqlite_no_rename"))
            
            # Выводим summary о пропущенных записях
            if skipped_records > 0:
                self.formatter.print_warning(
                    f"⚠️  {self.translator.get('database.skipped_records_violations', count=skipped_records)}"
                )
                
                if unique_violations_by_column:
                    unique_count = sum(unique_violations_by_column.values())
                    violations_summary = ", ".join([
                        f"{col}: {count}" for col, count in unique_violations_by_column.items()
                    ])
                    self.formatter.print_warning(f"   {self.translator.get('database.unique_violations', count=unique_count, summary=violations_summary)}")
                
                if fk_violations_by_column:
                    fk_count = sum(fk_violations_by_column.values())
                    violations_summary = ", ".join([
                        f"{col}: {count}" for col, count in fk_violations_by_column.items()
                    ])
                    self.formatter.print_warning(f"   {self.translator.get('database.fk_violations', count=fk_count, summary=violations_summary)}")
            
            # После пересоздания таблицы проверяем, что UNIQUE constraints созданы правильно
            # (fallback на случай, если что-то пошло не так при создании таблицы)
            self._ensure_unique_constraints(table_class)
            
            # Foreign Keys уже созданы в таблице при создании через to_metadata(),
            # дополнительного восстановления не требуется
            
            return True
            
        except Exception as e:
            self.formatter.print_error(self.translator.get("database.error_recreate_table", name=table_class.__table__.name, error=str(e)))
            raise
    
    def drop_table(self, table_name: str) -> bool:
        """Удаляет таблицу по имени"""
        try:
            inspector = inspect(self.engine)
            existing_tables = inspector.get_table_names()
            
            if table_name not in existing_tables:
                self.formatter.print_warning(self.translator.get("database.table_not_found", name=table_name))
                return False
            
            with self.engine.connect() as conn:
                self.formatter.print_warning(self.translator.get("database.dropping_table", name=table_name))
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
                conn.commit()
            self.formatter.print_success(self.translator.get("database.table_dropped", name=table_name))
            return True
            
        except Exception as e:
            self.formatter.print_error(self.translator.get("database.error_drop_table", name=table_name, error=str(e)))
            return False
    
    def _ensure_unique_constraints(self, table_class: Any) -> bool:
        """Убеждается, что UNIQUE constraints на колонках созданы правильно"""
        try:
            table = table_class.__table__
            inspector = inspect(self.engine)
            
            # Получаем колонки с unique=True из модели
            unique_columns = {col.name for col in table.columns if col.unique}
            
            if not unique_columns:
                return True
            
            # Получаем существующие UNIQUE индексы из БД
            # Для SQLite нужно проверять не только имя индекса, но и колонки
            existing_unique_indexes = set()
            indexes = inspector.get_indexes(table.name)
            for idx in indexes:
                if idx.get('unique', False) and len(idx['column_names']) == 1:
                    # Добавляем колонку из индекса
                    existing_unique_indexes.add(idx['column_names'][0])
            
            # Для SQLite также проверяем через PRAGMA index_list для более точного определения
            if self.db_type == 'sqlite':
                with self.engine.connect() as conn:
                    # Получаем все индексы таблицы через PRAGMA
                    index_list = conn.execute(text(f'PRAGMA index_list("{table.name}")')).fetchall()
                    for index_row in index_list:
                        index_name = index_row[1]  # Второй столбец - имя индекса
                        is_unique = index_row[2]  # Третий столбец - уникальность (1 = unique, 0 = не unique)
                        
                        if is_unique:
                            # Получаем колонки этого индекса
                            index_info = conn.execute(text(f'PRAGMA index_info("{index_name}")')).fetchall()
                            if len(index_info) == 1:
                                # Одно-колоночный уникальный индекс
                                col_name = index_info[0][2]  # Третий столбец - имя колонки
                                existing_unique_indexes.add(col_name)
            
            # Создаем UNIQUE индексы для колонок, которые имеют unique=True, но не имеют UNIQUE индекса
            with self.engine.connect() as conn:
                for col_name in unique_columns:
                    if col_name not in existing_unique_indexes:
                        # Создаем UNIQUE индекс для этой колонки
                        index_name = f"uq_{table.name}_{col_name}"
                        try:
                            self.formatter.print_info(self.translator.get("database.creating_unique_constraint", name=col_name))
                            if self.db_type == 'sqlite':
                                # В SQLite сначала удаляем старый автоматический индекс если есть
                                # (SQLite может создать его автоматически при создании таблицы)
                                # Затем создаем явный индекс с нужным именем
                                conn.execute(text(f'DROP INDEX IF EXISTS "sqlite_autoindex_{table.name}_1"'))
                                conn.execute(text(f'DROP INDEX IF EXISTS "sqlite_autoindex_{table.name}_2"'))
                                conn.execute(text(f'DROP INDEX IF EXISTS "sqlite_autoindex_{table.name}_3"'))
                                # Создаем явный UNIQUE индекс
                                conn.execute(text(f'CREATE UNIQUE INDEX IF NOT EXISTS "{index_name}" ON "{table.name}" ("{col_name}")'))
                            else:
                                # Для PostgreSQL создаем UNIQUE constraint
                                conn.execute(text(f'ALTER TABLE "{table.name}" ADD CONSTRAINT "{index_name}" UNIQUE ("{col_name}")'))
                            conn.commit()
                            self.formatter.print_success(self.translator.get("database.unique_constraint_created", name=col_name))
                        except Exception as e:
                            self.logger.warning(self.translator.get("database.error_create_unique_constraint", name=col_name, error=str(e)))
                            # Пробуем альтернативный способ - через индекс с уникальным именем
                            try:
                                alt_index_name = f"idx_{table.name}_{col_name}_unique"
                                conn.execute(text(f'CREATE UNIQUE INDEX IF NOT EXISTS "{alt_index_name}" ON "{table.name}" ("{col_name}")'))
                                conn.commit()
                                self.formatter.print_success(self.translator.get("database.unique_index_created_alt", name=col_name))
                            except Exception as e2:
                                self.logger.error(self.translator.get("database.error_create_unique_constraint", name=col_name, error=str(e2)))
            
            return True
            
        except Exception as e:
            self.logger.warning(self.translator.get("database.error_check_unique_constraints", error=str(e)))
            return False
    
    def can_drop_column(self) -> bool:
        """Проверяет, поддерживает ли текущая БД DROP COLUMN"""
        if self.db_type == 'postgresql':
            # PostgreSQL всегда поддерживает DROP COLUMN
            return True
        elif self.db_type == 'sqlite':
            # SQLite >= 3.35 поддерживает DROP COLUMN
            try:
                with self.engine.connect() as conn:
                    version = conn.execute(text('select sqlite_version()')).scalar()
                major, minor, *_ = map(int, version.split('.'))
                return (major, minor) >= (3, 35)
            except Exception:
                return False
        else:
            # Для других БД считаем что не поддерживает
            return False

