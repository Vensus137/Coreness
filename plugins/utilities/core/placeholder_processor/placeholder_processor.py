import re
from typing import Any, Dict, List

from .modules.object_utils import deep_merge

# Import utilities from modules
from .modules.path_parser import extract_literal_or_get_value, get_nested_value
from .modules.type_utils import determine_result_type


class PlaceholderProcessor:
    """
    High-performance placeholder processor with optimizations:
    - Precompiled regular expressions
    - Fast string checks
    - Result caching
    - Multi-level optimization
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Get settings through settings_manager
        settings = self.settings_manager.get_plugin_settings("placeholder_processor")
        
        # Settings
        self.enable_fast_check = settings.get('enable_fast_check', True)
        self.max_nesting_depth = settings.get('max_nesting_depth', 10)
        
        # Precompiled regular expressions
        # Support for one level of nesting: {...{...}...}
        # Based on this we do recursive substitution, which allows processing arbitrary depth
        self.placeholder_pattern = re.compile(r'\{((?:[^{}]|\{[^{}]*\})+)\}')
        self.modifier_pattern = re.compile(r'([^|:]+)(?::([^|]+))?')
        
        # Initialize modifiers
        self._init_modifiers()
    
    def _init_modifiers(self):
        """Initialize all available modifiers"""
        # Import all modules with modifiers
        from .modules.modifiers_arithmetic import ArithmeticModifiers
        from .modules.modifiers_array import ArrayModifiers
        from .modules.modifiers_async import AsyncModifiers
        from .modules.modifiers_basic import BasicModifiers
        from .modules.modifiers_conditional import ConditionalModifiers
        from .modules.modifiers_datetime import DatetimeModifiers
        from .modules.modifiers_formatting import FormattingModifiers
        
        # Create instances of classes with modifiers
        basic = BasicModifiers(self.logger)
        arithmetic = ArithmeticModifiers(self.logger)
        formatting = FormattingModifiers(self.logger)
        conditional = ConditionalModifiers(self.logger)
        datetime_mods = DatetimeModifiers(self.logger)
        array_mods = ArrayModifiers(self.logger)
        async_mods = AsyncModifiers(self.logger)
        
        self.modifiers = {
            # Fallback (remains in main class, as it uses _determine_result_type)
            'fallback': self._modifier_fallback,
            
            # Arithmetic
            '/': arithmetic.modifier_divide,
            '+': arithmetic.modifier_add,
            '-': arithmetic.modifier_subtract,
            '*': arithmetic.modifier_multiply,
            '%': arithmetic.modifier_modulo,
            
            # Basic string
            'upper': basic.modifier_upper,
            'lower': basic.modifier_lower,
            'title': basic.modifier_title,
            'capitalize': basic.modifier_capitalize,
            'truncate': basic.modifier_truncate,
            'length': basic.modifier_length,
            'case': basic.modifier_case,
            'regex': basic.modifier_regex,
            'code': basic.modifier_code,
            
            # Formatting
            'format': formatting.modifier_format,
            'tags': formatting.modifier_tags,
            'list': formatting.modifier_list,
            'comma': formatting.modifier_comma,
            
            # Conditional
            'equals': conditional.modifier_equals,
            'in_list': conditional.modifier_in_list,
            'true': conditional.modifier_true,
            'value': conditional.modifier_value,
            'exists': conditional.modifier_exists,
            'is_null': conditional.modifier_is_null,
            
            # Temporal (dates and time)
            'shift': datetime_mods.modifier_shift,
            'seconds': datetime_mods.modifier_seconds,
            'to_date': datetime_mods.modifier_to_date,
            'to_hour': datetime_mods.modifier_to_hour,
            'to_minute': datetime_mods.modifier_to_minute,
            'to_second': datetime_mods.modifier_to_second,
            'to_week': datetime_mods.modifier_to_week,
            'to_month': datetime_mods.modifier_to_month,
            'to_year': datetime_mods.modifier_to_year,
            
            # Arrays
            'expand': array_mods.modifier_expand,
            'keys': array_mods.modifier_keys,
            
            # Async actions
            'not_ready': async_mods.modifier_not_ready,
            'ready': async_mods.modifier_ready,
        }
    
    def process_placeholders(self, data_with_placeholders: Dict, values_dict: Dict, max_depth: int = None) -> Dict:
        """
        Universal method - processes placeholders in any dictionary,
        using values from values_dict with support for nested placeholders
        """
        try:
            # Use setting from config if max_depth not specified
            if max_depth is None:
                max_depth = self.max_nesting_depth
            
            # Single pass - nested placeholders are processed recursively
            result = self._process_object_optimized(data_with_placeholders, values_dict)
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error processing placeholders: {e}")
            return data_with_placeholders
    
    def process_placeholders_full(self, data_with_placeholders: Dict, values_dict: Dict, max_depth: int = None) -> Dict:
        """
        Processes placeholders in dictionary and returns FULL object with processed placeholders.
        Unlike process_placeholders, which returns only processed fields,
        this method returns the entire original object with replaced placeholders.
        """
        try:
            # Use setting from config if max_depth not specified
            if max_depth is None:
                max_depth = self.max_nesting_depth
            
            # Process placeholders recursively
            # _process_object_optimized already returns full object with merged nested structures
            processed_data = self._process_object_optimized(data_with_placeholders, values_dict)
            
            # Recursively merge original data with processed
            return deep_merge(data_with_placeholders, processed_data)
            
        except Exception as e:
            self.logger.error(f"❌ Error processing placeholders (full mode): {e}")
            return data_with_placeholders
    

    def process_text_placeholders(self, text: str, values_dict: Dict, max_depth: int = None) -> str:
        """
        Universal method for processing placeholders in string.
        Takes string and dictionary of values, returns processed string.
        """
        try:
            # Use setting from config if max_depth not specified
            if max_depth is None:
                max_depth = self.max_nesting_depth
            
            # Check if there are placeholders in text
            if not self._has_placeholders_fast(text):
                return text
            
            # Process string through optimized method
            result = self._process_string_optimized(text, values_dict, 0)
            
            # Ensure result is a string
            return str(result) if result is not None else text
            
        except Exception as e:
            self.logger.error(f"Error processing placeholders in text: {e}")
            return text
    
    def _process_placeholder_chain(self, placeholder: str, values_dict: Dict, depth: int = 0):
        """Processes modifier chain with support for nested placeholders"""
        # Recursion depth control
        if depth >= self.max_nesting_depth:
            self.logger.warning(f"⚠️ Maximum recursion depth ({self.max_nesting_depth}) reached for placeholder: {placeholder}")
            return f"{{{placeholder}}}"
        
        # First compute ALL inner placeholders inside current content (without outer brackets)
        if self._has_placeholders_fast(placeholder):
            try:
                def _inner_repl(m):
                    inner_content = m.group(1).strip()
                    return str(self._process_placeholder_chain(inner_content, values_dict, depth + 1))
                placeholder = self.placeholder_pattern.sub(_inner_repl, placeholder)
            except Exception as e:
                # EXPECTED: If failed to process nested placeholders (value not found, conversion error, etc.),
                # continue execution with original placeholder. This is normal behavior for cases when value is missing.
                self.logger.warning(f"Error processing nested placeholders: {e}")

        parts = placeholder.split('|')
        field_name = parts[0].strip()
        
        # Check if field_name is a literal value in quotes
        value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
        
        # If value is a string with placeholders, process recursively
        if isinstance(value, str) and self._has_placeholders_fast(value):
            value = self._process_string_optimized(value, values_dict, depth + 1)
        
        # Apply modifiers in order
        for modifier in parts[1:]:
            value = self._apply_modifier(value, modifier.strip())
        
        # Determine result type universally
        if value is not None:
            return determine_result_type(value)
        else:
            # EXPECTED: If value not found, return placeholder as string for easier debugging
            # This allows seeing which placeholders were not resolved
            return f"{{{placeholder}}}"
    
    def _process_object_optimized(self, obj: Any, values_dict: Dict) -> Dict:
        """Optimized object processing (dict, list, str)"""
        if isinstance(obj, dict):
            return self._process_dict_optimized(obj, values_dict)
        elif isinstance(obj, list):
            return self._process_list_optimized(obj, values_dict)
        elif isinstance(obj, str):
            return self._process_string_optimized(obj, values_dict, 0)
        else:
            return {}
    
    def _process_dict_optimized(self, obj: Dict, values_dict: Dict) -> Dict:
        """Optimized dictionary processing"""
        result = {}
        
        for key, value in obj.items():
            if isinstance(value, str):
                # Level 1: Fast check
                if self.enable_fast_check and not self._has_placeholders_fast(value):
                    continue
                
                # Level 2: String processing
                processed_value = self._process_string_optimized(value, values_dict, 0)
                # Compare considering possible type change
                # EXPECTED: If placeholder not resolved and remained string, it's not added to result.
                # Then _deep_merge takes original value from base, and placeholder remains string.
                # This is expected behavior for easier debugging.
                if processed_value != value or type(processed_value) is not type(value):
                    result[key] = processed_value
            
            elif isinstance(value, dict):
                # Process nested dictionary recursively
                processed_dict = self._process_dict_optimized(value, values_dict)
                # Merge original dictionary with processed fields
                # This ensures all fields will be in result, even if they didn't change
                merged_dict = {**value, **processed_dict}
                result[key] = merged_dict
            
            elif isinstance(value, list):
                processed_list = self._process_list_optimized(value, values_dict)
                if processed_list is not value:  # Add only if there are changes
                    result[key] = processed_list
        
            else:
                # Numeric values (int, float), bool, None and other types
                # Add as is, as they don't contain placeholders
                result[key] = value
        
        return result
    
    def _process_list_optimized(self, obj: List, values_dict: Dict) -> List:
        """Optimized list processing"""
        result = []
        has_changes = False
        
        for item in obj:
            if isinstance(item, str):
                # Fast check
                if self.enable_fast_check and not self._has_placeholders_fast(item):
                    result.append(item)  # Add elements without placeholders as is
                    continue
                
                # Check if placeholder contains expand modifier
                has_expand_modifier = '|expand' in item or item.endswith('|expand}')
                
                # String processing
                processed_item = self._process_string_optimized(item, values_dict, 0)
                
                # Compare considering possible type change
                if processed_item != item or type(processed_item) is not type(item):
                    has_changes = True
                    # If expand modifier used and result is array of arrays, expand it
                    if has_expand_modifier and isinstance(processed_item, list):
                        # Check if this is array of arrays
                        if processed_item and all(isinstance(subitem, list) for subitem in processed_item):
                            # Expand array of arrays one level
                            result.extend(processed_item)
                        else:
                            # Regular array add as is
                            result.append(processed_item)
                    # If result is array, and entire original element was one placeholder, expand it
                    elif isinstance(processed_item, list) and self._is_entire_placeholder(item):
                        # Expand array one level
                        result.extend(processed_item)
                    else:
                        result.append(processed_item)
                else:
                    result.append(item)
            
            elif isinstance(item, dict):
                processed_dict = self._process_dict_optimized(item, values_dict)
                # Merge original dictionary with processed fields
                # This ensures all fields will be in result, even if they didn't change
                merged_dict = {**item, **processed_dict}
                if merged_dict != item:  # Check if there were changes
                    has_changes = True
                result.append(merged_dict)
            
            elif isinstance(item, list):
                processed_list = self._process_list_optimized(item, values_dict)
                if processed_list is not item:  # Add only if there are changes
                    has_changes = True
                    result.append(processed_list)
                else:
                    # Add list even if it didn't change (important for static elements)
                    result.append(item)
        
        # EXPECTED: If no changes, return original object for optimization.
        # has_changes logic correctly tracks all changes (strings, dictionaries, lists).
        return result if has_changes else obj
    
    def _process_string_optimized(self, text: str, values_dict: Dict, depth: int = 0):
        """Optimized string processing with type preservation"""
        # Level 1: Fast check
        if self.enable_fast_check and not self._has_placeholders_fast(text):
            return text
        
        # Level 2: Simple replacement (if no modifiers)
        if self._is_simple_replacement(text):
            return self._simple_replace(text, values_dict, depth)
        
        # Level 3: Complex replacement with modifiers
        return self._complex_replace(text, values_dict, depth)
    
    def _has_placeholders_fast(self, text: str) -> bool:
        """Fast check for placeholder presence without regex"""
        return '{' in text and '}' in text
    
    def _is_simple_replacement(self, text: str) -> bool:
        """Checks if replacement is simple (without modifiers)"""
        # OPTIMIZATION: Fast check for | presence before full parsing
        if '|' not in text:
            return True
        
        # If | exists, check each placeholder for modifiers
        matches = self.placeholder_pattern.findall(text)
        for match in matches:
            if '|' in match:
                return False
        return True
    
    def _simple_replace(self, text: str, values_dict: Dict, depth: int = 0):
        """Simple replacement without modifiers with type preservation"""
        def replace_simple(match):
            field_name = match.group(1).strip()
            # Inside simple placeholder there can also be nested ones, they need to be computed first
            # But need to process nested placeholders recursively, replacing them with values,
            # to get final path for search
            if self._has_placeholders_fast(field_name):
                # Process nested placeholders, replacing them with values in string
                def _inner_repl(m):
                    inner_content = m.group(1).strip()
                    inner_value = self._process_placeholder_chain(inner_content, values_dict, depth + 1)
                    # If placeholder returned (not processed), return as is
                    if isinstance(inner_value, str) and inner_value.startswith('{') and inner_value.endswith('}'):
                        return inner_value
                    return str(inner_value)
                field_name = self.placeholder_pattern.sub(_inner_repl, field_name)
            # Use function to extract literals or values
            value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
            # In mixed text always return string
            result = str(determine_result_type(value)) if value is not None else match.group(0)
            return result
        
        # Check if there are placeholders in text
        if not self.placeholder_pattern.search(text):
            return text
        
        # If entire text is one placeholder, return value as is
        if self._is_entire_placeholder(text):
            field_name = text[1:-1].strip()
            
            if self._has_placeholders_fast(field_name):
                # If there are nested placeholders, process through _process_placeholder_chain
                # which will already return final value
                value = self._process_placeholder_chain(field_name, values_dict, depth)
                
                # If _process_placeholder_chain returned value (not None and not original placeholder)
                if value is not None:
                    # Check if it returned original placeholder as string
                    value_str = str(value)
                    if not (value_str.startswith('{') and value_str.endswith('}') and field_name in value_str):
                        return determine_result_type(value)
                # EXPECTED: If returned None or original placeholder, return original text (placeholder as string).
                # This simplifies debugging, allowing to see which placeholders were not resolved.
                return text
            # If no nested placeholders, use function to extract literals or values
            value = extract_literal_or_get_value(field_name, values_dict, get_nested_value)
            
            # EXPECTED: If value None, return original text (placeholder as string) for debugging
            return determine_result_type(value) if value is not None else text
        
        # If placeholders embedded in text, return string
        return self.placeholder_pattern.sub(replace_simple, text)
    
    def _complex_replace(self, text: str, values_dict: Dict, depth: int = 0):
        """Complex replacement with modifiers. For pure placeholder preserves result type."""
        def replace_complex(match):
            placeholder_content = match.group(1).strip()
            result = self._process_placeholder_chain(placeholder_content, values_dict, depth)
            # In mixed text always return string
            return str(result)
        
        # Iteratively expand placeholders, so after substituting inner ones
        # on next pass correctly process outer ones
        
        # If entire text is one placeholder with modifiers, preserve result type
        if self._is_entire_placeholder(text):
            placeholder_content = text[1:-1].strip()
            result = self._process_placeholder_chain(placeholder_content, values_dict, depth)
            
            # For pure placeholder preserve result type (don't convert to string)
            if result is not None:
                # Check if it returned original placeholder as string
                value_str = str(result)
                if not (value_str.startswith('{') and value_str.endswith('}') and placeholder_content in value_str):
                    return result
            # If returned None or original placeholder, return original text
            return text
        
        while True:
            if not self.placeholder_pattern.search(text):
                return text
            new_text = self.placeholder_pattern.sub(replace_complex, text)
            if new_text == text:
                return new_text
            text = new_text

    def _is_entire_placeholder(self, text: str) -> bool:
        """Checks that entire string is one placeholder with balanced brackets."""
        if not text or text[0] != '{' or text[-1] != '}':
            return False
        depth = 0
        for i, ch in enumerate(text):
            if ch == '{':
                depth += 1
                # first opening should be at position 0
                if depth == 1 and i != 0:
                    return False
            elif ch == '}':
                depth -= 1
                if depth < 0:
                    return False
                # if outer closed before end of string - this is not single placeholder
                if depth == 0 and i != len(text) - 1:
                    return False
        return depth == 0
    
    def _strip_quotes(self, text: str) -> str:
        """
        Remove surrounding quotes from parameter text.
        Handles both single (') and double (") quotes.
        Only removes if text starts and ends with same quote type.
        """
        if not text:
            return text
        
        text_stripped = text.strip()
        
        # Remove matching surrounding quotes
        if len(text_stripped) >= 2:
            first_char = text_stripped[0]
            last_char = text_stripped[-1]
            if (first_char == "'" and last_char == "'") or \
               (first_char == '"' and last_char == '"'):
                return text_stripped[1:-1]
        
        return text_stripped
    
    def _apply_modifier(self, value: Any, modifier: str) -> Any:
        """Applies one modifier"""
        # Check if modifier is arithmetic (starts with symbol)
        if modifier and modifier[0] in ['/', '+', '-', '*', '%']:
            mod_name = modifier[0]
            mod_param = modifier[1:] if len(modifier) > 1 else None
            # Strip surrounding quotes from arithmetic parameter if present
            if mod_param:
                mod_param = self._strip_quotes(mod_param)
        elif ':' in modifier:
            mod_name, mod_param = modifier.split(':', 1)
            # Strip surrounding quotes from parameter if present
            if mod_param:
                mod_param = self._strip_quotes(mod_param)
        else:
            mod_name, mod_param = modifier, None
        
        # Get modifier function
        modifier_func = self.modifiers.get(mod_name)
        if modifier_func:
            try:
                return modifier_func(value, mod_param)
            except Exception as e:
                self.logger.warning(f"Error applying modifier {mod_name}: {e}")
                return value
        
        return value
    
    # === Modifiers ===
    
    def _modifier_fallback(self, value: Any, param: str) -> Any:
        """Replacement with default: {field|fallback:default}"""
        # EXPECTED: Fallback triggers only for None and empty string.
        # False, 0, [], {} are considered valid values and don't trigger fallback.
        if value is not None and value != "":
            return value
        
        # Use universal type determination method
        if param is None:
            return None
        
        # EXPECTED: If param is empty string after strip(), returns empty string "", not None.
        # This is expected behavior for fallback: without value.
        return determine_result_type(param.strip())
    