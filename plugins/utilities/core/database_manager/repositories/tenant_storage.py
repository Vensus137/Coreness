"""
Репозиторий для работы с хранилищем данных тенанта (tenant_storage)
"""

from typing import Any, Dict, List, Optional

from sqlalchemy import delete, distinct, insert, select, update

from ..models import TenantStorage
from .base import BaseRepository


class TenantStorageRepository(BaseRepository):
    """
    Репозиторий для работы с хранилищем данных тенанта
    """
    
    async def get_records(
        self,
        tenant_id: int,
        group_key: Optional[str] = None,
        group_key_pattern: Optional[str] = None,
        key: Optional[str] = None,
        key_pattern: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Универсальное получение записей storage
        
        Логика определения режима:
        - Если все параметры None - получить все записи тенанта
        - Если указан только group_key/group_key_pattern - получить группу/группы
        - Если указаны group_key/pattern + key/pattern - получить значение/значения
        
        Значения value преобразуются в нужные типы (int, float, bool, list, dict или str)
        
        limit: опциональное ограничение на количество возвращаемых записей
        """
        try:
            with self._get_session() as session:
                conditions = [TenantStorage.tenant_id == tenant_id]
                
                # Группа: если есть точное значение - используем его, иначе паттерн
                if group_key:
                    conditions.append(TenantStorage.group_key == group_key)
                elif group_key_pattern:
                    conditions.append(TenantStorage.group_key.ilike(group_key_pattern))
                
                # Ключ: если есть точное значение - используем его, иначе паттерн
                # Преобразуем key в строку, т.к. в БД key имеет тип String
                if key:
                    conditions.append(TenantStorage.key == str(key))
                elif key_pattern:
                    conditions.append(TenantStorage.key.ilike(key_pattern))
                
                stmt = select(TenantStorage).where(*conditions)
                
                # Применяем лимит, если указан
                if limit is not None and limit > 0:
                    stmt = stmt.limit(limit)
                
                result = session.execute(stmt).scalars().all()
                
                # Преобразуем value автоматически через convert_text_fields
                return await self._to_dict_list(result, convert_text_fields=['value'])
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения записей storage: {e}")
            return None
    
    async def delete_records(
        self,
        tenant_id: int,
        group_key: Optional[str] = None,
        group_key_pattern: Optional[str] = None,
        key: Optional[str] = None,
        key_pattern: Optional[str] = None
    ) -> Optional[int]:
        """
        Универсальное удаление записей storage
        
        Логика:
        - Если указан key или key_pattern - удаляются значения (записи с указанными ключами)
        - Если key/key_pattern не указаны, но указаны group_key/pattern - удаляются группы (все записи группы)
        - Если все параметры None - удаляются все записи тенанта
        
        Возвращает количество удаленных записей
        """
        try:
            with self._get_session() as session:
                conditions = [TenantStorage.tenant_id == tenant_id]
                
                # Группа: если есть точное значение - используем его, иначе паттерн
                if group_key:
                    conditions.append(TenantStorage.group_key == group_key)
                elif group_key_pattern:
                    conditions.append(TenantStorage.group_key.ilike(group_key_pattern))
                
                # Ключ: если есть точное значение - используем его, иначе паттерн
                # Преобразуем key в строку, т.к. в БД key имеет тип String
                if key:
                    conditions.append(TenantStorage.key == str(key))
                elif key_pattern:
                    conditions.append(TenantStorage.key.ilike(key_pattern))
                
                stmt = delete(TenantStorage).where(*conditions)
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка удаления записей storage: {e}")
            return None
    
    async def set_records(
        self,
        tenant_id: int,
        values: Dict[str, Dict[str, Any]]
    ) -> Optional[bool]:
        """
        Универсальная установка записей storage (batch для всех групп)
        
        Принимает структуру {group_key: {key: value}} для установки одного или множества значений
        Оптимизированная версия: сначала получаем все существующие записи одним запросом,
        затем выполняем batch insert/update
        """
        try:
            if not values:
                return True  # Нет данных для установки
            
            with self._get_session() as session:
                # Собираем все ключи для проверки существования
                all_keys_to_check = []
                for group_key, group_data in values.items():
                    for key in group_data.keys():
                        all_keys_to_check.append((group_key, key))
                
                # Получаем все существующие записи одним запросом
                existing_records = set()
                if all_keys_to_check:
                    # Строим условия для всех комбинаций tenant_id + group_key + key
                    from sqlalchemy import or_
                    combined_conditions = []
                    
                    for group_key, key in all_keys_to_check:
                        # Преобразуем key в строку, т.к. в БД key имеет тип String
                        combined_conditions.append(
                            (TenantStorage.tenant_id == tenant_id) &
                            (TenantStorage.group_key == str(group_key)) & 
                            (TenantStorage.key == str(key))
                        )
                    
                    if combined_conditions:
                        conditions = [or_(*combined_conditions)]
                        
                        existing = session.execute(
                            select(TenantStorage.tenant_id, TenantStorage.group_key, TenantStorage.key).where(*conditions)
                        ).all()
                        existing_records = {(r.tenant_id, r.group_key, r.key) for r in existing}
                
                # Разделяем на insert и update
                to_insert = []
                to_update = []
                
                for group_key, group_data in values.items():
                    for key, value in group_data.items():
                        # Преобразуем key в строку для сравнения и сохранения, т.к. в БД key имеет тип String
                        key_str = str(key)
                        group_key_str = str(group_key)
                        if (tenant_id, group_key_str, key_str) in existing_records:
                            to_update.append((group_key_str, key_str, value))
                        else:
                            to_insert.append({
                                'tenant_id': tenant_id,
                                'group_key': group_key_str,
                                'key': key_str,
                                'value': value
                            })
                
                # Batch insert для новых записей
                if to_insert:
                    prepared_inserts = []
                    for record in to_insert:
                        prepared_fields = await self.data_preparer.prepare_for_insert(
                            model=TenantStorage,
                            fields=record,
                            json_fields=[]
                        )
                        prepared_inserts.append(prepared_fields)
                    
                    if prepared_inserts:
                        session.execute(insert(TenantStorage), prepared_inserts)
                
                # Batch update для существующих записей
                if to_update:
                    for group_key, key, value in to_update:
                        prepared_fields = await self.data_preparer.prepare_for_update(
                            model=TenantStorage,
                            fields={'value': value},
                            json_fields=[]
                        )
                        # Преобразуем key и group_key в строки, т.к. в БД они имеют тип String
                        stmt = update(TenantStorage).where(
                            TenantStorage.tenant_id == tenant_id,
                            TenantStorage.group_key == str(group_key),
                            TenantStorage.key == str(key)
                        ).values(**prepared_fields)
                        session.execute(stmt)
                
                session.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка установки записей storage: {e}")
            return None
    
    async def delete_groups_batch(self, tenant_id: int, group_keys: List[str]) -> Optional[int]:
        """
        Batch удаление нескольких групп одним запросом
        
        Оптимизированное удаление: удаляет все указанные группы одним SQL-запросом
        вместо множества отдельных запросов.
        
        Возвращает количество удаленных записей
        """
        try:
            if not group_keys:
                return 0
            
            with self._get_session() as session:
                from sqlalchemy import or_
                
                # Строим OR-условия для всех групп
                group_conditions = [
                    TenantStorage.group_key == group_key 
                    for group_key in group_keys
                ]
                
                if group_conditions:
                    conditions = [
                        TenantStorage.tenant_id == tenant_id,
                        or_(*group_conditions)
                    ]
                    
                    stmt = delete(TenantStorage).where(*conditions)
                    result = session.execute(stmt)
                    session.commit()
                    
                    return result.rowcount
                else:
                    return 0
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка batch удаления групп storage: {e}")
            return None
    
    async def get_group_keys(self, tenant_id: int, limit: Optional[int] = None) -> Optional[List[str]]:
        """
        Получение списка уникальных ключей групп для тенанта
        
        Возвращает список всех уникальных group_key для указанного tenant_id
        limit: опциональное ограничение на количество возвращаемых групп
        """
        try:
            with self._get_session() as session:
                stmt = select(distinct(TenantStorage.group_key)).where(
                    TenantStorage.tenant_id == tenant_id
                ).order_by(TenantStorage.group_key)
                
                # Применяем лимит, если указан
                if limit is not None and limit > 0:
                    stmt = stmt.limit(limit)
                
                result = session.execute(stmt).scalars().all()
                return list(result) if result else []
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения списка групп storage: {e}")
            return None
