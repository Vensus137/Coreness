import os
from typing import Any, Dict, Optional, List

from sqlalchemy import select, or_

from ..models import Cache


class CacheRepository:
    """
    Универсальный репозиторий для работы с таблицей Cache (кэш любых данных).
    """
    # JSON-поля, которые нужно автоматически декодировать
    JSON_FIELDS = ['hash_metadata']
    
    def __init__(self, session, logger, model, datetime_formatter, data_preparer, data_converter):
        self.logger = logger
        self.session = session
        self.model = model
        self.datetime_formatter = datetime_formatter
        self.data_preparer = data_preparer
        self.data_converter = data_converter

    def get_cache(self, hash_key: str) -> Optional[Dict[str, Any]]:
        """Получить данные из кэша"""
        try:
            stmt = select(self.model).where(self.model.hash_key == hash_key)
            cache_record = self.session.execute(stmt).scalar_one_or_none()
            
            if cache_record:
                return self.data_converter.to_dict(cache_record, json_fields=self.JSON_FIELDS)
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка получения кэша для {hash_key}: {e}")
            return None

    def add_cache(self, hash_key: str, hash_file_path: str = None, **metadata) -> bool:
        """
        Добавить новую запись в кэш
        """
        try:
            # Подготавливаем поля
            fields = {
                'hash_key': hash_key,
                'hash_file_path': hash_file_path,
                'created_at': self.datetime_formatter.now_local()
            }
            
            # Добавляем метаданные, если они переданы
            if metadata:
                fields['hash_metadata'] = metadata
            
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_insert(
                model=self.model,
                fields=fields,
                json_fields=self.JSON_FIELDS
            )
            
            if not prepared_fields:
                self.logger.error("Не удалось подготовить поля для создания кэша")
                return False
            
            # Создаем и сохраняем запись
            cache_record = self.model(**prepared_fields)
            self.session.add(cache_record)
            self.session.commit()
            return True
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка создания кэша для {hash_key}: {e}")
            return False

    def update_cache(self, hash_key: str, **fields) -> bool:
        """Обновить существующую запись в кэше"""
        try:
            # Подготавливаем поля через универсальный подготовщик
            prepared_fields = self.data_preparer.prepare_for_update(
                model=self.model,
                fields=fields,
                json_fields=self.JSON_FIELDS
            )
            
            if not prepared_fields:
                self.logger.error("Не удалось подготовить поля для обновления кэша")
                return False
            
            # Обновляем напрямую через UPDATE без SELECT
            result = self.session.query(self.model).filter(
                self.model.hash_key == hash_key
            ).update(prepared_fields)
            
            if result == 0:
                self.logger.error(f"Не удалось найти запись для обновления {hash_key}")
                return False
            
            self.session.commit()
            return True
                
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка обновления кэша для {hash_key}: {e}")
            return False

    def add_or_update_cache(self, hash_key: str, **fields) -> bool:
        """
        Универсальный метод для добавления или обновления кэша
        Классический подход: select → insert/update
        """
        try:
            # Проверяем существование записи
            existing_record = self.session.query(self.model).filter(
                self.model.hash_key == hash_key
            ).first()
            
            if existing_record:
                # Если запись существует, обновляем её
                return self.update_cache(hash_key=hash_key, **fields)
            else:
                # Если записи нет, создаем новую
                # Извлекаем hash_file_path из fields если он есть
                hash_file_path = fields.pop('hash_file_path', None)
                return self.add_cache(hash_key=hash_key, hash_file_path=hash_file_path, **fields)
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка add_or_update_cache для {hash_key}: {e}")
            return False

    def delete_cache(self, hash_key: str) -> bool:
        """Удалить запись из кэша"""
        try:
            cache_record = self.session.query(self.model).filter(
                self.model.hash_key == hash_key
            ).first()
            
            if cache_record:
                # Удаляем файл если существует
                file_path = getattr(cache_record, 'hash_file_path', None)
                if file_path:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        else:
                            pass
                    except Exception as fe:
                        self.logger.error(f"Ошибка удаления файла {file_path}: {fe}")
                
                # Удаляем запись из БД
                self.session.delete(cache_record)
                self.session.commit()
                return True
            return False
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка удаления кэша для {hash_key}: {e}")
            return False

    def has_cache(self, hash_key: str) -> bool:
        """Проверить наличие записи в кэше"""
        try:
            # Переиспользуем get_cache для оптимизации
            cache_data = self.get_cache(hash_key)
            return cache_data is not None
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки кэша для {hash_key}: {e}")
            return False 

    # === ДОПОЛНИТЕЛЬНЫЕ МЕТОДЫ ДЛЯ ОЧИСТКИ ===

    def list_old_cache(self, cutoff, with_files: bool, limit: int) -> List[Dict[str, Any]]:
        """Получить список устаревших записей кэша батчем."""
        try:
            query = self.session.query(self.model).filter(self.model.created_at < cutoff)
            if with_files:
                query = query.filter(self.model.hash_file_path.isnot(None), self.model.hash_file_path != '')
            else:
                query = query.filter(or_(self.model.hash_file_path.is_(None), self.model.hash_file_path == ''))

            records = query.limit(limit).all()
            if not records:
                return []
            return self.data_converter.to_dict_list(records, json_fields=self.JSON_FIELDS)
        except Exception as e:
            self.logger.error(f"Ошибка выборки устаревшего кэша: {e}")
            return []