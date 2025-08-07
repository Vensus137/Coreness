from typing import Any, Dict

from aiogram import Dispatcher, types

from .media_group_processor import MediaGroupProcessor


class EventManager:
    """
    Обработчик событий Telegram (сообщения, callback, poll, inline_query).
    Создаёт события и передаёт их в trigger_manager.
    """

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.trigger_manager = kwargs['trigger_manager']
        self.bot_initializer = kwargs['bot_initializer']
        self.settings_manager = kwargs['settings_manager']
        self.datetime_formatter = kwargs['datetime_formatter']
        self.data_converter = kwargs['data_converter']
        
        # Получаем время запуска из settings_manager
        self.startup_time = self.settings_manager.get_startup_time()
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings('event_manager')
        self.media_group_timeout = settings.get('media_group_timeout', 1.0)
        self.media_group_enabled = settings.get('media_group_enabled', True)
        self.max_event_age_seconds = settings.get('max_event_age_seconds', 60)
        
        self.media_group_processor = MediaGroupProcessor(self.media_group_timeout, self.logger)
        self._is_running = False

    async def run(self):
        """
        Запускает polling событий Telegram через aiogram Dispatcher.
        """
        self._is_running = True
        self.logger.info("▶️ старт polling Telegram событий (aiogram Dispatcher)")
        dp = Dispatcher()
        router = self._create_router()
        dp.include_router(router)
        bot = self.bot_initializer.get_bot()
        await dp.start_polling(bot)

    def _create_router(self):
        """
        Создаёт и настраивает router с обработчиками событий Telegram.
        """
        from aiogram import Router
        router = Router()

        # Обработчик обычных сообщений
        @router.message()
        async def handle_message(message: types.Message):
            # --- Новый блок: обработка вступления новых участников ---
            if message.new_chat_members:
                event = self._create_new_member_event(message)
        
                await self._dispatch_event(event)
                return
            # --- Конец нового блока ---
            event = await self._handle_message(message)
            if event:
                await self._dispatch_event(event)

        # Обработчик отредактированных сообщений (игнорируем)
        @router.edited_message()
        async def handle_edited_message(message: types.Message):
            return

        # Обработчик callback кнопок
        @router.callback_query()
        async def handle_callback(callback: types.CallbackQuery):
            event = await self._handle_callback(callback)
            if event:
                await self._dispatch_event(event)

        # Обработчик опросов
        @router.poll()
        async def handle_poll(poll: types.Poll):
            return

        # Обработчик inline запросов
        @router.inline_query()
        async def handle_inline_query(inline_query: types.InlineQuery):
            return

        return router

    async def _handle_message(self, message: types.Message):
        """
        Обрабатывает входящее сообщение. Возвращает event или None.
        """
        # Фильтрация нежелательных событий
        if self._should_ignore_message(message):
            return None

        # Создание события с вложениями
        event = self._create_message_event(message)

        # Обработка через Media Group Processor с callback
        if self.media_group_enabled:
            await self.media_group_processor.process_event(event, self._media_group_callback)
            return None  # Финальный event будет обработан в _media_group_callback
        else:
            return event

    def _should_ignore_message(self, message: types.Message) -> bool:
        """
        Проверяет, нужно ли игнорировать сообщение.
        Игнорируем forward сообщения.
        """
        # Forward сообщения
        if message.forward_from or message.forward_from_chat:
    
            return True
        return False

    def _create_message_event(self, message: types.Message) -> dict:
        """
        Создаёт событие из сообщения с извлечением вложений.
        """
        event = {
            'source_type': 'text',
            'user_id': message.from_user.id if message.from_user else None,
            'first_name': message.from_user.first_name if message.from_user else None,
            'last_name': message.from_user.last_name if message.from_user else None,
            'username': message.from_user.username if message.from_user else None,
            'is_bot': bool(message.from_user.is_bot) if message.from_user and message.from_user.is_bot is not None else False,
            'chat_id': message.chat.id,
            'chat_type': message.chat.type if message.chat else None,
            'chat_title': getattr(message.chat, 'title', None),  # название чата (None для личных)
            'message_id': message.message_id,
            'event_text': message.text or message.caption,  # текст или подпись к медиа
            'event_date': self.datetime_formatter.to_iso_string(
                self.datetime_formatter.to_local(message.date) if message.date else self.datetime_formatter.now_local()
            ),
            'media_group_id': message.media_group_id,  # для группировки медиа
            'attachments': []  # массив вложений
        }

        # Новое: если это reply-сообщение, добавляем текст исходного сообщения и данные автора
        if message.reply_to_message:
            event['reply_message_id'] = message.reply_to_message.message_id
            event['reply_message_text'] = message.reply_to_message.text or message.reply_to_message.caption
            # Добавляем данные автора исходного сообщения (безопасное обращение)
            event['reply_user_id'] = message.reply_to_message.from_user.id if message.reply_to_message.from_user else None
            event['reply_username'] = message.reply_to_message.from_user.username if message.reply_to_message.from_user else None
            event['reply_first_name'] = message.reply_to_message.from_user.first_name if message.reply_to_message.from_user else None
            event['reply_last_name'] = getattr(message.reply_to_message.from_user, 'last_name', None) if message.reply_to_message.from_user else None
            # Добавляем вложения исходного сообщения
            event['reply_attachments'] = self._extract_attachments(message.reply_to_message)

        # Извлекаем вложения
        event['attachments'] = self._extract_attachments(message)

        return event

    def _extract_attachments(self, message: types.Message) -> list:
        """
        Извлекает вложения из сообщения Telegram
        Возвращает массив вложений с их типами и file_id
        """
        attachments = []
        
        if message.photo:
            # Добавляем все размеры фото
            for photo in message.photo:
                attachments.append({
                    'type': 'photo',
                    'file_id': photo.file_id,
                })

        if message.document:
            # Проверяем MIME-тип для правильного определения типа
            mime_type = message.document.mime_type or ''
            file_name = message.document.file_name or ''

            if mime_type.startswith('image/'):
                attachment_type = 'photo'
            elif mime_type.startswith('video/'):
                attachment_type = 'video'
            elif mime_type.startswith('audio/'):
                attachment_type = 'audio'
            else:
                attachment_type = 'document'

            attachments.append({
                'type': attachment_type,
                'file_id': message.document.file_id,
                'mime_type': mime_type,
                'file_name': file_name
            })

        if message.video:
            attachments.append({
                'type': 'video',
                'file_id': message.video.file_id
            })

        if message.audio:
            attachments.append({
                'type': 'audio',
                'file_id': message.audio.file_id
            })

        if message.voice:
            attachments.append({
                'type': 'voice',
                'file_id': message.voice.file_id
            })

        if message.sticker:
            attachments.append({
                'type': 'sticker',
                'file_id': message.sticker.file_id
            })

        if message.animation:
            attachments.append({
                'type': 'animation',
                'file_id': message.animation.file_id
            })
            
        return attachments

    def _create_new_member_event(self, message: types.Message) -> dict:
        """
        Создаёт event для события вступления новых участников (new_chat_members).
        Все данные о новых участниках складываются в массивы (id, username, first_name, last_name, is_bot).
        Если есть invite_link — добавляется вся доступная информация.
        Остальные атрибуты (chat_id, chat_title, initiator и т.д.) — по аналогии с обычным сообщением.
        """
        joined_user_ids = []
        joined_usernames = []
        joined_first_names = []
        joined_last_names = []
        joined_is_bots = []
        for user in message.new_chat_members:
            joined_user_ids.append(user.id)
            joined_usernames.append(user.username)
            joined_first_names.append(user.first_name)
            joined_last_names.append(getattr(user, 'last_name', None))
            joined_is_bots.append(bool(user.is_bot) if user.is_bot is not None else False)

        event = {
            'source_type': 'new_member',
            'chat_id': message.chat.id,
            'chat_title': getattr(message.chat, 'title', None),
            'chat_type': getattr(message.chat, 'type', None),
            'joined_user_ids': joined_user_ids,
            'joined_usernames': joined_usernames,
            'joined_first_names': joined_first_names,
            'joined_last_names': joined_last_names,
            'joined_is_bots': joined_is_bots,
            'event_date': self.datetime_formatter.to_iso_string(
                self.datetime_formatter.to_local(message.date) if message.date else self.datetime_formatter.now_local()
            ),
        }

        # Для совместимости: user_id и username — первый из списка
        if joined_user_ids:
            event['user_id'] = joined_user_ids[0]
        if joined_usernames:
            event['username'] = joined_usernames[0]
        if joined_first_names:
            event['first_name'] = joined_first_names[0]
        if joined_last_names:
            event['last_name'] = joined_last_names[0]
        if joined_is_bots:
            event['is_bot'] = joined_is_bots[0]

        # Информация о пригласительной ссылке, если есть
        if getattr(message, 'invite_link', None):
            invite_link = message.invite_link
            event['invite_link'] = getattr(invite_link, 'invite_link', None)
            event['invite_link_creator_id'] = getattr(getattr(invite_link, 'creator', None), 'id', None)
            event['invite_link_creator_username'] = getattr(getattr(invite_link, 'creator', None), 'username', None)
            event['invite_link_creator_first_name'] = getattr(getattr(invite_link, 'creator', None), 'first_name', None)
            event['invite_link_creates_join_request'] = getattr(invite_link, 'creates_join_request', None)

        # Информация о том, кто инициировал добавление (если есть)
        if message.from_user:
            event['initiator_user_id'] = message.from_user.id
            event['initiator_username'] = message.from_user.username
            event['initiator_first_name'] = message.from_user.first_name
            event['initiator_last_name'] = getattr(message.from_user, 'last_name', None)

        return event

    async def _media_group_callback(self, event: dict):
        await self._dispatch_event(event)

    async def _handle_callback(self, callback: types.CallbackQuery):
        """
        Обрабатывает callback кнопки. Возвращает event.
        """
        chat_id = callback.message.chat.id if callback.message else None
        chat_type = callback.message.chat.type if callback.message and callback.message.chat else None
        chat_title = getattr(callback.message.chat, 'title', None) if callback.message and callback.message.chat else None
        message_id = callback.message.message_id if callback.message else None
        callback_id = callback.id
        event = {
            'source_type': 'callback',
            'user_id': callback.from_user.id,
            'first_name': callback.from_user.first_name,
            'last_name': callback.from_user.last_name if callback.from_user else None,
            'username': callback.from_user.username if callback.from_user else None,
            'is_bot': bool(callback.from_user.is_bot) if callback.from_user and callback.from_user.is_bot is not None else False,
            'chat_id': chat_id,
            'chat_type': chat_type,
            'chat_title': chat_title,  # название чата (None для личных)
            'message_id': message_id,
            'callback_id': callback_id,
            'callback_data': callback.data,
            'event_date': self.datetime_formatter.to_iso_string(self.datetime_formatter.now_local()),
        }
        return event

    async def _handle_poll(self, poll: types.Poll):
        """
        Обрабатывает опросы. Возвращает event.
        """
        event = {
            'source_type': 'poll',
        }
        return event

    async def _handle_inline_query(self, inline_query: types.InlineQuery):
        """
        Обрабатывает inline запросы. Возвращает event.
        """
        event = {
            'source_type': 'inline_query',
        }
        return event

    async def _dispatch_event(self, event: Dict[str, Any]):
        """
        Централизованная обработка и отправка event в trigger_manager.
        Здесь можно добавить pre-processing, валидацию, логику модификации event.
        """
        # Конвертируем event в безопасный словарь через DataConverter
        safe_event = self.data_converter.to_safe_dict(event)
        
        event_date = event.get('event_date')
        try:
            startup_dt = self.startup_time
            event_dt = self.datetime_formatter.parse(event_date) if isinstance(event_date, str) else event_date
            delta = (startup_dt - event_dt).total_seconds()
            if self.max_event_age_seconds > delta:
                await self.trigger_manager.handle_event(safe_event)
            else:
                return
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка при фильтрации event по времени: {e}")
            await self.trigger_manager.handle_event(safe_event)
