# Event Manager - Гайд по событиям

## Назначение
`EventManager` обрабатывает события Telegram (сообщения, callback, новые участники) и создаёт стандартизированные события для передачи в `trigger_manager`.

## Типы событий

### 1. `text` - Текстовые сообщения
**Когда создаётся:** Обычные сообщения, медиа с подписями, reply-сообщения

**Основные атрибуты:**
- `source_type: 'text'`
- `user_id`, `first_name`, `last_name`, `username`, `is_bot` - данные отправителя
- `chat_id`, `chat_type`, `chat_title` - данные чата
- `message_id` - ID сообщения
- `event_text` - текст сообщения или подпись к медиа
- `event_date` - дата события (ISO формат)
- `attachments` - массив вложений

**Атрибуты для reply-сообщений:**
- `reply_message_id` - ID исходного сообщения
- `reply_message_text` - текст исходного сообщения
- `reply_user_id`, `reply_username`, `reply_first_name`, `reply_last_name` - данные автора исходного сообщения

**Вложения (`attachments`):**
```yaml
- type: 'photo' | 'video' | 'audio' | 'document' | 'voice' | 'sticker' | 'animation'
  file_id: "строка"
  mime_type: "строка" # только для document
  file_name: "строка" # только для document
```

### 2. `new_member` - Новые участники
**Когда создаётся:** При добавлении новых участников в чат

**Основные атрибуты:**
- `source_type: 'new_member'`
- `chat_id`, `chat_type`, `chat_title` - данные чата
- `event_date` - дата события

**Данные новых участников (массивы):**
- `joined_user_ids`, `joined_usernames`, `joined_first_names`, `joined_last_names`, `joined_is_bots`

**Совместимость (первый участник):**
- `user_id`, `username`, `first_name`, `last_name`, `is_bot`

**Информация о приглашении:**
- `invite_link` - ссылка-приглашение
- `invite_link_creator_id`, `invite_link_creator_username`, `invite_link_creator_first_name`
- `invite_link_creates_join_request` - создаёт ли запрос на вступление

**Данные инициатора:**
- `initiator_user_id`, `initiator_username`, `initiator_first_name`, `initiator_last_name`

### 3. `callback` - Callback кнопки
**Когда создаётся:** При нажатии на inline кнопки

**Основные атрибуты:**
- `source_type: 'callback'`
- `user_id`, `first_name`, `last_name`, `username`, `is_bot` - данные пользователя
- `chat_id`, `chat_type`, `chat_title` - данные чата
- `message_id` - ID сообщения с кнопкой
- `callback_id` - ID callback
- `callback_data` - данные кнопки
- `event_date` - дата события

## Фильтрация событий

### Игнорируемые события:
- **Forward сообщения** - сообщения, пересланные из других чатов
- **Устаревшие события** - события старше `max_event_age_seconds` (по умолчанию 60 сек)

### Media Group обработка:
- Включена по умолчанию (`media_group_enabled: true`)
- Таймаут группировки: `media_group_timeout` (по умолчанию 1.0 сек)
- Группирует медиа с одинаковым `media_group_id`