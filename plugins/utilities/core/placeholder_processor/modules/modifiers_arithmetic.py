"""
Arithmetic modifiers
"""
from typing import Any, Union


class ArithmeticModifiers:
    """Class with arithmetic modifiers"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_divide(self, value: Any, param: str) -> Union[float, None]:
        """Division: {field|/value}"""
        if value is None:
            return None
        try:
            result = float(value) / float(param)
            # If result is whole number, return int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError, ZeroDivisionError):
            return value
    
    def modifier_add(self, value: Any, param: str) -> Union[float, None]:
        """Addition: {field|+value}"""
        if value is None:
            return None
        try:
            result = float(value) + float(param)
            # If result is whole number, return int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError):
            return value
    
    def modifier_subtract(self, value: Any, param: str) -> Union[float, None]:
        """Subtraction: {field|-value}"""
        if value is None:
            return None
        try:
            result = float(value) - float(param)
            # If result is whole number, return int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError):
            return value
    
    def modifier_multiply(self, value: Any, param: str) -> Union[float, None]:
        """Multiplication: {field|*value}"""
        if value is None:
            return None
        try:
            result = float(value) * float(param)
            # If result is whole number, return int
            if result.is_integer():
                return int(result)
            return result
        except (ValueError, TypeError):
            return value
    
    def modifier_modulo(self, value: Any, param: str) -> int:
        """Modulo: {field|%value}"""
        if value is None:
            return None
        try:
            return int(float(value) % float(param))
        except (ValueError, TypeError, ZeroDivisionError):
            return value
