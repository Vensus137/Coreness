"""
Module for backup rotation - deletion of old backups
"""

import os
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
        Deletes old backups, keeping only last N for specified DB type
        """
        try:
            if not os.path.exists(backup_dir):
                return 0
            
            # Get list of backup files only for specified DB type
            backup_files = self._get_backup_files(backup_dir, db_type)
            
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
    
    def _get_backup_files(self, backup_dir: str, db_type: str) -> List[tuple]:
        """
        Get list of backup files with their modification time for specified DB type
        """
        backup_files = []
        
        # Determine file extension based on DB type
        if db_type == 'sqlite':
            extension = '.bak.gz'
        elif db_type == 'postgresql':
            extension = '.sql.gz'
        else:
            self.logger.warning(f"Unsupported DB type for rotation: {db_type}")
            return backup_files
        
        try:
            for filename in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, filename)
                
                # Check that it's a backup file of needed type
                if not os.path.isfile(file_path):
                    continue
                
                # Check extension only for needed DB type
                if filename.endswith(extension):
                    mtime = os.path.getmtime(file_path)
                    backup_files.append((file_path, mtime))
        
        except Exception as e:
            self.logger.error(f"Error getting backup list: {e}")
        
        return backup_files
