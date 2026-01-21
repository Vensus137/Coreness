"""
Utilities for determining value types
"""
import json
from typing import Any


def determine_result_type(value: Any) -> Any:
    """
    Universal method for determining result type.
    Returns value in most appropriate type.
    """
    if value is None:
        return None
    
    # If it's not a string, return as is
    if not isinstance(value, str):
        return value
    
    # OPTIMIZATION: Compute strip() once and cache result
    value_stripped = value.strip()
    
    # If it's empty string, return as is
    if not value_stripped:
        return value
    
    # Check for JSON arrays and objects (should start with [ or {)
    if value_stripped.startswith('[') and value_stripped.endswith(']'):
        try:
            parsed = json.loads(value_stripped)
            # If successfully parsed array or object, return it
            if isinstance(parsed, (list, dict)):
                return parsed
        except (json.JSONDecodeError, ValueError):
            # If failed to parse, continue
            pass
    
    # OPTIMIZATION: Compute lower() once and cache result
    value_lower = value_stripped.lower()
    
    # Check for boolean values
    if value_lower == 'true':
        return True
    elif value_lower == 'false':
        return False
    
    # Check for numbers (including formatted)
    try:
        # First check if there are formatting characters
        if '₽' in value or '%' in value:
            # For currency and percent keep as strings
            return value
        
        # For regular numbers check if it's a number
        # EXPECTED: If string contains underscore, it's not a number (underscore used in identifiers).
        # This is a conscious decision, even though Python supports underscores in numbers (1_000).
        if '_' in value:
            # String with underscore - not a number, return as string
            return value
        
        # EXPECTED: "123.0" converts to float(123.0), not int(123).
        # This is expected behavior - preserve original number format.
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass
    
    # By default return string
    return value
