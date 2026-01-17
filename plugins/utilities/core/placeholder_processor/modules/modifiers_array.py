"""
Модификаторы для работы с массивами
"""
from typing import Any, List


class ArrayModifiers:
    """Класс с модификаторами для работы с массивами"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_expand(self, value: Any, param: str) -> Any:
        """
        Разворачивание массива массивов на один уровень: {field|expand}
        Используется для разворачивания динамических клавиатур в массивах
        
        Модификатор не изменяет значение, а только помечает его для разворачивания
        при использовании в массиве. Разворачивание происходит в _process_list_optimized.
        
        Примеры:
        - {keyboard|expand} в inline: ["{keyboard|expand}", ...] развернет массив массивов на один уровень
        - [[a, b], [c, d]] при использовании с expand в массиве станет [a, b, c, d]
        """
        # Модификатор не изменяет значение, только возвращает его как есть
        # Разворачивание происходит в _process_list_optimized при обнаружении модификатора expand
        return value
    
    def modifier_keys(self, value: Any, param: str) -> List:
        """Извлечение ключей из объекта (словаря): {field|keys}"""
        if value is None:
            return None
        if isinstance(value, dict):
            return list(value.keys())
        return []
