"""
Сервис для автоматического создания бэкапов базы данных
"""

import asyncio

from .modules.backup_rotator import BackupRotator


class BackupService:
    """
    Сервис для автоматического создания бэкапов БД
    - Создает бэкапы по расписанию (интервал в секундах)
    - Хранит только последние N бэкапов (ротация)
    - Формат: plain SQL + gzip для PostgreSQL, .bak.gz для SQLite
    """
    
    def __init__(self, **kwargs):
        """
        Инициализация сервиса бэкапов
        """
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.database_manager = kwargs['database_manager']
        
        # Получаем настройки сервиса
        plugin_settings = self.settings_manager.get_plugin_settings('backup_service')
        self.enabled = plugin_settings.get('enabled', True)
        self.backup_interval = plugin_settings.get('backup_interval', 86400)  # По умолчанию 24 часа
        self.retention_count = plugin_settings.get('retention_count', 3)
        
        # Получаем директорию бэкапов из глобальных настроек один раз
        global_settings = self.settings_manager.get_global_settings()
        self.backup_dir = global_settings.get('backup_dir', 'data/backups')
        
        # Получаем тип БД один раз
        db_config = self.database_manager.get_database_config()
        self.db_type = db_config.get('type')
        
        # Создаем модуль ротации
        self.backup_rotator = BackupRotator(self.logger)
        
        # Состояние сервиса
        self.is_running = False
    
    async def run(self):
        """
        Основной цикл работы сервиса
        - Создает бэкап при запуске
        - Затем создает бэкапы через указанный интервал
        """
        if not self.enabled:
            self.logger.info("Сервис автоматических бэкапов отключен")
            return
        
        if self.backup_interval <= 0:
            self.logger.warning("Интервал создания бэкапов не задан или равен 0, сервис не запущен")
            return
        
        try:
            self.is_running = True
            self.logger.info(f"Сервис автоматических бэкапов запущен (интервал: {self.backup_interval} сек, ретеншн: {self.retention_count} бэкапов)")
            
            # Создаем первый бэкап при запуске
            await self._create_backup_with_rotation()
            
            # Цикл создания бэкапов через интервал
            while self.is_running:
                await asyncio.sleep(self.backup_interval)
                
                if not self.is_running:
                    break
                
                await self._create_backup_with_rotation()
                
        except asyncio.CancelledError:
            self.logger.info("Сервис автоматических бэкапов остановлен")
        except Exception as e:
            self.logger.error(f"Ошибка в основном цикле сервиса бэкапов: {e}")
        finally:
            self.is_running = False
    
    async def _create_backup_with_rotation(self):
        """Создает бэкап и выполняет ротацию старых"""
        try:
            # Создаем бэкап через DatabaseManager (имя файла генерируется автоматически)
            backup_path = await self.database_manager.create_backup()
            
            if backup_path:
                # Выполняем ротацию старых бэкапов
                self.backup_rotator.rotate_backups(self.backup_dir, self.retention_count, self.db_type)
            else:
                self.logger.warning("Не удалось создать бэкап, ротация не выполнена")
                
        except Exception as e:
            self.logger.error(f"Ошибка создания бэкапа с ротацией: {e}")
    
    def shutdown(self):
        """Синхронный graceful shutdown сервиса"""
        if not self.is_running:
            return
        
        self.logger.info("Остановка сервиса автоматических бэкапов...")
        self.is_running = False

