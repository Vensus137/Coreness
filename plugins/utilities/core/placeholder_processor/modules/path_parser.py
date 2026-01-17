"""
Утилиты для парсинга путей и извлечения значений
"""
from typing import Any, List, Union


def parse_path_with_arrays(path: str) -> List[Union[str, int]]:
    """
    Парсит путь с поддержкой массивов и словарей:
    'attachment[0].file_id' -> ['attachment', 0, 'file_id']
    'attachment[-1].file_id' -> ['attachment', -1, 'file_id']
    'data[0][1].value' -> ['data', 0, 1, 'value']
    'users[0].permissions[0]' -> ['users', 0, 'permissions', 0]
    'predictions[key].field' -> ['predictions', 'key', 'field']  # строковый ключ для словаря
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
            # Ищем закрывающую скобку
            i += 1
            index_str = ""
            while i < len(path) and path[i] != ']':
                index_str += path[i]
                i += 1
            
            # Проверяем что нашли закрывающую скобку
            if i >= len(path) or path[i] != ']':
                return []  # Неверный формат - нет закрывающей скобки
            
            # Пытаемся преобразовать в число (для массивов)
            try:
                parts.append(int(index_str))
            except ValueError:
                # Если не число - это строковый ключ для словаря
                parts.append(index_str)
            
            # После обработки ] переходим на следующий символ (уже на i+1)
            i += 1
        else:
            current += char
            i += 1
    
    if current:
        parts.append(current)
    
    return parts


def get_nested_value(obj: Any, path: str) -> Any:
    """
    Получает значение по пути с поддержкой массивов:
    - 'field.subfield' - обычная точечная нотация
    - 'field[0].subfield' - доступ к элементу массива
    - 'field[-1].subfield' - отрицательные индексы
    - 'users[0].permissions[0]' - множественные индексы массивов
    """
    try:
        # Парсим путь с учетом массивов
        parts = parse_path_with_arrays(path)
        
        # Проверяем что путь распарсен успешно
        # ОЖИДАЕМО: Пустой путь или неверный формат (например, незакрытая скобка) возвращает None
        # Это нормальное поведение и не создает проблем в реальных сценариях
        if not parts:
            return None
        
        for part in parts:
            # Проверяем что obj не None перед обработкой
            if obj is None:
                return None
                
            if isinstance(part, str):
                # Обычный ключ
                if isinstance(obj, dict):
                    # Сначала пытаемся найти ключ как строку
                    found_value = obj.get(part)
                    # Если не нашли, пытаемся найти как число (int или float)
                    # ОПТИМИЗАЦИЯ: Проверяем, является ли part числом, до преобразования
                    if found_value is None:
                        # Проверяем, является ли строка числом (положительным или отрицательным)
                        if part.isdigit() or (part.startswith('-') and part[1:].isdigit()):
                            # Это целое число
                            try:
                                num_key = int(part)
                                found_value = obj.get(num_key)
                            except ValueError:
                                pass
                        elif '.' in part:
                            # Возможно float
                            try:
                                float_key = float(part)
                                found_value = obj.get(float_key)
                            except ValueError:
                                pass
                    obj = found_value
                    # Если все еще не нашли, возвращаем None
                    if obj is None:
                        return None
                elif hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return None
            elif isinstance(part, int):
                # Индекс массива (числовой)
                if isinstance(obj, list):
                    # Проверяем границы массива
                    if part < 0:
                        # Отрицательный индекс: -1 = последний элемент
                        if abs(part) <= len(obj):
                            obj = obj[part]
                        else:
                            return None
                    else:
                        # Положительный индекс
                        if part < len(obj):
                            obj = obj[part]
                        else:
                            return None
                elif isinstance(obj, dict):
                    # Если это словарь, пытаемся использовать как ключ
                    obj = obj.get(part)
                    if obj is None:
                        return None
                else:
                    return None
            else:
                # Это может быть строка из квадратных скобок (для словарей)
                # Но мы уже обработали строки выше, так что это не должно произойти
                return None
        
        return obj
    except Exception:
        return None


def extract_literal_or_get_value(field_name: str, values_dict: dict, get_nested_func) -> Any:
    """
    Извлекает литеральное значение из кавычек или получает значение из values_dict.
    
    Поддерживает:
    - Одинарные кавычки: 'hello world'
    - Двойные кавычки: "hello world"
    - Экранирование кавычек: 'it\\'s' или "say \\"hi\\""
    
    Если field_name в кавычках, возвращает содержимое (без кавычек).
    Иначе, получает значение из values_dict по пути field_name через get_nested_func.
    """
    field_name = field_name.strip()
    
    # Проверяем одинарные кавычки
    if len(field_name) >= 2 and field_name[0] == "'" and field_name[-1] == "'":
        # Извлекаем содержимое, убирая внешние кавычки
        literal_value = field_name[1:-1]
        # Обрабатываем экранирование \' -> '
        literal_value = literal_value.replace("\\'", "'")
        return literal_value
    
    # Проверяем двойные кавычки
    if len(field_name) >= 2 and field_name[0] == '"' and field_name[-1] == '"':
        # Извлекаем содержимое, убирая внешние кавычки
        literal_value = field_name[1:-1]
        # Обрабатываем экранирование \" -> "
        literal_value = literal_value.replace('\\"', '"')
        return literal_value
    
    # Если это не литерал, получаем значение из values_dict
    return get_nested_func(values_dict, field_name)
