# Примеры работы с валидатором

Валидатор — это мощный сервис для проверки данных в цепочках действий. Он позволяет создавать сложные правила валидации и может использоваться как заглушка для подмены данных через плейсхолдеры.

## Основные концепции

### Поведение валидатора

- **Без правил** — если `rules` не указаны или пустые, валидация пропускается, действие помечается как `completed`
- **С правилами** — выполняется валидация по указанным правилам
- **При ошибке** — действие помечается как `failed`, цепочка может прерваться
- **При успехе** — действие помечается как `completed`, цепочка продолжается

### Поддерживаемые типы правил

- **Сравнение**: `equals`, `not_equals`
- **Проверка пустоты**: `not_empty`, `empty`
- **Строковые операции**: `contains`, `starts_with`
- **Регулярные выражения**: `regex`
- **Проверка длины**: `length_min`, `length_max`
- **Проверка списков**: `in_list`, `not_in_list`

## Пример 1: Базовая валидация данных

```yaml
basic_validation:
  actions:
    - type: send
      text: "🔍 Начинаем валидацию данных"
      callback_edit: false
    - type: validator
      rules:
        user_id:
          - rule: not_empty
        username:
          - rule: length_min
            value: 3
          - rule: length_max
            value: 20
        email:
          - rule: contains
            value: "@"
          - rule: regex
            value: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
      chain: true
    - type: send
      text: "✅ Валидация прошла успешно"
      callback_edit: false
      chain: completed
```

**Как работает:**
1. Первое действие выполняется сразу
2. Второе действие валидирует данные по правилам:
   - `user_id` не должен быть пустым
   - `username` должен быть от 3 до 20 символов
   - `email` должен содержать "@" и соответствовать регулярному выражению
3. Третье действие выполняется только при успешной валидации

## Пример 2: Валидация с множественными правилами

```yaml
multiple_rules_validation:
  actions:
    - type: send
      text: "🔍 Сложная валидация с множественными правилами"
      callback_edit: false
    - type: validator
      rules:
        password:
          - rule: length_min
            value: 8
          - rule: contains
            value: "A"
          - rule: contains
            value: "a"
          - rule: contains
            value: "1"
        role:
          - rule: in_list
            value: ["admin", "moderator", "user", "guest"]
        age:
          - rule: not_empty
          - rule: regex
            value: "^\\d+$"
    - type: send
      text: "✅ Все правила валидации выполнены"
      callback_edit: false
      chain: completed
```

**Как работает:**
- `password` должен быть не менее 8 символов и содержать заглавную, строчную букву и цифру
- `role` должен быть одним из разрешенных значений
- `age` должен быть непустым числом

## Пример 3: Валидатор как заглушка с плейсхолдерами

```yaml
validator_as_stub:
  actions:
    - type: send
      text: "🔍 Валидатор как заглушка для подмены данных"
      callback_edit: false
    - type: validator
      rules: {}  # Пустые правила - валидация пропускается
      placeholder: true  # Включаем обработку плейсхолдеров
    - type: send
      text: "✅ Данные подменены через плейсхолдеры"
      callback_edit: false
      chain: completed
```

**Как работает:**
- Валидатор с пустыми правилами всегда завершается успешно
- Параметр `placeholder: true` включает обработку плейсхолдеров
- **Подмена данных**: Данные из `prev_data` и `response_data` подменяются в текущем действии
- **Накопление данных**: Обработанные данные "накапливаются" и передаются дальше по цепочке
- **Последующая обработка**: Все последующие действия в цепочке получают уже обработанные данные с подмененными плейсхолдерами

## Пример 4: Валидация в цепочке с обработкой ошибок

```yaml
validation_with_error_handling:
  actions:
    - type: send
      text: "🔍 Валидация с обработкой ошибок"
      callback_edit: false
    - type: validator
      rules:
        user_id:
          - rule: not_empty
        username:
          - rule: length_min
            value: 3
      chain: true
    - type: send
      text: "✅ Валидация прошла успешно"
      callback_edit: false
      chain: completed
    - type: send
      text: "❌ Ошибка валидации: {validation_error}"
      callback_edit: false
      chain: failed
    - type: send
      text: "🔄 Повторите ввод данных"
      callback_edit: false
      chain: ["completed", "failed"]
```

**Как работает:**
1. Первое действие выполняется сразу
2. Второе действие валидирует данные
3. Третье действие выполняется при успешной валидации
4. Четвертое действие выполняется при ошибке валидации
5. Пятое действие выполняется в любом случае

## Пример 5: Валидация через вложенные сценарии

```yaml
validation_in_nested_scenario:
  actions:
    - type: send
      text: "🔍 Валидация через вложенный сценарий"
      callback_edit: false
    - type: scenario
      value: "user_registration_check"
    - type: send
      text: "✅ Регистрация прошла успешно"
      callback_edit: false
      chain: completed

# Вложенный сценарий валидации
user_registration_check:
  actions:
    - type: validator
      rules:
        username:
          - rule: not_empty
          - rule: length_min
            value: 3
          - rule: regex
            value: "^[a-zA-Z0-9_]+$"
        email:
          - rule: not_empty
          - rule: contains
            value: "@"
        password:
          - rule: length_min
            value: 8
      chain: true
    - type: send
      text: "❌ Ошибка валидации данных регистрации"
      callback_edit: false
      chain: failed
    - type: validator  # Пустой валидатор как заглушка
      rules: {}
      chain: completed
```

