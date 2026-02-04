"""
Module for backup rotation - deletion of old backups
"""

import os
from pathlib import Path
from typing import List


class BackupRotator:
    """Manages backup rotation - deletes old ones, keeping only last N for specified DB type"""
    
    def __init__(self, logger):
        """
        Initialize backup rotator
        """
        self.logger = logger
    
    def rotate_backups(self, backup_dir: str, retention_count: int, db_type: str) -> int:
        """
        Deletes old backups, keeping only last N for specified DB type.
        Backups are stored in separate folders: backup_dir/sqlite/ and backup_dir/postgresql/
        """
        try:
            # Build path to DB type specific folder
            type_backup_dir = Path(backup_dir) / db_type
            
            if not type_backup_dir.exists():
                return 0
            
            # Get list of backup files (all files with 'backup_' prefix)
            backup_files = self._get_backup_files(type_backup_dir)
            
            if len(backup_files) <= retention_count:
                return 0
            
            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Delete old backups
            files_to_delete = backup_files[retention_count:]
            deleted_count = 0
            
            for file_path, _ in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to delete backup {file_path}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Deleted old {db_type} backups: {deleted_count}, kept: {retention_count}")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Error rotating backups: {e}")
            return 0
    
    def _get_backup_files(self, type_backup_dir: Path) -> List[tuple]:
        """
        Get list of backup files with their modification time.
        Since backups are in separate folders, we don't need to check extensions.
        """
        backup_files = []
        
        try:
            for file_path in type_backup_dir.iterdir():
                # Check that it's a file and starts with 'backup_'
                if file_path.is_file() and file_path.name.startswith('backup_'):
                    mtime = file_path.stat().st_mtime
                    backup_files.append((str(file_path), mtime))
        
        except Exception as e:
            self.logger.error(f"Error getting backup list: {e}")
        
        return backup_files
