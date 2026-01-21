"""
Modifiers for async actions
"""
from typing import Any


class AsyncModifiers:
    """Class with modifiers for working with async actions"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_not_ready(self, value: Any, param: str) -> bool:
        """
        Check that async action is still executing.
        value should already be a Future object obtained through _get_nested_value.
        """
        import asyncio
        
        if isinstance(value, asyncio.Future):
            return not value.done()
        return False
    
    def modifier_ready(self, value: Any, param: str) -> bool:
        """
        Check async action readiness.
        value should already be a Future object obtained through _get_nested_value.
        """
        import asyncio
        
        if isinstance(value, asyncio.Future):
            return value.done()
        return False
