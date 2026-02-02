"""Universal database migration - coordinates all modules."""

from pathlib import Path
from typing import Optional

from sqlalchemy import inspect

from ..connection.database_connection import DatabaseConnection
from .index_operations import IndexOperations
from .json_validator import JSONValidator
from .metadata import TableMetadataCache
from .sequence_sync import SequenceSync
from .table_operations import TableOperations


class UniversalMigration:
    """Universal database migration handler."""

    def __init__(self, db_connection: DatabaseConnection, logger, formatter, translator):
        self.db_connection = db_connection
        self.logger = logger
        self.formatter = formatter
        self.translator = translator

        self.metadata_cache = TableMetadataCache(
            db_connection.db_service,
            logger,
            formatter
        )

        db_type = db_connection.db_type

        self.table_ops = TableOperations(
            db_connection.db_service,
            db_connection.engine,
            db_type,
            self.metadata_cache,
            logger,
            formatter,
            translator
        )

        self.index_ops = IndexOperations(
            db_connection.engine,
            db_type,
            logger,
            formatter,
            translator
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
            formatter,
            translator
        )

        self._db_type = db_type

    def migrate_database(self, target_table: Optional[str] = None, backup_path: Optional[str] = None) -> bool:
        """Execute database migration."""
        try:
            engine = self.db_connection.engine
            inspector = inspect(engine)
            existing_tables = set(self.metadata_cache.get_existing_tables())
            table_class_map = self.metadata_cache.get_table_class_map()

            if self._db_type == 'postgresql':
                try:
                    db_service = self.db_connection.db_service
                    self.formatter.print_info(self.translator.get("database.dropping_views"))
                    db_service.drop_all_views()
                    self.formatter.print_success(self.translator.get("database.views_dropped"))
                except Exception as e:
                    self.formatter.print_warning(self.translator.get("database.views_drop_failed", error=str(e)))

            if target_table:
                if target_table not in table_class_map:
                    self.formatter.print_error(self.translator.get("database.unknown_table", table_name=target_table))
                    return False
                tables_to_migrate = {target_table: table_class_map[target_table]}
            else:
                tables_to_migrate = table_class_map

            if self._db_type == 'sqlite':
                tables_to_migrate = {
                    name: cls for name, cls in tables_to_migrate.items()
                    if name != 'vector_storage'
                }
                if 'vector_storage' in table_class_map:
                    self.formatter.print_info(self.translator.get("database.vector_storage_skipped"))

            for table_name, table_class in tables_to_migrate.items():
                self.formatter.print_section(self.translator.get("database.migrating_table") + f" {table_name}")

                if table_name not in existing_tables:
                    self.formatter.print_info(self.translator.get("database.table_not_found_creating", table_name=table_name))
                    try:
                        if not self.table_ops.create_table(table_class):
                            raise Exception(f"Failed to create table {table_name}")
                        self.formatter.print_success(self.translator.get("database.indexes_created_auto", table_name=table_name))
                        continue
                    except Exception as e:
                        self.formatter.print_error(f"{self.translator.get('database.table_create_failed')} {table_name}: {e}")
                        raise
                else:
                    self.formatter.print_success(self.translator.get("database.table_exists_format", table_name=table_name))

                db_cols = self.metadata_cache.get_db_columns(table_name)
                model_cols = self.metadata_cache.get_model_columns(table_class)
                need_recreate = False

                if db_cols == model_cols:
                    self.formatter.print_success(self.translator.get("database.schema_match_format", table_name=table_name))
                    self.index_ops.recreate_indexes(table_class)
                    continue

                with engine.connect() as conn:
                    from sqlalchemy import text

                    cols_to_add = [col for col in model_cols if col not in db_cols]
                    cols_to_remove = [col for col in db_cols if col not in model_cols]

                    if not cols_to_add and not cols_to_remove:
                        self.formatter.print_success(self.translator.get("database.all_columns_present"))
                    else:
                        if cols_to_add:
                            self.formatter.print_info(self.translator.get("database.cols_to_add_format", count=len(cols_to_add)))
                        if cols_to_remove:
                            self.formatter.print_info(self.translator.get("database.cols_to_remove_format", count=len(cols_to_remove)))

                    for col, col_info in model_cols.items():
                        if col not in db_cols:
                            self.formatter.print_info(self.translator.get("database.adding_column", col=col, table_name=table_name))
                            col_type = col_info.get('type') if isinstance(col_info, dict) else col_info
                            nullable = col_info.get('nullable', True) if isinstance(col_info, dict) else True

                            column_obj = getattr(table_class, col, None)
                            has_default = False
                            default_value = None

                            if column_obj and hasattr(column_obj, 'default') and column_obj.default is not None:
                                if hasattr(column_obj.default, 'arg'):
                                    if callable(column_obj.default.arg):
                                        col_type_str = str(col_type).upper()
                                        if 'TIMESTAMP' in col_type_str or 'DATETIME' in col_type_str:
                                            has_default = True
                                            default_value = "CURRENT_TIMESTAMP"
                                    else:
                                        has_default = True
                                        default_value = column_obj.default.arg
                                else:
                                    has_default = True
                                    default_value = column_obj.default

                            row_count_result = conn.execute(text(f'SELECT COUNT(*) FROM {table_name}'))
                            row_count = row_count_result.scalar()

                            if not nullable and row_count > 0:
                                if has_default and default_value:
                                    if default_value == "CURRENT_TIMESTAMP":
                                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type} DEFAULT CURRENT_TIMESTAMP'))
                                    else:
                                        conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type} DEFAULT {default_value}'))
                                else:
                                    conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type}'))
                                conn.commit()

                                if has_default and default_value == "CURRENT_TIMESTAMP":
                                    conn.execute(text(f'UPDATE {table_name} SET {col} = CURRENT_TIMESTAMP WHERE {col} IS NULL'))
                                elif has_default and default_value:
                                    conn.execute(text(f'UPDATE {table_name} SET {col} = {default_value} WHERE {col} IS NULL'))
                                else:
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
                                    elif 'TIMESTAMP' in col_type_str or 'DATETIME' in col_type_str:
                                        conn.execute(text(f'UPDATE {table_name} SET {col} = CURRENT_TIMESTAMP WHERE {col} IS NULL'))

                                if self._db_type == 'postgresql':
                                    conn.execute(text(f'ALTER TABLE {table_name} ALTER COLUMN {col} SET NOT NULL'))
                                    conn.commit()
                                    if has_default and default_value != "CURRENT_TIMESTAMP":
                                        conn.execute(text(f'ALTER TABLE {table_name} ALTER COLUMN {col} DROP DEFAULT'))
                                        conn.commit()
                                # SQLite: ADD COLUMN with DEFAULT already sets NOT NULL for new rows

                            else:
                                nullable_str = "" if nullable else " NOT NULL"
                                default_str = ""
                                if has_default and default_value:
                                    default_str = " DEFAULT CURRENT_TIMESTAMP" if default_value == "CURRENT_TIMESTAMP" else f" DEFAULT {default_value}"
                                conn.execute(text(f'ALTER TABLE {table_name} ADD COLUMN {col} {col_type}{nullable_str}{default_str}'))
                                conn.commit()

                    for col in db_cols:
                        if col not in model_cols:
                            pk_constraint = inspector.get_pk_constraint(table_name)
                            pk_columns = pk_constraint['constrained_columns'] if pk_constraint else []
                            if col in pk_columns:
                                self.formatter.print_warning(self.translator.get("database.col_is_pk_recreate", col=col))
                                need_recreate = True
                                break
                            existing_indexes = inspector.get_indexes(table_name)
                            indexes_using_column = [idx['name'] for idx in existing_indexes if col in idx['column_names']]
                            if indexes_using_column:
                                self.formatter.print_warning(self.translator.get("database.col_in_indexes_recreate", col=col))
                                need_recreate = True
                                break
                            if self.table_ops.can_drop_column():
                                self.formatter.print_warning(self.translator.get("database.dropping_column", col=col, table_name=table_name))
                                conn.execute(text(f'ALTER TABLE {table_name} DROP COLUMN {col}'))
                                conn.commit()
                                self.formatter.print_success(self.translator.get("database.col_removed_format", col=col))
                            else:
                                self.formatter.print_warning(self.translator.get("database.drop_col_not_supported"))
                                need_recreate = True

                constraint_changes = self.metadata_cache.check_constraint_changes(
                    table_name, table_class, self._db_type
                )
                if constraint_changes:
                    need_recreate = True

                type_mismatches = []
                nullable_mismatches = []
                for col in model_cols:
                    if col in db_cols:
                        db_type = db_cols[col].get('type') if isinstance(db_cols[col], dict) else db_cols[col]
                        model_type = model_cols[col].get('type') if isinstance(model_cols[col], dict) else model_cols[col]
                        if str(db_type) != str(model_type):
                            type_mismatches.append((col, db_type, model_type))
                        db_nullable = db_cols[col].get('nullable', True) if isinstance(db_cols[col], dict) else True
                        model_nullable = model_cols[col].get('nullable', True) if isinstance(model_cols[col], dict) else True
                        if db_nullable != model_nullable:
                            nullable_mismatches.append((col, db_nullable, model_nullable))

                if type_mismatches or nullable_mismatches:
                    if type_mismatches:
                        json_migrations, other_migrations = self.json_validator.determine_migration_strategy(
                            table_name, type_mismatches
                        )
                        if json_migrations or other_migrations:
                            need_recreate = True
                    if nullable_mismatches:
                        need_recreate = True

                if need_recreate:
                    self.formatter.print_info(self.translator.get("database.recreating_table", table_name=table_name))
                    try:
                        self.table_ops.recreate_table_with_data(table_class)
                        self.formatter.print_success(self.translator.get("database.table_recreated", table_name=table_name))
                        if self._db_type == 'postgresql':
                            self.formatter.print_info(self.translator.get("database.restoring_fk"))
                            self.index_ops.restore_foreign_keys_in_dependent_tables(table_name, table_class_map)
                    except Exception as e:
                        self.formatter.print_error(f"{self.translator.get('database.table_create_failed')} {table_name}: {e}")
                        raise

                self.formatter.print_info(self.translator.get("database.recreating_indexes", table_name=table_name))
                self.index_ops.recreate_indexes(table_class)

            self.formatter.print_info(self.translator.get("database.cleaning_temp_tables"))
            self.cleanup_temp_tables()

            if self._db_type == 'postgresql':
                self.formatter.print_info(self.translator.get("database.syncing_sequences"))
                self.sequence_sync.sync_postgresql_sequences()
                try:
                    db_service = self.db_connection.db_service
                    self.formatter.print_info(self.translator.get("database.recreating_views"))
                    db_service.create_all_views()
                    self.formatter.print_success(self.translator.get("database.views_recreated"))
                except Exception as e:
                    self.formatter.print_warning(self.translator.get("database.views_recreate_failed", error=str(e)))

            self.formatter.print_success(f"\n✓ {self.translator.get('database.migration_complete')}!")

            if backup_path:
                try:
                    backup_file = Path(backup_path)
                    if backup_file.is_file():
                        backup_file.unlink()
                        self.formatter.print_success(f"Backup removed: {backup_path}")
                except Exception as e:
                    self.logger.warning(self.translator.get("database.failed_to_remove_backup", error=str(e)))

            return True

        except Exception as e:
            self.formatter.print_error(self.translator.get("database.migration_error", error=str(e)))
            raise

    def cleanup_temp_tables(self):
        """Clean up temp tables from failed migrations."""
        try:
            inspector = inspect(self.db_connection.engine)
            existing_tables = inspector.get_table_names()
            temp_tables = [t for t in existing_tables if t.endswith('_tmp')]
            if temp_tables:
                with self.db_connection.engine.begin() as conn:
                    from sqlalchemy import text
                    for temp_table in temp_tables:
                        try:
                            conn.execute(text(f'DROP TABLE IF EXISTS {temp_table}'))
                            self.formatter.print_success(self.translator.get("database.removed_temp_table", table_name=temp_table))
                        except Exception as e:
                            self.formatter.print_warning(self.translator.get("database.failed_to_remove_temp", table_name=temp_table, error=str(e)))
        except Exception as e:
            self.logger.warning(self.translator.get("database.error_cleaning_temp_tables", error=str(e)))
