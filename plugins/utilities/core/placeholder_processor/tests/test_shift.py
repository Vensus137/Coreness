"""
Тесты для модификатора shift PlaceholderProcessor
Проверка сдвига дат на интервалы (PostgreSQL style)
"""

from conftest import assert_equal


def test_shift_basic_days(processor):
    """Тест базового сдвига на дни"""
    # +1 день
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Сдвиг +1 день")
    
    # -1 день
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-1 day}", {})
    assert_equal(result, "2024-12-24", "Сдвиг -1 день")
    
    # +7 дней
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+7 days}", {})
    assert_equal(result, "2025-01-01", "Сдвиг +7 дней (переход года)")


def test_shift_hours_minutes(processor):
    """Тест сдвига на часы и минуты"""
    # +2 часа
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+2 hours}", {})
    assert_equal(result, "2024-12-25 17:30:00", "Сдвиг +2 часа")
    
    # -3 часа
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:-3 hours}", {})
    assert_equal(result, "2024-12-25 12:30:00", "Сдвиг -3 часа")
    
    # +30 минут
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+30 minutes}", {})
    assert_equal(result, "2024-12-25 16:00:00", "Сдвиг +30 минут")


def test_shift_weeks(processor):
    """Тест сдвига на недели"""
    # +1 неделя
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 week}", {})
    assert_equal(result, "2025-01-01", "Сдвиг +1 неделя")
    
    # -2 недели
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-2 weeks}", {})
    assert_equal(result, "2024-12-11", "Сдвиг -2 недели")


def test_shift_months(processor):
    """Тест сдвига на месяцы"""
    # +1 месяц
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 month}", {})
    assert_equal(result, "2025-01-25", "Сдвиг +1 месяц")
    
    # -3 месяца
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-3 months}", {})
    assert_equal(result, "2024-09-25", "Сдвиг -3 месяца")
    
    # Край месяца: 31 января + 1 месяц
    result = processor.process_text_placeholders("{'2024-01-31'|shift:+1 month}", {})
    # relativedelta корректно обрабатывает: 31 января + 1 месяц = 29 февраля (високосный год)
    assert_equal(result, "2024-02-29", "Край месяца: 31 янв + 1 месяц")


def test_shift_years(processor):
    """Тест сдвига на годы"""
    # +1 год
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 year}", {})
    assert_equal(result, "2025-12-25", "Сдвиг +1 год")
    
    # -2 года
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-2 years}", {})
    assert_equal(result, "2022-12-25", "Сдвиг -2 года")
    
    # Високосный год: 29 февраля + 1 год
    result = processor.process_text_placeholders("{'2024-02-29'|shift:+1 year}", {})
    # relativedelta корректно обрабатывает: 29 февр + 1 год = 28 февр (невисокосный год)
    assert_equal(result, "2025-02-28", "Високосный год: 29 февр + 1 год")


def test_shift_complex_intervals(processor):
    """Тест сложных интервалов (несколько единиц)"""
    # +1 год 2 месяца
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 year 2 months}", {})
    assert_equal(result, "2026-02-25", "Сдвиг +1 год 2 месяца")
    
    # +1 неделя 3 дня
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 week 3 days}", {})
    assert_equal(result, "2025-01-04", "Сдвиг +1 неделя 3 дня")
    
    # -1 день 12 часов
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:-1 day 12 hours}", {})
    assert_equal(result, "2024-12-24 03:30:00", "Сдвиг -1 день 12 часов")


def test_shift_different_input_formats(processor):
    """Тест разных входных форматов дат"""
    # PostgreSQL формат (YYYY-MM-DD)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "PostgreSQL формат даты")
    
    # Наш формат (dd.mm.yyyy)
    result = processor.process_text_placeholders("{'25.12.2024'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Наш формат даты")
    
    # PostgreSQL формат с временем
    result = processor.process_text_placeholders("{'2024-12-25 15:30:45'|shift:+1 hour}", {})
    assert_equal(result, "2024-12-25 16:30:45", "PostgreSQL формат datetime")
    
    # Наш формат с временем
    result = processor.process_text_placeholders("{'25.12.2024 15:30'|shift:+2 hours}", {})
    assert_equal(result, "2024-12-25 17:30:00", "Наш формат datetime")
    
    # Unix timestamp
    # 1735128000 = 2024-12-25 12:00:00 UTC
    result = processor.process_text_placeholders("{'1735128000'|shift:+1 day}", {})
    # Результат зависит от timezone, проверяем что не вернулся исходный timestamp
    assert result != "1735128000", "Unix timestamp обрабатывается"


