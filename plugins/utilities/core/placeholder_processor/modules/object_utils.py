"""
Утилиты для работы с объектами (словари, списки)
"""
from typing import Dict


def deep_merge(base: Dict, updates: Dict) -> Dict:
    """
    Рекурсивно объединяет два словаря, сохраняя все поля из base и обновляя их значениями из updates
    """
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Рекурсивно объединяем вложенные словари
            result[key] = deep_merge(result[key], value)
        else:
            # Обновляем значение (или добавляем новое)
            result[key] = value
    
    return result
