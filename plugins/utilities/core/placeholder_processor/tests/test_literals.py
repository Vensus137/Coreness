"""
Тесты для литеральных значений в кавычках PlaceholderProcessor
Проверка работы всех модификаторов с явными значениями без values_dict
"""

from conftest import assert_equal


def test_literals_basic(processor):
    """Тест базовых литеральных значений в кавычках"""
    # Одинарные кавычки
    result = processor.process_text_placeholders("{'hello'}", {})
    assert_equal(result, "hello", "Литерал в одинарных кавычках")
    
    # Двойные кавычки
    result = processor.process_text_placeholders('{"world"}', {})
    assert_equal(result, "world", "Литерал в двойных кавычках")
    
    # Литерал с пробелами
    result = processor.process_text_placeholders("{'hello world'}", {})
    assert_equal(result, "hello world", "Литерал с пробелами")
    
    # Литерал с цифрами
    result = processor.process_text_placeholders("{'123'}", {})
    assert_equal(result, "123", "Литерал с цифрами")


def test_literals_string_modifiers(processor):
    """Тест строковых модификаторов с литералами"""
    # upper
    result = processor.process_text_placeholders("{'hello'|upper}", {})
    assert_equal(result, "HELLO", "Литерал с upper")
    
    # lower
    result = processor.process_text_placeholders("{'WORLD'|lower}", {})
    assert_equal(result, "world", "Литерал с lower")
    
    # title
    result = processor.process_text_placeholders("{'hello world'|title}", {})
    assert_equal(result, "Hello World", "Литерал с title")
    
    # capitalize
    result = processor.process_text_placeholders("{'hello world'|capitalize}", {})
    assert_equal(result, "Hello world", "Литерал с capitalize")
    
    # case:upper
    result = processor.process_text_placeholders("{'test'|case:upper}", {})
    assert_equal(result, "TEST", "Литерал с case:upper")


def test_literals_arithmetic_modifiers(processor):
    """Тест арифметических модификаторов с литералами"""
    # Сложение
    result = processor.process_text_placeholders("{'100'|+50}", {})
    assert_equal(result, 150, "Литерал с +50")
    
    # Вычитание
    result = processor.process_text_placeholders("{'100'|-30}", {})
    assert_equal(result, 70, "Литерал с -30")
    
    # Умножение
    result = processor.process_text_placeholders("{'10'|*5}", {})
    assert_equal(result, 50, "Литерал с *5")
    
    # Деление
    result = processor.process_text_placeholders("{'100'|/4}", {})
    assert_equal(result, 25, "Литерал с /4")
    
    # Остаток от деления
    result = processor.process_text_placeholders("{'10'|%3}", {})
    assert_equal(result, 1, "Литерал с %3")


def test_literals_seconds_modifier(processor):
    """Тест модификатора seconds с литералами"""
    # Простое время: 2h 30m = 2*3600 + 30*60 = 9000 секунд
    result = processor.process_text_placeholders("{'2h 30m'|seconds}", {})
    assert_equal(result, 9000, "Литерал '2h 30m' -> seconds")
    
    # Дни и недели: 1d 2w = 1*86400 + 2*604800 = 1296000 секунд
    result = processor.process_text_placeholders("{'1d 2w'|seconds}", {})
    assert_equal(result, 1296000, "Литерал '1d 2w' -> seconds")
    
    # Только минуты: 30m = 30*60 = 1800 секунд
    result = processor.process_text_placeholders("{'30m'|seconds}", {})
    assert_equal(result, 1800, "Литерал '30m' -> seconds")
    
    # Комплексное время: 1w 2d 3h 4m 5s
    # 1w = 604800, 2d = 172800, 3h = 10800, 4m = 240, 5s = 5
    # Итого: 788645
    result = processor.process_text_placeholders("{'1w 2d 3h 4m 5s'|seconds}", {})
    assert_equal(result, 788645, "Литерал комплексного времени -> seconds")


def test_literals_formatting_modifiers(processor):
    """Тест модификаторов форматирования с литералами"""
    # truncate
    result = processor.process_text_placeholders("{'long text here'|truncate:10}", {})
    assert_equal(result, "long te...", "Литерал с truncate:10")
    
    # length
    result = processor.process_text_placeholders("{'hello world'|length}", {})
    assert_equal(result, 11, "Литерал с length")
    
    # format:number
    result = processor.process_text_placeholders("{'1234.567'|format:number}", {})
    assert isinstance(result, str), "format:number возвращает строку"
    assert "1234.5" in result, "Литерал с format:number"
    
    # format:currency
    result = processor.process_text_placeholders("{'1000.5'|format:currency}", {})
    assert "₽" in result, "Литерал с format:currency"
    
    # format:percent
    result = processor.process_text_placeholders("{'25.5'|format:percent}", {})
    assert "%" in result, "Литерал с format:percent"


def test_literals_conditional_modifiers(processor):
    """Тест условных модификаторов с литералами"""
    # equals
    result = processor.process_text_placeholders("{'active'|equals:active}", {})
    assert_equal(result, True, "Литерал с equals (true)")
    
    result = processor.process_text_placeholders("{'active'|equals:inactive}", {})
    assert_equal(result, False, "Литерал с equals (false)")
    
    # in_list
    result = processor.process_text_placeholders("{'apple'|in_list:apple,orange,banana}", {})
    assert_equal(result, True, "Литерал с in_list (true)")
    
    result = processor.process_text_placeholders("{'grape'|in_list:apple,orange,banana}", {})
    assert_equal(result, False, "Литерал с in_list (false)")
    
    # exists
    result = processor.process_text_placeholders("{'value'|exists}", {})
    assert_equal(result, True, "Литерал с exists (true)")
    
    # is_null для пустой строки
    result = processor.process_text_placeholders("{''|is_null}", {})
    assert_equal(result, True, "Пустой литерал с is_null")


