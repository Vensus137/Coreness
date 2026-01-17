"""
Репозиторий для работы с инвойсами (invoice)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import insert, select, update

from ..models import Invoice
from .base import BaseRepository


class InvoiceRepository(BaseRepository):
    """
    Репозиторий для работы с инвойсами
    """
    
    async def get_by_id(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение инвойса по ID
        """
        try:
            with self._get_session() as session:
                stmt = select(Invoice).where(Invoice.id == invoice_id)
                result = session.execute(stmt).scalar_one_or_none()
                
                return await self._to_dict(result)
                    
        except Exception as e:
            self.logger.error(f"Ошибка получения инвойса {invoice_id}: {e}")
            return None
    
    async def get_by_user(self, tenant_id: int, user_id: int, include_cancelled: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        Получение всех инвойсов пользователя
        """
        try:
            with self._get_session() as session:
                stmt = select(Invoice).where(
                    Invoice.tenant_id == tenant_id,
                    Invoice.user_id == user_id
                )
                
                if not include_cancelled:
                    stmt = stmt.where(Invoice.is_cancelled.is_(False))
                
                stmt = stmt.order_by(Invoice.created_at.desc())
                result = session.execute(stmt).scalars().all()
                
                return await self._to_dict_list(result)
                    
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] [User-{user_id}] Ошибка получения инвойсов: {e}")
            return None
    
    async def create(self, invoice_data: Dict[str, Any]) -> Optional[int]:
        """
        Создание нового инвойса
        """
        try:
            with self._get_session() as session:
                prepared_fields = await self.data_preparer.prepare_for_insert(
                    model=Invoice,
                    fields={
                        'tenant_id': invoice_data.get('tenant_id'),
                        'user_id': invoice_data.get('user_id'),
                        'title': invoice_data.get('title'),
                        'description': invoice_data.get('description'),
                        'amount': invoice_data.get('amount'),
                        'link': invoice_data.get('link'),
                        'is_cancelled': invoice_data.get('is_cancelled', False),
                        'telegram_payment_charge_id': invoice_data.get('telegram_payment_charge_id'),
                        'paid_at': invoice_data.get('paid_at')
                    },
                    json_fields=[]
                )
                
                stmt = insert(Invoice).values(**prepared_fields)
                result = session.execute(stmt)
                session.commit()
                
                return result.inserted_primary_key[0] if result.inserted_primary_key else None
                
        except Exception as e:
            self.logger.error(f"[Tenant-{invoice_data.get('tenant_id')}] Ошибка создания инвойса: {e}")
            return None
    
    async def update(self, invoice_id: int, invoice_data: Dict[str, Any]) -> Optional[bool]:
        """
        Обновление инвойса
        """
        try:
            with self._get_session() as session:
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=Invoice,
                    fields=invoice_data,
                    json_fields=[]
                )
                
                if not prepared_fields:
                    return False
                
                stmt = update(Invoice).where(
                    Invoice.id == invoice_id
                ).values(**prepared_fields)
                
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Ошибка обновления инвойса {invoice_id}: {e}")
            return None
    
    async def mark_as_paid(self, invoice_id: int, telegram_payment_charge_id: str, paid_at: datetime) -> Optional[bool]:
        """
        Отметить инвойс как оплаченный
        """
        try:
            with self._get_session() as session:
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=Invoice,
                    fields={
                        'telegram_payment_charge_id': telegram_payment_charge_id,
                        'paid_at': paid_at
                    },
                    json_fields=[]
                )
                
                stmt = update(Invoice).where(
                    Invoice.id == invoice_id
                ).values(**prepared_fields)
                
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Ошибка отметки инвойса {invoice_id} как оплаченного: {e}")
            return None
    
    async def cancel(self, invoice_id: int) -> Optional[bool]:
        """
        Отменить инвойс (пометить как неактивный)
        """
        try:
            with self._get_session() as session:
                prepared_fields = await self.data_preparer.prepare_for_update(
                    model=Invoice,
                    fields={
                        'is_cancelled': True
                    },
                    json_fields=[]
                )
                
                stmt = update(Invoice).where(
                    Invoice.id == invoice_id
                ).values(**prepared_fields)
                
                result = session.execute(stmt)
                session.commit()
                
                return result.rowcount > 0
                
        except Exception as e:
            self.logger.error(f"Ошибка отмены инвойса {invoice_id}: {e}")
            return None

