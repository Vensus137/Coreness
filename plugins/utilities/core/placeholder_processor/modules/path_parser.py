"""
Utilities for parsing paths and extracting values
"""
from typing import Any, List, Union


def parse_path_with_arrays(path: str) -> List[Union[str, int]]:
    """
    Parses path with support for arrays and dictionaries:
    'attachment[0].file_id' -> ['attachment', 0, 'file_id']
    'attachment[-1].file_id' -> ['attachment', -1, 'file_id']
    'data[0][1].value' -> ['data', 0, 1, 'value']
    'users[0].permissions[0]' -> ['users', 0, 'permissions', 0]
    'predictions[key].field' -> ['predictions', 'key', 'field']  # string key for dictionary
    """
    parts = []
    current = ""
    i = 0
    
    while i < len(path):
        char = path[i]
        
        if char == '.':
            if current:
                parts.append(current)
                current = ""
            i += 1
        elif char == '[':
            if current:
                parts.append(current)
                current = ""
            # Find closing bracket
            i += 1
            index_str = ""
            while i < len(path) and path[i] != ']':
                index_str += path[i]
                i += 1
            
            # Check that we found closing bracket
            if i >= len(path) or path[i] != ']':
                return []  # Invalid format - no closing bracket
            
            # Try to convert to number (for arrays)
            try:
                parts.append(int(index_str))
            except ValueError:
                # If not a number - it's a string key for dictionary
                parts.append(index_str)
            
            # After processing ] move to next character (already at i+1)
            i += 1
        else:
            current += char
            i += 1
    
    if current:
        parts.append(current)
    
    return parts


def get_nested_value(obj: Any, path: str) -> Any:
    """
    Gets value by path with support for arrays:
    - 'field.subfield' - regular dot notation
    - 'field[0].subfield' - array element access
    - 'field[-1].subfield' - negative indices
    - 'users[0].permissions[0]' - multiple array indices
    """
    try:
        # Parse path considering arrays
        parts = parse_path_with_arrays(path)
        
        # Check that path was parsed successfully
        # EXPECTED: Empty path or invalid format (e.g., unclosed bracket) returns None
        # This is normal behavior and doesn't cause problems in real scenarios
        if not parts:
            return None
        
        for part in parts:
            # Check that obj is not None before processing
            if obj is None:
                return None
                
            if isinstance(part, str):
                # Regular key
                if isinstance(obj, dict):
                    # First try to find key as string
                    found_value = obj.get(part)
                    # If not found, try to find as number (int or float)
                    # OPTIMIZATION: Check if part is a number before conversion
                    if found_value is None:
                        # Check if string is a number (positive or negative)
                        if part.isdigit() or (part.startswith('-') and part[1:].isdigit()):
                            # It's an integer
                            try:
                                num_key = int(part)
                                found_value = obj.get(num_key)
                            except ValueError:
                                pass
                        elif '.' in part:
                            # Possibly float
                            try:
                                float_key = float(part)
                                found_value = obj.get(float_key)
                            except ValueError:
                                pass
                    obj = found_value
                    # If still not found, return None
                    if obj is None:
                        return None
                elif hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return None
            elif isinstance(part, int):
                # Array index (numeric)
                if isinstance(obj, list):
                    # Check array bounds
                    if part < 0:
                        # Negative index: -1 = last element
                        if abs(part) <= len(obj):
                            obj = obj[part]
                        else:
                            return None
                    else:
                        # Positive index
                        if part < len(obj):
                            obj = obj[part]
                        else:
                            return None
                elif isinstance(obj, dict):
                    # If it's a dictionary, try to use as key
                    obj = obj.get(part)
                    if obj is None:
                        return None
                else:
                    return None
            else:
                # This could be a string from square brackets (for dictionaries)
                # But we already processed strings above, so this shouldn't happen
                return None
        
        return obj
    except Exception:
        return None


def extract_literal_or_get_value(field_name: str, values_dict: dict, get_nested_func) -> Any:
    """
    Extracts literal value from quotes or gets value from values_dict.
    
    Supports:
    - Single quotes: 'hello world'
    - Double quotes: "hello world"
    - Quote escaping: 'it\\'s' or "say \\"hi\\""
    
    If field_name is in quotes, returns content (without quotes).
    Otherwise, gets value from values_dict by path field_name through get_nested_func.
    """
    field_name = field_name.strip()
    
    # Check single quotes
    if len(field_name) >= 2 and field_name[0] == "'" and field_name[-1] == "'":
        # Extract content, removing outer quotes
        literal_value = field_name[1:-1]
        # Handle escaping \' -> '
        literal_value = literal_value.replace("\\'", "'")
        return literal_value
    
    # Check double quotes
    if len(field_name) >= 2 and field_name[0] == '"' and field_name[-1] == '"':
        # Extract content, removing outer quotes
        literal_value = field_name[1:-1]
        # Handle escaping \" -> "
        literal_value = literal_value.replace('\\"', '"')
        return literal_value
    
    # If not a literal, get value from values_dict
    return get_nested_func(values_dict, field_name)
