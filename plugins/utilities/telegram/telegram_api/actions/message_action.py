"""
MessageAction - действия с сообщениями через Telegram API
"""

from typing import Any, Dict, Optional


class MessageAction:
    """Действия с сообщениями через Telegram API"""
    
    def __init__(self, api_client, button_mapper, attachment_handler, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
        self.button_mapper = button_mapper
        self.attachment_handler = attachment_handler
    
    async def send_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Отправка сообщения с полной логикой"""
        try:
            # Извлекаем параметры из плоского словаря
            target_chat_id = data.get('target_chat_id')  # Новый параметр: integer или array
            chat_id = data.get('chat_id')  # Fallback на chat_id из контекста
            text = data.get('text', '')
            inline = data.get('inline')
            reply = data.get('reply')
            message_edit = data.get('message_edit')
            message_reply = data.get('message_reply')
            message_id = data.get('message_id')
            parse_mode = data.get('parse_mode', 'HTML')
            attachment = data.get('attachment')
            
            # Определяем список чатов для отправки
            # Если target_chat_id не указан, используем chat_id из контекста
            if target_chat_id is None:
                if chat_id is None:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Не указан чат для отправки (target_chat_id или chat_id из события)"
                        }
                    }
                target_chat_ids = [chat_id]
            elif isinstance(target_chat_id, int):
                target_chat_ids = [target_chat_id]
            elif isinstance(target_chat_id, list):
                target_chat_ids = target_chat_id
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "target_chat_id должен быть integer или array"
                    }
                }
            
            # Определяем ID сообщения для редактирования
            target_message_id = None
            if 'message_edit' in data:
                # Атрибут явно указан
                if message_edit is True:
                    # Редактируем текущее сообщение
                    target_message_id = message_id
                elif isinstance(message_edit, int):
                    # Редактируем указанное сообщение
                    target_message_id = message_edit
                # Если False или None - target_message_id остается None (отправляем новое)
            else:
                # Атрибут не указан - по умолчанию редактируем текущее сообщение
                target_message_id = message_id
            
            # Определяем параметры для reply
            reply_to_message_id = None
            if 'message_reply' in data:  # Атрибут явно указан
                if message_reply is True:
                    reply_to_message_id = message_id
                elif isinstance(message_reply, int):
                    reply_to_message_id = message_reply
            # Если message_reply не указан или False - не делаем reply
            
            # Формируем reply_markup из клавиатуры
            reply_markup = self.button_mapper.build_reply_markup(inline=inline, reply=reply)
            
            # Экранируем текст для MarkdownV2 если нужно
            escaped_text = self._escape_text_for_parse_mode(text, parse_mode)
            
            # Единый цикл обработки всех чатов
            success_count = 0
            last_message_id = None
            errors = []
            is_first_chat = True
            
            for current_chat_id in target_chat_ids:
                try:
                    # Если указан ID сообщения для редактирования - редактируем только в первом чате
                    if target_message_id and is_first_chat:
                        try:
                            payload = {
                                'chat_id': current_chat_id,
                                'message_id': target_message_id,
                                'text': escaped_text,
                                'parse_mode': parse_mode
                            }
                            
                            # Добавляем reply_markup только если он не None
                            if reply_markup is not None:
                                payload['reply_markup'] = reply_markup
                            
                            result = await self.api_client.make_request_with_limit(bot_token, "editMessageText", payload, bot_id)
                            if result.get('result') == 'success':
                                success_count += 1
                                # Сохраняем ID сообщения первого чата
                                last_message_id = target_message_id
                                continue  # Успешно отредактировали, переходим к следующему чату
                            # Если редактирование не удалось - fallback на отправку нового сообщения
                        except Exception:
                            # Если ошибка редактирования - fallback на отправку нового сообщения
                            pass
                    
                    # Отправляем новое сообщение (либо потому что не редактируем, либо это не первый чат, либо fallback при ошибке)
                    if attachment:
                        # Отправляем с вложениями
                        msg_id = await self.attachment_handler.send_attachments(
                            bot_token, bot_id, current_chat_id, escaped_text, attachment, reply_markup, parse_mode, reply_to_message_id
                        )
                        if msg_id:
                            success_count += 1
                            # Сохраняем ID сообщения только для первого чата
                            if is_first_chat:
                                last_message_id = msg_id
                        else:
                            # Если вложения не удалось отправить, но есть текст - отправляем текстовое сообщение как fallback
                            # (основной fallback уже обработан в attachment_handler.py, здесь дополнительная защита)
                            if escaped_text:
                                msg_id, error_msg = await self._send_text_message(
                                    bot_token, bot_id, current_chat_id, escaped_text, 
                                    parse_mode, reply_markup, reply_to_message_id
                                )
                                if msg_id:
                                    success_count += 1
                                    # Сохраняем ID сообщения только для первого чата
                                    if is_first_chat:
                                        last_message_id = msg_id
                                else:
                                    errors.append(f"Не удалось отправить вложения и текстовое сообщение в чат {current_chat_id}: {error_msg}")
                            else:
                                errors.append(f"Не удалось отправить вложения в чат {current_chat_id}")
                    else:
                        # Отправляем текстовое сообщение
                        msg_id, error_msg = await self._send_text_message(
                            bot_token, bot_id, current_chat_id, escaped_text, 
                            parse_mode, reply_markup, reply_to_message_id
                        )
                        if msg_id:
                            success_count += 1
                            # Сохраняем ID сообщения только для первого чата
                            if is_first_chat:
                                last_message_id = msg_id
                        else:
                            errors.append(f"Ошибка отправки в чат {current_chat_id}: {error_msg}")
                except Exception as e:
                    errors.append(f"Исключение при обработке чата {current_chat_id}: {str(e)}")
                finally:
                    # После обработки первого чата (независимо от результата), остальные получают новое сообщение
                    if is_first_chat:
                        is_first_chat = False
            
            # Формируем результат в зависимости от количества успешных отправок
            if success_count > 0:
                if errors:
                    self.logger.warning(f"Частично успешная обработка: {success_count}/{len(target_chat_ids)} успешно. Ошибки: {errors}")
                # Возвращаем только last_message_id первого успешно обработанного сообщения
                return {"result": "success", "response_data": {"last_message_id": last_message_id}}
            else:
                error_msg = "Не удалось обработать ни один чат. " + "; ".join(errors) if errors else "Неизвестная ошибка"
                return {
                    "result": "error",
                    "error": {
                        "code": "API_ERROR",
                        "message": error_msg
                    }
                }
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    async def _send_text_message(self, bot_token: str, bot_id: int, chat_id: int, text: str, 
                                 parse_mode: str, reply_markup: Optional[dict], 
                                 reply_to_message_id: Optional[int]) -> tuple[Optional[int], Optional[str]]:
        """
        Отправляет текстовое сообщение
        """
        try:
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            # Добавляем reply_markup только если он не None
            if reply_markup is not None:
                payload['reply_markup'] = reply_markup
            
            # Добавляем reply_to_message_id если нужно
            if reply_to_message_id:
                payload['reply_to_message_id'] = reply_to_message_id
            
            result = await self.api_client.make_request_with_limit(bot_token, "sendMessage", payload, bot_id)
            if result.get('result') == 'success':
                msg_id = result.get('response_data', {}).get('message_id')
                return msg_id, None
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                return None, error_msg
        except Exception as e:
            return None, str(e)
    
    def _escape_text_for_parse_mode(self, text: str, parse_mode: str) -> str:
        """
        Конвертирует Markdown в MarkdownV2 используя библиотеку telegramify-markdown
        
        Это решает все проблемы с экранированием и конвертацией синтаксиса.
        """
        if not text:
            return text
        
        if parse_mode == 'MarkdownV2':
            try:
                import telegramify_markdown
                # Конвертируем обычный markdown в MarkdownV2
                text = telegramify_markdown.markdownify(text)
            except Exception as e:
                self.logger.error(f"Ошибка конвертации markdown: {e}")
        
        return text
    
    async def delete_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Удаление сообщения"""
        try:
            # Извлекаем параметры из плоского словаря
            chat_id = data.get('chat_id')
            
            # Приоритет: delete_message_id, затем message_id
            message_id = data.get('delete_message_id') or data.get('message_id')
            
            if not chat_id or not message_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "chat_id или message_id не указаны"
                    }
                }
            
            # Строим payload из параметров
            payload = {
                'chat_id': chat_id,
                'message_id': message_id
            }

            result = await self.api_client.make_request_with_limit(bot_token, "deleteMessage", payload, bot_id)
            
            # Обрабатываем результат и возвращаем только нужные поля
            if result.get('result') == 'success':
                # Согласно config.yaml, при успехе возвращаем только result без response_data
                return {"result": "success"}
            else:
                # Возвращаем только result и error, без response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Неизвестная ошибка"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления сообщения: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
