"""
Токенизатор условий с поддержкой маркера $name для полей
"""

import re
from typing import List, Optional

from .tokens import Token, TokenType


class ConditionTokenizer:
    """Токенизатор условий с поддержкой маркера $name"""
    
    def __init__(self):
        # Простые паттерны для разных типов токенов (в порядке приоритета)
        patterns = [
            # Булевы значения и None (должны быть перед полями)
            (r'\bTrue\b', TokenType.BOOLEAN),
            (r'\bFalse\b', TokenType.BOOLEAN),
            (r'\btrue\b', TokenType.BOOLEAN),
            (r'\bfalse\b', TokenType.BOOLEAN),
            (r'\bNone\b', TokenType.NONE),
            
            # Поля с маркером $name (должны быть перед строками)
            # Поддерживаем: $field, $field.subfield, $field[0], $field[0].subfield, $field[0][1]
            (r'[\$][\w\.]+(?:\[[^\]]+\])+(?:\.[\w]+)*', TokenType.FIELD),  # С массивами: хотя бы один [index]
            (r'[\$][\w\.]+(?:\.[\w]+)*', TokenType.FIELD),  # Без массивов: только точки
            
            # Строковые значения в кавычках
            (r'"[^"]*"', TokenType.STRING),
            (r"'[^']*'", TokenType.STRING),
            
            # Универсальный паттерн для строк с несколькими точками (даты, IP-адреса, версии и т.д.)
            # Паттерн: цифры, точка, цифры, точка, и еще что-то (цифры, пробелы, двоеточия и т.д.)
            # Это должно быть перед паттерном чисел, чтобы не распознавать как числа
            # Примеры: "02.12.2012", "192.168.1.1", "1.2.3.4", "25.12.2024 15:30"
            (r'\d+\.\d+\.\d+[.\d\s:]*', TokenType.STRING),  # Строки с несколькими точками
            
            # Строки, начинающиеся с цифры и содержащие буквы, дефисы или двоеточия
            # Примеры: "123:abc-def" (токены), "550e8400-e29b-41d4-a716-446655440000" (UUID), "123abc-def"
            # Важно: должен быть ПЕРЕД паттерном чисел, чтобы не распознавать как число
            # Паттерн требует хотя бы один символ из [a-zA-Z\-:] сразу после цифр, чтобы отличить от чистых чисел
            (r'\d+[a-zA-Z\-:][a-zA-Z0-9_\-:.]*', TokenType.STRING),  # Строки с цифрами и специальными символами
            
            # Числа (включая отрицательные и с плавающей точкой)
            (r'-?\d+\.\d+', TokenType.NUMBER),  # С плавающей точкой
            (r'-?\d+', TokenType.NUMBER),        # Целые числа
            
            # Специальные операторы с "not" (должны быть ПЕРЕД простым "not")
            (r'\bnot\s+is_null\b', TokenType.OPERATOR),  # "not is_null" как один токен
            (r'\bnot\s+in\b', TokenType.OPERATOR),       # "not in" как один токен
            
            # Логические операторы (должны быть перед операторами сравнения)
            (r'\band\b', TokenType.LOGICAL),
            (r'\bor\b', TokenType.LOGICAL),
            (r'\bnot\b', TokenType.LOGICAL),
            
            # Операторы сравнения и специальные операторы
            (r'>=', TokenType.OPERATOR),
            (r'<=', TokenType.OPERATOR),
            (r'!=', TokenType.OPERATOR),
            (r'==', TokenType.OPERATOR),
            (r'!~', TokenType.OPERATOR),
            (r'~', TokenType.OPERATOR),
            (r'>', TokenType.OPERATOR),
            (r'<', TokenType.OPERATOR),
            
            # Специальные операторы (должны быть после ~ и !~)
            (r'\bregex\b', TokenType.OPERATOR),
            (r'\bis_null\b', TokenType.OPERATOR),
            (r'\bin\b', TokenType.OPERATOR),
            
            # Универсальный паттерн для строк (идентификаторы, токены, UUID и т.д.)
            # Распознает любую последовательность букв, цифр, подчеркиваний, дефисов, двоеточий и точек как строку
            # Примеры: null, none, value, text, user_name, sk-or-v1-token, 123:abc-def, 550e8400-e29b-41d4, uuid-with-dashes
            # Важно: должен быть ПОСЛЕ всех специфичных паттернов (числа, булевы значения, операторы, поля)
            # чтобы не перехватывать уже обработанные токены
            (r'\b[a-zA-Z0-9_][a-zA-Z0-9_\-:.]*\b', TokenType.STRING),  # Универсальный паттерн для строк
            
            # Скобки
            (r'\(', TokenType.BRACKET),
            (r'\)', TokenType.BRACKET),
            (r'\[', TokenType.BRACKET),
            (r'\]', TokenType.BRACKET),
            
            # Запятая
            (r',', TokenType.COMMA),
        ]
        
        # Компилируем паттерны для производительности
        self._compiled_patterns = [
            (re.compile(pattern), token_type)
            for pattern, token_type in patterns
        ]
    
    def tokenize(self, expression: str) -> List[Token]:
        """Токенизирует выражение условия"""
        tokens = []
        position = 0
        expression = expression.strip()
        
        while position < len(expression):
            # Пропускаем пробелы
            if expression[position].isspace():
                position += 1
                continue
            
            # Пытаемся найти совпадение с одним из паттернов
            matched = False
            for pattern, token_type in self._compiled_patterns:
                match = pattern.match(expression, position)
                if match:
                    value = match.group(0)
                    end_pos = match.end()
                    
                    # Для строк с несколькими точками нужно ограничить длину до следующего оператора/пробела
                    if token_type == TokenType.STRING and value.count('.') >= 2:
                        # Ограничиваем строку до следующего оператора или конца строки
                        # Ищем конец строки (до оператора сравнения, логического оператора и т.д.)
                        actual_end = end_pos
                        # Сначала пропускаем пробелы в начале (они уже захвачены паттерном)
                        while actual_end < len(expression) and expression[actual_end].isspace():
                            actual_end += 1
                        
                        # Теперь ищем конец строки (до оператора)
                        while actual_end < len(expression):
                            char = expression[actual_end]
                            # Останавливаемся на операторах, скобках
                            if char in ['=', '!', '>', '<', '~', '&', '|', '(', ')', '[', ']', ',']:
                                break
                            # Останавливаемся на пробелах (они разделяют токены)
                            if char.isspace():
                                break
                            # Продолжаем, если это часть строки (цифры, точки, двоеточия)
                            if char.isdigit() or char in ['.', ':']:
                                actual_end += 1
                            else:
                                break
                        
                        # Убираем пробелы в конце
                        value = expression[position:actual_end].rstrip()
                        end_pos = position + len(value)
                    
                    tokens.append(Token(token_type, value, position))
                    position = end_pos
                    matched = True
                    break
            
            if not matched:
                # Не удалось распознать токен - это может быть неизвестный символ
                # Пытаемся найти следующий известный токен
                next_pos = position + 1
                found_next = False
                for pattern, _ in self._compiled_patterns:
                    match = pattern.match(expression, next_pos)
                    if match:
                        # Добавляем неизвестный токен
                        unknown_value = expression[position:next_pos]
                        tokens.append(Token(TokenType.UNKNOWN, unknown_value, position))
                        position = next_pos
                        found_next = True
                        break
                
                if not found_next:
                    # Не нашли следующий токен - добавляем остаток как неизвестный
                    unknown_value = expression[position:]
                    tokens.append(Token(TokenType.UNKNOWN, unknown_value, position))
                    break
        
        return tokens
    
    def get_field_name(self, token: Token) -> Optional[str]:
        """Извлекает имя поля из токена (убирает маркер $)"""
        if token.type == TokenType.FIELD:
            return token.value[1:]  # Убираем $
        return None

