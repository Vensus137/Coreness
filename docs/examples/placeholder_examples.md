# Примеры работы с плейсхолдер-процессором

Плейсхолдер-процессор — это мощная система для динамической подстановки и преобразования данных в сценариях. Он позволяет создавать гибкие шаблоны с поддержкой модификаторов, арифметических операций и форматирования.

## Основные концепции

### Синтаксис плейсхолдеров

- **Простая замена**: `{field_name}`
- **С модификатором**: `{field_name|modifier:param}`
- **Цепочка модификаторов**: `{field_name|modifier1:param1|modifier2:param2}`
- **Fallback значение**: `{field_name|fallback:default_value}`

### Источники данных

- **`prev_data`** — данные из предыдущих действий в цепочке
- **`response_data`** — данные, возвращенные сервисами
- **`parsed_action`** — данные текущего действия
- **Любые поля** из контекста выполнения

### Включение обработки плейсхолдеров

**⚠️ Важно:** По умолчанию плейсхолдеры **НЕ обрабатываются** для оптимизации производительности.

**Для включения обработки плейсхолдеров:**
- Добавьте `placeholder: true` к действию
- Это включает обработку плейсхолдеров во всех полях действия

**Исключение — сервис Messenger:**
- **По умолчанию включена** автоматическая обработка плейсхолдеров в текстовых сообщениях
- Это самый частый сценарий использования — подстановка данных в сообщения
- Не требует дополнительной настройки для простых текстовых подстановок

## Пример 1: Простая подстановка данных

```yaml
simple_substitution:
  actions:
    - type: send
      text: "Привет, {username}! Ваш ID: {user_id}"
      callback_edit: false
    - type: send
      text: "Текущее время: {current_time|format:datetime}"
      callback_edit: false
      chain: true
    - type: send
      text: "Количество сообщений: {message_count|+1}"
      callback_edit: false
      chain: completed
```

**Как работает:**
- `{username}` — простая подстановка имени пользователя
- `{user_id}` — подстановка ID пользователя
- `{current_time|format:datetime}` — форматирование времени
- `{message_count|+1}` — арифметическая операция

**💡 Автоматическая обработка:** В сервисе `messenger` (тип `send`) плейсхолдеры обрабатываются автоматически без дополнительных настроек.

## Пример 2: Арифметические операции

```yaml
arithmetic_operations:
  actions:
    - type: send
      text: "🔢 Арифметические операции с плейсхолдерами"
      callback_edit: false
    - type: send
      text: |
        Исходное значение: {base_value}
        + 10: {base_value|+10}
        - 5: {base_value|-5}
        * 2: {base_value|*2}
        / 3: {base_value|/3}
        % 7: {base_value|%7}
      callback_edit: false
      chain: true
    - type: send
      text: "Результат вычислений: {result}"
      callback_edit: false
      chain: completed
```

**Поддерживаемые операции:**
- `|+value` — сложение
- `|-value` — вычитание
- `|*value` — умножение
- `|/value` — деление
- `|%value` — остаток от деления

## Пример 3: Преобразования текста

```yaml
text_transformations:
  actions:
    - type: send
      text: "🔤 Преобразования текста"
      callback_edit: false
    - type: send
      text: |
        Исходный текст: {original_text}
        Верхний регистр: {original_text|upper}
        Нижний регистр: {original_text|lower}
        Заглавные буквы: {original_text|title}
        Первая заглавная: {original_text|capitalize}
      callback_edit: false
      chain: true
    - type: send
      text: "Обрезанный текст: {long_text|truncate:50}"
      callback_edit: false
      chain: completed
```

**Поддерживаемые преобразования:**
- `|upper` — верхний регистр
- `|lower` — нижний регистр
- `|title` — заглавные буквы каждого слова
- `|capitalize` — первая заглавная буква
- `|truncate:length` — обрезка текста с "..."
- `|regex:pattern` — извлечение данных по регулярному выражению

