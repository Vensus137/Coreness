"""
Утилиты для определения типов значений
"""
import json
from typing import Any


def determine_result_type(value: Any) -> Any:
    """
    Универсальный метод определения типа результата.
    Возвращает значение в наиболее подходящем типе.
    """
    if value is None:
        return None
    
    # Если это не строка, возвращаем как есть
    if not isinstance(value, str):
        return value
    
    # ОПТИМИЗАЦИЯ: Вычисляем strip() один раз и кэшируем результат
    value_stripped = value.strip()
    
    # Если это пустая строка, возвращаем как есть
    if not value_stripped:
        return value
    
    # Проверяем на JSON-массивы и объекты (должно начинаться с [ или {)
    if value_stripped.startswith('[') and value_stripped.endswith(']'):
        try:
            parsed = json.loads(value_stripped)
            # Если успешно распарсили массив или объект, возвращаем его
            if isinstance(parsed, (list, dict)):
                return parsed
        except (json.JSONDecodeError, ValueError):
            # Если не удалось распарсить, продолжаем дальше
            pass
    
    # ОПТИМИЗАЦИЯ: Вычисляем lower() один раз и кэшируем результат
    value_lower = value_stripped.lower()
    
    # Проверяем на булевы значения
    if value_lower == 'true':
        return True
    elif value_lower == 'false':
        return False
    
    # Проверяем на числа (включая форматированные)
    try:
        # Сначала проверяем, есть ли символы форматирования
        if '₽' in value or '%' in value:
            # Для валют и процентов сохраняем как строки
            return value
        
        # Для обычных чисел проверяем на число
        # ОЖИДАЕМО: Если строка содержит подчеркивание, это не число (подчеркивание используется в идентификаторах).
        # Это осознанное решение, даже если Python поддерживает подчеркивания в числах (1_000).
        if '_' in value:
            # Строка с подчеркиванием - это не число, возвращаем как строку
            return value
        
        # ОЖИДАЕМО: "123.0" преобразуется в float(123.0), а не int(123).
        # Это ожидаемое поведение - сохраняем исходный формат числа.
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        pass
    
    # По умолчанию возвращаем строку
    return value
