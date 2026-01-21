"""
Basic modifiers for working with strings
"""
from typing import Any


class BasicModifiers:
    """Class with basic modifiers for working with strings"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_upper(self, value: Any, param: str) -> str:
        """Uppercase: {field|upper}"""
        return str(value).upper() if value is not None else ""
    
    def modifier_lower(self, value: Any, param: str) -> str:
        """Lowercase: {field|lower}"""
        return str(value).lower() if value is not None else ""
    
    def modifier_title(self, value: Any, param: str) -> str:
        """Title case: {field|title}"""
        return str(value).title() if value is not None else ""
    
    def modifier_capitalize(self, value: Any, param: str) -> str:
        """First letter uppercase: {field|capitalize}"""
        return str(value).capitalize() if value is not None else ""
    
    def modifier_truncate(self, value: Any, param: str) -> str:
        """Text truncation: {field|truncate:length}"""
        if not value or not param:
            return str(value) if value is not None else ""
        try:
            length = int(param)
            text = str(value)
            if len(text) <= length:
                return text
            return text[:length-3] + "..."
        except (ValueError, TypeError):
            return str(value)
    
    def modifier_length(self, value: Any, param: str) -> int:
        """Count length of string or array: {field|length}"""
        if value is None:
            return 0
        # For arrays return number of elements
        if isinstance(value, list):
            return len(value)
        # For strings and other types return length of string representation
        return len(str(value))
    
    def modifier_case(self, value: Any, param: str) -> str:
        """Case conversion: {field|case:type}"""
        if not value or not param:
            return str(value) if value is not None else ""
        
        text = str(value)
        if param == 'upper':
            return text.upper()
        elif param == 'lower':
            return text.lower()
        elif param == 'title':
            return text.title()
        elif param == 'capitalize':
            return text.capitalize()
        
        return text
    
    def modifier_regex(self, value: Any, param: str) -> str:
        """Data extraction by regex: {field|regex:pattern}"""
        if not value or not param:
            return str(value) if value is not None else ""
        
        try:
            import re

            # Compile regular expression
            pattern = re.compile(param)
            
            # Search for match
            match = pattern.search(str(value))
            
            if match:
                # Return first group (group 1) if exists, otherwise entire string (group 0)
                if match.groups():
                    return match.group(1)
                else:
                    return match.group(0)
            else:
                # If match not found, return empty string
                return ""
                
        except Exception as e:
            self.logger.warning(f"Error applying regex modifier with pattern '{param}': {e}")
            return str(value)
    
    def modifier_code(self, value: Any, param: str) -> str:
        """
        Wrapping value in code block: {field|code}
        Returns value wrapped in <code>...</code>
        Modifier order matters:
        - {items|list|code} - first list, then wrap: <code>• a\n• b</code>
        - {items|code|list} - first wrap each element, then list: • <code>a</code>\n• <code>b</code>
        """
        if value is None:
            return '<code></code>'
        if isinstance(value, list):
            # If it's a list, process each element
            return '\n'.join(f'<code>{str(item)}</code>' for item in value)
        return f'<code>{str(value)}</code>'
