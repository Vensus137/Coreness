#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for migrating data from SQLite to PostgreSQL
Transfers all data from data/core.db to PostgreSQL database
"""

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, insert, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Project imports (after adding project_root to sys.path)
from app.di_container import DIContainer  # noqa: E402
from plugins.utilities.core.database_manager.models import Base  # noqa: E402
from plugins.utilities.foundation.logger.logger import Logger  # noqa: E402
from plugins.utilities.foundation.plugins_manager.plugins_manager import PluginsManager  # noqa: E402
from plugins.utilities.foundation.settings_manager.settings_manager import SettingsManager  # noqa: E402


# Colors for output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Table migration order (considering FK dependencies)
MIGRATION_ORDER = [
    'tenant',              # No dependencies
    'id_sequence',         # No dependencies
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

# Batch size for data insertion
BATCH_SIZE = 1000


class SQLiteToPostgreSQLMigrator:
    """Class for migrating data from SQLite to PostgreSQL"""
    
    def __init__(self):
        """Initialize migrator"""
        self.logger = Logger()
        self.log = self.logger.get_logger("migration")
        
        # Initialize DI container for PostgreSQL
        self._init_di_container()
        
        # Connect to databases
        self._connect_to_sqlite()
        self._connect_to_postgresql()
        
        # Get table class map
        self.table_class_map = self.db_service.get_table_class_map()
    
    def _init_di_container(self):
        """Initializes DI container for PostgreSQL access"""
        self.log.info("Initializing DI container...")
        
        plugins_manager = PluginsManager(logger=self.logger)
        settings_manager = SettingsManager(logger=self.logger, plugins_manager=plugins_manager)
        
        # Check if we're running in Docker
        is_inside_docker = os.path.exists('/.dockerenv')
        
        if is_inside_docker:
            # In Docker - use config settings as is (host will be service name)
            postgres_host = os.getenv('POSTGRES_HOST', 'postgres')
            postgres_port = os.getenv('POSTGRES_PORT', '5432')
        else:
            # On host - override settings for connection via localhost
            postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
            postgres_port = os.getenv('POSTGRES_PORT', None)  # Auto-detect if not specified
            
            # Auto-detect port by environment
            if postgres_port is None:
                environment = os.getenv('ENVIRONMENT', '')
                if environment == 'test':
                    postgres_port = '5433'  # Test environment uses port 5433
                else:
                    postgres_port = '5432'  # Prod uses port 5432
        
        postgres_user = os.getenv('POSTGRES_USER', 'postgres')
        postgres_password = os.getenv('POSTGRES_PASSWORD', '')
        postgres_db = os.getenv('POSTGRES_DB', 'core_db')
        
        # Override settings in settings_manager before creating DI container
        original_get_plugin_settings = settings_manager.get_plugin_settings
        
        def patched_get_plugin_settings(self_ref, plugin_name: str):
            settings = original_get_plugin_settings(plugin_name)
            if plugin_name == 'database_manager':
                settings = settings.copy()
                if 'database' not in settings:
                    settings['database'] = {}
                if 'postgresql' not in settings['database']:
                    settings['database']['postgresql'] = {}
                # Override connection settings
                settings['database']['postgresql']['host'] = postgres_host
                settings['database']['postgresql']['port'] = int(postgres_port)
                settings['database']['postgresql']['username'] = postgres_user
                if postgres_password:
                    settings['database']['postgresql']['password'] = postgres_password
                settings['database']['postgresql']['database'] = postgres_db
            return settings
        
        # Temporarily patch method to override settings
        import types
        settings_manager.get_plugin_settings = types.MethodType(patched_get_plugin_settings, settings_manager)
        
        # Log applied settings (only on host)
        if not is_inside_docker:
            self.log.info(f"PostgreSQL settings overridden for host: {postgres_host}:{postgres_port}")
        
        self.di_container = DIContainer(
            logger=self.logger,
            plugins_manager=plugins_manager,
            settings_manager=settings_manager
        )
        
        # Get database_manager
        self.db_service = self.di_container.get_utility_on_demand("database_manager")
        if not self.db_service:
            raise RuntimeError("Failed to get database_manager from DI container")
        
        self.log.info(f"DI container initialized (PostgreSQL: {postgres_host}:{postgres_port}/{postgres_db})")
    
    def _connect_to_sqlite(self):
        """Connects to SQLite database"""
        sqlite_path = project_root / "data" / "core.db"
        
        if not sqlite_path.exists():
            raise FileNotFoundError(f"SQLite database not found: {sqlite_path}")
        
        sqlite_url = f"sqlite:///{sqlite_path}"
        self.sqlite_engine = create_engine(sqlite_url, echo=False)
        self.sqlite_session_factory = sessionmaker(bind=self.sqlite_engine)
        
        self.log.info(f"Connected to SQLite: {sqlite_path}")
    
    def _connect_to_postgresql(self):
        """Connects to PostgreSQL database"""
        # Check that current DB is PostgreSQL
        db_info = self.db_service.get_database_info()
        if db_info.get('type') != 'postgresql':
            raise RuntimeError(f"Current DB is not PostgreSQL, but {db_info.get('type')}")
        
        self.pg_engine = self.db_service.engine
        self.pg_session_factory = self.db_service.session_factory
        
        self.log.info(f"Connected to PostgreSQL: {db_info.get('url')}")
    
    def _clear_postgresql_database(self):
        """Clears PostgreSQL database"""
        self.print_info("Clearing target DB (PostgreSQL)...")
        
        try:
            with self.pg_engine.begin() as conn:
                # Remove all objects in public schema
                conn.execute(text('DROP SCHEMA public CASCADE'))
                conn.execute(text('CREATE SCHEMA public'))
                conn.execute(text('GRANT ALL ON SCHEMA public TO postgres'))
                conn.execute(text('GRANT ALL ON SCHEMA public TO public'))
                
            self.print_success("Target DB cleared")
        except Exception as e:
            self.print_error(f"Error clearing DB: {e}")
            raise
    
    def _create_postgresql_schema(self):
        """Creates schema in PostgreSQL"""
        self.print_info("Creating schema in PostgreSQL...")
        
        try:
            Base.metadata.create_all(self.pg_engine)
            self.print_success("Schema created")
        except Exception as e:
            self.print_error(f"Error creating schema: {e}")
            raise
    
    def _get_table_count(self, table_name: str, engine) -> int:
        """Gets record count in table"""
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar() or 0
    
    def _get_existing_parent_ids(self, parent_table_name: str) -> set:
        """Gets set of existing IDs from parent table in PostgreSQL"""
        try:
            with self.pg_engine.connect() as conn:
                result = conn.execute(text(f"SELECT id FROM {parent_table_name}"))
                return {row[0] for row in result}
        except Exception as e:
            self.logger.warning(f"Error getting IDs from {parent_table_name}: {e}")
            return set()
    
    def _get_foreign_key_relations(self, table_class) -> list:
        """Gets list of FK relations for table: [(column_name, referenced_table_name, referenced_column_name)]"""
        fk_relations = []
        for column in table_class.__table__.columns:
            for fk in column.foreign_keys:
                # fk.column.table.name - table name referenced by FK
                # fk.column.name - column name in parent table
                fk_relations.append((column.name, fk.column.table.name, fk.column.name))
        return fk_relations
    
    def _migrate_table(self, table_name: str) -> bool:
        """Migrates data for one table"""
        if table_name not in self.table_class_map:
            self.print_warning(f"Table {table_name} not found in models, skipping")
            return True
        
        table_class = self.table_class_map[table_name]
        
        # Get record count
        source_count = self._get_table_count(table_name, self.sqlite_engine)
        
        if source_count == 0:
            self.print_info(f"Table {table_name} is empty, skipping")
            return True
        
        self.print_info(f"Migrating table {table_name} ({source_count} records)...")
        
        try:
            # Get all records from SQLite
            with self.sqlite_session_factory() as sqlite_session:
                records = sqlite_session.query(table_class).all()
            
            if not records:
                return True
            
            # Check FK relations and get existing IDs from parent tables
            fk_relations = self._get_foreign_key_relations(table_class)
            parent_ids_map = {}
            for fk_column, parent_table, _parent_column in fk_relations:
                parent_ids_map[fk_column] = self._get_existing_parent_ids(parent_table)
                if not parent_ids_map[fk_column]:
                    self.print_warning(f"  Parent table {parent_table} is empty, all records will be skipped")
            
            # Filter records by FK - keep only those with parent records
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
                self.print_warning(f"  Skipped {skipped_count} records due to missing parent records")
            
            if not filtered_records:
                self.print_warning(f"  No records to migrate after filtering")
                return True
            
            # Insert in batches to PostgreSQL
            with self.pg_session_factory() as pg_session:
                inserted = 0
                for i in range(0, len(filtered_records), BATCH_SIZE):
                    batch = filtered_records[i:i + BATCH_SIZE]
                    
                    # Convert records to dictionaries for insertion
                    batch_data = []
                    for record in batch:
                        record_dict = {}
                        for column in table_class.__table__.columns:
                            value = getattr(record, column.name)
                            # Values are already from DB, just pass as is
                            record_dict[column.name] = value
                        batch_data.append(record_dict)
                    
                    # Insert batch using insert()
                    if batch_data:
                        pg_session.execute(insert(table_class), batch_data)
                        pg_session.commit()
                    
                    inserted += len(batch)
                    progress = (inserted / len(filtered_records)) * 100
                    self.print_info(f"  Progress: {progress:.1f}% ({inserted}/{len(filtered_records)})", end='\r')
                
                self.print_info("")  # New line after progress
            
            # Check record count in target DB
            target_count = self._get_table_count(table_name, self.pg_engine)
            
            if skipped_count > 0:
                expected_count = source_count - skipped_count
                if target_count == expected_count:
                    self.print_success(f"Table {table_name} migrated: {target_count} records (skipped {skipped_count})")
                    return True
                else:
                    self.print_warning(f"Record count mismatch in {table_name}: expected {expected_count}, got {target_count}")
                    return False
            else:
                if target_count == source_count:
                    self.print_success(f"Table {table_name} migrated: {target_count} records")
                    return True
                else:
                    self.print_warning(f"Record count mismatch in {table_name}: {source_count} → {target_count}")
                    return False
                
        except Exception as e:
            self.print_error(f"Error migrating table {table_name}: {e}")
            raise
    
    def _sync_sequences(self):
        """Synchronizes sequences in PostgreSQL"""
        self.print_info("Synchronizing sequences...")
        
        try:
            with self.pg_engine.begin() as conn:
                # Get all tables with autoincrement
                for table_name, table_class in self.table_class_map.items():
                    # Check if there's an autoincrement id field
                    if hasattr(table_class, 'id'):
                        id_column = table_class.id
                        if hasattr(id_column, 'property') and hasattr(id_column.property, 'columns'):
                            # Get maximum ID
                            result = conn.execute(text(f"SELECT MAX(id) FROM {table_name}"))
                            max_id = result.scalar() or 0
                            
                            if max_id > 0:
                                sequence_name = f"{table_name}_id_seq"
                                # Synchronize sequence with maximum ID
                                conn.execute(text(f"SELECT setval('{sequence_name}', {max_id})"))
                                self.print_success(f"Sequence {sequence_name} set to {max_id}")
            
            return True
            
        except Exception as e:
            self.print_error(f"Error synchronizing sequences: {e}")
            return False
    
    def _validate_migration(self) -> bool:
        """Validates migration - compares record counts"""
        self.print_info("Validating migration...")
        
        all_ok = True
        for table_name in MIGRATION_ORDER:
            if table_name not in self.table_class_map:
                continue
            
            source_count = self._get_table_count(table_name, self.sqlite_engine)
            target_count = self._get_table_count(table_name, self.pg_engine)
            
            if source_count == target_count:
                self.print_success(f"  {table_name}: {source_count} records ✓")
            else:
                self.print_error(f"  {table_name}: {source_count} → {target_count} ✗")
                all_ok = False
        
        return all_ok
    
    def migrate(self, clear_target: bool = True) -> bool:
        """Performs full data migration"""
        try:
            self.print_separator("DATA MIGRATION SQLite → PostgreSQL")
            
            # 1. Clear target DB
            if clear_target:
                self._clear_postgresql_database()
            
            # 2. Create schema
            self._create_postgresql_schema()
            
            # 3. Migrate data in order
            self.print_separator("DATA MIGRATION")
            for table_name in MIGRATION_ORDER:
                if not self._migrate_table(table_name):
                    self.print_error(f"Error migrating table {table_name}")
                    return False
            
            # 4. Synchronize sequences
            self.print_separator("SEQUENCE SYNCHRONIZATION")
            self._sync_sequences()
            
            # 5. Validation
            self.print_separator("VALIDATION")
            if not self._validate_migration():
                self.print_warning("Validation showed mismatches, but migration completed")
            
            self.print_separator("MIGRATION COMPLETED")
            self.print_success("✅ Data migration completed successfully!")
            
            return True
            
        except Exception as e:
            self.print_error(f"❌ Migration error: {e}")
            raise
    
    def print_info(self, message: str, end: str = '\n'):
        """Prints informational message"""
        print(f"{Colors.CYAN}ℹ️ {message}{Colors.END}", end=end)
    
    def print_success(self, message: str):
        """Prints success message"""
        print(f"{Colors.GREEN}✅ {message}{Colors.END}")
    
    def print_warning(self, message: str):
        """Prints warning"""
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.END}")
    
    def print_error(self, message: str):
        """Prints error"""
        print(f"{Colors.RED}❌ {message}{Colors.END}")
    
    def print_separator(self, title: str = None):
        """Prints separator"""
        if title:
            print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
            print(f"{Colors.BOLD}{title:^60}{Colors.END}")
            print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
        else:
            print(f"{Colors.CYAN}{'='*60}{Colors.END}\n")
    
    def cleanup(self):
        """Cleans up resources"""
        if hasattr(self, 'sqlite_engine'):
            self.sqlite_engine.dispose()
        if hasattr(self, 'di_container'):
            try:
                self.di_container.shutdown()
            except Exception:
                pass


def main():
    """Main function"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{'SQLite → PostgreSQL MIGRATION':^60}{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")
    
    # Confirmation
    print(f"{Colors.YELLOW}⚠️ WARNING:{Colors.END}")
    print(f"{Colors.CYAN}This script will:{Colors.END}")
    print(f"  1. Clear target DB (PostgreSQL)")
    print(f"  2. Transfer all data from SQLite (data/core.db) to PostgreSQL")
    print(f"  3. Synchronize sequences")
    print()
    
    confirm = input(f"{Colors.YELLOW}Continue? (y/N): {Colors.END}").strip().lower()
    if confirm != 'y':
        print(f"{Colors.CYAN}Migration cancelled{Colors.END}")
        return
    
    migrator = None
    try:
        migrator = SQLiteToPostgreSQLMigrator()
        migrator.migrate(clear_target=True)
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️ Migration interrupted by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}❌ Critical error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
    finally:
        if migrator:
            migrator.cleanup()


if __name__ == '__main__':
    main()

