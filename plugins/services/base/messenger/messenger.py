import asyncio
import mimetypes
import os
from typing import Dict, List, Optional, Union

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, InputMediaDocument,
                           InputMediaPhoto, InputMediaVideo, KeyboardButton,
                           ReplyKeyboardMarkup, ReplyKeyboardRemove)

# MAX_MEDIA_GROUP оставляю, остальные переменные удаляю
MAX_MEDIA_GROUP = 10

def detect_attachment_type(file_path: str) -> str:
    # Специальная обработка GIF как анимации (должна быть ПЕРЕД проверкой image/)
    if file_path.lower().endswith('.gif'):
        return 'animation'
    
    mime, _ = mimetypes.guess_type(file_path)
    
    if not mime:
        return 'document'
    
    if mime.startswith('image/'):
        return 'photo'
    if mime.startswith('video/'):
        return 'video'
    if mime.startswith('audio/'):
        return 'audio'
    return 'document'

class MessengerService:
    def __init__(self, **kwargs):
        self.button_mapper = kwargs['button_mapper']
        self.logger = kwargs['logger']
        self.database_service = kwargs['database_service']
        self.settings_manager = kwargs['settings_manager']
        self.bot = kwargs['bot_initializer'].get_bot()
        self.placeholder_processor = kwargs.get('placeholder_processor')
        
        # Получаем настройки через settings_manager
        settings = self.settings_manager.get_plugin_settings('messenger')
        self.callback_edit_default = settings.get('callback_edit_default', True)
        self.interval = settings.get('queue_read_interval', 0.05)
        self.batch_size = settings.get('queue_batch_size', 50)
        self.parse_mode = settings.get('parse_mode', None)
        self.enable_placeholder = settings.get('enable_placeholder', False)
        


    async def handle_action(self, action: dict) -> dict:
        try:
            if action.get('type') == 'send':
                params = self._extract_common_params(action)
                result = await self.send_message(action, params)
                if not result.get('success'):
                    self.logger.error(f"send: ошибка для chat_id={params['chat_id']}: {result.get('error', 'Неизвестная ошибка')}")
                return result
            elif action.get('type') == 'remove':
                result = await self.remove_message(action)
                if not result.get('success'):
                    self.logger.error(f"remove: ошибка для chat_id={action['chat_id']}: {result.get('error', 'Неизвестная ошибка')}")
                return result
            else:
                self.logger.error(f"неподдерживаемый тип действия: {action.get('type')}")
                return {'success': False, 'error': 'Неподдерживаемый тип действия'}
        except Exception as e:
            self.logger.exception(f"error: {e}")
            return {'success': False, 'error': str(e)}

    async def run(self):
        """
        Асинхронный цикл: читает pending-действия типа 'send' и 'remove' и обрабатывает их.
        """
        self.logger.info(f"старт фонового цикла обработки очереди действий (interval={self.interval}, batch_size={self.batch_size}).")
        while True:
            try:
                with self.database_service.session_scope('actions') as (_, repos):
                    actions_repo = repos['actions']
                    # Обрабатываем действия типа 'send' и 'remove'
                    actions = actions_repo.get_pending_actions_by_type_parsed(['send', 'remove'], limit=self.batch_size)
                    
                    for action in actions:
                        action_id = action['id']
                        try:
                            result = await self.handle_action(action)
                            status = 'completed' if result.get('success') else 'failed'
                        except Exception as e:
                            self.logger.exception(f"Ошибка при обработке действия {action_id}: {e}")
                            status = 'failed'
                        
                        # Обновляем статус действия
                        if not actions_repo.update_action(action_id, status=status):
                            self.logger.error(f"Не удалось обновить статус действия {action_id} на {status}")
                    
            except Exception as e:
                self.logger.error(f"ошибка в основном цикле: {e}")
            await asyncio.sleep(self.interval)

    def _extract_common_params(self, action: dict) -> dict:
        chat_id = action['chat_id']
        message_id = action.get('message_id')

        # --- Обработка private_answer ---
        user_id = action.get('user_id')
        private_answer = action.get('private_answer', False)
        
        if private_answer and user_id:
            chat_id = user_id
        elif private_answer and not user_id:
            self.logger.error("private_answer=True, но user_id отсутствует в action. Сообщение будет отправлено в исходный чат.")

        inline = action.get('inline')
        reply = action.get('reply')
        attachments = self._parse_attachments(action)

        # Логика приоритетов: callback_edit > remove > глобальный callback_edit_default
        message_reply = action.get('message_reply', False)
        callback_edit = action.get('callback_edit')
        if callback_edit is None:
            callback_edit = self.callback_edit_default if self.callback_edit_default is not None else False
        remove = action.get('remove', False)

        # --- Проверка совместимости параметров (message_reply > edit > remove) ---
        if message_reply:
            if callback_edit:
                self.logger.warning("Параметр callback_edit игнорируется, так как задан message_reply (message_reply > edit)")
            if remove:
                self.logger.warning("Параметр remove игнорируется, так как задан message_reply (message_reply > remove)")
            callback_edit = False
            remove = False
        elif callback_edit:
            if remove:
                self.logger.warning("Параметр remove игнорируется, так как задан edit (edit > remove)")
            remove = False
        # иначе remove может быть true

        return {
            'chat_id': chat_id,
            'message_id': message_id,
            'callback_edit': callback_edit,
            'remove': remove,
            'inline': inline,
            'reply': reply,
            'attachments': attachments,
            'message_reply': message_reply,  # Новое поле
            'private_answer': private_answer,
            'user_id': user_id,
        }

    async def send_message(self, action: dict, params: dict) -> dict:
        """Отправляет сообщение с правильной обработкой ошибок."""
        try:
            # Критическая проверка 1: бот инициализирован
            if not self.bot:
                self.logger.error("Бот не инициализирован")
                return {'success': False, 'error': 'Бот не инициализирован'}

            chat_id = params['chat_id']
            
            # Получаем текст (может быть пустым или отсутствовать)
            text = action.get('text', '')
            
            # --- Добавляем additional_text если указан ---
            additional_text = action.get('additional_text')
            if additional_text:
                text = text + additional_text
            
            # --- Обработка плейсхолдеров в тексте ---
            # Проверяем глобальную настройку и явное отключение в action
            placeholders_enabled = self.enable_placeholder
            if 'placeholder' in action:
                # Явное указание в action имеет приоритет над глобальной настройкой
                placeholders_enabled = action['placeholder']
            
            if placeholders_enabled and self.placeholder_processor:
                try:
                    # Используем action как словарь значений для плейсхолдеров
                    text = self.placeholder_processor.process_text_placeholders(text, action)
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки плейсхолдеров в тексте: {e}")
            
            # --- Обработка плейсхолдеров в attachment ---
            if placeholders_enabled and self.placeholder_processor and 'attachment' in action:
                try:
                    attachment_raw = action['attachment']
                    if isinstance(attachment_raw, str) and '{' in attachment_raw:
                        processed_attachment = self.placeholder_processor.process_text_placeholders(attachment_raw, action)
                        action['attachment'] = processed_attachment
                except Exception as e:
                    self.logger.warning(f"Ошибка обработки плейсхолдеров в attachment: {e}")
            
            message_id = params['message_id']
            callback_edit = params['callback_edit']
            remove = params['remove']
            inline = params['inline']
            reply = params['reply']
            attachments = params['attachments']
            message_reply = params.get('message_reply', False)

            # Определяем parse_mode: приоритет у action, иначе используем настройку
            parse_mode = action.get('parse_mode') or self.parse_mode

            # --- Проверка и обрезка длины текста ---
            if text:  # Проверяем только если текст не пустой
                max_text_length = 1024 if attachments else 4096
                if len(text) > max_text_length:
                    original_length = len(text)
                    text = text[:max_text_length]
                    self.logger.warning(
                        f"Текст обрезан с {original_length} до {max_text_length} символов "
                        f"(лимит для {'вложений' if attachments else 'обычных сообщений'})"
                    )

            # Если есть вложения, всегда отправляем новое сообщение (редактировать с вложениями нельзя)
            if attachments and callback_edit:
                self.logger.warning(f"callback_edit=True игнорируется, так как у сообщения есть вложения. Будет отправлено новое сообщение без редактирования.")
                callback_edit = False

            # Получаем координаты из action_data для формирования callback_data
            reply_markup = self._build_reply_markup(inline, reply)

            # Отправляем или редактируем сообщение
            try:
                if callback_edit and message_id:
                    await self._edit_message(chat_id, message_id, text, reply_markup, parse_mode)
                else:
                    if attachments:
                        await self._send_attachments(chat_id, text, attachments, reply_markup, parse_mode, message_id, message_reply)
                    elif text:  # Отправляем текстовое сообщение только если есть текст
                        # Новое: если message_reply true и есть message_id, отправляем как reply
                        send_kwargs = dict(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                        if message_reply and message_id:
                            send_kwargs['reply_to_message_id'] = message_id
                            try:
                                await self.bot.send_message(**send_kwargs)
                            except TelegramBadRequest as e:
                                if 'message to reply not found' in str(e).lower():
                                    self.logger.warning(f"ответ на сообщение не удался (сообщение для ответа не найдено) для chat_id={chat_id}, message_id={message_id}: {e}. Отправляю новое сообщение без reply_to_message_id.")
                                    send_kwargs.pop('reply_to_message_id', None)
                                    await self.bot.send_message(**send_kwargs)
                                else:
                                    raise
                        else:
                            await self.bot.send_message(**send_kwargs)
                    else:
                        # Нет ни текста, ни вложений - это ошибка
                        self.logger.error("Тип действия 'send' требует либо 'text', либо 'attachment'")
                        return {'success': False, 'error': 'Не указан текст или вложение'}
            except Exception as e:
                self.logger.error(f"Критическая ошибка при отправке сообщения: {e}")
                return {'success': False, 'error': f'Ошибка отправки сообщения: {str(e)}'}

            # Удаляем исходное сообщение если указан атрибут remove
            if remove and message_id:
                try:
                    await self.bot.delete_message(chat_id, message_id)
                except TelegramBadRequest as e:
                    self.logger.warning(f"Не удалось удалить исходное сообщение chat_id={chat_id}, message_id={message_id}: {e}")
                except Exception as e:
                    self.logger.error(f"Ошибка при удалении исходного сообщения chat_id={chat_id}, message_id={message_id}: {e}")

            return {'success': True}

        except Exception as e:
            self.logger.error(f"Неожиданная ошибка в send_message: {e}")
            return {'success': False, 'error': f'Неожиданная ошибка: {str(e)}'}

    def _parse_attachments(self, action: dict) -> List[dict]:
        """
        Преобразует вложения в список словарей с ключами: file, type (document, photo, video, audio)
        Поддерживает старый и новый формат.
        Если явно указан type — использовать его приоритетно, не определять по mime.
        """
        raw = action.get('attachment')
        if not raw:
            return []
        
        result = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    file = item.get('attachment') or item.get('file')
                    atype = item.get('type')
                    if not file:
                        continue  # пропускаем если нет файла
                    if atype:
                        result.append({'file': file, 'type': atype})
                    else:
                        detected_type = detect_attachment_type(file)
                        result.append({'file': file, 'type': detected_type})
                elif isinstance(item, str):
                    detected_type = detect_attachment_type(item)
                    result.append({'file': item, 'type': detected_type})
        elif isinstance(raw, dict):
            file = raw.get('attachment') or raw.get('file')
            if not file:
                return result
            atype = raw.get('type')
            if atype:
                result.append({'file': file, 'type': atype})
            else:
                detected_type = detect_attachment_type(file)
                result.append({'file': file, 'type': detected_type})
        elif isinstance(raw, str):
            detected_type = detect_attachment_type(raw)
            result.append({'file': raw, 'type': detected_type})
        
        return result

    def _resolve_attachment_path(self, file_path: str) -> str:
        if os.path.isabs(file_path):
            resolved_path = file_path
        else:
            # Используем глобальную настройку для базового пути
            resolved_path = self.settings_manager.resolve_file_path(file_path)
        return resolved_path

    def _build_reply_markup(self, inline, reply) -> Optional[Union[InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove]]:
        # Приоритет: inline > reply
        if inline:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        self._build_inline_button(btn) for btn in row
                    ]
                    for row in inline
                ]
            )
            return markup
        
        # Обработка reply клавиатуры
        if reply is not None:  # Изменено: проверяем на None, а не на truthiness
            if reply == []:  # Пустой список = убрать клавиатуру
                from aiogram.types import ReplyKeyboardRemove
                return ReplyKeyboardRemove()
            elif reply:  # Непустой список = показать клавиатуру
                markup = ReplyKeyboardMarkup(
                    keyboard=[
                        [KeyboardButton(text=btn) for btn in row]
                        for row in reply
                    ],
                    resize_keyboard=True
                )
                return markup
        
        return None

    def _build_inline_button(self, btn) -> InlineKeyboardButton:
        """
        Строит InlineKeyboardButton с универсальной логикой.
        
        Поддерживаемые форматы:
        - "Текст" -> callback_data с нормализованным текстом
        - {"Текст": "scenario_name"} -> callback_data с :scenario_name
        - {"Текст": "https://example.com"} -> URL кнопка (если значение похоже на ссылку)
        """
        if isinstance(btn, str):
            # Простая строка -> callback_data
            return InlineKeyboardButton(
                        text=btn,
                        callback_data=self.button_mapper.normalize(btn)
                    )
        elif isinstance(btn, dict):
            text = list(btn.keys())[0]
            value = list(btn.values())[0]
            
            if isinstance(value, str):
                # Проверяем, является ли значение ссылкой
                if value.startswith(("http://", "https://", "tg://")):
                    return InlineKeyboardButton(
                        text=text,
                        url=value
                    )
                else:
                    # Иначе считаем это именем сценария
                    return InlineKeyboardButton(
                        text=text,
                        callback_data=f":{value}"
                    )
            else:
                # Неизвестный тип значения -> резервный вариант
                self.logger.warning(f"Неизвестный тип значения кнопки: {type(value)}. Использую резервный вариант.")
                return InlineKeyboardButton(
                    text=text,
                    callback_data=self.button_mapper.normalize(text)
                )
        else:
            # Неизвестный тип -> резервный вариант
            self.logger.warning(f"Неизвестный тип кнопки: {type(btn)}. Использую резервный вариант.")
            return InlineKeyboardButton(
                text=str(btn),
                callback_data=self.button_mapper.normalize(str(btn))
            )

    async def _edit_message(self, chat_id, message_id, text, reply_markup, parse_mode):
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except TelegramBadRequest as e:
            self.logger.warning(
                f"edit_message не удался для chat_id={chat_id}, message_id={message_id}: {e}. Отправляю новое сообщение."
            )
            await self.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    async def _send_attachments(self, chat_id, text, attachments, reply_markup, parse_mode, message_id=None, message_reply=False):
        # Группируем вложения: media (фото+видео), document (только документы)
        groups = self._group_attachments(attachments)
        text_sent = False
        any_sent = False
        first_group = True
        for group_type in ("media", "animation", "document", "audio"):
            files = groups.get(group_type, [])
            if not files:
                continue
            # --- Одиночное вложение ---
            if len(files) == 1:
                att = files[0]
                file_path = self._resolve_attachment_path(att['file'])
                if not os.path.isfile(file_path):
                    self.logger.warning(f"Вложение не найдено: {file_path}")
                    continue
                try:
                    file = FSInputFile(file_path)
                    caption = text if not text_sent else None
                    
                    # Подготавливаем параметры для отправки
                    send_kwargs = dict(
                        chat_id=chat_id,
                        reply_markup=reply_markup,
                        parse_mode=parse_mode
                    )
                    
                    # Добавляем reply_to_message_id если нужно
                    if message_reply and message_id:
                        send_kwargs['reply_to_message_id'] = message_id
                    
                    msg = None
                    try:
                        if att['type'] == 'photo':
                            send_kwargs.update(photo=file, caption=caption)
                            msg = await self.bot.send_photo(**send_kwargs)
                        elif att['type'] == 'animation':
                            send_kwargs.update(animation=file, caption=caption)
                            msg = await self.bot.send_animation(**send_kwargs)
                        elif att['type'] == 'video':
                            send_kwargs.update(video=file, caption=caption)
                            msg = await self.bot.send_video(**send_kwargs)
                        elif att['type'] == 'document':
                            send_kwargs.update(document=file, caption=caption)
                            msg = await self.bot.send_document(**send_kwargs)
                        elif att['type'] == 'audio':
                            send_kwargs.update(audio=file, caption=caption)
                            msg = await self.bot.send_audio(**send_kwargs)
                    except TelegramBadRequest as e:
                        if 'message to reply not found' in str(e).lower() and message_reply and message_id:
                            self.logger.warning(f"ответ на сообщение не удался (сообщение для ответа не найдено) для chat_id={chat_id}, message_id={message_id}: {e}. Отправляю вложение без reply_to_message_id.")
                            send_kwargs.pop('reply_to_message_id', None)
                            if att['type'] == 'photo':
                                send_kwargs.update(photo=file, caption=caption)
                                msg = await self.bot.send_photo(**send_kwargs)
                            elif att['type'] == 'animation':
                                send_kwargs.update(animation=file, caption=caption)
                                msg = await self.bot.send_animation(**send_kwargs)
                            elif att['type'] == 'video':
                                send_kwargs.update(video=file, caption=caption)
                                msg = await self.bot.send_video(**send_kwargs)
                            elif att['type'] == 'document':
                                send_kwargs.update(document=file, caption=caption)
                                msg = await self.bot.send_document(**send_kwargs)
                            elif att['type'] == 'audio':
                                send_kwargs.update(audio=file, caption=caption)
                                msg = await self.bot.send_audio(**send_kwargs)
                        else:
                            raise
                    text_sent = True
                    any_sent = True
                    first_group = False
                except Exception as e:
                    self.logger.error(f"Ошибка при отправке вложения {file_path}: {e}")
                continue  # не обрабатываем как группу
            
            # --- Анимации и аудио всегда отправляются по отдельности ---
            if group_type in ('animation', 'audio'):
                for att in files:
                    file_path = self._resolve_attachment_path(att['file'])
                    if not os.path.isfile(file_path):
                        self.logger.warning(f"Вложение не найдено: {file_path}")
                        continue
                    try:
                        file = FSInputFile(file_path)
                        caption = text if not text_sent else None
                        
                        # Подготавливаем параметры для отправки
                        send_kwargs = dict(
                            chat_id=chat_id,
                            reply_markup=reply_markup,
                            parse_mode=parse_mode
                        )
                        
                        # Добавляем reply_to_message_id если нужно
                        if message_reply and message_id:
                            send_kwargs['reply_to_message_id'] = message_id
                        
                        try:
                            if group_type == 'animation':
                                send_kwargs.update(animation=file, caption=caption)
                                await self.bot.send_animation(**send_kwargs)
                            elif group_type == 'audio':
                                send_kwargs.update(audio=file, caption=caption)
                                await self.bot.send_audio(**send_kwargs)
                        except TelegramBadRequest as e:
                            if 'message to reply not found' in str(e).lower() and message_reply and message_id:
                                self.logger.warning(f"ответ на сообщение не удался (сообщение для ответа не найдено) для chat_id={chat_id}, message_id={message_id}: {e}. Отправляю вложение без reply_to_message_id.")
                                send_kwargs.pop('reply_to_message_id', None)
                                if group_type == 'animation':
                                    send_kwargs.update(animation=file, caption=caption)
                                    await self.bot.send_animation(**send_kwargs)
                                elif group_type == 'audio':
                                    send_kwargs.update(audio=file, caption=caption)
                                    await self.bot.send_audio(**send_kwargs)
                            else:
                                raise
                        text_sent = True
                        any_sent = True
                        first_group = False
                    except Exception as e:
                        self.logger.error(f"Ошибка при отправке анимации/аудиофайла {file_path}: {e}")
                continue  # не обрабатываем как группу

            # --- Несколько вложений ---
            for i in range(0, len(files), MAX_MEDIA_GROUP):
                batch = files[i:i+MAX_MEDIA_GROUP]
                media = []
                for idx, att in enumerate(batch):
                    file_path = self._resolve_attachment_path(att['file'])
                    if not os.path.isfile(file_path):
                        self.logger.warning(f"Вложение не найдено: {file_path}")
                        continue
                    try:
                        file = FSInputFile(file_path)
                        caption = text if first_group and idx == 0 and not text_sent else None
                        if group_type == 'media':
                            if att['type'] == 'photo':
                                media.append(InputMediaPhoto(media=file, caption=caption, parse_mode=parse_mode))
                            elif att['type'] == 'video':
                                media.append(InputMediaVideo(media=file, caption=caption, parse_mode=parse_mode))
                        elif group_type == 'document':
                            media.append(InputMediaDocument(media=file, caption=caption, parse_mode=parse_mode))
                    except Exception as e:
                        self.logger.error(f"Ошибка при подготовке media {file_path}: {e}")
                if media:
                    try:
                        # Подготавливаем параметры для отправки media group
                        send_kwargs = dict(chat_id=chat_id, media=media)
                        
                        # Добавляем reply_to_message_id если нужно (поддерживается в Telegram API)
                        if message_reply and message_id:
                            send_kwargs['reply_to_message_id'] = message_id
                        
                        try:
                            await self.bot.send_media_group(**send_kwargs)
                        except TelegramBadRequest as e:
                            if 'message to reply not found' in str(e).lower() and message_reply and message_id:
                                self.logger.warning(f"ответ на сообщение не удался (сообщение для ответа не найдено) для chat_id={chat_id}, message_id={message_id}: {e}. Отправляю группу медиа без reply_to_message_id.")
                                send_kwargs.pop('reply_to_message_id', None)
                                await self.bot.send_media_group(**send_kwargs)
                            else:
                                raise
                        text_sent = True
                        any_sent = True
                        first_group = False
                    except Exception as e:
                        self.logger.error(f"Ошибка при отправке группы медиа: {e}")
        # Если ни одно вложение не отправлено, а текст есть — отправить текстовое сообщение
        if not any_sent and text:
            await self.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif not any_sent and not text:
            # Нет ни вложений, ни текста - это ошибка
            self.logger.error("Не отправлено ни вложений, ни текста")
            raise ValueError("Нет контента для отправки")

    def _group_attachments(self, attachments: List[dict]) -> Dict[str, List[dict]]:
        """
        Группирует вложения: media (фото+видео), animation (только анимации), document (только документы).
        Анимации и аудио отправляются отдельно, так как не поддерживаются в media groups.
        """
        groups = {'media': [], 'animation': [], 'document': [], 'audio': []}
        for att in attachments:
            if att['type'] == 'photo' or att['type'] == 'video':
                groups['media'].append(att)
            elif att['type'] == 'animation':
                groups['animation'].append(att)
            elif att['type'] == 'document':
                groups['document'].append(att)
            elif att['type'] == 'audio':
                groups['audio'].append(att)
        return groups

    async def remove_message(self, action: dict) -> dict:
        """
        Удаляет сообщение из чата.
        """
        chat_id = action['chat_id']
        message_id = action['message_id']

        try:
            await self.bot.delete_message(chat_id, message_id)
            return {'success': True}
        except TelegramBadRequest as e:
            self.logger.warning(f"Не удалось удалить сообщение chat_id={chat_id}, message_id={message_id}: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            self.logger.error(f"Ошибка при удалении сообщения chat_id={chat_id}, message_id={message_id}: {e}")
            return {'success': False, 'error': str(e)}



