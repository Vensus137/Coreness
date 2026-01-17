"""
Модуль для ротации бэкапов - удаление старых бэкапов
"""

import os
from typing import List


class BackupRotator:
    """Управляет ротацией бэкапов - удаляет старые, оставляя только последние N для указанного типа БД"""
    
    def __init__(self, logger):
        """
        Инициализация ротатора бэкапов
        """
        self.logger = logger
    
    def rotate_backups(self, backup_dir: str, retention_count: int, db_type: str) -> int:
        """
        Удаляет старые бэкапы, оставляя только последние N для указанного типа БД
        """
        try:
            if not os.path.exists(backup_dir):
                return 0
            
            # Получаем список файлов бэкапов только для указанного типа БД
            backup_files = self._get_backup_files(backup_dir, db_type)
            
            if len(backup_files) <= retention_count:
                return 0
            
            # Сортируем по времени модификации (новые первыми)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Удаляем старые бэкапы
            files_to_delete = backup_files[retention_count:]
            deleted_count = 0
            
            for file_path, _ in files_to_delete:
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    self.logger.warning(f"Не удалось удалить бэкап {file_path}: {e}")
            
            if deleted_count > 0:
                self.logger.info(f"Удалено старых бэкапов {db_type}: {deleted_count}, оставлено: {retention_count}")
            
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Ошибка ротации бэкапов: {e}")
            return 0
    
    def _get_backup_files(self, backup_dir: str, db_type: str) -> List[tuple]:
        """
        Получает список файлов бэкапов с их временем модификации для указанного типа БД
        """
        backup_files = []
        
        # Определяем расширение файла в зависимости от типа БД
        if db_type == 'sqlite':
            extension = '.bak.gz'
        elif db_type == 'postgresql':
            extension = '.sql.gz'
        else:
            self.logger.warning(f"Неподдерживаемый тип БД для ротации: {db_type}")
            return backup_files
        
        try:
            for filename in os.listdir(backup_dir):
                file_path = os.path.join(backup_dir, filename)
                
                # Проверяем, что это файл бэкапа нужного типа
                if not os.path.isfile(file_path):
                    continue
                
                # Проверяем расширение только для нужного типа БД
                if filename.endswith(extension):
                    mtime = os.path.getmtime(file_path)
                    backup_files.append((file_path, mtime))
        
        except Exception as e:
            self.logger.error(f"Ошибка получения списка бэкапов: {e}")
        
        return backup_files