def test_literals_chains(processor):
    """Тест цепочек модификаторов с литералами"""
    # Цепочка: арифметика + форматирование
    result = processor.process_text_placeholders("{'1000'|*0.9|format:currency}", {})
    assert "₽" in result, "Литерал с цепочкой *0.9|format:currency"
    
    # Цепочка: строковые модификаторы
    result = processor.process_text_placeholders("{'hello world'|upper|truncate:5}", {})
    assert "HE" in result, "Литерал с цепочкой upper|truncate:5"
    
    # Цепочка: seconds + арифметика
    result = processor.process_text_placeholders("{'2h 30m'|seconds|/60}", {})
    assert_equal(result, 150, "Литерал с цепочкой seconds|/60 (минуты)")
    
    # Цепочка: fallback + upper
    result = processor.process_text_placeholders("{'default'|fallback:other|upper}", {})
    assert_equal(result, "DEFAULT", "Литерал с fallback (не срабатывает) + upper")


def test_literals_fallback(processor):
    """Тест модификатора fallback с литералами"""
    # Литерал с fallback (не должен срабатывать для непустого литерала)
    result = processor.process_text_placeholders("{'value'|fallback:default}", {})
    assert_equal(result, "value", "Литерал с fallback (не срабатывает)")
    
    # Пустой литерал с fallback
    result = processor.process_text_placeholders("{''|fallback:default}", {})
    assert_equal(result, "default", "Пустой литерал с fallback (срабатывает)")


def test_literals_mixed_with_placeholders(processor):
    """Тест комбинации литералов и обычных плейсхолдеров"""
    values_dict = {
        'name': 'John',
        'age': 25,
    }
    
    # Литерал + плейсхолдер в одной строке
    result = processor.process_text_placeholders("Hello, {'world'}! My name is {name}.", values_dict)
    assert result == "Hello, world! My name is John.", "Литерал + плейсхолдер в строке"
    
    # Литерал с модификатором + плейсхолдер
    result = processor.process_text_placeholders("{'test'|upper} - {age}", values_dict)
    assert_equal(result, "TEST - 25", "Литерал с модификатором + плейсхолдер")


def test_literals_with_special_characters(processor):
    """Тест литералов со специальными символами"""
    # Литерал с экранированной одинарной кавычкой
    result = processor.process_text_placeholders("{'it\\'s working'}", {})
    assert_equal(result, "it's working", "Литерал с экранированной одинарной кавычкой")
    
    # Литерал с экранированной двойной кавычкой
    result = processor.process_text_placeholders('{" say \\"hi\\" "}', {})
    assert_equal(result, ' say "hi" ', "Литерал с экранированной двойной кавычкой")


def test_literals_code_modifier(processor):
    """Тест модификатора code с литералами"""
    # Простая строка оборачивается в code
    result = processor.process_text_placeholders("{'hello'|code}", {})
    assert_equal(result, "<code>hello</code>", "Литерал с code")
    
    # Число оборачивается в code
    result = processor.process_text_placeholders("{'123'|code}", {})
    assert_equal(result, "<code>123</code>", "Литерал числа с code")


def test_literals_regex_modifier(processor):
    """Тест модификатора regex с литералами"""
    # Извлечение чисел
    result = processor.process_text_placeholders("{'Hello 123 World'|regex:\\d+}", {})
    assert_equal(result, "123", "Литерал с regex для извлечения чисел")
    
    # Извлечение времени
    result = processor.process_text_placeholders("{'Meeting at 2h 30m'|regex:(?:\\d+\\s*[dhms]\\s*)+}", {})
    assert "2h" in result, "Литерал с regex для извлечения времени"
    assert "30m" in result, "Литерал с regex для извлечения времени"


def test_literals_edge_cases(processor):
    """Тест граничных случаев с литералами"""
    # Пустая строка в кавычках
    result = processor.process_text_placeholders("{''}", {})
    assert_equal(result, "", "Пустой литерал")
    
    # Литерал с только пробелами
    result = processor.process_text_placeholders("{'   '}", {})
    assert_equal(result, "   ", "Литерал с пробелами")
    
    # Литерал с переносом строки (если поддерживается)
    result = processor.process_text_placeholders("{'line1\\nline2'}", {})
    # Проверяем что не падает и возвращает что-то осмысленное
    assert isinstance(result, str), "Литерал с переносом строки"


def test_literals_type_preservation(processor):
    """Тест сохранения типов при использовании литералов"""
    # Литерал числа возвращает число (после обработки _determine_result_type)
    result = processor.process_text_placeholders("{'123'}", {})
    # _determine_result_type преобразует '123' в int(123)
    assert_equal(result, 123, "Литерал числа возвращает int")
    
    # Литерал float
    result = processor.process_text_placeholders("{'123.45'}", {})
    # _determine_result_type преобразует '123.45' в float(123.45)
    assert_equal(result, 123.45, "Литерал float возвращает float")
    
    # Литерал boolean
    result = processor.process_text_placeholders("{'true'}", {})
    # _determine_result_type преобразует 'true' в True
    assert_equal(result, True, "Литерал 'true' возвращает True")
    
    result = processor.process_text_placeholders("{'false'}", {})
    # _determine_result_type преобразует 'false' в False
    assert_equal(result, False, "Литерал 'false' возвращает False")
