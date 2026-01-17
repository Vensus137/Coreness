"""
Утилита для парсинга raw событий Telegram в стандартный формат
"""

from typing import Any, Dict, List, Optional


class EventParser:
    """
    Парсер raw событий Telegram в стандартный формат событий.
    """

    def __init__(self, logger, datetime_formatter, data_converter, database_manager, user_manager, cache_manager):
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        self.data_converter = data_converter
        self.database_manager = database_manager
        self.user_manager = user_manager
        self.cache_manager = cache_manager
        
        # Локальный кэш для tenant_id по bot_id (вечный)
        self._bot_tenant_cache: Dict[int, int] = {}

    async def parse_event(self, telegram_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Парсинг Telegram события в стандартный формат события
        """
        try:
            # Получаем bot_id из системного поля
            bot_id = telegram_event.get('system', {}).get('bot_id')
            if not bot_id:
                self.logger.warning("bot_id отсутствует в системном поле события")
                return None
            
            # Получаем tenant_id по bot_id (с кэшированием)
            tenant_id = await self._get_tenant_by_bot_id(bot_id)
            if not tenant_id:
                self.logger.warning(f"tenant_id не найден для bot_id {bot_id}")
                return None
            
            # Определяем тип события
            if 'message' in telegram_event:
                message = telegram_event['message']
                # Проверяем, является ли это событием входа/выхода участника
                if 'new_chat_member' in message:
                    event = await self._parse_member_joined_from_message(message)
                elif 'left_chat_member' in message:
                    event = await self._parse_member_left_from_message(message)
                elif 'successful_payment' in message:
                    event = await self._parse_successful_payment_from_message(message)
                else:
                    event = await self._parse_message(message)
            elif 'callback_query' in telegram_event:
                event = await self._parse_callback_query(telegram_event['callback_query'])
            elif 'pre_checkout_query' in telegram_event:
                event = await self._parse_pre_checkout_query(telegram_event['pre_checkout_query'])
            else:
                # Игнорируем неизвестные типы событий
                return None
            
            if event:
                # Добавляем bot_id и tenant_id в системное поле события (для защиты)
                event['system'] = {
                    'bot_id': bot_id,
                    'tenant_id': tenant_id
                }
                
                # Добавляем bot_id и tenant_id в плоский словарь (для использования в действиях)
                event['bot_id'] = bot_id
                event['tenant_id'] = tenant_id
                
                # Добавляем конфиг тенанта в событие
                tenant_config = await self._get_tenant_config(tenant_id)
                if tenant_config:
                    # Кладем весь конфиг в _config (действия будут извлекать нужные атрибуты оттуда)
                    event['_config'] = tenant_config
                
                # Автоматически сохраняем данные пользователя
                await self._save_user_data(event)
            
            return event
                
        except Exception as e:
            self.logger.error(f"Ошибка парсинга обновления: {e}")
            return None

    async def _parse_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг сообщения в стандартный формат события"""
        try:
            # Базовая информация
            chat_type = message.get('chat', {}).get('type')
            event = {
                'event_source': 'telegram',
                'event_type': 'message',
                'user_id': message.get('from', {}).get('id') if message.get('from') else None,
                'chat_id': message.get('chat', {}).get('id'),
                'chat_type': chat_type,
                'is_group': chat_type in ['group', 'supergroup'],
                'message_id': message.get('message_id'),
                'event_text': message.get('text') or message.get('caption'),
                'event_date': await self.datetime_formatter.to_iso_local_string(
                    await self.datetime_formatter.to_local(message.get('date')) if message.get('date') else await self.datetime_formatter.now_local()
                ),
                'media_group_id': message.get('media_group_id'),
                'event_attachment': self._extract_attachments(message)
            }

            # Информация о пользователе
            if message.get('from'):
                from_user = message['from']
                event.update({
                    'username': from_user.get('username'),
                    'first_name': from_user.get('first_name'),
                    'last_name': from_user.get('last_name'),
                    'language_code': from_user.get('language_code'),
                    'is_bot': from_user.get('is_bot', False),
                    'is_premium': from_user.get('is_premium', False)
                })

            # Информация о чате
            if message.get('chat'):
                chat = message['chat']
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })

            # Флаги
            event.update({
                'is_reply': bool(message.get('reply_to_message')),
                'is_forward': bool(message.get('forward_from') or message.get('forward_from_chat'))
            })

            # Обработка reply-сообщений
            if message.get('reply_to_message'):
                reply_msg = message['reply_to_message']
                event.update({
                    'reply_message_id': reply_msg.get('message_id'),
                    'reply_message_text': reply_msg.get('text') or reply_msg.get('caption'),
                    'reply_user_id': reply_msg.get('from', {}).get('id') if reply_msg.get('from') else None,
                    'reply_username': reply_msg.get('from', {}).get('username') if reply_msg.get('from') else None,
                    'reply_first_name': reply_msg.get('from', {}).get('first_name') if reply_msg.get('from') else None,
                    'reply_last_name': reply_msg.get('from', {}).get('last_name') if reply_msg.get('from') else None,
                    'reply_date': await self.datetime_formatter.to_iso_string(
                        await self.datetime_formatter.to_local(reply_msg.get('date', 0))
                    ),
                    'reply_attachment': self._extract_attachments(reply_msg)
                })

            # Обработка forward-сообщений
            if message.get('forward_from') or message.get('forward_from_chat'):
                event.update({
                    'forward_message_id': message.get('forward_from_message_id'),
                    'forward_from_user_id': message.get('forward_from', {}).get('id') if message.get('forward_from') else None,
                    'forward_from_user_username': message.get('forward_from', {}).get('username') if message.get('forward_from') else None,
                    'forward_from_user_first_name': message.get('forward_from', {}).get('first_name') if message.get('forward_from') else None,
                    'forward_from_user_last_name': message.get('forward_from', {}).get('last_name') if message.get('forward_from') else None,
                    'forward_from_chat_id': message.get('forward_from_chat', {}).get('id') if message.get('forward_from_chat') else None,
                    'forward_from_chat_title': message.get('forward_from_chat', {}).get('title') if message.get('forward_from_chat') else None,
                    'forward_from_chat_type': message.get('forward_from_chat', {}).get('type') if message.get('forward_from_chat') else None,
                    'forward_date': await self.datetime_formatter.to_iso_string(
                        await self.datetime_formatter.to_local(message.get('forward_date', 0))
                    )
                })

            # Обработка inline-клавиатуры
            inline_keyboard = self._extract_inline_keyboard(message)
            if inline_keyboard:
                event['inline_keyboard'] = inline_keyboard

            # Конвертируем в безопасный словарь
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Ошибка парсинга сообщения: {e}")
            return None

    async def _parse_callback_query(self, callback: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг callback_query в стандартный формат события"""
        try:
            chat_type = callback.get('message', {}).get('chat', {}).get('type') if callback.get('message') else None
            event = {
                'event_source': 'telegram',
                'event_type': 'callback',
                'user_id': callback.get('from', {}).get('id') if callback.get('from') else None,
                'chat_id': callback.get('message', {}).get('chat', {}).get('id') if callback.get('message') else None,
                'chat_type': chat_type,
                'is_group': chat_type in ['group', 'supergroup'] if chat_type else False,
                'message_id': callback.get('message', {}).get('message_id') if callback.get('message') else None,
                'callback_id': callback.get('id'),
                'callback_data': callback.get('data'),
                'callback_message_text': (callback.get('message', {}).get('text') or callback.get('message', {}).get('caption')) if callback.get('message') else None,
                'event_date': await self.datetime_formatter.to_iso_local_string(await self.datetime_formatter.now_local())
            }

            # Информация о пользователе
            if callback.get('from'):
                from_user = callback['from']
                event.update({
                    'username': from_user.get('username'),
                    'first_name': from_user.get('first_name'),
                    'last_name': from_user.get('last_name'),
                    'language_code': from_user.get('language_code'),
                    'is_bot': from_user.get('is_bot', False),
                    'is_premium': from_user.get('is_premium', False)
                })

            # Информация о чате
            if callback.get('message') and callback['message'].get('chat'):
                chat = callback['message']['chat']
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })

            # Обработка inline-клавиатуры из сообщения callback
            if callback.get('message'):
                inline_keyboard = self._extract_inline_keyboard(callback['message'])
                if inline_keyboard:
                    event['inline_keyboard'] = inline_keyboard

            # Конвертируем в безопасный словарь
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Ошибка парсинга callback: {e}")
            return None

    async def _parse_member_joined_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг события вступления участника из message с new_chat_member"""
        try:
            new_member = message.get('new_chat_member')
            if not new_member:
                self.logger.warning("Не найден new_chat_member в сообщении о вступлении")
                return None
            
            chat = message.get('chat', {})
            chat_type = chat.get('type')
            
            event = {
                'event_source': 'telegram',
                'event_type': 'member_joined',
                'user_id': new_member.get('id'),
                'chat_id': chat.get('id'),
                'chat_type': chat_type,
                'is_group': chat_type in ['group', 'supergroup'],
                'message_id': message.get('message_id'),
                'event_date': await self.datetime_formatter.to_iso_local_string(
                    await self.datetime_formatter.to_local(message.get('date')) if message.get('date') else await self.datetime_formatter.now_local()
                )
            }
            
            # Информация о пользователе
            event.update({
                'username': new_member.get('username'),
                'first_name': new_member.get('first_name'),
                'last_name': new_member.get('last_name'),
                'language_code': new_member.get('language_code'),
                'is_bot': new_member.get('is_bot', False),
                'is_premium': new_member.get('is_premium', False)
            })
            
            # Информация о чате
            if chat:
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })
            
            # Конвертируем в безопасный словарь
            return await self.data_converter.to_safe_dict(event)
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга member_joined из message: {e}")
            return None

    async def _parse_member_left_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг события выхода участника из message с left_chat_member"""
        try:
            left_member = message.get('left_chat_member')
            if not left_member:
                self.logger.warning("Не найден left_chat_member в сообщении о выходе")
                return None
            
            chat = message.get('chat', {})
            chat_type = chat.get('type')
            
            event = {
                'event_source': 'telegram',
                'event_type': 'member_left',
                'user_id': left_member.get('id'),
                'chat_id': chat.get('id'),
                'chat_type': chat_type,
                'is_group': chat_type in ['group', 'supergroup'],
                'message_id': message.get('message_id'),
                'event_date': await self.datetime_formatter.to_iso_local_string(
                    await self.datetime_formatter.to_local(message.get('date')) if message.get('date') else await self.datetime_formatter.now_local()
                )
            }
            
            # Информация о пользователе
            event.update({
                'username': left_member.get('username'),
                'first_name': left_member.get('first_name'),
                'last_name': left_member.get('last_name'),
                'language_code': left_member.get('language_code'),
                'is_bot': left_member.get('is_bot', False),
                'is_premium': left_member.get('is_premium', False)
            })
            
            # Информация о чате
            if chat:
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })
            
            # Конвертируем в безопасный словарь
            return await self.data_converter.to_safe_dict(event)
            
        except Exception as e:
            self.logger.error(f"Ошибка парсинга member_left из message: {e}")
            return None

    async def _parse_pre_checkout_query(self, pre_checkout_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг pre_checkout_query в стандартный формат события"""
        try:
            event = {
                'event_source': 'telegram',
                'event_type': 'pre_checkout_query',
                'user_id': pre_checkout_query.get('from', {}).get('id') if pre_checkout_query.get('from') else None,
                'pre_checkout_query_id': pre_checkout_query.get('id'),
                'invoice_payload': pre_checkout_query.get('invoice_payload'),
                'currency': pre_checkout_query.get('currency'),
                'total_amount': pre_checkout_query.get('total_amount'),
                'event_date': await self.datetime_formatter.to_iso_local_string(await self.datetime_formatter.now_local())
            }

            # Информация о пользователе
            if pre_checkout_query.get('from'):
                from_user = pre_checkout_query['from']
                event.update({
                    'username': from_user.get('username'),
                    'first_name': from_user.get('first_name'),
                    'last_name': from_user.get('last_name'),
                    'language_code': from_user.get('language_code'),
                    'is_bot': from_user.get('is_bot', False),
                    'is_premium': from_user.get('is_premium', False)
                })

            # Конвертируем в безопасный словарь
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Ошибка парсинга pre_checkout_query: {e}")
            return None

    async def _parse_successful_payment_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Парсинг successful_payment из message в стандартный формат события"""
        try:
            successful_payment = message.get('successful_payment')
            if not successful_payment:
                self.logger.warning("Не найден successful_payment в сообщении")
                return None
            
            chat = message.get('chat', {})
            chat_type = chat.get('type')
            
            event = {
                'event_source': 'telegram',
                'event_type': 'payment_successful',
                'user_id': message.get('from', {}).get('id') if message.get('from') else None,
                'chat_id': chat.get('id'),
                'chat_type': chat_type,
                'is_group': chat_type in ['group', 'supergroup'],
                'message_id': message.get('message_id'),
                'invoice_payload': successful_payment.get('invoice_payload'),
                'currency': successful_payment.get('currency'),
                'total_amount': successful_payment.get('total_amount'),
                'telegram_payment_charge_id': successful_payment.get('telegram_payment_charge_id'),
                'event_date': await self.datetime_formatter.to_iso_local_string(
                    await self.datetime_formatter.to_local(message.get('date')) if message.get('date') else await self.datetime_formatter.now_local()
                )
            }

            # Информация о пользователе
            if message.get('from'):
                from_user = message['from']
                event.update({
                    'username': from_user.get('username'),
                    'first_name': from_user.get('first_name'),
                    'last_name': from_user.get('last_name'),
                    'language_code': from_user.get('language_code'),
                    'is_bot': from_user.get('is_bot', False),
                    'is_premium': from_user.get('is_premium', False)
                })

            # Информация о чате
            if chat:
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })

            # Конвертируем в безопасный словарь
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Ошибка парсинга successful_payment из message: {e}")
            return None

    def _extract_inline_keyboard(self, message: Dict[str, Any]) -> Optional[List[List[Dict[str, str]]]]:
        """
        Извлекает inline-клавиатуру из сообщения и преобразует в наш формат.
        
        Формат Telegram: [[{text, callback_data}, ...], ...]
        Наш формат: [[{"Текст": "callback_data"}, ...], ...]
        
        Возвращает массив массивов, где каждый внутренний массив - строка кнопок.
        Каждая кнопка представлена словарем формата {"Текст кнопки": "callback_data"}.
        """
        try:
            reply_markup = message.get('reply_markup', {})
            if not reply_markup:
                return None
            
            inline_keyboard = reply_markup.get('inline_keyboard')
            if not inline_keyboard or not isinstance(inline_keyboard, list):
                return None
            
            # Преобразуем в наш формат: {"Текст": "callback_data"}
            parsed_keyboard = []
            for row in inline_keyboard:
                if not isinstance(row, list):
                    continue
                
                parsed_row = []
                for button in row:
                    if not isinstance(button, dict):
                        continue
                    
                    button_text = button.get('text')
                    if not button_text:
                        continue
                    
                    # Приоритет: callback_data > url > пустая строка
                    button_value = button.get('callback_data')
                    if not button_value:
                        button_value = button.get('url', '')
                    
                    # Преобразуем в формат проекта: {"Текст": "значение"}
                    if button_value:
                        button_data = {button_text: button_value}
                        parsed_row.append(button_data)
                
                # Добавляем строку только если в ней есть кнопки
                if parsed_row:
                    parsed_keyboard.append(parsed_row)
            
            return parsed_keyboard if parsed_keyboard else None
            
        except Exception as e:
            self.logger.warning(f"Ошибка извлечения inline-клавиатуры: {e}")
            return None

    def _extract_attachments(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Извлекает вложения из сообщения"""
        attachments = []

        # Фото
        if message.get('photo'):
            largest_photo = message['photo'][-1]  # Берем самое большое
            attachments.append({
                'type': 'photo',
                'file_id': largest_photo.get('file_id')
            })

        # Документ
        if message.get('document'):
            attachments.append({
                'type': 'document',
                'file_id': message['document'].get('file_id')
            })

        # Видео
        if message.get('video'):
            attachments.append({
                'type': 'video',
                'file_id': message['video'].get('file_id')
            })

        # Аудио
        if message.get('audio'):
            attachments.append({
                'type': 'audio',
                'file_id': message['audio'].get('file_id')
            })

        # Голосовое сообщение
        if message.get('voice'):
            attachments.append({
                'type': 'voice',
                'file_id': message['voice'].get('file_id')
            })

        # Стикер
        if message.get('sticker'):
            attachments.append({
                'type': 'sticker',
                'file_id': message['sticker'].get('file_id')
            })

        # Анимация
        if message.get('animation'):
            attachments.append({
                'type': 'animation',
                'file_id': message['animation'].get('file_id')
            })

        # Видео заметка
        if message.get('video_note'):
            attachments.append({
                'type': 'video_note',
                'file_id': message['video_note'].get('file_id')
            })

        return attachments
    
    async def _get_tenant_by_bot_id(self, bot_id: int) -> Optional[int]:
        """
        Получение tenant_id по bot_id из базы данных с кэшированием
        """
        try:
            # Проверяем кэш
            if bot_id in self._bot_tenant_cache:
                return self._bot_tenant_cache[bot_id]
            
            # Получаем из базы данных
            master_repo = self.database_manager.get_master_repository()
            bot_data = await master_repo.get_bot_by_id(bot_id)
            
            if bot_data and 'tenant_id' in bot_data:
                tenant_id = bot_data['tenant_id']
                # Сохраняем в кэш
                self._bot_tenant_cache[bot_id] = tenant_id
                return tenant_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка получения tenant_id по bot_id {bot_id}: {e}")
            return None
    
    async def _save_user_data(self, event: Dict[str, Any]) -> None:
        """
        Автоматическое сохранение данных пользователя при парсинге события
        """
        try:
            user_id = event.get('user_id')
            tenant_id = event.get('tenant_id')
            
            if not user_id or not tenant_id:
                # Нет данных пользователя для сохранения
                return
            
            # Подготавливаем данные пользователя
            user_data = {
                'tenant_id': tenant_id,
                'user_id': user_id,
                'username': event.get('username'),
                'first_name': event.get('first_name'),
                'last_name': event.get('last_name'),
                'language_code': event.get('language_code'),
                'is_bot': event.get('is_bot', False),
                'is_premium': event.get('is_premium', False)
            }
            
            # Сохраняем данные пользователя (с кэшированием)
            await self.user_manager.save_user_data(user_data)
            
            # Получаем состояние с проверкой истечения
            state_data = await self.user_manager.get_user_state(user_id, tenant_id)
            if state_data:
                event['user_state'] = state_data.get('user_state')
                event['user_state_expired_at'] = state_data.get('user_state_expired_at')
            
        except Exception as e:
            self.logger.error(f"Ошибка автоматического сохранения данных пользователя: {e}")
    
    def _get_tenant_config_key(self, tenant_id: int) -> str:
        """Генерация ключа кэша для конфига тенанта (совпадает с TenantCache)"""
        return f"tenant:{tenant_id}:config"
    
    async def _get_tenant_config(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Получение конфига тенанта из общего кэша (cache_manager) с fallback на БД
        Использует тот же ключ, что и TenantCache, поэтому всегда синхронизирован
        Возвращает словарь с конфигом (например, {"ai_token": "..."})
        
        Логика: сначала проверяем кэш, если нет - загружаем из БД и сохраняем в кэш.
        Это решает проблему рассинхрона при обновлении конфига.
        """
        try:
            # Шаг 1: Проверяем кэш
            cache_key = self._get_tenant_config_key(tenant_id)
            cached_config = await self.cache_manager.get(cache_key)
            
            if cached_config is not None:
                return cached_config
            
            # Шаг 2: Кэша нет - загружаем из БД (fallback для решения проблемы рассинхрона)
            self.logger.warning(f"[Tenant-{tenant_id}] Конфиг тенанта не найден в кэше, загружаем из БД")
            
            master_repo = self.database_manager.get_master_repository()
            tenant_data = await master_repo.get_tenant_by_id(tenant_id)
            
            if not tenant_data:
                return None
            
            # Формируем словарь конфига из всех полей БД (исключаем служебные)
            # Служебные поля: id, processed_at (и relationship поля, но они не попадают в словарь)
            config = {}
            excluded_fields = {'id', 'processed_at'}
            for key, value in tenant_data.items():
                if key not in excluded_fields and value is not None:
                    config[key] = value
            
            # Не сохраняем в кэш - им управляет TenantCache
            # Это редкий кейс, когда кэша нет, поэтому просто возвращаем данные из БД
            return config
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Ошибка получения конфига тенанта: {e}")
            return None
