"""
Module for database backup operations
Creating and restoring backups for SQLite and PostgreSQL
"""

import datetime
import gzip
import os
import shutil
import subprocess
from typing import Optional


class BackupOperations:
    """Class for database backup operations"""
    
    def __init__(self, logger, db_config, engine, settings_manager):
        """
        Initialize backup operations
        """
        self.logger = logger
        self.db_config = db_config
        self.engine = engine
        self.settings_manager = settings_manager
    
    def _get_backup_dir(self, db_type: str = None) -> str:
        """
        Gets backup directory from global settings.
        If db_type is provided, returns path to type-specific subdirectory.
        """
        global_settings = self.settings_manager.get_global_settings()
        base_dir = global_settings.get('backup_dir', 'data/backups')
        
        if db_type:
            return os.path.join(base_dir, db_type)
        return base_dir
    
    async def create_backup(self, backup_filename: Optional[str] = None) -> Optional[str]:
        """Creates database backup with gzip compression in type-specific folder"""
        try:
            db_type = self.db_config.get('type')
            backup_dir = self._get_backup_dir(db_type)
            
            if db_type == 'sqlite':
                return await self._create_sqlite_backup(backup_dir, self.db_config, backup_filename)
            elif db_type == 'postgresql':
                return await self._create_postgresql_backup(backup_dir, self.db_config, backup_filename)
            else:
                self.logger.error(f"Unsupported DB type for backup: {db_type}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating backup: {e}")
            return None
    
    async def restore_backup(self, backup_filename: Optional[str] = None) -> bool:
        """Restores database from backup in type-specific folder"""
        try:
            db_type = self.db_config.get('type')
            backup_dir = self._get_backup_dir(db_type)
            
            # If filename not specified, find latest backup
            if backup_filename is None:
                backup_filename = self._find_latest_backup(backup_dir, db_type)
                if backup_filename is None:
                    self.logger.error("No backup found for restoration")
                    return False
            
            backup_path = os.path.join(backup_dir, backup_filename)
            
            if db_type == 'sqlite':
                return await self._restore_sqlite_backup(backup_path, self.db_config)
            elif db_type == 'postgresql':
                return await self._restore_postgresql_backup(backup_path, self.db_config)
            else:
                self.logger.error(f"Unsupported DB type for restoration: {db_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error restoring backup: {e}")
            return False
    
    def _find_latest_backup(self, backup_dir: str, db_type: str) -> Optional[str]:
        """Finds latest backup in type-specific directory (simplified - no extension filtering needed)"""
        try:
            if not os.path.exists(backup_dir):
                return None
            
            # Find all backup files with 'backup_' prefix
            backup_files = []
            for filename in os.listdir(backup_dir):
                if filename.startswith('backup_'):
                    file_path = os.path.join(backup_dir, filename)
                    if os.path.isfile(file_path):
                        backup_files.append((filename, os.path.getmtime(file_path)))
            
            if not backup_files:
                return None
            
            # Sort by modification time (latest = newest)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            return backup_files[0][0]
            
        except Exception as e:
            self.logger.warning(f"Error finding latest backup: {e}")
            return None
    
    async def _create_sqlite_backup(self, backup_dir: str, db_config: dict, backup_filename: Optional[str] = None) -> Optional[str]:
        """Creates SQLite backup with gzip compression"""
        try:
            db_path = db_config.get('db_path')
            
            if not db_path or not os.path.exists(db_path):
                self.logger.warning(f"SQLite DB file not found: {db_path}")
                return None
            
            # Form backup filename
            if backup_filename:
                # If name specified, add extension if missing
                if not backup_filename.endswith('.db.gz'):
                    backup_filename = f"{backup_filename}.db.gz"
            else:
                # Generate automatically with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"backup_{timestamp}.db.gz"
            
            backup_path = os.path.join(backup_dir, backup_filename)
            # Create directory if needed
            os.makedirs(backup_dir, exist_ok=True)
            
            # Read DB file and compress with maximum compression level
            with open(db_path, 'rb') as f_in:
                with gzip.open(backup_path, 'wb', compresslevel=9) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            self.logger.info(f"SQLite backup created: {backup_path}")
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Error creating SQLite backup: {e}")
            return None
    
    async def _create_postgresql_backup(self, backup_dir: str, db_config: dict, backup_filename: Optional[str] = None) -> Optional[str]:
        """Creates PostgreSQL backup with custom format and compression"""
        backup_path = None
        try:
            # Get connection parameters from config
            postgresql_host = db_config.get('host')
            postgresql_port = db_config.get('port')
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Form backup filename
            if backup_filename:
                # If name specified, add extension if missing
                if not backup_filename.endswith('.dump'):
                    backup_filename = f"{backup_filename}.dump"
            else:
                # Generate automatically with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_filename = f"backup_{timestamp}.dump"
            
            backup_path = os.path.join(backup_dir, backup_filename)
            # Create directory if needed
            os.makedirs(backup_dir, exist_ok=True)
            
            # Command for creating dump with custom format and compression
            cmd = [
                'pg_dump',
                '-h', str(postgresql_host),
                '-p', str(postgresql_port),
                '-U', postgresql_username,
                '-d', postgresql_database,
                '-F', 'c',  # Custom format (already compressed)
                '-Z', '9',  # Maximum compression level
                '-f', backup_path,
                '--no-password'
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            if postgresql_password:
                env['PGPASSWORD'] = postgresql_password
            
            # Run pg_dump
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.logger.info(f"PostgreSQL backup created: {backup_path}")
                return backup_path
            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                self.logger.error(f"Error creating PostgreSQL backup: {error_msg}")
                # Remove partially created file on error
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                return None
                
        except FileNotFoundError:
            self.logger.error("pg_dump not found, PostgreSQL backup creation impossible")
            return None
        except Exception as e:
            self.logger.error(f"Error creating PostgreSQL backup: {e}")
            # Remove partially created file on error
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
            return None
    
    async def _restore_sqlite_backup(self, backup_path: str, db_config: dict) -> bool:
        """Restores SQLite from backup"""
        try:
            # Check backup file existence
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            db_path = db_config.get('db_path')
            if not db_path:
                self.logger.error("SQLite DB file path not defined")
                return False
            
            # Close all DB connections before restoration
            try:
                self.engine.dispose()
            except Exception as e:
                self.logger.warning(f"Error closing connections: {e}")
            
            # Create DB directory if it doesn't exist
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Remove existing DB file if present
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except PermissionError:
                    # If file is locked, try again after short delay
                    import time
                    time.sleep(0.1)
                    os.remove(db_path)
            
            # Unpack and copy file
            if backup_path.endswith('.gz'):
                # Unpack gzip
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(db_path, 'wb') as f_out:
                        f_out.writelines(f_in)
            else:
                # Just copy file
                shutil.copy2(backup_path, db_path)
            
            self.logger.info(f"SQLite DB restored from {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error restoring SQLite backup: {e}")
            return False
    
    async def _restore_postgresql_backup(self, backup_path: str, db_config: dict) -> bool:
        """Restores PostgreSQL from custom format backup"""
        try:
            # Check backup file existence
            if not os.path.exists(backup_path):
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Get connection parameters from config
            postgresql_host = db_config.get('host')
            postgresql_port = db_config.get('port')
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Command for restoration using pg_restore for custom format
            cmd = [
                'pg_restore',
                '-h', str(postgresql_host),
                '-p', str(postgresql_port),
                '-U', postgresql_username,
                '-d', postgresql_database,
                '--clean',
                '--if-exists',
                '--disable-triggers',
                '--no-owner',
                '--no-acl',
                '--no-password',
                backup_path
            ]
            
            # Set password via environment variable
            env = os.environ.copy()
            if postgresql_password:
                env['PGPASSWORD'] = postgresql_password
            
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                self.logger.info(f"PostgreSQL DB restored from {backup_path}")
                return True
            else:
                stderr = result.stderr if result.stderr else "Unknown error"
                # pg_restore may return non-zero but still succeed with warnings
                if "errors ignored on restore" in stderr:
                    self.logger.warning(f"PostgreSQL restored with warnings: {stderr}")
                    return True
                self.logger.error(f"Error restoring PostgreSQL: {stderr}")
                return False
                
        except FileNotFoundError:
            self.logger.error("pg_restore not found, PostgreSQL restoration impossible")
            return False
        except Exception as e:
            self.logger.error(f"Error restoring PostgreSQL backup: {e}")
            return False
    
    async def _clear_postgresql_database(self, db_config: dict) -> bool:
        """Clears PostgreSQL database before restoration"""
        try:
            postgresql_host = db_config.get('host')
            postgresql_port = db_config.get('port')
            postgresql_username = db_config.get('username')
            postgresql_database = db_config.get('database')
            postgresql_password = db_config.get('password')
            
            # Command for clearing DB
            cmd = [
                'psql',
                '-h', str(postgresql_host),
                '-p', str(postgresql_port),
                '-U', postgresql_username,
                '-d', postgresql_database,
                '--no-password',
                '-c', 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
            ]
            
            # Set password via environment variable
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
            self.logger.warning("psql not found, DB clearing skipped")
            return False
        except Exception as e:
            self.logger.warning(f"Error clearing DB: {e}")
            return False

