"""
Репозиторий для работы с хранилищем данных пользователя (user_storage)
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, insert, select, update

from ..models import UserStorage
from .base import BaseRepository


class UserStorageRepository(BaseRepository):
    """
    Репозиторий для работы с хранилищем данных пользователя
    """
    
    async def get_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Универсальное получение записей storage
        
        Логика определения режима:
        - Если все параметры None (кроме tenant_id, user_id) - получить все записи пользователя
        - Если указан key - получить конкретное значение
        - Если указан key_pattern - получить значения по паттерну
        
        Значения value преобразуются в нужные типы (int, float, bool, list, dict или str)
        
        limit: опциональное ограничение на количество возвращаемых записей
        """
        try:
            with self._get_session() as session:
                conditions = [
                    UserStorage.tenant_id == tenant_id,
                    UserStorage.user_id == user_id
                ]
                
                # Ключ: если есть точное значение - используем его, иначе паттерн
                if key:
                    conditions.append(UserStorage.key == key)
                elif key_pattern:
                    conditions.append(UserStorage.key.ilike(key_pattern))
                
                stmt = select(UserStorage).where(*conditions)
                
                # Применяем лимит, если указан
                if limit is not None and limit > 0:
                    stmt = stmt.limit(limit)
                
                result = session.execute(stmt).scalars().all()
                
                # Преобразуем value автоматически через convert_text_fields
                return await self._to_dict_list(result, convert_text_fields=['value'])
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка получения записей storage: {e}")
            return None
    
    async def set_records(self, tenant_id: int, user_id: int, values: Dict[str, Any]) -> Optional[bool]:
        """
        Универсальная установка записей storage (batch для всех ключей)
        
        Принимает структуру {key: value} для установки одного или множества значений
        Оптимизированная версия: сначала получаем все существующие записи одним запросом,
        затем выполняем batch insert/update
        """
        try:
            if not values:
                return True  # Нет данных для установки
            
            with self._get_session() as session:
                # Получаем все существующие записи для пользователя одним запросом
                existing_keys = set()
                if values:
                    existing_records = session.execute(
                        select(UserStorage.key).where(
                            UserStorage.tenant_id == tenant_id,
                            UserStorage.user_id == user_id,
                            UserStorage.key.in_(values.keys())
                        )
                    ).scalars().all()
                    existing_keys = set(existing_records)
                
                # Разделяем на insert и update
                to_insert = []
                to_update = []
                
                for key, value in values.items():
                    if key in existing_keys:
                        to_update.append((key, value))
                    else:
                        to_insert.append({
                            'tenant_id': tenant_id,
                            'user_id': user_id,
                            'key': key,
                            'value': value
                        })
                
                # Batch insert для новых записей
                if to_insert:
                    prepared_inserts = []
                    for record in to_insert:
                        prepared_fields = await self.data_preparer.prepare_for_insert(
                            model=UserStorage,
                            fields=record,
                            json_fields=[]
                        )
                        prepared_inserts.append(prepared_fields)
                    
                    if prepared_inserts:
                        session.execute(insert(UserStorage), prepared_inserts)
                
                # Batch update для существующих записей
                if to_update:
                    for key, value in to_update:
                        prepared_fields = await self.data_preparer.prepare_for_update(
                            model=UserStorage,
                            fields={'value': value},
                            json_fields=[]
                        )
                        stmt = update(UserStorage).where(
                            UserStorage.tenant_id == tenant_id,
                            UserStorage.user_id == user_id,
                            UserStorage.key == key
                        ).values(**prepared_fields)
                        session.execute(stmt)
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка установки записей storage: {e}")
            return None
    
    async def delete_records(self, tenant_id: int, user_id: int, key: Optional[str] = None, key_pattern: Optional[str] = None) -> Optional[int]:
        """
        Универсальное удаление записей storage
        
        Логика:
        - Если указан key или key_pattern - удаляются записи с указанными ключами
        - Если key и key_pattern не указаны - удаляются все записи пользователя
        
        Возвращает количество удаленных записей
        """
        try:
            with self._get_session() as session:
                conditions = [
                    UserStorage.tenant_id == tenant_id,
                    UserStorage.user_id == user_id
                ]
                
                # Ключ: если есть точное значение - используем его, иначе паттерн
                if key:
                    conditions.append(UserStorage.key == key)
                elif key_pattern:
                    conditions.append(UserStorage.key.ilike(key_pattern))
                
                stmt = delete(UserStorage).where(*conditions)
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка удаления записей storage: {e}")
            return None
    
    async def get_by_tenant_and_key(self, tenant_id: int, key: str) -> Optional[List[Dict[str, Any]]]:
        """
        Получение всех записей storage для тенанта по ключу
        Использует индекс idx_user_storage_tenant_key для быстрого поиска
        Значения value преобразуются в нужные типы (int, float, bool, list или str)
        
        Используется для поиска пользователей по значению (find_users_by_storage_value)
        """
        try:
            with self._get_session() as session:
                stmt = select(UserStorage).where(
                    UserStorage.tenant_id == tenant_id,
                    UserStorage.key == key
                )
                result = session.execute(stmt).scalars().all()
                
                # Преобразуем value автоматически через convert_text_fields
                return await self._to_dict_list(result, convert_text_fields=['value'])
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения записей по ключу {key}: {e}")
            return None
