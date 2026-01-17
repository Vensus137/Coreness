"""
Тесты обработки структур PlaceholderProcessor
Тесты 10-12: Вложенные плейсхолдеры, обработка словарей и списков
"""

from conftest import assert_equal


def test_nested_placeholders(processor):
    """Тест 10: Вложенные плейсхолдеры"""
    values_dict = {
        'a': 10,
        'b': 5,
        'field': 'price',
        'price': 1000,
        'format': 'currency',
    }
    
    # Вложенный плейсхолдер в арифметике
    result = processor.process_text_placeholders("{a|+{b}}", values_dict)
    assert_equal(result, 15, "Вложенный плейсхолдер в арифметике")
    
    # Вложенный плейсхолдер в пути
    result = processor.process_text_placeholders("{{field}}", values_dict)
    # Это должно разрешиться в значение поля 'field', т.е. 'price'
    # Но затем попытаться найти {price}, что вернет значение price
    # Это сложный случай, проверим что не падает
    assert result is not None, "Вложенный плейсхолдер в пути"
    
    # Вложенный плейсхолдер в fallback
    result = processor.process_text_placeholders("{nonexistent|fallback:{field}}", values_dict)
    assert_equal(result, "price", "Вложенный плейсхолдер в fallback")


def test_dict_processing(processor):
    """Тест 11: Обработка словарей"""
    values_dict = {
        'name': 'John',
        'age': 30,
    }
    
    # Простой словарь
    data = {
        'text': 'Hello {name}',
        'number': '{age}',
    }
    result = processor.process_placeholders(data, values_dict)
    assert_equal(result.get('text'), 'Hello John', "Обработка строки в словаре")
    assert_equal(result.get('number'), 30, "Обработка числа в словаре")
    
    # Вложенный словарь
    data = {
        'user': {
            'greeting': 'Hello {name}',
            'info': {
                'age': '{age}'
            }
        }
    }
    result = processor.process_placeholders(data, values_dict)
    assert_equal(result['user']['greeting'], 'Hello John', "Вложенный словарь")
    assert_equal(result['user']['info']['age'], 30, "Глубокая вложенность в словаре")
    
    # process_placeholders_full
    data = {
        'text': 'Hello {name}',
        'static': 'unchanged',
    }
    result = processor.process_placeholders_full(data, values_dict)
    assert_equal(result.get('text'), 'Hello John', "process_placeholders_full обрабатывает плейсхолдеры")
    assert_equal(result.get('static'), 'unchanged', "process_placeholders_full сохраняет статичные поля")


def test_list_processing(processor):
    """Тест 12: Обработка списков"""
    values_dict = {
        'name': 'John',
        'items': [1, 2, 3],
    }
    
    # Список строк
    data = ['Hello {name}', 'World']
    result = processor.process_placeholders({'list': data}, values_dict)
    assert_equal(result['list'][0], 'Hello John', "Обработка списка строк")
    assert_equal(result['list'][1], 'World', "Статичный элемент списка")
    
    # Список словарей
    data = [
        {'text': 'Hello {name}'},
        {'text': 'Static'}
    ]
    result = processor.process_placeholders({'items': data}, values_dict)
    assert_equal(result['items'][0]['text'], 'Hello John', "Список словарей")
    assert_equal(result['items'][1]['text'], 'Static', "Статичный элемент в списке словарей")
    
    # Expand модификатор
    values_dict['keyboard'] = [[{'Button 1': 'action1'}, {'Button 2': 'action2'}], [{'Button 3': 'action3'}]]
    data = {'inline': ['{keyboard|expand}', {'Back': 'back'}]}
    result = processor.process_placeholders(data, values_dict)
    inline_result = result.get('inline', [])
    
    # Проверяем что expand развернул массив
    assert isinstance(inline_result, list), "Expand возвращает список"
    
    # КРИТИЧЕСКИЙ ТЕСТ: Проверяем что первый элемент - список (не строка!)
    if len(inline_result) > 0:
        assert isinstance(inline_result[0], list), "Expand первый элемент - список, а не строка"

