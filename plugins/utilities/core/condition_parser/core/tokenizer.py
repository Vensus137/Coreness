"""
Condition tokenizer with support for $name marker for fields
"""

import re
from typing import List, Optional

from .tokens import Token, TokenType


class ConditionTokenizer:
    """Condition tokenizer with support for $name marker"""
    
    def __init__(self):
        # Simple patterns for different token types (in priority order)
        patterns = [
            # Boolean values and None (should be before fields)
            (r'\bTrue\b', TokenType.BOOLEAN),
            (r'\bFalse\b', TokenType.BOOLEAN),
            (r'\btrue\b', TokenType.BOOLEAN),
            (r'\bfalse\b', TokenType.BOOLEAN),
            (r'\bNone\b', TokenType.NONE),
            
            # Fields with $name marker (should be before strings)
            # Support: $field, $field.subfield, $field[0], $field[0].subfield, $field[0][1]
            (r'[\$][\w\.]+(?:\[[^\]]+\])+(?:\.[\w]+)*', TokenType.FIELD),  # With arrays: at least one [index]
            (r'[\$][\w\.]+(?:\.[\w]+)*', TokenType.FIELD),  # Without arrays: only dots
            
            # String values in quotes
            (r'"[^"]*"', TokenType.STRING),
            (r"'[^']*'", TokenType.STRING),
            
            # Universal pattern for strings with multiple dots (dates, IP addresses, versions, etc.)
            # Pattern: digits, dot, digits, dot, and something else (digits, spaces, colons, etc.)
            # This should be before number pattern to avoid recognizing as numbers
            # Examples: "02.12.2012", "192.168.1.1", "1.2.3.4", "25.12.2024 15:30"
            (r'\d+\.\d+\.\d+[.\d\s:]*', TokenType.STRING),  # Strings with multiple dots
            
            # Strings starting with digit and containing letters, dashes or colons
            # Examples: "123:abc-def" (tokens), "550e8400-e29b-41d4-a716-446655440000" (UUID), "123abc-def"
            # Important: must be BEFORE number pattern to avoid recognizing as number
            # Pattern requires at least one character from [a-zA-Z\-:] immediately after digits to distinguish from pure numbers
            (r'\d+[a-zA-Z\-:][a-zA-Z0-9_\-:.]*', TokenType.STRING),  # Strings with digits and special characters
            
            # Numbers (including negative and floating point)
            (r'-?\d+\.\d+', TokenType.NUMBER),  # Floating point
            (r'-?\d+', TokenType.NUMBER),        # Integers
            
            # Special operators with "not" (should be BEFORE simple "not")
            (r'\bnot\s+is_null\b', TokenType.OPERATOR),  # "not is_null" as one token
            (r'\bnot\s+in\b', TokenType.OPERATOR),       # "not in" as one token
            
            # Logical operators (should be before comparison operators)
            (r'\band\b', TokenType.LOGICAL),
            (r'\bor\b', TokenType.LOGICAL),
            (r'\bnot\b', TokenType.LOGICAL),
            
            # Comparison operators and special operators
            (r'>=', TokenType.OPERATOR),
            (r'<=', TokenType.OPERATOR),
            (r'!=', TokenType.OPERATOR),
            (r'==', TokenType.OPERATOR),
            (r'!~', TokenType.OPERATOR),
            (r'~', TokenType.OPERATOR),
            (r'>', TokenType.OPERATOR),
            (r'<', TokenType.OPERATOR),
            
            # Special operators (should be after ~ and !~)
            (r'\bregex\b', TokenType.OPERATOR),
            (r'\bis_null\b', TokenType.OPERATOR),
            (r'\bin\b', TokenType.OPERATOR),
            
            # Universal pattern for strings (identifiers, tokens, UUID, etc.)
            # Recognizes any sequence of letters, digits, underscores, dashes, colons and dots as string
            # Examples: null, none, value, text, user_name, sk-or-v1-token, 123:abc-def, 550e8400-e29b-41d4, uuid-with-dashes
            # Important: must be AFTER all specific patterns (numbers, booleans, operators, fields)
            # to avoid intercepting already processed tokens
            (r'\b[a-zA-Z0-9_][a-zA-Z0-9_\-:.]*\b', TokenType.STRING),  # Universal pattern for strings
            
            # Brackets
            (r'\(', TokenType.BRACKET),
            (r'\)', TokenType.BRACKET),
            (r'\[', TokenType.BRACKET),
            (r'\]', TokenType.BRACKET),
            
            # Comma
            (r',', TokenType.COMMA),
        ]
        
        # Compile patterns for performance
        self._compiled_patterns = [
            (re.compile(pattern), token_type)
            for pattern, token_type in patterns
        ]
    
    def tokenize(self, expression: str) -> List[Token]:
        """Tokenizes condition expression"""
        tokens = []
        position = 0
        expression = expression.strip()
        
        while position < len(expression):
            # Skip spaces
            if expression[position].isspace():
                position += 1
                continue
            
            # Try to find match with one of patterns
            matched = False
            for pattern, token_type in self._compiled_patterns:
                match = pattern.match(expression, position)
                if match:
                    value = match.group(0)
                    end_pos = match.end()
                    
                    # For strings with multiple dots need to limit length to next operator/space
                    if token_type == TokenType.STRING and value.count('.') >= 2:
                        # Limit string to next operator or end of string
                        # Find end of string (until comparison operator, logical operator, etc.)
                        actual_end = end_pos
                        # First skip spaces at start (already captured by pattern)
                        while actual_end < len(expression) and expression[actual_end].isspace():
                            actual_end += 1
                        
                        # Now find end of string (until operator)
                        while actual_end < len(expression):
                            char = expression[actual_end]
                            # Stop on operators, brackets
                            if char in ['=', '!', '>', '<', '~', '&', '|', '(', ')', '[', ']', ',']:
                                break
                            # Stop on spaces (they separate tokens)
                            if char.isspace():
                                break
                            # Continue if it's part of string (digits, dots, colons)
                            if char.isdigit() or char in ['.', ':']:
                                actual_end += 1
                            else:
                                break
                        
                        # Remove spaces at end
                        value = expression[position:actual_end].rstrip()
                        end_pos = position + len(value)
                    
                    tokens.append(Token(token_type, value, position))
                    position = end_pos
                    matched = True
                    break
            
            if not matched:
                # Failed to recognize token - may be unknown character
                # Try to find next known token
                next_pos = position + 1
                found_next = False
                for pattern, _ in self._compiled_patterns:
                    match = pattern.match(expression, next_pos)
                    if match:
                        # Add unknown token
                        unknown_value = expression[position:next_pos]
                        tokens.append(Token(TokenType.UNKNOWN, unknown_value, position))
                        position = next_pos
                        found_next = True
                        break
                
                if not found_next:
                    # Didn't find next token - add remainder as unknown
                    unknown_value = expression[position:]
                    tokens.append(Token(TokenType.UNKNOWN, unknown_value, position))
                    break
        
        return tokens
    
    def get_field_name(self, token: Token) -> Optional[str]:
        """Extracts field name from token (removes $ marker)"""
        if token.type == TokenType.FIELD:
            return token.value[1:]  # Remove $
        return None

