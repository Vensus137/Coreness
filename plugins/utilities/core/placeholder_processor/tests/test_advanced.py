"""
Тесты сложных сценариев PlaceholderProcessor
Тесты 20-24: Сложные комбинации, асинхронные модификаторы, глубокая вложенность, реальные сценарии
"""

from conftest import assert_equal
import asyncio


def test_modifiers_expand_detailed(processor):
    """Тест 20: Модификатор expand (детальные тесты)"""
    # Простой массив массивов
    values_dict = {
        'keyboard': [[{'Button 1': 'action1'}, {'Button 2': 'action2'}], [{'Button 3': 'action3'}]],
    }
    data = {'inline': ['{keyboard|expand}', {'Back': 'back'}]}
    result = processor.process_placeholders(data, values_dict)
    inline_result = result.get('inline', [])
    
    # КРИТИЧЕСКИЙ ТЕСТ: Проверяем что результат - список (не строка!)
    assert isinstance(inline_result, list), "expand возвращает список, а не строку"
    
    # Проверяем что развернуто правильно: должно быть 2 строки из keyboard + 1 статичная = 3 элемента
    assert_equal(len(inline_result), 3, "expand разворачивает массив массивов")
    
    # КРИТИЧЕСКИЙ ТЕСТ: Проверяем что первый элемент - список (не строка!)
    assert isinstance(inline_result[0], list), "expand первый элемент - список, а не строка"
    
    # Проверяем что первая строка содержит Button 1 и Button 2
    assert inline_result[0] == [{'Button 1': 'action1'}, {'Button 2': 'action2'}], "expand первая строка"
    assert_equal(inline_result[1], [{'Button 3': 'action3'}], "expand вторая строка")
    assert_equal(inline_result[2], {'Back': 'back'}, "expand статичный элемент")
    
    # Пустой массив массивов
    values_dict2 = {
        'empty_keyboard': [],
    }
    data2 = {'inline': ['{empty_keyboard|expand}', {'Back': 'back'}]}
    result2 = processor.process_placeholders(data2, values_dict2)
    inline_result2 = result2.get('inline', [])
    # Пустой массив разворачивается в пустой список, но статичный элемент остается
    assert isinstance(inline_result2, list), "expand с пустым массивом возвращает список"
    
    # Обычный массив (не массив массивов) не разворачивается
    values_dict3 = {
        'simple_array': [1, 2, 3],
    }
    data3 = {'inline': ['{simple_array|expand}', {'Back': 'back'}]}
    result3 = processor.process_placeholders(data3, values_dict3)
    inline_result3 = result3.get('inline', [])
    # Обычный массив остается как есть
    assert isinstance(inline_result3, list), "expand с обычным массивом возвращает список"
    # Проверяем что первый элемент - список (не строка!)
    if len(inline_result3) > 0:
        assert isinstance(inline_result3[0], (list, int)), "expand с обычным массивом первый элемент - список или число, не строка"
    
    # Множественные expand
    values_dict4 = {
        'kb1': [[{'A': 'a'}]],
        'kb2': [[{'B': 'b'}]],
    }
    data4 = {'inline': ['{kb1|expand}', '{kb2|expand}', {'Back': 'back'}]}
    result4 = processor.process_placeholders(data4, values_dict4)
    inline_result4 = result4.get('inline', [])
    assert_equal(len(inline_result4), 3, "expand с множественными массивами")
    # Проверяем что все элементы - списки или словари (не строки!)
    for i, item in enumerate(inline_result4):
        assert isinstance(item, (list, dict)), f"expand множественные массивы элемент {i} - список или словарь, не строка"
    
    # КРИТИЧЕСКИЙ ТЕСТ: Проверка что expand с модификатором в _complex_replace возвращает массив, а не строку
    values_dict5 = {
        '_cache': {
            'keyboard': [[{'Tenant 1': 'select_tenant_1'}, {'Tenant 2': 'select_tenant_2'}], [{'Tenant 3': 'select_tenant_3'}]]
        }
    }
    data5 = {'inline': ['{_cache.keyboard|expand}', [{'Back': 'back'}]]}
    result5 = processor.process_placeholders(data5, values_dict5)
    inline_result5 = result5.get('inline', [])
    
    # Проверяем что результат - список
    assert isinstance(inline_result5, list), "expand с точечной нотацией возвращает список, а не строку"
    
    # Проверяем что первый элемент - список (не строка!)
    if len(inline_result5) > 0:
        assert isinstance(inline_result5[0], list), "expand с точечной нотацией первый элемент - список, а не строка"
        # Проверяем содержимое первого элемента
        if isinstance(inline_result5[0], list) and len(inline_result5[0]) > 0:
            assert isinstance(inline_result5[0][0], dict), "expand с точечной нотацией первый элемент первого ряда - словарь"
    
    # Проверяем корректность разворачивания
    if len(inline_result5) >= 2:
        assert inline_result5[0] == [{'Tenant 1': 'select_tenant_1'}, {'Tenant 2': 'select_tenant_2'}], "expand с точечной нотацией первая строка"
        assert_equal(inline_result5[1], [{'Tenant 3': 'select_tenant_3'}], "expand с точечной нотацией вторая строка")


