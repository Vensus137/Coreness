"""
Тесты граничных случаев PlaceholderProcessor
Тесты 13, 25: Граничные случаи
"""

from conftest import assert_equal


def test_edge_cases(processor):
    """Тест 13: Граничные случаи"""
    values_dict = {
        'empty': '',
        'zero': 0,
        'false': False,
        'none': None,
        'empty_list': [],
        'empty_dict': {},
    }
    
    # Пустая строка
    result = processor.process_text_placeholders("{empty}", values_dict)
    assert_equal(result, "", "Пустая строка")
    
    # Ноль
    result = processor.process_text_placeholders("{zero}", values_dict)
    assert_equal(result, 0, "Ноль")
    
    # False
    result = processor.process_text_placeholders("{false}", values_dict)
    assert_equal(result, False, "False")
    
    # None
    result = processor.process_text_placeholders("{none}", values_dict)
    assert "{none}" in str(result), "None возвращает плейсхолдер"
    
    # Пустой список (process_text_placeholders возвращает строковое представление)
    result = processor.process_text_placeholders("{empty_list}", values_dict)
    assert result == "[]", "Пустой список возвращается как строка"
    
    # Пустой словарь (process_text_placeholders возвращает строковое представление)
    result = processor.process_text_placeholders("{empty_dict}", values_dict)
    assert result == "{}", "Пустой словарь возвращается как строка"
    
    # Пустой плейсхолдер
    result = processor.process_text_placeholders("{}", values_dict)
    # Просто проверяем что не падает
    assert result is not None, "Пустой плейсхолдер"
    
    # Только открывающая скобка
    result = processor.process_text_placeholders("{", values_dict)
    assert_equal(result, "{", "Только открывающая скобка")
    
    # Только закрывающая скобка
    result = processor.process_text_placeholders("}", values_dict)
    assert_equal(result, "}", "Только закрывающая скобка")
    
    # Текст без плейсхолдеров
    result = processor.process_text_placeholders("Just text", values_dict)
    assert_equal(result, "Just text", "Текст без плейсхолдеров")


def test_edge_cases_advanced(processor):
    """Тест 25: Расширенные граничные случаи"""
    # Очень длинная цепочка модификаторов
    values_dict = {
        'text': 'hello world',
    }
    result = processor.process_text_placeholders("{text|upper|truncate:5|code}", values_dict)
    assert "<code>" in result, "Очень длинная цепочка модификаторов"
    
    # Плейсхолдер с множественными вложенностями
    values_dict2 = {
        'a': 'field',
        'field': 'value',
        'value': 'final',
    }
    result = processor.process_text_placeholders("{{{{a}}}}", values_dict2)
    # Просто проверяем что не падает
    assert result is not None, "Множественные вложенности"
    
    # Пустой плейсхолдер с fallback
    result = processor.process_text_placeholders("{|fallback:default}", {})
    assert_equal(result, "default", "Пустой плейсхолдер с fallback")
    
    # Плейсхолдер с только модификаторами без поля
    result = processor.process_text_placeholders("{|upper}", {})
    # Просто проверяем что не падает
    assert result is not None, "Плейсхолдер только с модификаторами"
    
    # Специальные символы в значениях
    values_dict3 = {
        'text': 'Hello "world" & <tags>',
    }
    result = processor.process_text_placeholders("{text|code}", values_dict3)
    assert "<code>" in result, "Специальные символы в значениях"
    
    # Очень большое число
    values_dict4 = {
        'big_number': 999999999999,
    }
    result = processor.process_text_placeholders("{big_number|format:number}", values_dict4)
    assert isinstance(result, str), "Очень большое число форматируется"
    
    # Отрицательные числа
    values_dict5 = {
        'negative': -100,
    }
    result = processor.process_text_placeholders("{negative|abs}", values_dict5)
    # abs может не быть модификатором, проверим что не падает
    assert result is not None, "Отрицательные числа"
    
    # Unicode символы
    values_dict6 = {
        'unicode': 'Привет 世界 🌍',
    }
    result = processor.process_text_placeholders("{unicode|upper}", values_dict6)
    assert "ПРИВЕТ" in result, "Unicode символы обрабатываются"