**Преимущества такого подхода:**
- Валидация вынесена в отдельный переиспользуемый сценарий
- Легко добавлять новые правила валидации
- Четкое разделение логики валидации и основного потока
- Возможность переиспользования в других сценариях

## Пример 6: Валидация с условными правилами

```yaml
conditional_validation:
  actions:
    - type: send
      text: "🔍 Условная валидация данных"
      callback_edit: false
    - type: validator
      rules:
        user_type:
          - rule: in_list
            value: ["individual", "company"]
        # Условные правила в зависимости от типа пользователя
        company_name:
          - rule: not_empty
            condition: "user_type == 'company'"
        individual_name:
          - rule: not_empty
            condition: "user_type == 'individual'"
        phone:
          - rule: regex
            value: "^\\+?[1-9]\\d{1,14}$"
      chain: true
    - type: send
      text: "✅ Условная валидация выполнена"
      callback_edit: false
      chain: completed
```

**⚠️ В разработке:** Условные правила с атрибутом `condition` в текущей реализации валидатора не поддерживаются. Может быть реализована в будущих версиях.

## Пример 7: Валидация с кастомными сообщениями

```yaml
validation_with_custom_messages:
  actions:
    - type: send
      text: "🔍 Валидация с кастомными сообщениями"
      callback_edit: false
    - type: validator
      rules:
        username:
          - rule: not_empty
            message: "Имя пользователя обязательно для заполнения"
          - rule: length_min
            value: 3
            message: "Имя пользователя должно содержать минимум 3 символа"
          - rule: regex
            value: "^[a-zA-Z0-9_]+$"
            message: "Имя пользователя может содержать только буквы, цифры и подчеркивания"
        email:
          - rule: not_empty
            message: "Email обязателен для заполнения"
          - rule: regex
            value: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
            message: "Неверный формат email адреса"
      chain: true
    - type: send
      text: "✅ Валидация с кастомными сообщениями выполнена"
      callback_edit: false
      chain: completed
```

**⚠️ В разработке:** Кастомные сообщения об ошибках с атрибутом `message` в текущей реализации валидатора не поддерживаются. Может быть реализована в будущих версиях.

## Пример 8: Валидация с подменой данных через плейсхолдеры

```yaml
validation_with_placeholder_substitution:
  actions:
    - type: send
      text: "🔍 Валидация с подменой данных"
      callback_edit: false
    - type: validator
      rules:
        processed_username:
          - rule: not_empty
          - rule: length_min
            value: 3
      placeholder: true  # Включаем обработку плейсхолдеров
      # Данные будут подменены из prev_data/response_data
    - type: send
      text: "✅ Данные подменены и валидированы: {processed_username}"
      callback_edit: false
      chain: completed
```

**Как работает:**
- `placeholder: true` включает обработку плейсхолдеров
- Данные из предыдущих действий подменяются в текущем действии
- Валидация выполняется уже с подмененными данными

## Лучшие практики

### ✅ Рекомендуется
- **Группировать связанные правила** для одного поля
- **Использовать вложенные сценарии** для сложной валидации
- **Добавлять кастомные сообщения** для лучшего UX
- **Использовать валидатор как заглушку** для подмены данных
- **Тестировать различные сценарии** валидации

### ❌ Запрещено
- Создавать **циклические зависимости** в правилах валидации
- Использовать **слишком сложные регулярные выражения** без тестирования

### ⚠️ Не рекомендуется
- **Смешивать валидацию** с бизнес-логикой
- **Создавать слишком много правил** для одного поля
- **Игнорировать производительность** при сложных регулярных выражениях

## Отладка валидации

### Рекомендации по отладке
- **Включите debug режим** для получения подробных логов валидации
- **Проверьте логи** сервиса validator для анализа ошибок
- **Тестируйте правила** по отдельности перед объединением
- **Используйте простые регулярные выражения** для начала

### Проверка правил валидации
```yaml
# Тестовый сценарий для проверки правил
test_validation_rules:
  actions:
    - type: validator
      rules:
        test_field:
          - rule: not_empty
          - rule: length_min
            value: 3
      chain: true
    - type: send
      text: "✅ Правило работает корректно"
      callback_edit: false
      chain: completed
```

## Заключение

Валидатор предоставляет мощный механизм для проверки данных в цепочках действий. Правильное использование правил валидации и плейсхолдеров позволяет создавать надежные и гибкие сценарии обработки данных.

Ключевые моменты:
- **Планируйте правила валидации** заранее
- **Используйте вложенные сценарии** для сложной валидации
- **Тестируйте регулярные выражения** отдельно
- **Применяйте валидатор как заглушку** для подмены данных
- **Добавляйте кастомные сообщения** для лучшего пользовательского опыта 