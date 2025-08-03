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
        self.attachments_root = settings.get('attachments_root', 'resources')
        self.parse_mode = settings.get('parse_mode', None)
        self.enable_placeholder = settings.get('enable_placeholder', False)
        
        # Условная загрузка расширений
        self.extensions = None
        try:
            from .messenger_extensions import MessengerExtensions
            self.extensions = MessengerExtensions()
            self.logger.info("Расширения messenger загружены успешно")
        except ImportError:
            self.logger.info("Расширения messenger недоступны - функционал private_answer и remove_message отключен")

    async def handle_action(self, action: dict) -> dict:
        try:
            if action.get('type') == 'send':
                params = self._extract_common_params(action)
                result = await self.send_message(action, params)
                if not result.get('success'):
                    self.logger.error(f"send: ошибка для chat_id={params['chat_id']}: {result.get('error', 'Неизвестная ошибка')}")
                return result
            elif action.get('type') == 'remove':
                if self.extensions:
                    result = await self.extensions.remove_message(self.bot, action, self.logger)
                    if not result.get('success'):
                        self.logger.error(f"remove: ошибка для chat_id={action['chat_id']}: {result.get('error', 'Неизвестная ошибка')}")
                    return result
                else:
                    self.logger.warning("Функционал удаления сообщений недоступен - расширения не загружены")
                    return {'success': False, 'error': 'Функционал удаления отключен'}
            else:
                self.logger.error(f"неподдерживаемый тип действия: {action.get('type')}")
                return {'success': False, 'error': 'Unsupported action type'}
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

        # --- Обработка private_answer через расширения ---
        user_id = action.get('user_id')
        private_answer = action.get('private_answer', False)  # Инициализируем переменную
        
        if self.extensions:
            chat_id = self.extensions.process_private_answer(action, chat_id, user_id, self.logger)
        else:
            # Если расширения недоступны, игнорируем private_answer
            if private_answer:
                self.logger.warning("private_answer=True, но extensions не загружены. Сообщение будет отправлено в исходный чат.")

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
                self.logger.error("Bot not initialized")
                return {'success': False, 'error': 'Bot not initialized'}

            chat_id = params['chat_id']
            
            # Критическая проверка 2: наличие текста
            if 'text' not in action:
                self.logger.error("Action type 'send' requires 'text' field")
                return {'success': False, 'error': 'No text provided'}
            
            text = action['text']
            
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
                        await self._send_attachments(chat_id, text, attachments, reply_markup, parse_mode)
                    else:
                        # Новое: если message_reply true и есть message_id, отправляем как reply
                        send_kwargs = dict(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
                        if message_reply and message_id:
                            send_kwargs['reply_to_message_id'] = message_id
                            try:
                                await self.bot.send_message(**send_kwargs)
                            except TelegramBadRequest as e:
                                if 'message to reply not found' in str(e).lower():
                                    self.logger.warning(f"message_reply failed (message to reply not found) для chat_id={chat_id}, message_id={message_id}: {e}. Отправляю новое сообщение без reply_to_message_id.")
                                    send_kwargs.pop('reply_to_message_id', None)
                                    await self.bot.send_message(**send_kwargs)
                                else:
                                    raise
                        else:
                            await self.bot.send_message(**send_kwargs)
            except Exception as e:
                self.logger.error(f"Критическая ошибка при отправке сообщения: {e}")
                return {'success': False, 'error': f'Failed to send message: {str(e)}'}

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
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}

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
                        result.append({'file': file, 'type': detect_attachment_type(file)})
                elif isinstance(item, str):
                    result.append({'file': item, 'type': detect_attachment_type(item)})
        elif isinstance(raw, dict):
            file = raw.get('attachment') or raw.get('file')
            if not file:
                return result
            atype = raw.get('type')
            if atype:
                result.append({'file': file, 'type': atype})
            else:
                result.append({'file': file, 'type': detect_attachment_type(file)})
        elif isinstance(raw, str):
            result.append({'file': raw, 'type': detect_attachment_type(raw)})
        return result

    def _resolve_attachment_path(self, file_path: str) -> str:
        if os.path.isabs(file_path):
            return file_path
        return os.path.join(self.attachments_root, file_path)

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
                # Неизвестный тип значения -> fallback
                self.logger.warning(f"Неизвестный тип значения кнопки: {type(value)}. Использую fallback.")
                return InlineKeyboardButton(
                    text=text,
                    callback_data=self.button_mapper.normalize(text)
                )
        else:
            # Неизвестный тип -> fallback
            self.logger.warning(f"Неизвестный тип кнопки: {type(btn)}. Использую fallback.")
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
                f"edit_message failed for chat_id={chat_id}, message_id={message_id}: {e}. Will send new message instead."
            )
            await self.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    async def _send_attachments(self, chat_id, text, attachments, reply_markup, parse_mode):
        # Группируем вложения: media (фото+видео), document (только документы)
        groups = self._group_attachments(attachments)
        text_sent = False
        any_sent = False
        first_group = True
        for group_type in ("media", "animation", "document"):
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
                    msg = None
                    if att['type'] == 'photo':
                        msg = await self.bot.send_photo(chat_id, photo=file, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                    elif att['type'] == 'animation':
                        msg = await self.bot.send_animation(chat_id, animation=file, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                    elif att['type'] == 'video':
                        msg = await self.bot.send_video(chat_id, video=file, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                    elif att['type'] == 'document':
                        msg = await self.bot.send_document(chat_id, document=file, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                    elif att['type'] == 'audio':
                        msg = await self.bot.send_audio(chat_id, audio=file, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                    text_sent = True
                    any_sent = True
                    first_group = False
                except Exception as e:
                    self.logger.error(f"Ошибка при отправке вложения {file_path}: {e}")
                continue  # не обрабатываем как группу
            
            # --- Анимации всегда отправляются по отдельности ---
            if group_type == 'animation':
                for att in files:
                    file_path = self._resolve_attachment_path(att['file'])
                    if not os.path.isfile(file_path):
                        self.logger.warning(f"Вложение не найдено: {file_path}")
                        continue
                    try:
                        file = FSInputFile(file_path)
                        caption = text if not text_sent else None
                        await self.bot.send_animation(chat_id, animation=file, caption=caption, reply_markup=reply_markup, parse_mode=parse_mode)
                        text_sent = True
                        any_sent = True
                        first_group = False
                    except Exception as e:
                        self.logger.error(f"Ошибка при отправке анимации {file_path}: {e}")
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
                        await self.bot.send_media_group(chat_id, media=media)
                        text_sent = True
                        any_sent = True
                        first_group = False
                    except Exception as e:
                        self.logger.error(f"Ошибка при отправке media_group: {e}")
        # Если ни одно вложение не отправлено, а текст есть — отправить текстовое сообщение
        if not any_sent and text:
            await self.bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

    def _group_attachments(self, attachments: List[dict]) -> Dict[str, List[dict]]:
        """
        Группирует вложения: media (фото+видео), animation (только анимации), document (только документы).
        Анимации отправляются отдельно, так как не поддерживаются в media groups.
        Аудио и прочие неподдерживаемые типы игнорируются в группах.
        """
        groups = {'media': [], 'animation': [], 'document': []}
        for att in attachments:
            if att['type'] == 'photo' or att['type'] == 'video':
                groups['media'].append(att)
            elif att['type'] == 'animation':
                groups['animation'].append(att)
            elif att['type'] == 'document':
                groups['document'].append(att)
            # audio и другие типы игнорируются в группах
        return groups



