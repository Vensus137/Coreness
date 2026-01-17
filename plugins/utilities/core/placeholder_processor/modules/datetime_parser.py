"""
Утилиты для парсинга дат и временных интервалов
"""
import re
from datetime import datetime
from typing import Dict, Optional, Tuple


def parse_datetime_value(value) -> Tuple[Optional[datetime], bool]:
    """
    Конвертирует любой формат даты в datetime
    
    Поддерживаемые форматы:
    - Unix timestamp: 1735128000
    - PostgreSQL: 2024-12-25, 2024-12-25 15:30:45
    - Стандартные: 25.12.2024, 25.12.2024 15:30, 25.12.2024 15:30:45
    - ISO: 2024-12-25T15:30:45
    - datetime объекты Python
    
    Возвращает: (datetime_obj, has_time)
    - datetime_obj: объект datetime или None если не удалось распарсить
    - has_time: True если была информация о времени (не только дата)
    """
    if value is None:
        return None, False
    
    # Уже datetime объект
    if isinstance(value, datetime):
        # Проверяем, есть ли время (не 00:00:00)
        has_time = value.hour != 0 or value.minute != 0 or value.second != 0
        return value, has_time
    
    # Конвертируем в строку
    value_str = str(value).strip()
    
    if not value_str:
        return None, False
    
    # Unix timestamp (только цифры)
    if value_str.isdigit():
        try:
            return datetime.fromtimestamp(int(value_str)), True
        except (ValueError, OSError):
            pass
    
    # Пробуем разные форматы
    # Формат: (pattern, has_time)
    formats = [
        # PostgreSQL форматы
        ('%Y-%m-%d %H:%M:%S', True),
        ('%Y-%m-%d %H:%M', True),
        ('%Y-%m-%d', False),
        
        # Наши форматы (dd.mm.yyyy)
        ('%d.%m.%Y %H:%M:%S', True),
        ('%d.%m.%Y %H:%M', True),
        ('%d.%m.%Y', False),
        
        # ISO форматы
        ('%Y-%m-%dT%H:%M:%S', True),
        ('%Y-%m-%dT%H:%M', True),
    ]
    
    for fmt, has_time in formats:
        try:
            dt = datetime.strptime(value_str, fmt)
            return dt, has_time
        except ValueError:
            continue
    
    # Не удалось распарсить
    return None, False


def parse_interval_string(interval: str) -> Dict[str, int]:
    """
    Парсит интервал в PostgreSQL стиле
    
    Поддерживаемые единицы (case-insensitive, единственное/множественное число):
    - year, years, y
    - month, months, mon
    - week, weeks, w
    - day, days, d
    - hour, hours, h
    - minute, minutes, min, m
    - second, seconds, sec, s
    
    Примеры:
    - "1 day" → {"years": 0, "months": 0, ..., "days": 1, ...}
    - "2 hours 30 minutes" → {"hours": 2, "minutes": 30}
    - "1 year 2 months" → {"years": 1, "months": 2}
    - "1 YEAR 3 Days" → {"years": 1, "days": 3} (case-insensitive)
    
    Возвращает словарь с ключами: years, months, weeks, days, hours, minutes, seconds
    """
    # Паттерн: число + пробелы + единица времени
    # (?i) в начале делает паттерн case-insensitive
    pattern = r'(\d+)\s+(year|years|y|month|months|mon|week|weeks|w|day|days|d|hour|hours|h|minute|minutes|min|m|second|seconds|sec|s)\b'
    
    result = {
        'years': 0,
        'months': 0,
        'weeks': 0,
        'days': 0,
        'hours': 0,
        'minutes': 0,
        'seconds': 0
    }
    
    # Ищем все совпадения (case-insensitive)
    matches = re.findall(pattern, interval, re.IGNORECASE)
    
    if not matches:
        return result
    
    for value, unit in matches:
        value = int(value)
        unit_lower = unit.lower()
        
        # Маппинг единиц времени на ключи словаря
        if unit_lower in ['year', 'years', 'y']:
            result['years'] += value
        elif unit_lower in ['month', 'months', 'mon']:
            result['months'] += value
        elif unit_lower in ['week', 'weeks', 'w']:
            result['weeks'] += value
        elif unit_lower in ['day', 'days', 'd']:
            result['days'] += value
        elif unit_lower in ['hour', 'hours', 'h']:
            result['hours'] += value
        elif unit_lower in ['minute', 'minutes', 'min', 'm']:
            result['minutes'] += value
        elif unit_lower in ['second', 'seconds', 'sec', 's']:
            result['seconds'] += value
    
    return result
