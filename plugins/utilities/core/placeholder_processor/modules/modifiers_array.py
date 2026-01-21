"""
Modifiers for working with arrays
"""
from typing import Any, List


class ArrayModifiers:
    """Class with modifiers for working with arrays"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_expand(self, value: Any, param: str) -> Any:
        """
        Expanding array of arrays one level: {field|expand}
        Used for expanding dynamic keyboards in arrays
        
        Modifier doesn't change value, only marks it for expansion
        when used in array. Expansion happens in _process_list_optimized.
        
        Examples:
        - {keyboard|expand} in inline: ["{keyboard|expand}", ...] will expand array of arrays one level
        - [[a, b], [c, d]] when used with expand in array becomes [a, b, c, d]
        """
        # Modifier doesn't change value, only returns it as is
        # Expansion happens in _process_list_optimized when expand modifier is detected
        return value
    
    def modifier_keys(self, value: Any, param: str) -> List:
        """Extract keys from object (dictionary): {field|keys}"""
        if value is None:
            return None
        if isinstance(value, dict):
            return list(value.keys())
        return []
