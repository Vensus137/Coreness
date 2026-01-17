"""
Подмодуль для обработки вложений
"""

from typing import Dict, List, Optional

# Максимальное количество файлов в media group
MAX_MEDIA_GROUP = 10


class AttachmentHandler:
    """
    Подмодуль для обработки вложений Telegram
    """
    
    def __init__(self, api_client, **kwargs):
        self.logger = kwargs['logger']
        self.api_client = api_client
    
    def _create_media_item(self, media_type: str, file_id: str, caption: str = None, parse_mode: str = 'HTML') -> dict:
        """Создает корректный media объект для sendMediaGroup"""
        media_item = {"type": media_type, "media": file_id}
        if caption:
            media_item["caption"] = caption
            media_item["parse_mode"] = parse_mode
        return media_item
    
    def _group_attachments(self, attachments: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Группирует вложения: media (фото+видео), animation (только анимации), document (только документы).
        Анимации, аудио, голосовые сообщения, стикеры и видео заметки отправляются отдельно.
        """
        groups = {'media': [], 'animation': [], 'document': [], 'audio': [], 'voice': [], 'sticker': [], 'video_note': []}
        for att in attachments:
            if att['type'] == 'photo' or att['type'] == 'video':
                groups['media'].append(att)
            elif att['type'] == 'animation':
                groups['animation'].append(att)
            elif att['type'] == 'document':
                groups['document'].append(att)
            elif att['type'] == 'audio':
                groups['audio'].append(att)
            elif att['type'] == 'voice':
                groups['voice'].append(att)
            elif att['type'] == 'sticker':
                groups['sticker'].append(att)
            elif att['type'] == 'video_note':
                groups['video_note'].append(att)
        return groups
    
    async def send_attachments(self, bot_token: str, bot_id: int, chat_id: int, text: str, attachments: List[Dict[str, str]], 
                              reply_markup, parse_mode: str, reply_to_message_id: Optional[int] = None) -> Optional[int]:
        """Отправляет вложения с правильной группировкой"""
        
        if not attachments:
            return None
        
        # Группируем вложения
        groups = self._group_attachments(attachments)
        text_sent = False
        any_sent = False
        first_group = True
        last_message_id = None
        
        for group_type in ("media", "animation", "document", "audio", "voice", "sticker", "video_note"):
            files = groups.get(group_type, [])
            if not files:
                continue
            
            # Одиночное вложение (только для типов, которые могут быть в группах)
            if len(files) == 1 and group_type in ('media', 'document'):
                att = files[0]
                file_id = att['file_id']
                
                try:
                    caption = text if not text_sent else None
                    
                    # Подготавливаем параметры для отправки
                    payload = {
                        'chat_id': chat_id,
                        'reply_markup': reply_markup,
                        'parse_mode': parse_mode
                    }
                    
                    # Добавляем reply_to_message_id если нужно
                    if reply_to_message_id:
                        payload['reply_to_message_id'] = reply_to_message_id
                    
                    result = None
                    
                    try:
                        if att['type'] == 'photo':
                            payload.update(photo=file_id, caption=caption)
                            result = await self.api_client.make_request_with_limit(bot_token, "sendPhoto", payload, bot_id)
                        elif att['type'] == 'video':
                            payload.update(video=file_id, caption=caption)
                            result = await self.api_client.make_request_with_limit(bot_token, "sendVideo", payload, bot_id)
                        elif att['type'] == 'document':
                            payload.update(document=file_id, caption=caption)
                            result = await self.api_client.make_request_with_limit(bot_token, "sendDocument", payload, bot_id)
                    except Exception as e:
                        if 'message to reply not found' in str(e).lower() and reply_to_message_id:
                            self.logger.warning(f"Ответ на сообщение не удался для chat_id={chat_id}, message_id={reply_to_message_id}: {e}. Отправляю вложение без reply_to_message_id.")
                            payload.pop('reply_to_message_id', None)
                            if att['type'] == 'photo':
                                payload.update(photo=file_id, caption=caption)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendPhoto", payload, bot_id)
                            elif att['type'] == 'video':
                                payload.update(video=file_id, caption=caption)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendVideo", payload, bot_id)
                            elif att['type'] == 'document':
                                payload.update(document=file_id, caption=caption)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendDocument", payload, bot_id)
                        else:
                            raise
                    
                    if result and result.get('result') == 'success':
                        last_message_id = result.get('response_data', {}).get('message_id')
                        text_sent = True
                        any_sent = True
                        first_group = False
                    else:
                        # Если отправка не удалась, логируем предупреждение (fallback на текст будет позже)
                        if result:
                            self.logger.warning(f"[Bot-{bot_id}] Не удалось отправить вложение {file_id}: {result.get('error', 'Неизвестная ошибка')}")
                        else:
                            self.logger.warning(f"[Bot-{bot_id}] Не удалось отправить вложение {file_id}: результат пуст")
                except Exception as e:
                    self.logger.warning(f"Ошибка при отправке вложения {file_id}: {e}")
                continue  # не обрабатываем как группу
            
            # Анимации, аудио, голосовые сообщения, стикеры и видео заметки всегда отправляются по отдельности
            if group_type in ('animation', 'audio', 'voice', 'sticker', 'video_note'):
                for att in files:
                    try:
                        file_id = att['file_id']
                        caption = text if not text_sent else None
                        
                        # Подготавливаем параметры для отправки
                        payload = {
                            'chat_id': chat_id,
                            'reply_markup': reply_markup,
                            'parse_mode': parse_mode
                        }
                        
                        # Добавляем reply_to_message_id если нужно
                        if reply_to_message_id:
                            payload['reply_to_message_id'] = reply_to_message_id
                        
                        try:
                            if group_type == 'animation':
                                payload.update(animation=file_id, caption=caption)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendAnimation", payload, bot_id)
                            elif group_type == 'audio':
                                payload.update(audio=file_id, caption=caption)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendAudio", payload, bot_id)
                            elif group_type == 'voice':
                                payload.update(voice=file_id, caption=caption)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendVoice", payload, bot_id)
                            elif group_type == 'sticker':
                                payload.update(sticker=file_id)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendSticker", payload, bot_id)
                            elif group_type == 'video_note':
                                payload.update(video_note=file_id)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendVideoNote", payload, bot_id)
                        except Exception as e:
                            if 'message to reply not found' in str(e).lower() and reply_to_message_id:
                                self.logger.warning(f"Ответ на сообщение не удался для chat_id={chat_id}, message_id={reply_to_message_id}: {e}. Отправляю вложение без reply_to_message_id.")
                                payload.pop('reply_to_message_id', None)
                                if group_type == 'animation':
                                    payload.update(animation=file_id, caption=caption)
                                    result = await self.api_client.make_request_with_limit(bot_token, "sendAnimation", payload, bot_id)
                                elif group_type == 'audio':
                                    payload.update(audio=file_id, caption=caption)
                                    result = await self.api_client.make_request_with_limit(bot_token, "sendAudio", payload, bot_id)
                                elif group_type == 'voice':
                                    payload.update(voice=file_id, caption=caption)
                                    result = await self.api_client.make_request_with_limit(bot_token, "sendVoice", payload, bot_id)
                                elif group_type == 'sticker':
                                    payload.update(sticker=file_id)
                                    result = await self.api_client.make_request_with_limit(bot_token, "sendSticker", payload, bot_id)
                                elif group_type == 'video_note':
                                    payload.update(video_note=file_id)
                                    result = await self.api_client.make_request_with_limit(bot_token, "sendVideoNote", payload, bot_id)
                            else:
                                raise
                        
                        if result and result.get('result') == 'success':
                            last_message_id = result.get('response_data', {}).get('message_id')
                            text_sent = True
                            any_sent = True
                            first_group = False
                        else:
                            self.logger.warning(f"[Bot-{bot_id}] Не удалось отправить вложение {file_id}: {result.get('error', 'Неизвестная ошибка') if result else 'Результат пуст'}")
                    except Exception as e:
                        self.logger.warning(f"Ошибка при отправке вложения {file_id}: {e}")
                continue  # не обрабатываем как группу

            # Несколько вложений (media groups)
            for i in range(0, len(files), MAX_MEDIA_GROUP):
                batch = files[i:i+MAX_MEDIA_GROUP]
                media = []
                for idx, att in enumerate(batch):
                    try:
                        file_id = att['file_id']
                        caption = text if first_group and idx == 0 and not text_sent else None
                        if group_type == 'media':
                            if att['type'] == 'photo':
                                media.append(self._create_media_item("photo", file_id, caption, parse_mode))
                            elif att['type'] == 'video':
                                media.append(self._create_media_item("video", file_id, caption, parse_mode))
                        elif group_type == 'document':
                            media.append(self._create_media_item("document", file_id, caption, parse_mode))
                    except Exception as e:
                        self.logger.warning(f"Ошибка при подготовке media {file_id}: {e}")
                if media:
                    try:
                        # Подготавливаем параметры для отправки media group
                        payload = {'chat_id': chat_id, 'media': media}
                        
                        # Добавляем reply_to_message_id если нужно
                        if reply_to_message_id:
                            payload['reply_to_message_id'] = reply_to_message_id
                        
                        try:
                            result = await self.api_client.make_request_with_limit(bot_token, "sendMediaGroup", payload, bot_id)
                        except Exception as e:
                            if 'message to reply not found' in str(e).lower() and reply_to_message_id:
                                self.logger.warning(f"Ответ на сообщение не удался для chat_id={chat_id}, message_id={reply_to_message_id}: {e}. Отправляю группу медиа без reply_to_message_id.")
                                payload.pop('reply_to_message_id', None)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendMediaGroup", payload, bot_id)
                            else:
                                raise
                        if result and result.get('result') == 'success':
                            text_sent = True
                            any_sent = True
                            first_group = False
                            
                            # Для групп медиа используем последний файл как приближение last_message_id
                            # Telegram API не возвращает массив сообщений, поэтому это лучшее приближение
                            if media:
                                last_message_id = None  # Группы медиа не дают точного message_id
                        else:
                            self.logger.warning(f"[Bot-{bot_id}] Не удалось отправить группу медиа: {result.get('error', 'Неизвестная ошибка') if result else 'Результат пуст'}")
                    except Exception as e:
                        self.logger.warning(f"Ошибка при отправке группы медиа: {e}")
        
        # Если ни одно вложение не отправлено, а текст есть — отправить текстовое сообщение
        if not any_sent and text:
            self.logger.warning(f"[Bot-{bot_id}] Не удалось отправить вложения в чат {chat_id}, отправляю текстовое сообщение")
            payload = {
                'chat_id': chat_id,
                'text': text,
                'reply_markup': reply_markup,
                'parse_mode': parse_mode
            }
            
            if reply_to_message_id:
                payload['reply_to_message_id'] = reply_to_message_id
            result = await self.api_client.make_request_with_limit(bot_token, "sendMessage", payload, bot_id)
            if result and result.get('result') == 'success':
                last_message_id = result.get('response_data', {}).get('message_id')
            else:
                # Если и текст не удалось отправить - это ошибка
                self.logger.error(f"[Bot-{bot_id}] Не удалось отправить вложения и текстовое сообщение в чат {chat_id}: {result.get('error', 'Неизвестная ошибка') if result else 'Результат пуст'}")
                return None
        elif not any_sent and not text:
            # Нет ни вложений, ни текста - это ошибка
            self.logger.error(f"[Bot-{bot_id}] Не отправлено ни вложений, ни текста в чат {chat_id}")
            return None
        
        return last_message_id
