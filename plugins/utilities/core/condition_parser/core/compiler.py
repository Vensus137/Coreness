"""
Компилятор условий в Python функции
"""

import re
from typing import Any, Callable, Dict, List, Optional

from .operators import get_operator_functions
from .tokens import Token, TokenType


class ConditionCompiler:
    """Компилятор условий в Python функции"""
    
    def __init__(self, logger, tokenizer):
        self.logger = logger
        self.tokenizer = tokenizer
        self._operator_functions = get_operator_functions()
    
    def compile(self, condition_string: str) -> Optional[Callable]:
        """Компилирует строку условия в Python функцию"""
        try:
            condition_stripped = condition_string.strip()
            
            # Специальная обработка для простых булевых значений
            if condition_stripped.lower() == 'true':
                return lambda data: True
            elif condition_stripped.lower() == 'false':
                return lambda data: False
            
            # Токенизируем выражение
            tokens = self.tokenizer.tokenize(condition_stripped)
            
            if not tokens:
                self.logger.error(f"Пустое условие после токенизации: {condition_string}")
                return None
            
            # Преобразуем токены в Python выражение
            python_expr = self._tokens_to_python_expression(tokens)
            
            if python_expr is None:
                return None
            
            # Создаем функцию для выполнения выражения
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
                    self.logger.error(f"Ошибка выполнения выражения '{python_expr}': {e}")
                    return False
            
            return compiled_function
            
        except Exception as e:
            self.logger.error(f"Ошибка компиляции условия '{condition_string}': {e}")
            return None
    
    def _tokens_to_python_expression(self, tokens: List[Token]) -> Optional[str]:
        """Преобразует список токенов в Python выражение"""
        result = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            if token.type == TokenType.FIELD:
                # Поле с маркером: $user_id -> data.get("user_id")
                field_name = self.tokenizer.get_field_name(token)
                if field_name:
                    python_field = self._field_to_data_get(field_name)
                    result.append(python_field)
                else:
                    self.logger.error(f"Не удалось извлечь имя поля из токена: {token}")
                    return None
            
            elif token.type == TokenType.STRING:
                # Строковое значение: "text" -> "text" (уже в кавычках)
                # Если строка без кавычек (например, дата dd.mm.yyyy), добавляем кавычки
                if token.value.startswith('"') or token.value.startswith("'"):
                    result.append(token.value)
                else:
                    # Добавляем кавычки для строк без кавычек
                    result.append(f"'{token.value}'")
            
            elif token.type == TokenType.NUMBER:
                # Число: 123 -> 123
                result.append(token.value)
            
            elif token.type == TokenType.BOOLEAN:
                # Булево значение: True -> True
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
                # Обрабатываем операторы
                result_len_before = len(result)
                expr, skip = self._process_operator(tokens, i, result)
                if expr is None:
                    return None
                
                # Если результат изменился (оператор удалил операнды из результата)
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
                # Логические операторы: and, or, not
                result.append(token.value)
            
            elif token.type == TokenType.BRACKET:
                # Скобки: ( ) [ ]
                result.append(token.value)
            
            elif token.type == TokenType.COMMA:
                # Запятая: ,
                result.append(',')
            
            elif token.type == TokenType.UNKNOWN:
                # Неизвестный токен - пропускаем с предупреждением
                self.logger.warning(f"Неизвестный токен: {token.value}")
            
            i += 1
        
        # Объединяем результат
        expr = ' '.join(result)
        # Нормализуем пробелы
        expr = re.sub(r'\s+', ' ', expr)
        # Добавляем пробелы вокруг логических операторов если их нет
        expr = re.sub(r'\)\s*(and|or|not)\s*\(', r') \1 (', expr)
        expr = re.sub(r'\)\s*(and|or|not)\s*([a-zA-Z_$])', r') \1 \2', expr)
        expr = re.sub(r'([a-zA-Z_$])\s*(and|or|not)\s*\(', r'\1 \2 (', expr)
        # Убираем лишние пробелы вокруг скобок
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
        """Обрабатывает оператор и возвращает Python выражение"""
        token = tokens[index]
        operator = token.value
        
        # Операторы сравнения
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
        
        # Операторы строк
        elif operator == '~':
            return self._process_string_operator('~', tokens, index, result)
        elif operator == '!~':
            return self._process_string_operator('!~', tokens, index, result)
        
        # Специальные операторы
        elif operator == 'regex':
            return self._process_regex_operator(tokens, index, result)
        elif operator == 'is_null':
            return self._process_is_null_operator(tokens, index, result)
        elif operator == 'not is_null':
            return self._process_not_is_null_operator(tokens, index, result)
        
        # Операторы списков
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
            self.logger.error(f"Неизвестный оператор: {operator}")
            return (None, 0)
    
    def _process_comparison_operator(
        self,
        func_name: str,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[str, int]:
        """Обрабатывает оператор сравнения: ==, !=, >, <, >=, <="""
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
        """Обрабатывает операторы строк: ~, !~"""
        if index > 0 and index + 1 < len(tokens):
            left = result[-1] if result else ''
            right_token = tokens[index + 1]
            
            if right_token.type == TokenType.STRING:
                value = right_token.value[1:-1]  # Убираем кавычки
                
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
        """Обрабатывает оператор regex"""
        if index > 0 and index + 1 < len(tokens):
            left = result[-1] if result else ''
            right_token = tokens[index + 1]
            
            if right_token.type == TokenType.STRING:
                pattern = right_token.value[1:-1]  # Убираем кавычки
                
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
        """Обрабатывает оператор is_null"""
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
        """Обрабатывает оператор not is_null"""
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
        """Обрабатывает оператор in со списком: field in [value1, value2, ...]"""
        if index > 0 and index + 1 < len(tokens) and tokens[index + 1].value == '[':
            left = result[-1] if result else ''
            if result:
                result.pop()
            
            # Собираем элементы списка
            list_items = []
            i = index + 2  # Пропускаем 'in' и '['

            while i < len(tokens) and tokens[i].value != ']':
                if tokens[i].type == TokenType.COMMA:
                    i += 1
                    continue
                
                item_value = self._token_to_python_value(tokens[i])
                list_items.append(item_value)
                i += 1
            
            # Пропускаем закрывающую скобку ']' если она есть
            if i < len(tokens) and tokens[i].value == ']':
                i += 1
            
            # Формируем выражение
            list_expr = f'[{", ".join(list_items)}]'
            skip_count = i - index - 1  # Пропускаем токены от index+1 до i-1 включительно
            
            return (f'{left} in {list_expr}', skip_count)
        
        return ('in', 0)
    
    def _process_not_in_list_operator(
        self,
        tokens: List[Token],
        index: int,
        result: List[str]
    ) -> tuple[Optional[str], int]:
        """Обрабатывает оператор not in со списком"""
        if index + 1 < len(tokens) and tokens[index + 1].value == '[':
            left = result[-1] if result else ''
            if result:
                result.pop()
            
            # Собираем элементы списка
            list_items = []
            i = index + 2  # Пропускаем 'not in' (1 токен) и '[' (1 токен)
            
            while i < len(tokens) and tokens[i].value != ']':
                if tokens[i].type == TokenType.COMMA:
                    i += 1
                    continue
                
                item_value = self._token_to_python_value(tokens[i])
                list_items.append(item_value)
                i += 1
            
            # Пропускаем закрывающую скобку ']' если она есть
            if i < len(tokens) and tokens[i].value == ']':
                i += 1
            
            list_expr = f'[{", ".join(list_items)}]'
            skip_count = i - index - 1
            
            return (f'{left} not in {list_expr}', skip_count)
        
        return ('not in', 0)
    
    def _token_to_python_value(self, token: Token) -> str:
        """Преобразует токен в Python значение"""
        if token.type == TokenType.FIELD:
            field_name = self.tokenizer.get_field_name(token)
            return self._field_to_data_get(field_name) if field_name else 'None'
        elif token.type == TokenType.STRING:
            # Если строка без кавычек (например, дата dd.mm.yyyy), добавляем кавычки
            if token.value.startswith('"') or token.value.startswith("'"):
                return token.value  # Уже в кавычках
            else:
                return f"'{token.value}'"  # Добавляем кавычки для строк без кавычек
        elif token.type == TokenType.NUMBER:
            return token.value
        elif token.type == TokenType.BOOLEAN:
            return 'True' if token.value.lower() == 'true' else 'False'
        elif token.type == TokenType.NONE:
            return 'None'
        else:
            return token.value
    
    def _field_to_data_get(self, field_name: str) -> str:
        """Преобразует имя поля в вызов data.get() с поддержкой массивов"""
        import re
        
        # Обрабатываем массивы [0], [0].field, [0][1] и т.д.
        # Ищем все массивы в поле: field[0][1].subfield
        array_pattern = r'(\[[^\]]+\])'
        array_matches = list(re.finditer(array_pattern, field_name))
        
        if array_matches:
            # Разделяем поле на части: base_field, массивы, остаток через точку
            first_array_pos = array_matches[0].start()
            base_field = field_name[:first_array_pos]
            rest_with_arrays = field_name[first_array_pos:]
            
            # Получаем базовое выражение
            base_expr = self._field_to_data_get(base_field) if base_field else 'data'
            
            # Обрабатываем все массивы и точки после них
            current_expr = base_expr
            i = 0
            
            while i < len(rest_with_arrays):
                # Ищем следующий массив
                if rest_with_arrays[i] == '[':
                    # Находим закрывающую скобку
                    end_bracket = rest_with_arrays.find(']', i)
                    if end_bracket == -1:
                        break
                    
                    index = rest_with_arrays[i+1:end_bracket]  # Убираем скобки
                    
                    # Добавляем доступ к массиву с проверкой
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
                
                # Обрабатываем доступ через точку
                elif rest_with_arrays[i] == '.':
                    # Находим следующую точку или конец строки
                    next_dot = rest_with_arrays.find('.', i + 1)
                    next_bracket = rest_with_arrays.find('[', i + 1)
                    
                    if next_dot == -1 and next_bracket == -1:
                        # Последняя часть
                        rest_field = rest_with_arrays[i+1:]
                        parts = rest_field.split('.')
                        for part in parts:
                            current_expr = f'({current_expr}.get("{part}", {{}}) if isinstance({current_expr}, dict) else None)'
                        break
                    elif next_bracket != -1 and (next_dot == -1 or next_bracket < next_dot):
                        # Следующий массив
                        part = rest_with_arrays[i+1:next_bracket]
                        current_expr = f'({current_expr}.get("{part}", {{}}) if isinstance({current_expr}, dict) else None)'
                        i = next_bracket
                    else:
                        # Следующая точка
                        part = rest_with_arrays[i+1:next_dot]
                        current_expr = f'({current_expr}.get("{part}", {{}}) if isinstance({current_expr}, dict) else None)'
                        i = next_dot
                else:
                    i += 1
            
            return current_expr
        
        # Обычная обработка вложенных полей через точку
        parts = field_name.split('.')
        
        if len(parts) == 1:
            return f'data.get("{field_name}")'
        
        # Вложенные поля: message.text -> data.get("message", {}).get("text")
        result = 'data'
        for part in parts:
            result = f'{result}.get("{part}", {{}})'
        
        return result

