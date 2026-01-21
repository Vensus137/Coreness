"""
Module with classes for condition tokenization
"""

from enum import Enum


class TokenType(Enum):
    """Token types"""
    FIELD = "field"           # Field with marker: $user_id, $message.text
    STRING = "string"         # String value: "text", 'text'
    NUMBER = "number"         # Number: 123, 45.67
    BOOLEAN = "boolean"       # Boolean value: True, False, true, false
    NONE = "none"             # None
    OPERATOR = "operator"     # Operator: ==, !=, >, <, >=, <=, ~, !~, in, not in, regex, is_null, not is_null
    LOGICAL = "logical"       # Logical operator: and, or, not
    BRACKET = "bracket"       # Bracket: (, ), [, ]
    COMMA = "comma"           # Comma: ,
    UNKNOWN = "unknown"       # Unknown token


class Token:
    """Token with type and value"""
    
    def __init__(self, token_type: TokenType, value: str, position: int = 0):
        self.type = token_type
        self.value = value
        self.position = position
    
    def __repr__(self):
        return f"Token({self.type.value}, {self.value!r}, pos={self.position})"
    
    def __eq__(self, other):
        if not isinstance(other, Token):
            return False
        return self.type == other.type and self.value == other.value