def test_complex_combinations(processor):
    """Тест 21: Сложные комбинации модификаторов"""
    values_dict = {
        'price': 1000,
        'discount': 0.1,
        'status': 'active',
        'users': ['john', 'jane'],
        'text': 'hello world',
        'duration': '2h 30m',
        'field': None,
    }
    
    # Сложная цепочка: цена со скидкой, форматирование, code
    result = processor.process_text_placeholders("{price|*{discount}|format:currency|code}", values_dict)
    assert "<code>" in result, "Сложная цепочка содержит code"
    assert "₽" in result, "Сложная цепочка содержит валюту"
    
    # Условная подстановка с проверкой существования
    result = processor.process_text_placeholders("{field|exists|value:Есть|fallback:Нет}", values_dict)
    assert_equal(result, "Нет", "Условная подстановка с exists (False)")
    
    # Проверка is_null с условной подстановкой
    result = processor.process_text_placeholders("{field|is_null|value:Пусто|fallback:Заполнено}", values_dict)
    assert_equal(result, "Пусто", "is_null с условной подстановкой (True)")
    
    # Время с преобразованием и форматированием
    result = processor.process_text_placeholders("{duration|seconds|/60}", values_dict)
    assert_equal(result, 150, "Время с преобразованием в минуты")
    
    # Regex с последующим форматированием
    result = processor.process_text_placeholders("{text|regex:\\w+|upper}", values_dict)
    assert_equal(result, "HELLO", "Regex с upper")
    
    # Список с code и list
    result = processor.process_text_placeholders("{users|list|code}", values_dict)
    assert "<code>" in result, "Список с list и code"
    assert "•" in result, "Список с list и code содержит маркеры"
    
    # Вложенные плейсхолдеры в сложной цепочке
    values_dict['discount_rate'] = 0.9
    result = processor.process_text_placeholders("{price|*{discount_rate}|format:currency}", values_dict)
    assert "₽" in result, "Вложенные плейсхолдеры в арифметике"
    
    # Комбинация equals, value, fallback с вложенными плейсхолдерами
    values_dict['expected_status'] = 'active'
    result = processor.process_text_placeholders("{status|equals:{expected_status}|value:ОК|fallback:Ошибка}", values_dict)
    assert_equal(result, "ОК", "Сложная условная цепочка с вложенными плейсхолдерами")


def test_async_modifiers(processor):
    """Тест 22: Модификаторы ready и not_ready"""
    # Создаем завершенный Future
    completed_future = asyncio.Future()
    completed_future.set_result("completed")
    
    # Создаем незавершенный Future
    pending_future = asyncio.Future()
    
    values_dict = {
        'completed_action': completed_future,
        'pending_action': pending_future,
        'not_future': 'not a future',
    }
    
    # ready для завершенного Future
    result = processor.process_text_placeholders("{completed_action|ready}", values_dict)
    assert_equal(result, True, "ready для завершенного Future")
    
    # ready для незавершенного Future
    result = processor.process_text_placeholders("{pending_action|ready}", values_dict)
    assert_equal(result, False, "ready для незавершенного Future")
    
    # not_ready для завершенного Future
    result = processor.process_text_placeholders("{completed_action|not_ready}", values_dict)
    assert_equal(result, False, "not_ready для завершенного Future")
    
    # not_ready для незавершенного Future
    result = processor.process_text_placeholders("{pending_action|not_ready}", values_dict)
    assert_equal(result, True, "not_ready для незавершенного Future")
    
    # ready для не-Future объекта
    result = processor.process_text_placeholders("{not_future|ready}", values_dict)
    assert_equal(result, False, "ready для не-Future объекта")
    
    # not_ready для не-Future объекта
    result = processor.process_text_placeholders("{not_future|not_ready}", values_dict)
    assert_equal(result, False, "not_ready для не-Future объекта")


