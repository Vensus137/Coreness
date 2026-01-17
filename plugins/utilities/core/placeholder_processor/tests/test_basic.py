"""
Базовые тесты PlaceholderProcessor
Тесты 1-3: Базовые плейсхолдеры, вложенность, массивы
"""

from conftest import assert_equal


def test_basic_placeholders(processor):
    """Тест 1: Базовые плейсхолдеры"""
    values_dict = {
        'name': 'John',
        'age': 30,
        'active': True,
        'count': 0,
        'empty': '',
        'none': None,
    }
    
    # Простая замена
    result = processor.process_text_placeholders("{name}", values_dict)
    assert_equal(result, "John", "Простая замена строки")
    
    result = processor.process_text_placeholders("{age}", values_dict)
    assert_equal(result, 30, "Простая замена числа")
    
    result = processor.process_text_placeholders("{active}", values_dict)
    assert_equal(result, True, "Простая замена булева")
    
    # Неразрешенный плейсхолдер
    result = processor.process_text_placeholders("{nonexistent}", values_dict)
    assert "{nonexistent}" in str(result), "Неразрешенный плейсхолдер возвращается как строка"
    
    # Смешанный текст
    result = processor.process_text_placeholders("Hello {name}, age {age}", values_dict)
    assert result == "Hello John, age 30", "Смешанный текст"
    
    # Пустое значение
    result = processor.process_text_placeholders("{empty}", values_dict)
    assert_equal(result, "", "Пустое значение")
    
    # None значение
    result = processor.process_text_placeholders("{none}", values_dict)
    assert "{none}" in str(result), "None значение возвращает плейсхолдер"
    
    # Ноль
    result = processor.process_text_placeholders("{count}", values_dict)
    assert_equal(result, 0, "Ноль как валидное значение")


def test_nested_access(processor):
    """Тест 2: Точечная нотация и вложенный доступ"""
    values_dict = {
        'user': {
            'name': 'John',
            'profile': {
                'age': 30,
                'email': 'john@example.com',
                'settings': {
                    'theme': 'dark'
                }
            }
        },
        'data': {
            'items': [1, 2, 3],
            'meta': {
                'count': 42
            }
        }
    }
    
    # Простая точечная нотация
    result = processor.process_text_placeholders("{user.name}", values_dict)
    assert_equal(result, "John", "Простая точечная нотация")
    
    # Глубокая вложенность
    result = processor.process_text_placeholders("{user.profile.age}", values_dict)
    assert_equal(result, 30, "Глубокая вложенность")
    
    result = processor.process_text_placeholders("{user.profile.settings.theme}", values_dict)
    assert_equal(result, "dark", "Очень глубокая вложенность")
    
    # Несуществующий путь
    result = processor.process_text_placeholders("{user.nonexistent}", values_dict)
    assert "{user.nonexistent}" in str(result), "Несуществующий путь"
    
    # Вложенный доступ в словаре
    result = processor.process_text_placeholders("{data.meta.count}", values_dict)
    assert_equal(result, 42, "Вложенный доступ в словаре")


def test_array_access(processor):
    """Тест 3: Доступ к массивам"""
    values_dict = {
        'items': [10, 20, 30, 40, 50],
        'users': [
            {'name': 'John', 'id': 1},
            {'name': 'Jane', 'id': 2},
            {'name': 'Bob', 'id': 3}
        ],
        'matrix': [[1, 2], [3, 4]],
        'empty': [],
    }
    
    # Положительный индекс
    result = processor.process_text_placeholders("{items[0]}", values_dict)
    assert_equal(result, 10, "Доступ по положительному индексу")
    
    result = processor.process_text_placeholders("{items[2]}", values_dict)
    assert_equal(result, 30, "Доступ по среднему индексу")
    
    # Отрицательный индекс
    result = processor.process_text_placeholders("{items[-1]}", values_dict)
    assert_equal(result, 50, "Доступ по отрицательному индексу (-1")
    
    result = processor.process_text_placeholders("{items[-2]}", values_dict)
    assert_equal(result, 40, "Доступ по отрицательному индексу (-2")
    
    # Доступ к полю объекта в массиве
    result = processor.process_text_placeholders("{users[0].name}", values_dict)
    assert_equal(result, "John", "Доступ к полю объекта в массиве")
    
    result = processor.process_text_placeholders("{users[-1].id}", values_dict)
    assert_equal(result, 3, "Доступ к полю последнего объекта")
    
    # Множественные индексы
    result = processor.process_text_placeholders("{matrix[0][1]}", values_dict)
    assert_equal(result, 2, "Множественные индексы")
    
    # Выход за границы
    result = processor.process_text_placeholders("{items[10]}", values_dict)
    assert "{items[10]}" in str(result), "Выход за границы массива"
    
    # Пустой массив
    result = processor.process_text_placeholders("{empty[0]}", values_dict)
    assert "{empty[0]}" in str(result), "Доступ к пустому массиву"

