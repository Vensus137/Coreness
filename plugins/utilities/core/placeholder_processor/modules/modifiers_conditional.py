"""
Условные модификаторы
"""
from typing import Any


class ConditionalModifiers:
    """Класс с условными модификаторами"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_equals(self, value: Any, param: str) -> bool:
        """Проверка равенства: {field|equals:value}"""
        return str(value) == str(param)
    
    def modifier_in_list(self, value: Any, param: str) -> bool:
        """Проверка вхождения в список: {field|in_list:item1,item2}"""
        if not param:
            return False
        items = [item.strip() for item in param.split(',')]
        return str(value) in items
    
    def modifier_true(self, value: Any, param: str) -> bool:
        """Проверка истинности: {field|true}"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            # Преобразуем только строки 'true' и 'false' в булевы значения
            value_lower = value.lower().strip()
            if value_lower == 'true':
                return True
            if value_lower == 'false':
                return False
            # Для других строк проверяем непустоту
            return bool(value.strip())
        elif isinstance(value, (int, float)):
            return value != 0
        return bool(value)
    
    def modifier_value(self, value: Any, param: str) -> str:
        """Возврат значения при истинности: {field|value:result}"""
        # Этот модификатор работает в связке с другими условными модификаторами
        # Например: {field|equals:active|value:Активен|fallback:Неактивен}
        return str(param) if value else ""
    
    def modifier_exists(self, value: Any, param: str) -> bool:
        """
        Проверка существования значения: {field|exists}
        Возвращает True если значение не None и не пустая строка, иначе False
        """
        return value is not None and value != ''
    
    def modifier_is_null(self, value: Any, param: str) -> bool:
        """
        Проверка на null: {field|is_null}
        Возвращает True если значение None, пустая строка или строка "null", иначе False
        Используется для замены обработки is_null в condition parser
        """
        return value is None or value == '' or (isinstance(value, str) and value.lower() == 'null')
