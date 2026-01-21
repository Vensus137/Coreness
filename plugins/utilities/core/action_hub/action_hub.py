"""
Action Hub - central action hub
"""

import asyncio
from typing import Any, Dict, Optional, Union


class ActionHub:
    """
    Central action hub
    Routes actions to corresponding services
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        
        # Create access validator
        from .core.access_validator import AccessValidator
        self.access_validator = AccessValidator(**kwargs)
        
        # Components
        from .core.action_registry import ActionRegistry
        
        # Pass validators to ActionRegistry
        kwargs['access_validator'] = self.access_validator
        # action_validator is passed through DI if available
        self.action_registry = ActionRegistry(**kwargs)
    
    # === Service Registry ===
    
    def register(self, service_name: str, service_instance) -> bool:
        """Register service"""
        return self.action_registry.register(service_name, service_instance)
    
    def get_action_config(self, action_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full action configuration
        
        Returns action configuration from mapping or None if action not found
        """
        return self.action_registry.get_action_config(action_name)
    
    # === Actions for scenarios ===
    
    async def execute_action(self, action_name: str, data: dict = None, queue_name: str = None, 
                            fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """Execute action through corresponding service (internal calls)"""
        return await self.action_registry.execute_action(action_name, data, queue_name, fire_and_forget, return_future)
    
    async def execute_action_secure(self, action_name: str, data: dict = None, queue_name: str = None, 
                                   fire_and_forget: bool = False, return_future: bool = False) -> Union[Dict[str, Any], asyncio.Future]:
        """
        Secure action execution for scenarios
        Checks tenant_access before execution
        """
        return await self.action_registry.execute_action_secure(action_name, data, queue_name, fire_and_forget, return_future)