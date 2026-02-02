"""
Модуль для работы с метаданными таблиц
Кэширование метаданных, получение информации о колонках, constraints
"""

from typing import Any, Dict, Optional

from sqlalchemy import Integer, inspect, text

from .constants import TYPE_DEFAULTS


class TableMetadataCache:
    """Класс для кэширования метаданных таблиц"""
    
    def __init__(self, db_service, logger, formatter):
        """
        Инициализация кэша метаданных
        """
        self.db_service = db_service
        self.logger = logger
        self.formatter = formatter
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._build_cache()
    
    def _build_cache(self):
        """Строит полный кэш метаданных всех таблиц при инициализации"""
        try:
            all_tables = self.get_table_class_map()
            
            for table_name, table_class in all_tables.items():
                # Получаем все колонки первичного ключа
                primary_key_columns = list(table_class.__table__.primary_key.columns.keys())
                
                # Получаем дефолтные значения для всех колонок
                column_defaults = {}
                for column in table_class.__table__.columns:
                    column_defaults[column.name] = self._get_column_default_value(table_class, column.name)
                
                # Определяем JSON поля из модели
                json_fields = []
                for column in table_class.__table__.columns:
                    if str(column.type).upper() in ['JSON', 'JSONB']:
                        json_fields.append(column.name)
                
                # Определяем autoincrement поля и их sequence имена
                autoincrement_fields = []
                for column in table_class.__table__.columns:
                    # Строгая проверка: только ID колонки с Integer типом и primary key
                    if (column.autoincrement is True and 
                        column.name == 'id' and 
                        isinstance(column.type, Integer) and
                        column.primary_key):
                        sequence_name = f"{table_name}_{column.name}_seq"
                        autoincrement_fields.append({
                            'column_name': column.name,
                            'sequence_name': sequence_name
                        })
                
                # Кэшируем все метаданные
                self._cache[table_name] = {
                    'table_class': table_class,
                    'primary_key_columns': primary_key_columns,
                    'column_defaults': column_defaults,
                    'columns': {col.name: col for col in table_class.__table__.columns},
                    'json_fields': json_fields,
                    'autoincrement_fields': autoincrement_fields
                }
            
            self.logger.info(f"Кэш метаданных построен для {len(self._cache)} таблиц")
            
        except Exception as e:
            self.logger.warning(f"Ошибка построения кэша метаданных: {e}")
    
    def get_table_class_map(self) -> Dict[str, Any]:
        """Получает карту таблиц из database_service"""
        return self.db_service.get_table_class_map()
    
    def get_table_class(self, table_name: str) -> Optional[Any]:
        """Получает класс модели по имени таблицы"""
        table_class_map = self.get_table_class_map()
        return table_class_map.get(table_name)
    
    def get_existing_tables(self) -> list:
        """Возвращает список существующих таблиц в базе данных"""
        inspector = inspect(self.db_service.engine)
        return inspector.get_table_names()
    
    def get_available_tables(self) -> list:
        """Возвращает список доступных таблиц из модели"""
        table_class_map = self.get_table_class_map()
        return list(table_class_map.keys())
    
    def get_db_columns(self, table_name: str) -> Dict[str, Any]:
        """Получает колонки таблицы из базы данных"""
        inspector = inspect(self.db_service.engine)
        columns = inspector.get_columns(table_name)
        return {col['name']: {'type': col['type'], 'nullable': col.get('nullable', True)} for col in columns}
    
    def get_model_columns(self, table_class: Any) -> Dict[str, Any]:
        """Получает колонки таблицы из модели"""
        return {col.name: {'type': col.type, 'nullable': col.nullable} for col in table_class.__table__.columns}
    
    def _get_column_default_value(self, table_class: Any, column_name: str) -> Optional[Any]:
        """Получает дефолтное значение для колонки из модели или по типу данных"""
        try:
            column = getattr(table_class, column_name)
            
            # 1. Проверяем дефолт в модели
            if hasattr(column, 'default') and column.default is not None:
                # Если есть дефолт в модели
                if hasattr(column.default, 'arg'):
                    # Для callable дефолтов (например, func.now())
                    if callable(column.default.arg):
                        # Пропускаем SQLAlchemy функции - они обрабатываются на уровне БД
                        return None
                    else:
                        return column.default.arg
                else:
                    return column.default
            
            # 2. Проверяем nullable
            if hasattr(column, 'nullable') and not column.nullable:
                # NOT NULL без дефолта - используем дефолт по типу
                column_type = str(column.type).upper()
                
                # Ищем подходящий дефолт по типу
                for type_name, default_value in TYPE_DEFAULTS.items():
                    if type_name in column_type:
                        return default_value
                
                # Если не нашли подходящий тип - возвращаем None (будет ошибка при вставке)
                self.logger.warning(f"Неизвестный тип {column_type} для NOT NULL поля {column_name}")
                return None
            else:
                # NULLABLE - возвращаем None
                return None
                
        except Exception as e:
            self.logger.warning(f"Ошибка получения дефолта для {column_name}: {e}")
            return None
    
    def _get_primary_key_columns(self, table_name: str) -> list:
        """Получает список всех колонок первичного ключа из кэша"""
        return self._cache.get(table_name, {}).get('primary_key_columns', ['id'])
    
    def _get_autoincrement_columns(self, table_name: str) -> list:
        """Получает список autoincrement колонок из кэша"""
        autoincrement_fields = self._cache.get(table_name, {}).get('autoincrement_fields', [])
        return [field['column_name'] for field in autoincrement_fields]
    
    def get_table_class_cached(self, table_name: str) -> Optional[Any]:
        """Получает класс таблицы из кэша"""
        return self._cache.get(table_name, {}).get('table_class')
    
    def get_column_default_cached(self, table_name: str, column_name: str) -> Optional[Any]:
        """Получает дефолтное значение колонки из кэша"""
        return self._cache.get(table_name, {}).get('column_defaults', {}).get(column_name)
    
    def get_json_fields_cached(self, table_name: str) -> list:
        """Получает JSON поля таблицы из кэша"""
        return self._cache.get(table_name, {}).get('json_fields', [])
    
    def get_autoincrement_fields_cached(self, table_name: str) -> list:
        """Получает autoincrement поля таблицы из кэша"""
        return self._cache.get(table_name, {}).get('autoincrement_fields', [])
    
    def check_constraint_changes(self, table_name: str, table_class: Any, db_type: str) -> bool:
        """
        Проверяет изменения constraints (UNIQUE, PRIMARY KEY и т.д.)
        Возвращает True если constraints изменились
        """
        try:
            inspector = inspect(self.db_service.engine)
            
            # Получаем constraints из БД
            db_unique_constraints = set()
            db_primary_keys = set()
            
            if db_type == 'sqlite':
                # Для SQLite используем pragma
                with self.db_service.engine.connect() as conn:
                    # Получаем информацию о таблице
                    cursor = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    for row in cursor:
                        _, column_name, _, _, _, is_pk = row
                        if is_pk:
                            db_primary_keys.add(column_name)
                    
                    # Проверяем уникальные constraints через PRAGMA index_list для более точного определения
                    # В SQLite UNIQUE создается как index, но может иметь автоматические имена
                    index_list = conn.execute(text(f'PRAGMA index_list("{table_name}")')).fetchall()
                    for index_row in index_list:
                        index_name = index_row[1]  # Второй столбец - имя индекса
                        is_unique = index_row[2]  # Третий столбец - уникальность (1 = unique, 0 = не unique)
                        
                        if is_unique:
                            # Получаем колонки этого индекса
                            index_info = conn.execute(text(f'PRAGMA index_info("{index_name}")')).fetchall()
                            if len(index_info) == 1:
                                # Одно-колоночный уникальный индекс
                                col_name = index_info[0][2]  # Третий столбец - имя колонки
                                db_unique_constraints.add(col_name)
            else:
                # Для PostgreSQL
                unique_constraints = inspector.get_unique_constraints(table_name)
                for constraint in unique_constraints:
                    if len(constraint['column_names']) == 1:
                        db_unique_constraints.add(constraint['column_names'][0])
                
                pk_constraint = inspector.get_pk_constraint(table_name)
                if pk_constraint:
                    db_primary_keys.update(pk_constraint.get('constrained_columns', []))
            
            # Получаем constraints из модели
            model_unique_constraints = set()
            model_primary_keys = set()
            
            for column in table_class.__table__.columns:
                if column.primary_key:
                    model_primary_keys.add(column.name)
                if column.unique:
                    model_unique_constraints.add(column.name)
            
            # Сравниваем
            unique_changed = db_unique_constraints != model_unique_constraints
            pk_changed = db_primary_keys != model_primary_keys
            
            if unique_changed or pk_changed:
                if unique_changed:
                    self.formatter.print_warning(
                        f"Изменены UNIQUE constraints: "
                        f"БД={sorted(db_unique_constraints)}, Модель={sorted(model_unique_constraints)}"
                    )
                if pk_changed:
                    self.formatter.print_warning(
                        f"Изменены PRIMARY KEY: "
                        f"БД={sorted(db_primary_keys)}, Модель={sorted(model_primary_keys)}"
                    )
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Ошибка проверки constraints: {e}")
            # При ошибке возвращаем False, чтобы не ломать миграцию
            return False

