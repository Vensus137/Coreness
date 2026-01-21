"""
Conditional modifiers
"""
from typing import Any


class ConditionalModifiers:
    """Class with conditional modifiers"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_equals(self, value: Any, param: str) -> bool:
        """Equality check: {field|equals:value}"""
        return str(value) == str(param)
    
    def modifier_in_list(self, value: Any, param: str) -> bool:
        """Check if value in list: {field|in_list:item1,item2}"""
        if not param:
            return False
        items = [item.strip() for item in param.split(',')]
        return str(value) in items
    
    def modifier_true(self, value: Any, param: str) -> bool:
        """Truth check: {field|true}"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            # Convert only strings 'true' and 'false' to boolean values
            value_lower = value.lower().strip()
            if value_lower == 'true':
                return True
            if value_lower == 'false':
                return False
            # For other strings check non-emptiness
            return bool(value.strip())
        elif isinstance(value, (int, float)):
            return value != 0
        return bool(value)
    
    def modifier_value(self, value: Any, param: str) -> str:
        """Return value if truthy: {field|value:result}"""
        # This modifier works in combination with other conditional modifiers
        # Example: {field|equals:active|value:Active|fallback:Inactive}
        return str(param) if value else ""
    
    def modifier_exists(self, value: Any, param: str) -> bool:
        """
        Check value existence: {field|exists}
        Returns True if value is not None and not empty string, else False
        """
        return value is not None and value != ''
    
    def modifier_is_null(self, value: Any, param: str) -> bool:
        """
        Null check: {field|is_null}
        Returns True if value is None, empty string or string "null", else False
        Used to replace is_null handling in condition parser
        """
        return value is None or value == '' or (isinstance(value, str) and value.lower() == 'null')
