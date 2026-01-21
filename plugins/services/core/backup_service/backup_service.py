"""
Service for automatic database backup creation
"""

import asyncio

from .modules.backup_rotator import BackupRotator


class BackupService:
    """
    Service for automatic database backup creation
    - Creates backups on schedule (interval in seconds)
    - Stores only last N backups (rotation)
    - Format: plain SQL + gzip for PostgreSQL, .bak.gz for SQLite
    """
    
    def __init__(self, **kwargs):
        """
        Initialize backup service
        """
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.database_manager = kwargs['database_manager']
        
        # Get service settings
        plugin_settings = self.settings_manager.get_plugin_settings('backup_service')
        self.enabled = plugin_settings.get('enabled', True)
        self.backup_interval = plugin_settings.get('backup_interval', 86400)  # Default 24 hours
        self.retention_count = plugin_settings.get('retention_count', 3)
        
        # Get backup directory from global settings once
        global_settings = self.settings_manager.get_global_settings()
        self.backup_dir = global_settings.get('backup_dir', 'data/backups')
        
        # Get DB type once
        db_config = self.database_manager.get_database_config()
        self.db_type = db_config.get('type')
        
        # Create rotation module
        self.backup_rotator = BackupRotator(self.logger)
        
        # Service state
        self.is_running = False
    
    async def run(self):
        """
        Main service loop
        - Creates backup on startup
        - Then creates backups at specified interval
        """
        if not self.enabled:
            self.logger.info("Automatic backup service disabled")
            return
        
        if self.backup_interval <= 0:
            self.logger.warning("Backup creation interval not set or equals 0, service not started")
            return
        
        try:
            self.is_running = True
            self.logger.info(f"Automatic backup service started (interval: {self.backup_interval} sec, retention: {self.retention_count} backups)")
            
            # Create first backup on startup
            await self._create_backup_with_rotation()
            
            # Loop for creating backups at interval
            while self.is_running:
                await asyncio.sleep(self.backup_interval)
                
                if not self.is_running:
                    break
                
                await self._create_backup_with_rotation()
                
        except asyncio.CancelledError:
            self.logger.info("Automatic backup service stopped")
        except Exception as e:
            self.logger.error(f"Error in backup service main loop: {e}")
        finally:
            self.is_running = False
    
    async def _create_backup_with_rotation(self):
        """Create backup and rotate old ones"""
        try:
            # Create backup through DatabaseManager (filename generated automatically)
            backup_path = await self.database_manager.create_backup()
            
            if backup_path:
                # Rotate old backups
                self.backup_rotator.rotate_backups(self.backup_dir, self.retention_count, self.db_type)
            else:
                self.logger.warning("Failed to create backup, rotation not performed")
                
        except Exception as e:
            self.logger.error(f"Error creating backup with rotation: {e}")
    
    def shutdown(self):
        """Synchronous graceful service shutdown"""
        if not self.is_running:
            return
        
        self.logger.info("Stopping automatic backup service...")
        self.is_running = False