def test_shift_case_insensitive(processor):
    """Тест case-insensitive парсинга единиц времени"""
    # Верхний регистр
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 DAY}", {})
    assert_equal(result, "2024-12-26", "Верхний регистр: DAY")
    
    # Смешанный регистр
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 Month}", {})
    assert_equal(result, "2025-01-25", "Смешанный регистр: Month")
    
    # Комбинация
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 YEAR 2 months}", {})
    assert_equal(result, "2026-02-25", "Смешанный регистр: YEAR + months")


def test_shift_single_plural_forms(processor):
    """Тест единственного и множественного числа"""
    # Единственное число
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Единственное: day")
    
    # Множественное число
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+2 days}", {})
    assert_equal(result, "2024-12-27", "Множественное: days")
    
    # Сокращения
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 d}", {})
    assert_equal(result, "2024-12-26", "Сокращение: d")
    
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 y}", {})
    assert_equal(result, "2025-12-25", "Сокращение: y")


def test_shift_with_chain(processor):
    """Тест цепочки модификаторов с shift"""
    # shift + format
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day|format:date}", {})
    assert_equal(result, "26.12.2024", "shift + format:date")
    
    # shift + shift (двойной сдвиг)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 year|shift:+6 months}", {})
    assert_equal(result, "2026-06-25", "Двойной shift: +1.5 года")
    
    # shift + format:datetime
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+1 day|format:datetime}", {})
    assert_equal(result, "26.12.2024 15:30", "shift + format:datetime")


def test_shift_with_dict_values(processor):
    """Тест shift с обычными плейсхолдерами (не литералами)"""
    values = {
        "created": "2024-12-25",
        "updated": "2024-12-25 15:30:00"
    }
    
    result = processor.process_text_placeholders("{created|shift:+1 day}", values)
    assert_equal(result, "2024-12-26", "shift с dict значением (дата)")
    
    result = processor.process_text_placeholders("{updated|shift:+2 hours}", values)
    assert_equal(result, "2024-12-25 17:30:00", "shift с dict значением (datetime)")


def test_shift_error_handling(processor):
    """Тест обработки ошибок"""
    # Нет знака + или -
    result = processor.process_text_placeholders("{'2024-12-25'|shift:1 day}", {})
    assert_equal(result, "2024-12-25", "Без знака возвращает исходное значение")
    
    # Неверный формат даты
    result = processor.process_text_placeholders("{'invalid-date'|shift:+1 day}", {})
    assert_equal(result, "invalid-date", "Неверная дата возвращает исходное значение")
    
    # Неверный интервал
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 invalid}", {})
    assert_equal(result, "2024-12-25", "Неверный интервал возвращает исходное значение")


def test_shift_preserves_time_presence(processor):
    """Тест сохранения наличия времени в выводе"""
    # Если входная дата без времени, выход тоже без времени
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Дата без времени остается без времени")
    
    # Если входная дата с временем, выход тоже с временем
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26 15:30:00", "Дата с временем остается с временем")


def test_shift_abbreviated_units(processor):
    """Тест сокращенных единиц времени"""
    # y (year)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 y}", {})
    assert_equal(result, "2025-12-25", "Сокращение: y")
    
    # mon (month)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+2 mon}", {})
    assert_equal(result, "2025-02-25", "Сокращение: mon")
    
    # w (week)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 w}", {})
    assert_equal(result, "2025-01-01", "Сокращение: w")
    
    # d (day)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+3 d}", {})
    assert_equal(result, "2024-12-28", "Сокращение: d")
    
    # h (hour)
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+2 h}", {})
    assert_equal(result, "2024-12-25 17:30:00", "Сокращение: h")
    
    # min (minute)
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+45 min}", {})
    assert_equal(result, "2024-12-25 16:15:00", "Сокращение: min")
    
    # sec (second)
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+30 sec}", {})
    assert_equal(result, "2024-12-25 15:30:30", "Сокращение: sec")