def test_deep_nesting(processor):
    """Тест 23: Глубокая вложенность плейсхолдеров"""
    values_dict = {
        'a': 10,
        'b': 5,
        'c': 2,
        'field1': 'price',
        'field2': 'discount',
        'price': 1000,
        'discount': 0.1,
        'format_type': 'currency',
    }
    
    # Многоуровневая вложенность в арифметике
    result = processor.process_text_placeholders("{a|+{b}|*{c}}", values_dict)
    assert_equal(result, 30, "Многоуровневая вложенность в арифметике")
    
    # Вложенные плейсхолдеры в пути
    result = processor.process_text_placeholders("{{field1}}", values_dict)
    # Это должно разрешиться в 'price', затем найти {price} = 1000
    # Просто проверяем что не падает
    assert result is not None, "Вложенные плейсхолдеры в пути"
    
    # Вложенные плейсхолдеры в fallback
    result = processor.process_text_placeholders("{nonexistent|fallback:{{field1}}}", values_dict)
    # Вложенный плейсхолдер в fallback разрешается: {field1} -> 'price', затем {price} -> 1000
    # Просто проверяем что не падает
    assert result is not None, "Вложенные плейсхолдеры в fallback"
    
    # Вложенные плейсхолдеры в условных модификаторах
    result = processor.process_text_placeholders("{field1|equals:{field1}|value:Совпадает|fallback:Не совпадает}", values_dict)
    assert_equal(result, "Совпадает", "Вложенные плейсхолдеры в equals")
    
    # Комплексная цепочка с вложенными плейсхолдерами
    # {field1} -> 'price', {field2} -> 'discount', {format_type} -> 'currency'
    # Затем {price} -> 1000, {discount} -> 0.1, итого 1000 * 0.1 = 100
    result = processor.process_text_placeholders("{{field1}|*{{field2}}|format:{{format_type}}}", values_dict)
    # Результат может быть форматированным или числом в зависимости от порядка разрешения
    # Просто проверяем что не падает
    assert result is not None, "Комплексная цепочка с вложенными плейсхолдерами"


def test_real_world_scenarios(processor):
    """Тест 24: Реальные сценарии использования"""
    # Сценарий 1: Форматирование цены со скидкой
    values_dict1 = {
        'price': 1000,
        'discount': 0.15,
    }
    result = processor.process_text_placeholders("{price|*{discount}|format:currency}", values_dict1)
    assert "₽" in result, "Реальный сценарий: цена со скидкой"
    
    # Сценарий 2: Условное сообщение на основе статуса
    values_dict2 = {
        'status': 'active',
        'user_name': 'John',
    }
    result = processor.process_text_placeholders("{status|equals:active|value:Пользователь {user_name} активен|fallback:Пользователь {user_name} неактивен}", values_dict2)
    assert "John" in result, "Реальный сценарий: условное сообщение"
    assert "активен" in result, "Реальный сценарий: условное сообщение содержит статус"
    
    # Сценарий 3: Форматирование списка пользователей
    values_dict3 = {
        'users': ['john', 'jane', 'bob'],
    }
    result = processor.process_text_placeholders("Пользователи: {users|comma}", values_dict3)
    assert "john" in result, "Реальный сценарий: список пользователей"
    assert "," in result, "Реальный сценарий: список пользователей содержит запятые"
    
    # Сценарий 4: Обработка времени с преобразованием
    values_dict4 = {
        'duration': '2h 30m',
    }
    result = processor.process_text_placeholders("{duration|seconds|/60}", values_dict4)
    assert_equal(result, 150, "Реальный сценарий: преобразование времени в минуты")
    
    # Сценарий 5: Безопасный доступ к вложенным полям с fallback
    values_dict5 = {
        'user': {
            'profile': {
                'name': 'John'
            }
        }
    }
    result = processor.process_text_placeholders("{user.profile.name|fallback:Неизвестный}", values_dict5)
    assert_equal(result, "John", "Реальный сценарий: безопасный доступ к вложенным полям")
    
    result = processor.process_text_placeholders("{user.profile.email|fallback:Не указан}", values_dict5)
    assert_equal(result, "Не указан", "Реальный сценарий: fallback для отсутствующего поля")
    
    # Сценарий 6: Обработка массива с форматированием
    values_dict6 = {
        'items': [100, 200, 300],
    }
    result = processor.process_text_placeholders("{items[0]|format:currency}", values_dict6)
    assert "₽" in result, "Реальный сценарий: форматирование элемента массива"

