"""
TenantDataManager - подмодуль для работы с данными тенантов
"""

from typing import Any, Dict


class TenantDataManager:
    """
    Подмодуль для работы с данными тенантов
    Содержит логику синхронизации настроек тенантов
    """
    
    def __init__(self, database_manager, logger):
        self.database_manager = database_manager
        self.logger = logger
    
    async def sync_tenant_data(self, tenant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Синхронизация данных тенанта: создание/обновление тенанта"""
        try:
            tenant_id = tenant_data.get('tenant_id')
            if not tenant_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "tenant_id обязателен в tenant_data"
                    }
                }
            
            # Синхронизация настроек тенанта (создание без данных из settings.yaml)
            try:
                await self._sync_tenant_settings(tenant_id, tenant_data)
            except Exception as e:
                return {
                    "result": "error",
                    "error": {
                        "code": "SYNC_ERROR",
                        "message": f"Ошибка синхронизации настроек тенанта: {str(e)}"
                    }
                }
            
            return {
                "result": "success",
                "response_data": {
                    "tenant_id": tenant_id
                }
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации данных тенанта: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def _sync_tenant_settings(self, tenant_id: int, tenant_data: Dict[str, Any]):
        """Синхронизация настроек тенанта - создание тенанта без данных из settings.yaml"""
        try:
            master_repo = self.database_manager.get_master_repository()
            
            # Ищем существующего тенанта
            existing_tenant = await master_repo.get_tenant_by_id(tenant_id)
            
            if not existing_tenant:
                # Создаем нового тенанта
                created_id = await master_repo.create_tenant({
                    'id': tenant_id
                })
                
                if created_id:
                    self.logger.info(f"[Tenant-{tenant_id}] Создан новый тенант (без данных из settings.yaml)")
                else:
                    self.logger.warning(f"[Tenant-{tenant_id}] Не удалось создать тенант")
                
        except Exception as e:
            self.logger.error(f"Ошибка синхронизации настроек тенанта {tenant_id}: {e}")
            # Не перебрасываем исключение, так как оно обрабатывается в sync_tenant_data