## Пример 4: Извлечение данных по регулярным выражениям

```yaml
regex_extraction:
  actions:
    - type: send
      text: "🔍 Извлечение данных по регулярным выражениям"
      callback_edit: false
    - type: send
      text: |
        Время из текста: {event_text|regex:(?:\\d+\\s*[dhms]\\s*)+}
        Email из сообщения: {message|regex:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}}
        Телефон: {contact|regex:\\+?[1-9]\\d{1,14}}
        URL: {text|regex:https?://[^\\s]+}
      callback_edit: false
      chain: true
    - type: send
      text: "Извлеченные данные: {extracted_data}"
      callback_edit: false
      chain: completed
```

**Как работает regex модификатор:**
- `|regex:pattern` — извлекает данные по регулярному выражению
- Возвращает первое совпадение (группа 0)
- Если совпадение не найдено, возвращает пустую строку
- Поддерживает все стандартные regex паттерны Python

**Примеры паттернов:**
- `(?:\\d+\\s*[dhms]\\s*)+` — время (1h 30m, 2d 5h, etc.)
- `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}` — email
- `\\+?[1-9]\\d{1,14}` — номер телефона
- `https?://[^\\s]+` — URL

## Пример 5: Форматирование дат и времени

```yaml
datetime_formatting:
  actions:
    - type: send
      text: "📅 Форматирование дат и времени"
      callback_edit: false
    - type: send
      text: |
        Timestamp: {timestamp|format:timestamp}
        Дата: {timestamp|format:date}
        Время: {timestamp|format:time}
        Дата и время: {timestamp|format:datetime}
      callback_edit: false
      chain: true
    - type: send
      text: "Относительное время: {relative_time}"
      callback_edit: false
      chain: completed
```

**Поддерживаемые форматы:**
- `|format:timestamp` — преобразование в timestamp
- `|format:date` — формат даты (dd.mm.yyyy)
- `|format:time` — формат времени (hh:mm)
- `|format:datetime` — полный формат даты и времени

## Пример 6: Работа со списками

```yaml
list_operations:
  actions:
    - type: send
      text: "📋 Работа со списками"
      callback_edit: false
    - type: send
      text: |
        Список пользователей: {users|list}
        Через запятую: {users|comma}
        Теги: {users|tags}
        Количество: {users|length}
      callback_edit: false
      chain: true
    - type: send
      text: "Первый пользователь: {users|first}"
      callback_edit: false
      chain: completed
```

**Поддерживаемые операции со списками:**
- `|list` — маркированный список (• item)
- `|comma` — через запятую (item1, item2)
- `|tags` — преобразование в теги (@user)
- `|length` — количество элементов
- `|first` — первый элемент
- `|last` — последний элемент

## Пример 7: Fallback значения

```yaml
fallback_values:
  actions:
    - type: send
      text: "🔄 Fallback значения"
      callback_edit: false
    - type: send
      text: |
        Имя пользователя: {username|fallback:Гость}
        Возраст: {age|fallback:Не указан}
        Email: {email|fallback:Нет данных}
        Пустое поле: {|fallback:100}
      callback_edit: false
      chain: true
    - type: send
      text: "Комбинированный fallback: {value|upper|fallback:ПО УМОЛЧАНИЮ}"
      callback_edit: false
      chain: completed
```

**Как работает fallback:**
- `|fallback:value` — замена при отсутствии значения
- Можно комбинировать с другими модификаторами
- Работает с пустыми полями и отсутствующими данными

## Пример 8: Цепочки модификаторов

```yaml
modifier_chains:
  actions:
    - type: send
      text: "🔗 Цепочки модификаторов"
      callback_edit: false
    - type: send
      text: |
        Сложная цепочка: {raw_data|lower|truncate:20|fallback:Нет данных}
        Математика + форматирование: {number|+100|*2|format:number}
        Список + теги + обрезка: {users|tags|truncate:50}
        Regex + форматирование: {event_text|regex:(?:\\d+\\s*[dhms]\\s*)+|upper}
      callback_edit: false
      chain: true
    - type: send
      text: "Результат: {processed_result}"
      callback_edit: false
      chain: completed
```

