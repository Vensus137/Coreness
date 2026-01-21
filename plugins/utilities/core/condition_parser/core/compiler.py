"""
Condition compiler to Python functions
"""

import re
from typing import Any, Callable, Dict, List, Optional

from .operators import get_operator_functions
from .tokens import Token, TokenType


class ConditionCompiler:
    """Condition compiler to Python functions"""
    
    def __init__(self, logger, tokenizer):
        self.logger = logger
        self.tokenizer = tokenizer
        self._operator_functions = get_operator_functions()
    
    def compile(self, condition_string: str) -> Optional[Callable]:
        """Compiles condition string to Python function"""
        try:
            condition_stripped = condition_string.strip()
            
            # Special handling for simple boolean values
            if condition_stripped.lower() == 'true':
                return lambda data: True
            elif condition_stripped.lower() == 'false':
                return lambda data: False
            
            # Tokenize expression
            tokens = self.tokenizer.tokenize(condition_stripped)
            
            if not tokens:
                self.logger.error(f"Empty condition after tokenization: {condition_string}")
                return None
            
            # Convert tokens to Python expression
            python_expr = self._tokens_to_python_expression(tokens)
            
            if python_expr is None:
                return None
            
            # Create function to execute expression
            def compiled_function(data: Dict[str, Any]) -> bool:
                try:
                    context = {
                        'data': data,
                        'True': True,
                        'False': False,
                        'None': None,
                        'str': str,
                        'list': list,
                        'dict': dict,
                        'isinstance': isinstance,
                        'len': len,
                        'abs': abs,
                        **self._operator_functions
                    }
                    
                    return eval(python_expr, {"__builtins__": {}}, context)
                except Exception as e:
                    self.logger.error(f"Error executing expression '{python_expr}': {e}")
                    return False
            
            return compiled_function
            
        except Exception as e:
            self.logger.error(f"Error compiling condition '{condition_string}': {e}")
            return None
    
    def _tokens_to_python_expression(self, tokens: List[Token]) -> Optional[str]:
        """Converts list of tokens to Python expression"""
        result = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == TokenType.FIELD:
                # Field with marker: $user_id -> data.get("user_id")
                field_name = self.tokenizer.get_field_name(token)
                if field_name:
                    python_field = self._field_to_data_get(field_name)
                    result.append(python_field)
                else:
                    self.logger.error(f"Failed to extract field name from token: {token}")
                    return None
            
            elif token.type == TokenType.STRING:
                # String value: "text" -> "text" (already in quotes)
                # If string without quotes (e.g., date dd.mm.yyyy), add quotes
                if token.value.startswith('"') or token.value.startswith("'"):
                    result.append(token.value)
                else:
                    # Add quotes for strings without quotes
                    result.append(f"'{token.value}'")
            
            elif token.type == TokenType.NUMBER:
                # Number: 123 -> 123
                result.append(token.value)
            
            elif token.type == TokenType.BOOLEAN:
                # Boolean value: True -> True
                if token.value.lower() == 'true':
                    result.append('True')
                elif token.value.lower() == 'false':
                    result.append('False')
                else:
                    result.append(token.value)
            
            elif token.type == TokenType.NONE:
                # None -> None
                result.append('None')
            
            elif token.type == TokenType.OPERATOR:
                # Process operators
                result_len_before = len(result)
                expr, skip = self._process_operator(tokens, i, result)
                if expr is None:
                    return None
                
                # If result changed (operator removed operands from result)
                if len(result) < result_len_before:
                    result.append(expr)
                    i += 1 + skip
                elif expr:
                    result.append(expr)
                    i += 1
                else:
                    i += 1
                continue
            
            elif token.type == TokenType.LOGICAL:
                # Logical operators: and, or, not
                result.append(token.value)
            
            elif token.type == TokenType.BRACKET:
                # Brackets: ( ) [ ]
                result.append(token.value)
            
            elif token.type == TokenType.COMMA:
                # Comma: ,
                result.append(',')
            
            elif token.type == TokenType.UNKNOWN:
                # Unknown token - skip with warning
                self.logger.warning(f"Unknown token: {token.value}")
            
            i += 1
        
        # Join result
        expr = ' '.join(result)
        # Normalize spaces
        expr = re.sub(r'\s+', ' ', expr)
        # Add spaces around logical operators if missing
        expr = re.sub(r'\)\s*(and|or|not)\s*\(', r') \1 (', expr)
        expr = re.sub(r'\)\s*(and|or|not)\s*([a-zA-Z_$])', r') \1 \2', expr)
        expr = re.sub(r'([a-zA-Z_$])\s*(and|or|not)\s*\(', r'\1 \2 (', expr)
        # Remove extra spaces around brackets
        expr = re.sub(r'\s*\(\s*', '(', expr)
        expr = re.sub(r'\s*\)\s*', ')', expr)
        expr = re.sub(r'\s*,\s*', ', ', expr)
        return expr.strip()
    
    def _process_operator(
        self,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[Optional[str], int]:
        """Processes operator and returns Python expression"""
        token = tokens[index]
        operator = token.value
        
        # Comparison operators
        if operator == '==':
            return self._process_comparison_operator('safe_eq', tokens, index, result)
        elif operator == '!=':
            return self._process_comparison_operator('safe_ne', tokens, index, result)
        elif operator == '>':
            return self._process_comparison_operator('safe_gt', tokens, index, result)
        elif operator == '<':
            return self._process_comparison_operator('safe_lt', tokens, index, result)
        elif operator == '>=':
            return self._process_comparison_operator('safe_gte', tokens, index, result)
        elif operator == '<=':
            return self._process_comparison_operator('safe_lte', tokens, index, result)
        
        # String operators
        elif operator == '~':
            return self._process_string_operator('~', tokens, index, result)
        elif operator == '!~':
            return self._process_string_operator('!~', tokens, index, result)
        
        # Special operators
        elif operator == 'regex':
            return self._process_regex_operator(tokens, index, result)
        elif operator == 'is_null':
            return self._process_is_null_operator(tokens, index, result)
        elif operator == 'not is_null':
            return self._process_not_is_null_operator(tokens, index, result)
        
        # List operators
        elif operator == 'in':
            if index + 1 < len(tokens) and tokens[index + 1].value == '[':
                return self._process_in_list_operator(tokens, index, result)
            else:
                return ('in', 0)
        elif operator == 'not in':
            if index + 1 < len(tokens) and tokens[index + 1].value == '[':
                return self._process_not_in_list_operator(tokens, index, result)
            else:
                return ('not in', 0)
        
        else:
            self.logger.error(f"Unknown operator: {operator}")
            return (None, 0)
    
    def _process_comparison_operator(
        self,
        func_name: str,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[str, int]:
        """Processes comparison operator: ==, !=, >, <, >=, <="""
        if index > 0 and index + 1 < len(tokens):
            left = result[-1] if result else ''
            right_token = tokens[index + 1]
            right = self._token_to_python_value(right_token)
            
            if result:
                result.pop()
            
            return (f'{func_name}({left}, {right})', 1)
        return (func_name, 0)
    
    def _process_string_operator(
        self,
        operator: str,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[str, int]:
        """Processes string operators: ~, !~"""
        if index > 0 and index + 1 < len(tokens):
            left = result[-1] if result else ''
            right_token = tokens[index + 1]
            
            if right_token.type == TokenType.STRING:
                value = right_token.value[1:-1]  # Remove quotes
                
                if result:
                    result.pop()
                
                if operator == '~':
                    return (f'"{value}" in str({left})', 1)
                elif operator == '!~':
                    return (f'"{value}" not in str({left})', 1)
        
        return (operator, 0)
    
    def _process_regex_operator(
        self,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[str, int]:
        """Processes regex operator"""
        if index > 0 and index + 1 < len(tokens):
            left = result[-1] if result else ''
            right_token = tokens[index + 1]
            
            if right_token.type == TokenType.STRING:
                pattern = right_token.value[1:-1]  # Remove quotes
                
                if result:
                    result.pop()
                
                return (f'regex({left}, "{pattern}")', 1)
        
        return ('regex', 0)
    
    def _process_is_null_operator(
        self,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[str, int]:
        """Processes is_null operator"""
        if index > 0:
            left = result[-1] if result else ''
            
            if result:
                result.pop()
            
            return (f'is_null({left})', 0)
        
        return ('is_null', 0)
    
    def _process_not_is_null_operator(
        self,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[str, int]:
        """Processes not is_null operator"""
        if index > 0:
            left = result[-1] if result else ''
            
            if result:
                result.pop()
            
            return (f'not_is_null({left})', 0)
        
        return ('not_is_null', 0)
    
    def _process_in_list_operator(
        self,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[Optional[str], int]:
        """Processes in operator with list: field in [value1, value2, ...]"""
        if index > 0 and index + 1 < len(tokens) and tokens[index + 1].value == '[':
            left = result[-1] if result else ''
            if result:
                result.pop()
            
            # Collect list items
            list_items = []
            i = index + 2  # Skip 'in' and '['
            
            while i < len(tokens) and tokens[i].value != ']':
                if tokens[i].type == TokenType.COMMA:
                    i += 1
                    continue
                
                item_value = self._token_to_python_value(tokens[i])
                list_items.append(item_value)
                i += 1
            
            # Skip closing bracket ']' if present
            if i < len(tokens) and tokens[i].value == ']':
                i += 1
            
            # Form expression
            list_expr = f'[{", ".join(list_items)}]'
            skip_count = i - index - 1  # Skip tokens from index+1 to i-1 inclusive
            
            return (f'{left} in {list_expr}', skip_count)
        
        return ('in', 0)
    
    def _process_not_in_list_operator(
        self,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[Optional[str], int]:
        """Processes not in operator with list"""
        if index + 1 < len(tokens) and tokens[index + 1].value == '[':
            left = result[-1] if result else ''
            if result:
                result.pop()
            
            # Collect list items
            list_items = []
            i = index + 2  # Skip 'not in' (1 token) and '[' (1 token)
            
            while i < len(tokens) and tokens[i].value != ']':
                if tokens[i].type == TokenType.COMMA:
                    i += 1
                    continue
                
                item_value = self._token_to_python_value(tokens[i])
                list_items.append(item_value)
                i += 1
            
            # Skip closing bracket ']' if present
            if i < len(tokens) and tokens[i].value == ']':
                i += 1
            
            list_expr = f'[{", ".join(list_items)}]'
            skip_count = i - index - 1
            
            return (f'{left} not in {list_expr}', skip_count)
        
        return ('not in', 0)
    
    def _token_to_python_value(self, token: Token) -> str:
        """Converts token to Python value"""
        if token.type == TokenType.FIELD:
            field_name = self.tokenizer.get_field_name(token)
            return self._field_to_data_get(field_name) if field_name else 'None'
        elif token.type == TokenType.STRING:
            # If string without quotes (e.g., date dd.mm.yyyy), add quotes
            if token.value.startswith('"') or token.value.startswith("'"):
                return token.value  # Already in quotes
            else:
                return f"'{token.value}'"  # Add quotes for strings without quotes
        elif token.type == TokenType.NUMBER:
            return token.value
        elif token.type == TokenType.BOOLEAN:
            return 'True' if token.value.lower() == 'true' else 'False'
        elif token.type == TokenType.NONE:
            return 'None'
        else:
            return token.value
    
    def _field_to_data_get(self, field_name: str) -> str:
        """Converts field name to data.get() call with array support"""
        import re
        
        # Process arrays [0], [0].field, [0][1], etc.
        # Find all arrays in field: field[0][1].subfield
        array_pattern = r'(\[[^\]]+\])'
        array_matches = list(re.finditer(array_pattern, field_name))
        
        if array_matches:
            # Split field into parts: base_field, arrays, remainder via dot
            first_array_pos = array_matches[0].start()
            base_field = field_name[:first_array_pos]
            rest_with_arrays = field_name[first_array_pos:]
            
            # Get base expression
            base_expr = self._field_to_data_get(base_field) if base_field else 'data'
            
            # Process all arrays and dots after them
            current_expr = base_expr
            i = 0
            
            while i < len(rest_with_arrays):
                # Find next array
                if rest_with_arrays[i] == '[':
                    # Find closing bracket
                    end_bracket = rest_with_arrays.find(']', i)
                    if end_bracket == -1:
                        break
                    
                    index = rest_with_arrays[i+1:end_bracket]  # Remove brackets
                    
                    # Add array access with check
                    try:
                        index_int = int(index)
                        if index_int < 0:
                            array_expr = f'({current_expr}[{index}] if isinstance({current_expr}, list) and len({current_expr}) >= abs({index}) else None)'
                        else:
                            array_expr = f'({current_expr}[{index}] if isinstance({current_expr}, list) and len({current_expr}) > {index} else None)'
                    except ValueError:
                        array_expr = f'({current_expr}[{index}] if isinstance({current_expr}, list) and 0 <= {index} < len({current_expr}) else None)'
                    
                    current_expr = array_expr
                    i = end_bracket + 1
                
                # Process access via dot
                elif rest_with_arrays[i] == '.':
                    # Find next dot or end of string
                    next_dot = rest_with_arrays.find('.', i + 1)
                    next_bracket = rest_with_arrays.find('[', i + 1)
                    
                    if next_dot == -1 and next_bracket == -1:
                        # Last part
                        rest_field = rest_with_arrays[i+1:]
                        parts = rest_field.split('.')
                        for part in parts:
                            current_expr = f'({current_expr}.get("{part}", {{}}) if isinstance({current_expr}, dict) else None)'
                        break
                    elif next_bracket != -1 and (next_dot == -1 or next_bracket < next_dot):
                        # Next array
                        part = rest_with_arrays[i+1:next_bracket]
                        current_expr = f'({current_expr}.get("{part}", {{}}) if isinstance({current_expr}, dict) else None)'
                        i = next_bracket
                    else:
                        # Next dot
                        part = rest_with_arrays[i+1:next_dot]
                        current_expr = f'({current_expr}.get("{part}", {{}}) if isinstance({current_expr}, dict) else None)'
                        i = next_dot
                else:
                    i += 1
            
            return current_expr
        
        # Regular processing of nested fields via dot
        parts = field_name.split('.')
        
        if len(parts) == 1:
            return f'data.get("{field_name}")'
        
        # Nested fields: message.text -> data.get("message", {}).get("text")
        result = 'data'
        for part in parts:
            result = f'{result}.get("{part}", {{}})'
        
        return result

