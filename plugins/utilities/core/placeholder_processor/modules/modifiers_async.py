"""
Модификаторы для асинхронных действий
"""
from typing import Any


class AsyncModifiers:
    """Класс с модификаторами для работы с асинхронными действиями"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_not_ready(self, value: Any, param: str) -> bool:
        """
        Проверка что асинхронное действие еще выполняется.
        value уже должен быть Future объектом, полученным через _get_nested_value.
        """
        import asyncio
        
        if isinstance(value, asyncio.Future):
            return not value.done()
        return False
    
    def modifier_ready(self, value: Any, param: str) -> bool:
        """
        Проверка готовности асинхронного действия.
        value уже должен быть Future объектом, полученным через _get_nested_value.
        """
        import asyncio
        
        if isinstance(value, asyncio.Future):
            return value.done()
        return False
