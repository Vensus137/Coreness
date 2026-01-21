"""
Formatting modifiers
"""
from datetime import datetime
from typing import Any


class FormattingModifiers:
    """Class with formatting modifiers"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_format(self, value: Any, param: str) -> str:
        """Date and number formatting: {field|format:type}"""
        if not value or not param:
            return str(value) if value is not None else ""
        
        try:
            if param == 'timestamp':
                # Convert to timestamp
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return str(int(dt.timestamp()))
            elif param == 'date':
                # Date format
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return dt.strftime('%d.%m.%Y')
            elif param == 'time':
                # Time format
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return dt.strftime('%H:%M')
            elif param == 'time_full':
                # Time format with seconds
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return dt.strftime('%H:%M:%S')
            elif param == 'datetime':
                # Full date and time format
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return dt.strftime('%d.%m.%Y %H:%M')
            elif param == 'datetime_full':
                # Full date and time format with seconds
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return dt.strftime('%d.%m.%Y %H:%M:%S')
            elif param == 'pg_date':
                # Date format for PostgreSQL (YYYY-MM-DD)
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return dt.strftime('%Y-%m-%d')
            elif param == 'pg_datetime':
                # Date and time format for PostgreSQL (YYYY-MM-DD HH:MM:SS)
                if isinstance(value, str):
                    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                else:
                    dt = value
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            elif param == 'currency':
                # Currency formatting
                return f"{float(value):.2f} ₽"
            elif param == 'percent':
                # Percent formatting
                return f"{float(value):.1f}%"
            elif param == 'number':
                # Number formatting - always with two decimal places
                return f"{float(value):.2f}"
        except Exception:
            pass
        
        return str(value)
    
    def modifier_tags(self, value: Any, param: str) -> str:
        """Convert to tags: {field|tags}"""
        if not value:
            return ""
        if isinstance(value, list):
            return " ".join(f"@{str(item).lstrip('@')}" for item in value)
        return f"@{str(value).lstrip('@')}"
    
    def modifier_list(self, value: Any, param: str) -> str:
        """Bullet list: {field|list}"""
        if not value:
            return ""
        if isinstance(value, list):
            return "\n".join(f"• {str(item)}" for item in value)
        return f"• {str(value)}"
    
    def modifier_comma(self, value: Any, param: str) -> str:
        """Comma-separated: {field|comma}"""
        if not value:
            return ""
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)
