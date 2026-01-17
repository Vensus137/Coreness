"""
Базовые модификаторы для работы со строками
"""
from typing import Any


class BasicModifiers:
    """Класс с базовыми модификаторами для работы со строками"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def modifier_upper(self, value: Any, param: str) -> str:
        """Верхний регистр: {field|upper}"""
        return str(value).upper() if value is not None else ""
    
    def modifier_lower(self, value: Any, param: str) -> str:
        """Нижний регистр: {field|lower}"""
        return str(value).lower() if value is not None else ""
    
    def modifier_title(self, value: Any, param: str) -> str:
        """Заглавные буквы: {field|title}"""
        return str(value).title() if value is not None else ""
    
    def modifier_capitalize(self, value: Any, param: str) -> str:
        """Первая заглавная: {field|capitalize}"""
        return str(value).capitalize() if value is not None else ""
    
    def modifier_truncate(self, value: Any, param: str) -> str:
        """Обрезка текста: {field|truncate:length}"""
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
        """Подсчет длины строки или массива: {field|length}"""
        if value is None:
            return 0
        # Для массивов возвращаем количество элементов
        if isinstance(value, list):
            return len(value)
        # Для строк и других типов возвращаем длину строкового представления
        return len(str(value))
    
    def modifier_case(self, value: Any, param: str) -> str:
        """Преобразование регистра: {field|case:type}"""
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
        """Извлечение данных по regex: {field|regex:pattern}"""
        if not value or not param:
            return str(value) if value is not None else ""
        
        try:
            import re

            # Компилируем регулярное выражение
            pattern = re.compile(param)
            
            # Ищем совпадение
            match = pattern.search(str(value))
            
            if match:
                # Возвращаем первую группу (группа 1), если она есть, иначе всю строку (группа 0)
                if match.groups():
                    return match.group(1)
                else:
                    return match.group(0)
            else:
                # Если совпадение не найдено, возвращаем пустую строку
                return ""
                
        except Exception as e:
            self.logger.warning(f"Ошибка применения regex модификатора с паттерном '{param}': {e}")
            return str(value)
    
    def modifier_code(self, value: Any, param: str) -> str:
        """
        Оборачивание значения в code блок: {field|code}
        Возвращает значение обернутое в <code>...</code>
        Порядок модификаторов имеет значение:
        - {items|list|code} - сначала список, потом обертка: <code>• a\n• b</code>
        - {items|code|list} - сначала обертка каждого элемента, потом список: • <code>a</code>\n• <code>b</code>
        """
        if value is None:
            return '<code></code>'
        if isinstance(value, list):
            # Если это список, обрабатываем каждый элемент
            return '\n'.join(f'<code>{str(item)}</code>' for item in value)
        return f'<code>{str(value)}</code>'