**Порядок выполнения:**
1. Модификаторы выполняются слева направо
2. Результат каждого модификатора передается следующему
3. Fallback применяется в конце цепочки

## Пример 9: Условная подстановка

```yaml
conditional_substitution:
  actions:
    - type: send
      text: "🎯 Условная подстановка"
      callback_edit: false
    - type: send
      text: |
        Статус: {status|fallback:Неизвестно}
        Сообщение: {status|equals:active|fallback:Неактивен|value:Активен}
        Роль: {role|in_list:admin,moderator|fallback:Пользователь|value:Администратор}
      callback_edit: false
      chain: true
    - type: send
      text: "Условный текст: {condition|true|value:Да|fallback:Нет}"
      callback_edit: false
      chain: completed
```

**Как работают условные модификаторы:**
- `|equals:value` — проверяет равенство значения
- `|in_list:item1,item2` — проверяет вхождение в список
- `|true` — проверяет истинность значения
- `|value:result` — возвращает результат при истинности (работает в связке с другими условными модификаторами)

## Пример 10: Рекурсивная обработка плейсхолдеров

```yaml
recursive_placeholders:
  actions:
    - type: send
      text: "🔄 Рекурсивная обработка плейсхолдеров"
      callback_edit: false
    - type: send
      text: |
        Простая замена: {username}
        Рекурсивная замена: {nested_field}
        Цепочка модификаторов: {username|upper|truncate:10}
      callback_edit: false
      chain: true
    - type: send
      text: "Результат: {processed_result}"
      callback_edit: false
      chain: completed
```

**Как работает рекурсивная обработка:**
- Если значение поля содержит плейсхолдеры, они обрабатываются рекурсивно
- Поддерживается до 3 уровней вложенности (настраивается в `max_nesting_depth`)
- При достижении максимальной глубины плейсхолдер возвращается как есть с предупреждением

**Пример рекурсивной обработки:**
```yaml
# Если в values_dict есть:
# username: "john"
# nested_field: "Привет, {username}!"  # Содержит плейсхолдер
# 
# То {nested_field} будет обработан как: "Привет, john!"
```

## Пример 11: Автоматическая vs ручная обработка плейсхолдеров

```yaml
placeholder_processing_modes:
  actions:
    # Автоматическая обработка в messenger (по умолчанию)
    - type: send
      text: "Привет, {username}! Ваш ID: {user_id}"
      callback_edit: false
      # placeholder: true НЕ нужно - обрабатывается автоматически
    
    # Ручное включение для других сервисов
    - type: validator
      rules:
        processed_username:
          - rule: not_empty
          - rule: length_min
            value: 3
      placeholder: true  # Обязательно для обработки плейсхолдеров
      chain: true
    
    # Ручное включение для пользовательских действий
    - type: user
      user_state: "awaiting_{action_type}"
      placeholder: true  # Включаем обработку плейсхолдеров
      chain: completed
    
    # Автоматическая обработка в messenger (снова)
    - type: send
      text: "Состояние: {user_state}, Обработанное имя: {processed_username|title}"
      callback_edit: false
      chain: completed
```

**Как работает:**
- **Messenger (send)**: Плейсхолдеры обрабатываются автоматически
- **Другие сервисы**: Требуют `placeholder: true` для обработки
- **Пользовательские действия**: Также требуют явного включения

## Пример 12: Сложные вычисления

```yaml
complex_calculations:
  actions:
    - type: send
      text: "🧮 Сложные вычисления"
      callback_edit: false
    - type: send
      text: |
        Процент: {score|/100|*100|format:percent}
        Среднее: {total|/count|format:number}
        Скидка: {price|*0.9|format:currency}
        Рейтинг: {rating|*5|format:number}/5
      callback_edit: false
      chain: true
    - type: send
      text: "Итоговая сумма: {base_price|+tax|+fee|format:currency}"
      callback_edit: false
      chain: completed
```

