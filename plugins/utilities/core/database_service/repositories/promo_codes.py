import json
from typing import Dict, List, Optional, Any
from sqlalchemy import and_, or_, text, select, update
from sqlalchemy.orm import Session

from ..models import PromoCode


class PromoCodesRepository:
    """Репозиторий для работы с промокодами"""
    
    def __init__(self, session, logger, model, datetime_formatter, data_preparer, data_converter):
        self.logger = logger
        self.session = session
        self.model = model
        self.datetime_formatter = datetime_formatter
        self.data_preparer = data_preparer
        self.data_converter = data_converter
    
    def get_promo_by_id(self, promo_id: int) -> Optional[Dict[str, Any]]:
        """Получает промокод по ID"""
        try:
            promo = self.session.query(self.model).filter(self.model.id == promo_id).first()
            if promo:
                return self.data_converter.to_dict(promo)
            return None
        except Exception as e:
            self.logger.error(f"Ошибка получения промокода по ID {promo_id}: {e}")
            return None

    def get_promo_by_hash_id(self, hash_id: str) -> Optional[Dict[str, Any]]:
        """Получает промокод по хэш-идентификатору"""
        try:
            promo = self.session.query(self.model).filter(self.model.hash_id == hash_id).first()
            if promo:
                return self.data_converter.to_dict(promo)
            return None
        except Exception as e:
            self.logger.error(f"Ошибка получения промокода по hash_id {hash_id}: {e}")
            return None
    
    def get_promos_by_filters(self, **filters) -> List[Dict[str, Any]]:
        """Получает промокоды по фильтрам"""
        try:
            stmt = select(self.model)
            
            # Применяем фильтры
            if 'name_pattern' in filters and filters['name_pattern']:
                stmt = stmt.where(self.model.promo_name.ilike(f"%{filters['name_pattern']}%"))
            
            if 'user_id' in filters and filters['user_id']:
                stmt = stmt.where(self.model.user_id == filters['user_id'])
            
            if 'promo_code' in filters and filters['promo_code']:
                stmt = stmt.where(self.model.promo_code == filters['promo_code'].upper())
            
            if 'status' in filters:
                now = self.datetime_formatter.now_local()
                if filters['status'] == 'active':
                    stmt = stmt.where(
                        and_(self.model.started_at <= now, self.model.expired_at > now)
                    )
                elif filters['status'] == 'expired':
                    stmt = stmt.where(self.model.expired_at <= now)
            
            if 'date_from' in filters and filters['date_from']:
                stmt = stmt.where(self.model.created_at >= filters['date_from'])
            
            if 'date_to' in filters and filters['date_to']:
                stmt = stmt.where(self.model.created_at <= filters['date_to'])
            
            if 'expired_before' in filters and filters['expired_before']:
                stmt = stmt.where(self.model.expired_at <= filters['expired_before'])
            
            if 'expired_after' in filters and filters['expired_after']:
                stmt = stmt.where(self.model.expired_at > filters['expired_after'])
            
            # Сортировка по дате создания (новые сначала)
            stmt = stmt.order_by(self.model.created_at.desc())
            
            promos = self.session.execute(stmt).scalars().all()
            
            return self.data_converter.to_dict_list(promos)
                
        except Exception as e:
            self.logger.error(f"Ошибка получения промокодов по фильтрам: {e}")
            return []
    
    def create_promo(self, **fields) -> Optional[int]:
        """Создает новый промокод"""
        try:
            # Подготавливаем поля через data_preparer
            prepared_fields = self.data_preparer.prepare_for_insert(
                model=self.model,
                fields=fields,
                auto_timestamp_fields={
                    'created_at': self.datetime_formatter.now_local(),
                    'updated_at': self.datetime_formatter.now_local()
                }
            )
            
            if not prepared_fields:
                self.logger.error("Не удалось подготовить поля для создания промокода")
                return None
            
            # Создаем и сохраняем промокод
            promo = self.model(**prepared_fields)
            self.session.add(promo)
            self.session.commit()
            self.session.flush()
            
            return getattr(promo, 'id', 0)
                
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка создания промокода: {e}")
            return None
    
    def update_promo(self, promo_id: int, **fields) -> bool:
        """Обновляет промокод"""
        try:
            # Подготавливаем поля через data_preparer
            prepared_fields = self.data_preparer.prepare_for_update(
                model=self.model,
                fields=fields,
                auto_timestamp_fields={
                    'updated_at': self.datetime_formatter.now_local()
                }
            )
            
            if not prepared_fields:
                self.logger.warning(f"Нет валидных полей для обновления промокода {promo_id}")
                return False
            
            # Выполняем обновление
            stmt = update(self.model).where(self.model.id == promo_id).values(**prepared_fields)
            result = self.session.execute(stmt)
            self.session.commit()
            
            # Принудительно обновляем сессию чтобы избежать кэширования
            self.session.expire_all()
            
            if result.rowcount > 0:
                return True
            else:
                self.logger.warning(f"Промокод {promo_id} не найден для обновления")
                return False
                
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка обновления промокода {promo_id}: {e}")
            return False
    
    def delete_promo(self, promo_id: int) -> bool:
        """Удаляет промокод"""
        try:
            promo = self.session.query(self.model).filter(self.model.id == promo_id).first()
            if not promo:
                return False
            
            self.session.delete(promo)
            self.session.commit()
            return True
                
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Ошибка удаления промокода {promo_id}: {e}")
            return False
