"""
Модуль для синхронизации sequences в PostgreSQL
"""

from sqlalchemy import text

from .metadata import TableMetadataCache


class SequenceSync:
    """Класс для синхронизации sequences в PostgreSQL"""
    
    def __init__(self, db_service, engine, db_type: str, metadata_cache: TableMetadataCache, logger, formatter, translator):
        self.db_service = db_service
        self.engine = engine
        self.db_type = db_type
        self.metadata_cache = metadata_cache
        self.logger = logger
        self.formatter = formatter
        self.translator = translator

    def sync_postgresql_sequences(self) -> bool:
        """Синхронизирует sequence с максимальными ID в таблицах для PostgreSQL"""
        if self.db_type != 'postgresql':
            return True
        
        try:
            with self.engine.begin() as conn:
                # Получаем все таблицы из кэша
                all_tables = self.metadata_cache.get_table_class_map()
                
                for table_name, _table_class in all_tables.items():
                    # Получаем autoincrement поля из кэша
                    autoincrement_fields = self.metadata_cache.get_autoincrement_fields_cached(table_name)
                    
                    if not autoincrement_fields:
                        continue
                    
                    for field_info in autoincrement_fields:
                        column_name = field_info['column_name']
                        sequence_name = field_info['sequence_name']
                        
                        # Получаем максимальный ID в таблице
                        result = conn.execute(text(f"SELECT MAX({column_name}) FROM {table_name}"))
                        max_id = result.fetchone()[0] or 0
                        
                        if max_id > 0:
                            # Синхронизируем sequence
                            conn.execute(text(f"SELECT setval('{sequence_name}', {max_id})"))
                            self.formatter.print_success(self.translator.get("database.sequence_synced", name=sequence_name, max_id=max_id))
            
            return True
            
        except Exception as e:
            self.formatter.print_error(self.translator.get("database.sequence_sync_error", error=str(e)))
            return False

