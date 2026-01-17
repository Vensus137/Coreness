"""
Арифметические модификаторы
"""
from typing import Any, Union


class ArithmeticModifiers:
    """Класс с арифметическими модификаторами"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_divide(self, value: Any, param: str) -> Union[float, None]:
        """Деление: {field|/value}"""
        if value is None:
            return None
        try:
            result = float(value) / float(param)
            # Если результат целое число, возвращаем int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError, ZeroDivisionError):
            return value
    
    def modifier_add(self, value: Any, param: str) -> Union[float, None]:
        """Сложение: {field|+value}"""
        if value is None:
            return None
        try:
            result = float(value) + float(param)
            # Если результат целое число, возвращаем int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError):
            return value
    
    def modifier_subtract(self, value: Any, param: str) -> Union[float, None]:
        """Вычитание: {field|-value}"""
        if value is None:
            return None
        try:
            result = float(value) - float(param)
            # Если результат целое число, возвращаем int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError):
            return value
    
    def modifier_multiply(self, value: Any, param: str) -> Union[float, None]:
        """Умножение: {field|*value}"""
        if value is None:
            return None
        try:
            result = float(value) * float(param)
            # Если результат целое число, возвращаем int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError):
            return value
    
    def modifier_modulo(self, value: Any, param: str) -> int:
        """Остаток от деления: {field|%value}"""
        if value is None:
            return None
        try:
            return int(float(value) % float(param))
        except (ValueError, TypeError, ZeroDivisionError):
            return value
