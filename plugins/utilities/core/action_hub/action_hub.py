"""
Action Hub - центральный хаб действий
"""

import asyncio
from typing import Any, Dict, Optional, Union


class ActionHub:
    """
    Центральный хаб действий
    Маршрутизирует действия к соответствующим сервисам
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        
        # Создаем валидатор доступа
        from .core.access_validator import AccessValidator
        self.access_validator = AccessValidator(**kwargs)
        
        # Компоненты
        from .core.action_registry import ActionRegistry
        
        # Передаем валидаторы в ActionRegistry
        kwargs['access_validator'] = self.access_validator
        # action_validator передается через DI, если доступен
        self.action_registry = ActionRegistry(**kwargs)
    
    # === Registry сервисов ===
    
    def register(self, service_name: str, service_instance) -> bool:
        """Регистрация сервиса"""
        return self.action_registry.register(service_name, service_instance)
    
    def get_action_config(self, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Получение полной конфигурации действия
        
        Возвращает конфигурацию действия из маппинга или None если действие не найдено
        """
        return self.action_registry.get_action_config(action_name)
    
    # === Actions для сценариев ===
    
    async def execute_action(self, action_name: str, data: dict = None, queue_name: str = None, 
                            fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """Выполнение действия через соответствующий сервис (внутренние вызовы)"""
        return await self.action_registry.execute_action(action_name, data, queue_name, fire_and_forget, return_future)
    
    async def execute_action_secure(self, action_name: str, data: dict = None, queue_name: str = None, 
                                   fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Безопасное выполнение действия для сценариев
        Проверяет tenant_access перед выполнением
        """
        return await self.action_registry.execute_action_secure(action_name, data, queue_name, fire_and_forget, return_future)