"""
Тесты для модификаторов приведения дат к началу периода
"""

from conftest import assert_equal
import sys
from pathlib import Path

import pytest

# Динамический импорт conftest из текущей директории плагина
_test_dir = Path(__file__).parent
if str(_test_dir) not in sys.path:
    sys.path.insert(0, str(_test_dir))

# Используем фикстуру processor из conftest
# Если нужна assert_equal, импортируем её тоже
from conftest import processor  # noqa: F401


def test_to_date(processor):
    """Тест приведения к началу дня"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'date': '2024-12-25',
        'timestamp': 1735128045  # 2024-12-25 15:30:45
    }
    
    # Полная дата и время → начало дня
    result = processor.process_text_placeholders("{datetime|to_date}", values_dict)
    assert result == "2024-12-25 00:00:00"
    
    # Дата без времени → начало дня
    result = processor.process_text_placeholders("{date|to_date}", values_dict)
    assert result == "2024-12-25 00:00:00"
    
    # Timestamp → начало дня
    result = processor.process_text_placeholders("{timestamp|to_date}", values_dict)
    assert result == "2024-12-25 00:00:00"
    
    # С цепочкой форматирования
    result = processor.process_text_placeholders("{datetime|to_date|format:datetime}", values_dict)
    assert "00:00" in result


def test_to_hour(processor):
    """Тест приведения к началу часа"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'datetime_mid': '2024-12-25 15:00:00'
    }
    
    # Время 15:30:45 → 15:00:00
    result = processor.process_text_placeholders("{datetime|to_hour}", values_dict)
    assert result == "2024-12-25 15:00:00"
    
    # Время 15:00:00 → 15:00:00 (уже начало часа)
    result = processor.process_text_placeholders("{datetime_mid|to_hour}", values_dict)
    assert result == "2024-12-25 15:00:00"


def test_to_minute(processor):
    """Тест приведения к началу минуты"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'datetime_mid': '2024-12-25 15:30:00'
    }
    
    # Время 15:30:45 → 15:30:00
    result = processor.process_text_placeholders("{datetime|to_minute}", values_dict)
    assert result == "2024-12-25 15:30:00"
    
    # Время 15:30:00 → 15:30:00 (уже начало минуты)
    result = processor.process_text_placeholders("{datetime_mid|to_minute}", values_dict)
    assert result == "2024-12-25 15:30:00"


def test_to_second(processor):
    """Тест приведения к началу секунды"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'datetime_clean': '2024-12-25 15:30:45'
    }
    
    # Дата → начало секунды (без микросекунд)
    result = processor.process_text_placeholders("{datetime|to_second}", values_dict)
    assert result == "2024-12-25 15:30:45"
    
    # Дата без микросекунд → без изменений
    result = processor.process_text_placeholders("{datetime_clean|to_second}", values_dict)
    assert result == "2024-12-25 15:30:45"


def test_to_week(processor):
    """Тест приведения к началу недели (понедельник)"""
    values_dict = {
        'monday': '2024-12-23 15:30:45',    # Понедельник
        'tuesday': '2024-12-24 15:30:45',   # Вторник
        'wednesday': '2024-12-25 15:30:45', # Среда
        'sunday': '2024-12-29 15:30:45',    # Воскресенье
    }
    
    # Понедельник → понедельник 00:00:00
    result = processor.process_text_placeholders("{monday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"
    
    # Вторник → понедельник 00:00:00
    result = processor.process_text_placeholders("{tuesday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"
    
    # Среда → понедельник 00:00:00
    result = processor.process_text_placeholders("{wednesday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"
    
    # Воскресенье → понедельник предыдущей недели 00:00:00
    result = processor.process_text_placeholders("{sunday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"


def test_to_month(processor):
    """Тест приведения к началу месяца"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'first_day': '2024-12-01 15:30:45',
        'end_of_month': '2024-12-31 23:59:59'
    }
    
    # 25 декабря → 1 декабря 00:00:00
    result = processor.process_text_placeholders("{datetime|to_month}", values_dict)
    assert result == "2024-12-01 00:00:00"
    
    # 1 декабря → 1 декабря 00:00:00
    result = processor.process_text_placeholders("{first_day|to_month}", values_dict)
    assert result == "2024-12-01 00:00:00"
    
    # 31 декабря → 1 декабря 00:00:00
    result = processor.process_text_placeholders("{end_of_month|to_month}", values_dict)
    assert result == "2024-12-01 00:00:00"


def test_to_year(processor):
    """Тест приведения к началу года"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'january': '2024-01-15 15:30:45',
        'december': '2024-12-31 23:59:59'
    }
    
    # 25 декабря 2024 → 1 января 2024 00:00:00
    result = processor.process_text_placeholders("{datetime|to_year}", values_dict)
    assert result == "2024-01-01 00:00:00"
    
    # 15 января 2024 → 1 января 2024 00:00:00
    result = processor.process_text_placeholders("{january|to_year}", values_dict)
    assert result == "2024-01-01 00:00:00"
    
    # 31 декабря 2024 → 1 января 2024 00:00:00
    result = processor.process_text_placeholders("{december|to_year}", values_dict)
    assert result == "2024-01-01 00:00:00"


def test_to_period_with_literals(processor):
    """Тест приведения к периоду с литералами"""
    # Литеральная дата → начало дня
    result = processor.process_text_placeholders("{'2024-12-25 15:30:45'|to_date}", {})
    assert result == "2024-12-25 00:00:00"
    
    # Литеральная дата → начало недели
    result = processor.process_text_placeholders("{'2024-12-25'|to_week}", {})
    assert "00:00:00" in result


def test_to_period_with_chains(processor):
    """Тест приведения к периоду с цепочками модификаторов"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45'
    }
    
    # Начало дня → форматирование
    result = processor.process_text_placeholders("{datetime|to_date|format:datetime}", values_dict)
    assert "00:00" in result
    
    # Начало месяца → форматирование
    result = processor.process_text_placeholders("{datetime|to_month|format:date}", values_dict)
    assert "01.12.2024" == result


def test_to_period_edge_cases(processor):
    """Тест граничных случаев"""
    values_dict = {
        'invalid': 'invalid-date',
        'empty': '',
        'none': None
    }
    
    # Невалидная дата → возвращается исходное значение (модификатор не может обработать)
    result = processor.process_text_placeholders("{invalid|to_date}", values_dict)
    assert result == "invalid-date"  # Возвращается исходное значение
    
    # Пустая строка → возвращается исходное значение
    result = processor.process_text_placeholders("{empty|to_date}", values_dict)
    assert result == ""  # Возвращается пустая строка
    
    # None → плейсхолдер не разрешился
    result = processor.process_text_placeholders("{none|to_date}", values_dict)
    assert result == "{none|to_date}"  # Плейсхолдер не разрешился (None не обрабатывается)