## Пример 13: Форматирование дат и времени

```yaml
datetime_formatting:
  actions:
    - type: send
      text: "📅 Форматирование дат и времени"
      callback_edit: false
    - type: send
      text: |
        Timestamp: {timestamp|format:timestamp}
        Дата: {timestamp|format:date}
        Время: {timestamp|format:time}
        Дата и время: {timestamp|format:datetime}
      callback_edit: false
      chain: true
    - type: send
      text: "Итог: {current_time|format:datetime|fallback:Неизвестно}"
      callback_edit: false
      chain: completed
```

**Поддерживаемые форматы:**
- **Даты и время:**
  - `|format:timestamp` — преобразование в timestamp (Unix time)
  - `|format:date` — формат даты (dd.mm.yyyy)
  - `|format:time` — формат времени (hh:mm)
  - `|format:datetime` — полный формат даты и времени (dd.mm.yyyy hh:mm)
- **Числа и валюты:**
  - `|format:currency` — форматирование валюты (1000.00 ₽)
  - `|format:percent` — форматирование процентов (25.5%)
  - `|format:number` — форматирование чисел (1234.56)

## Лучшие практики

### ✅ Рекомендуется
- **Использовать fallback** для всех критических полей
- **Группировать модификаторы** логически
- **Тестировать сложные цепочки** модификаторов
- **Документировать** сложные плейсхолдеры
- **Использовать вложенные сценарии** для сложной логики
- **Помнить про `placeholder: true`** для сервисов кроме messenger
- **Использовать автоматическую обработку** в messenger для простых подстановок
- **Применять условные модификаторы** для динамической логики
- **Использовать форматирование** для красивого вывода чисел и дат
- **Применять regex модификатор** для извлечения структурированных данных из текста
- **Тестировать regex паттерны** отдельно перед использованием в плейсхолдерах

### ❌ Запрещено
- Создавать **циклические зависимости** в плейсхолдерах
- Использовать **слишком глубокую вложенность** (>3 уровней)

### ⚠️ Не рекомендуется
- **Создавать слишком длинные цепочки** модификаторов
- **Использовать сложные вычисления** без тестирования
- **Игнорировать производительность** при множественных плейсхолдерах

## Отладка плейсхолдеров

### Рекомендации по отладке
- **Включите debug режим** для получения подробных логов
- **Проверяйте промежуточные значения** в цепочках модификаторов
- **Тестируйте модификаторы** по отдельности
- **Используйте fallback** для отладки отсутствующих данных
- **Проверьте `placeholder: true`** для сервисов кроме messenger
- **Убедитесь в наличии данных** в источниках (prev_data, response_data)

### Проверка плейсхолдеров
```yaml
# Тестовый сценарий для проверки плейсхолдеров
test_placeholders:
  actions:
    - type: send
      text: "Тест: {test_field|upper|fallback:ТЕСТ}"
      callback_edit: false
    - type: send
      text: "Regex тест: {event_text|regex:(?:\\d+\\s*[dhms]\\s*)+|fallback:Время не найдено}"
      callback_edit: false
    - type: send
      text: "Результат: {result}"
      callback_edit: false
      chain: completed
```

## Заключение

Плейсхолдер-процессор предоставляет мощный механизм для динамической обработки данных в сценариях. Правильное использование модификаторов и fallback значений позволяет создавать гибкие и надежные шаблоны.

Ключевые моменты:
- **Планируйте цепочки модификаторов** заранее
- **Используйте fallback** для всех важных полей
- **Тестируйте сложные плейсхолдеры** отдельно
- **Документируйте** сложную логику подстановки
- **Следите за производительностью** при множественных плейсхолдерах 