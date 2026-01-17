"""
Модуль для валидации и исправления JSON полей
"""

import json
from typing import Any, List, Tuple

from sqlalchemy import or_

from .constants import JSON_BATCH_SIZE
from .metadata import TableMetadataCache


class JSONValidator:
    """Класс для валидации и исправления JSON полей"""
    
    def __init__(self, db_service, metadata_cache: TableMetadataCache, logger, formatter):
        """
        Инициализация валидатора JSON
        """
        self.db_service = db_service
        self.metadata_cache = metadata_cache
        self.logger = logger
        self.formatter = formatter
    
    def is_json_migration(self, db_type: Any, model_type: Any) -> bool:
        """Проверяет, является ли это миграцией JSON поля"""
        db_str = str(db_type).lower()
        model_str = str(model_type).lower()
        
        # TEXT → JSONB требует предварительной проверки валидности
        # Также проверяем TEXT → JSON (на всякий случай)
        return (
            ('text' in db_str and 'json' in model_str) or
            ('text' in db_str and 'jsonb' in model_str)
        )
    
    def determine_migration_strategy(self, table_name: str, type_mismatches: List[Tuple[str, Any, Any]]) -> Tuple[List[Tuple], List[Tuple]]:
        """Определяет стратегию миграции для каждого поля"""
        json_migrations = []
        other_migrations = []
        
        for col, db_type, model_type in type_mismatches:
            if self.is_json_migration(db_type, model_type):
                json_migrations.append((col, db_type, model_type))
            else:
                other_migrations.append((col, db_type, model_type))
        
        return json_migrations, other_migrations
    
    def check_and_fix_json_optimized(self, table_name: str, json_columns: List[str], batch_size: int = JSON_BATCH_SIZE) -> bool:
        """Оптимизированная проверка и исправление всех JSON полей таблицы за один проход"""
        try:
            table_class = self.metadata_cache.get_table_class_cached(table_name)
            if not table_class:
                return True
            
            if not json_columns:
                return True
            
            # Получаем дефолтные значения из кэша
            column_defaults = {}
            for column_name in json_columns:
                column_defaults[column_name] = self.metadata_cache.get_column_default_cached(table_name, column_name)
            
            with self.db_service.session_scope() as (session, repos):
                # Получаем общее количество записей с любыми JSON полями
                filters = []
                for column_name in json_columns:
                    filters.append(
                        getattr(table_class, column_name).isnot(None) &
                        (getattr(table_class, column_name) != '')
                    )
                
                # Объединяем фильтры через OR
                combined_filter = or_(*filters)
                
                total_count = session.query(table_class).filter(combined_filter).count()
                
                if total_count == 0:
                    return True
                
                self.formatter.print_info(f"Проверяю {total_count} записей в {table_name} ({len(json_columns)} JSON полей)...")
                
                # Обрабатываем порциями
                offset = 0
                fixed_count = 0
                
                while offset < total_count:
                    # Получаем порцию записей
                    records = session.query(table_class).filter(combined_filter).offset(offset).limit(batch_size).all()
                    
                    if not records:
                        break
                    
                    # Проверяем и исправляем каждую запись для всех JSON полей
                    batch_fixed_count = 0
                    for record in records:
                        for column_name in json_columns:
                            json_value = getattr(record, column_name)
                            if json_value:
                                try:
                                    json.loads(json_value)
                                except (json.JSONDecodeError, TypeError):
                                    # Исправляем невалидный JSON используя кэшированный дефолт
                                    replacement_value = column_defaults[column_name]
                                    setattr(record, column_name, replacement_value)
                                    batch_fixed_count += 1
                    
                    # Сохраняем изменения только если были исправления в этом батче
                    if batch_fixed_count > 0:
                        session.commit()
                        fixed_count += batch_fixed_count
                    offset += batch_size
                    
                    # Показываем прогресс
                    progress = min(100, (offset / total_count) * 100)
                    self.formatter.print_info(f"Прогресс: {progress:.1f}% ({offset}/{total_count})")
                
                self.formatter.print_success(f"Исправлено {fixed_count} невалидных JSON записей")
                return True
                
        except Exception as e:
            self.formatter.print_error(f"Ошибка оптимизированной проверки JSON: {e}")
            return False
    
    def check_and_fix_invalid_json(self, json_migrations: List[Tuple]) -> bool:
        """Проверяет и исправляет невалидные JSON данные только для мигрируемых полей"""
        if not json_migrations:
            return True  # Нет JSON миграций для проверки
        
        self.formatter.print_info("Проверяю JSON поля для миграции...")
        
        # Группируем миграции по таблицам
        table_migrations = {}
        for col, db_type, model_type in json_migrations:
            table_name = col.table.name
            if table_name not in table_migrations:
                table_migrations[table_name] = []
            table_migrations[table_name].append((col, db_type, model_type))
        
        # Обрабатываем каждую таблицу
        for table_name, migrations in table_migrations.items():
            # Все JSON миграции теперь только TEXT → JSON/JSONB (требуют проверки)
            text_to_json_columns = [col.name for col, db_type, model_type in migrations]
            
            if text_to_json_columns:
                self.formatter.print_info(f"Проверяю {table_name} ({len(text_to_json_columns)} полей: TEXT → JSON/JSONB)...")
                
                if not self.check_and_fix_json_optimized(table_name, text_to_json_columns):
                    self.formatter.print_error(f"Ошибка при проверке {table_name}")
                    return False
        
        self.formatter.print_success("Все мигрируемые JSON поля проверены и исправлены")
        return True

