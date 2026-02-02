# 🎯 System Actions Guide

> **Note:** This guide is being translated. Some parts may still be in Russian or incomplete.

Complete description of all available actions with their parameters and results.

## 📋 Table of Contents

- [action_hub](#action_hub) (1 actions)
  - [get_available_actions](#get_available_actions)
- [bot_hub](#bot_hub) (10 actions)
  - [get_bot_info](#get_bot_info)
  - [get_bot_status](#get_bot_status)
  - [get_telegram_bot_info](#get_telegram_bot_info)
  - [set_bot_token](#set_bot_token)
  - [start_bot](#start_bot)
  - [stop_all_bots](#stop_all_bots)
  - [stop_bot](#stop_bot)
  - [sync_bot](#sync_bot)
  - [sync_bot_commands](#sync_bot_commands)
  - [sync_bot_config](#sync_bot_config)
- [event_processor](#event_processor) (1 actions)
  - [process_event](#process_event)
- [scenario_processor](#scenario_processor) (2 actions)
  - [process_scenario_event](#process_scenario_event)
  - [sync_scenarios](#sync_scenarios)
- [tenant_hub](#tenant_hub) (11 actions)
  - [get_tenant_status](#get_tenant_status)
  - [get_tenants_list](#get_tenants_list)
  - [sync_all_tenants](#sync_all_tenants)
  - [sync_tenant](#sync_tenant)
  - [sync_tenant_bot](#sync_tenant_bot)
  - [sync_tenant_config](#sync_tenant_config)
  - [sync_tenant_data](#sync_tenant_data)
  - [sync_tenant_scenarios](#sync_tenant_scenarios)
  - [sync_tenant_storage](#sync_tenant_storage)
  - [sync_tenants_from_files](#sync_tenants_from_files)
  - [update_tenant_config](#update_tenant_config)

## action_hub

**Description:** Центральный хаб действий для маршрутизации к сервисам

<a id="get_available_actions"></a>
### get_available_actions

**Description:** Получение всех доступных действий с их метаданными

**Input Parameters:**

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Словарь всех доступных действий с метаданными

**Usage Example:**

```yaml
# In scenario
- action: "get_available_actions"
  params:
    # Parameters not required
```


## bot_hub

**Description:** Центральный сервис для управления всеми ботами

<a id="get_bot_info"></a>
### get_bot_info

**Description:** Получение информации о боте из базы данных (с кэшированием)

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`force_refresh`** (`boolean`, optional) — Принудительное обновление из БД (игнорирует кэш)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`bot_id`** (`integer`) — ID бота
  - **`telegram_bot_id`** (`integer`) — ID бота в Telegram
  - **`tenant_id`** (`integer`) — ID тенанта
  - **`bot_token`** (`string`) — Токен бота
  - **`username`** (`string`) — Username бота
  - **`first_name`** (`string`) — Имя бота
  - **`is_active`** (`boolean`) — Активен ли бот
  - **`bot_command`** (`array`) — Команды бота

**Usage Example:**

```yaml
# In scenario
- action: "get_bot_info"
  params:
    bot_id: 123
    # force_refresh: boolean (optional)
```


<a id="get_bot_status"></a>
### get_bot_status

**Description:** Получение статуса пулинга и активности бота

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`is_polling`** (`boolean`) — Активен ли пулинг: true - активен, false - не активен
  - **`is_active`** (`boolean`) — Активен ли бот из настроек БД: true - активен, false - не активен

**Usage Example:**

```yaml
# In scenario
- action: "get_bot_status"
  params:
    bot_id: 123
```


<a id="get_telegram_bot_info"></a>
### get_telegram_bot_info

**Description:** Получение информации о боте через Telegram API

**Input Parameters:**

- **`bot_token`** (`string`, required, min length: 1) — Токен бота

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`telegram_bot_id`** (`integer`) — ID бота в Telegram
  - **`username`** (`string`) — Username бота
  - **`first_name`** (`string`) — Имя бота
  - **`is_bot`** (`boolean`) — Флаг, что это бот
  - **`can_join_groups`** (`boolean`) — Может ли бот присоединяться к группам
  - **`can_read_all_group_messages`** (`boolean`) — Может ли бот читать все сообщения в группах
  - **`supports_inline_queries`** (`boolean`) — Поддерживает ли бот inline запросы

**Usage Example:**

```yaml
# In scenario
- action: "get_telegram_bot_info"
  params:
    bot_token: "example"
```


<a id="set_bot_token"></a>
### set_bot_token

**Description:** Установка токена бота. Бот должен быть создан через синхронизацию конфигурации (sync_bot_config). Токен будет проверен автоматически при запуске пулинга

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`bot_token`** (`string|None`, optional) — Токен бота (опционально, если не передан - поле не обновляется, если передан null - удаляется)

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

**Usage Example:**

```yaml
# In scenario
- action: "set_bot_token"
  params:
    tenant_id: 123
    # bot_token: string|None (optional)
```


<a id="start_bot"></a>
### start_bot

**Description:** Запуск бота

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

**Usage Example:**

```yaml
# In scenario
- action: "start_bot"
  params:
    bot_id: 123
```


<a id="stop_all_bots"></a>
### stop_all_bots

**Description:** Остановка всех ботов

**Input Parameters:**


**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

**Usage Example:**

```yaml
# In scenario
- action: "stop_all_bots"
  params:
```


<a id="stop_bot"></a>
### stop_bot

**Description:** Остановка бота

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

**Usage Example:**

```yaml
# In scenario
- action: "stop_bot"
  params:
    bot_id: 123
```


<a id="sync_bot"></a>
### sync_bot

**Description:** Синхронизация бота: конфигурация + команды (обертка над sync_bot_config + sync_bot_commands)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`bot_token`** (`string`, required, min length: 1) — Токен бота
- **`is_active`** (`boolean`, optional) — Активен ли бот (по умолчанию true)
- **`bot_commands`** (`array`, optional) — Список команд для применения (опционально)

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`bot_id`** (`integer`) — ID бота
  - **`action`** (`string`) — Действие: created или updated

**Usage Example:**

```yaml
# In scenario
- action: "sync_bot"
  params:
    tenant_id: 123
    bot_token: "example"
    # is_active: boolean (optional)
    # bot_commands: array (optional)
```


<a id="sync_bot_commands"></a>
### sync_bot_commands

**Description:** Синхронизация команд бота: сохранение в БД → применение в Telegram

**Input Parameters:**

- **`bot_id`** (`integer`, required, min: 1) — ID бота
- **`command_list`** (`array`) — Список команд для применения

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)

**Usage Example:**

```yaml
# In scenario
- action: "sync_bot_commands"
  params:
    bot_id: 123
    command_list: []
```


<a id="sync_bot_config"></a>
### sync_bot_config

**Description:** Синхронизация конфигурации бота: создание/обновление бота + запуск пулинга. Если bot_token не передан, используется токен из БД (приоритет конфига)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`bot_token`** (`string`, optional, min length: 1) — Токен бота (опционально, если не передан - используется из БД)
- **`is_active`** (`boolean`) — Активен ли бот

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки (например, ошибки валидации полей)
- **`response_data`** (`object`) — Данные ответа
  - **`bot_id`** (`integer`) — ID бота
  - **`action`** (`string`) — Действие: created или updated

**Usage Example:**

```yaml
# In scenario
- action: "sync_bot_config"
  params:
    tenant_id: 123
    # bot_token: string (optional)
    is_active: true
```


## event_processor

**Description:** Сервис для обработки событий от пулинга

<a id="process_event"></a>
### process_event

**Description:** Обработка события от пулинга

**Input Parameters:**

- **`data`** (`object`) — Сырое событие от пулинга

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "process_event"
  params:
    data: {}
```


## scenario_processor

**Description:** Сервис для обработки событий по сценариям

<a id="process_scenario_event"></a>
### process_scenario_event

**Description:** Обработка события по сценариям

**Input Parameters:**

- **`event_type`** (`string`, required, min length: 1) — Тип события (message, callback_query, etc.)
- **`bot_id`** (`integer`, required, min: 1) — ID бота от которого пришло событие

**Output Parameters:**

- **`result`** (`string`) — Результат обработки (success/error)
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "process_scenario_event"
  params:
    event_type: "example"
    bot_id: 123
```


<a id="sync_scenarios"></a>
### sync_scenarios

**Description:** Синхронизация сценариев тенанта: удаление старых → сохранение новых → перезагрузка кэша

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID tenant'а для синхронизации сценариев
- **`scenarios`** (`array`) — Массив сценариев для синхронизации

**Output Parameters:**

- **`result`** (`string`) — Результат синхронизации (success/partial_success/error)
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_scenarios"
  params:
    tenant_id: 123
    scenarios: []
```


## tenant_hub

**Description:** Сервис для управления конфигурациями тенантов - координатор загрузки данных

<a id="get_tenant_status"></a>
### get_tenant_status

**Description:** Получение статуса тенанта

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — Данные ответа
  - **`bot_is_active`** (`boolean`) — Активен ли бот тенанта из настроек БД (флаг is_active в БД)
  - **`bot_is_polling`** (`boolean`) — Активен ли пулинг бота тенанта (запущен ли процесс пулинга)
  - **`bot_is_webhook_active`** (`boolean`) — Активен ли вебхук бота тенанта (установлен ли вебхук через Telegram API)
  - **`bot_is_working`** (`boolean`) — Работает ли бот тенанта (пулинг ИЛИ вебхуки активны). Показывает реальный статус работы бота
  - **`last_updated_at`** (`string`) (optional) — Дата последнего успешного обновления тенанта
  - **`last_failed_at`** (`string`) (optional) — Дата последней ошибки при обновлении тенанта
  - **`last_error`** (`string`) (optional) — Текст последней ошибки при обновлении тенанта

**Usage Example:**

```yaml
# In scenario
- action: "get_tenant_status"
  params:
    tenant_id: 123
```


<a id="get_tenants_list"></a>
### get_tenants_list

**Description:** Получение списка всех ID тенантов с разделением на публичные и системные

**Input Parameters:**


<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки
- **`response_data`** (`object`) — 
  - **`tenant_ids`** (`array`) — Массив ID всех тенантов
  - **`public_tenant_ids`** (`array`) — Массив ID публичных тенантов
  - **`system_tenant_ids`** (`array`) — Массив ID системных тенантов
  - **`tenant_count`** (`integer`) — Общее количество тенантов

**Usage Example:**

```yaml
# In scenario
- action: "get_tenants_list"
  params:
```


<a id="sync_all_tenants"></a>
### sync_all_tenants

**Description:** Синхронизация всех тенантов (сначала pull из GitHub, потом синхронизация всех)

**Input Parameters:**


**Output Parameters:**

- **`result`** (`string`) — Результат: success, partial_success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_all_tenants"
  params:
```


<a id="sync_tenant"></a>
### sync_tenant

**Description:** Синхронизация конфигурации тенанта с базой данных (сначала обновляет из GitHub, затем синхронизирует)

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта для синхронизации

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error, timeout, not_found
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenant"
  params:
    tenant_id: 123
```


<a id="sync_tenant_bot"></a>
### sync_tenant_bot

**Description:** Синхронизация бота тенанта: pull из GitHub + парсинг + синхронизация

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenant_bot"
  params:
    tenant_id: 123
```


<a id="sync_tenant_config"></a>
### sync_tenant_config

**Description:** Синхронизация конфига тенанта: pull из GitHub + парсинг + синхронизация

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenant_config"
  params:
    tenant_id: 123
```


<a id="sync_tenant_data"></a>
### sync_tenant_data

**Description:** Синхронизация данных тенанта: создание/обновление тенанта

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenant_data"
  params:
    tenant_id: 123
```


<a id="sync_tenant_scenarios"></a>
### sync_tenant_scenarios

**Description:** Синхронизация сценариев тенанта: pull из GitHub + парсинг + синхронизация

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenant_scenarios"
  params:
    tenant_id: 123
```


<a id="sync_tenant_storage"></a>
### sync_tenant_storage

**Description:** Синхронизация storage тенанта: pull из GitHub + парсинг + синхронизация

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenant_storage"
  params:
    tenant_id: 123
```


<a id="sync_tenants_from_files"></a>
### sync_tenants_from_files

**Description:** Синхронизация тенантов из списка измененных файлов (универсальный метод для вебхуков и пуллинга)

**Input Parameters:**

- **`files`** (`array`) — Список файлов в формате ["path1", "path2"] или [{"filename": "path"}, ...]

<details>
<summary>⚙️ Additional Parameters</summary>

- **`_namespace`** (`string`) (optional) — Custom key for creating nesting in `_cache`. If specified, data is saved in `_cache[_namespace]` instead of flat cache. Used to control overwriting on repeated calls of the same action. Access via `{_cache._namespace.field}`. By default, data is merged directly into `_cache` (flat caching).

</details>

**Output Parameters:**

- **`result`** (`string`) — Результат: success, partial_success, error
- **`response_data`** (`object`) (optional) — Данные ответа (synced_tenants, total_tenants, errors)
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке

**Usage Example:**

```yaml
# In scenario
- action: "sync_tenants_from_files"
  params:
    files: []
```


<a id="update_tenant_config"></a>
### update_tenant_config

**Description:** Обновление конфига тенанта (обновляет БД, инвалидирует кэш). Обновляет только переданные поля, остальные не трогает

**Input Parameters:**

- **`tenant_id`** (`integer`, required, min: 1) — ID тенанта
- **`ai_token`** (`string|None`, optional) — AI API токен для тенанта (опционально, если не передан - поле не обновляется, если передан null - удаляется)

**Output Parameters:**

- **`result`** (`string`) — Результат: success, error
- **`error`** (`object`) (optional) — Структура ошибки
  - **`code`** (`string`) — Код ошибки
  - **`message`** (`string`) — Сообщение об ошибке
  - **`details`** (`array`) (optional) — Детали ошибки

**Usage Example:**

```yaml
# In scenario
- action: "update_tenant_config"
  params:
    tenant_id: 123
    # ai_token: string|None (optional)
```

