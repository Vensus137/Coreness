"""
MessageAction - actions with messages via Telegram API
"""

from typing import Any, Dict, Optional


class MessageAction:
    """Actions with messages via Telegram API"""
    
    def __init__(self, api_client, button_mapper, attachment_handler, **kwargs):
        self.api_client = api_client
        self.logger = kwargs['logger']
        self.button_mapper = button_mapper
        self.attachment_handler = attachment_handler
    
    async def send_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Send message with full logic"""
        try:
            # Extract parameters from flat dictionary
            target_chat_id = data.get('target_chat_id')  # New parameter: integer or array
            chat_id = data.get('chat_id')  # Fallback to chat_id from context
            text = data.get('text', '')
            inline = data.get('inline')
            reply = data.get('reply')
            message_edit = data.get('message_edit')
            message_reply = data.get('message_reply')
            message_id = data.get('message_id')
            parse_mode = data.get('parse_mode', 'HTML')
            attachment = data.get('attachment')
            
            # Determine list of chats to send to
            # If target_chat_id is not specified, use chat_id from context
            if target_chat_id is None:
                if chat_id is None:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "Chat not specified for sending (target_chat_id or chat_id from event)"
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
                        "message": "target_chat_id must be integer or array"
                    }
                }
            
            # Determine message ID for editing
            target_message_id = None
            if 'message_edit' in data:
                # Attribute explicitly specified
                if message_edit is True:
                    # Edit current message
                    target_message_id = message_id
                elif isinstance(message_edit, int):
                    target_message_id = message_edit
                elif isinstance(message_edit, str):
                    parsed = self._parse_message_id(message_edit)
                    if parsed is not None:
                        target_message_id = parsed
                # If False or None - target_message_id remains None (send new)
            else:
                # Attribute not specified - by default edit current message
                target_message_id = message_id

            # Determine parameters for reply
            reply_to_message_id = None
            if 'message_reply' in data:  # Attribute explicitly specified
                if message_reply is True:
                    reply_to_message_id = message_id
                elif isinstance(message_reply, int):
                    reply_to_message_id = message_reply
                elif isinstance(message_reply, str):
                    parsed = self._parse_message_id(message_reply)
                    if parsed is not None:
                        reply_to_message_id = parsed
            # If message_reply not specified or False - don't do reply
            
            # Build reply_markup from keyboard
            reply_markup = self.button_mapper.build_reply_markup(inline=inline, reply=reply)
            
            # Escape text for MarkdownV2 if needed
            escaped_text = self._escape_text_for_parse_mode(text, parse_mode)
            
            # Single loop for processing all chats
            success_count = 0
            last_message_id = None
            errors = []
            is_first_chat = True
            
            for current_chat_id in target_chat_ids:
                try:
                    # If message ID for editing is specified - edit only in first chat
                    if target_message_id and is_first_chat:
                        try:
                            payload = {
                                'chat_id': current_chat_id,
                                'message_id': target_message_id,
                                'text': escaped_text,
                                'parse_mode': parse_mode
                            }
                            
                            # Add reply_markup only if it's not None
                            if reply_markup is not None:
                                payload['reply_markup'] = reply_markup
                            
                            result = await self.api_client.make_request_with_limit(bot_token, "editMessageText", payload, bot_id)
                            if result.get('result') == 'success':
                                success_count += 1
                                # Save message ID of first chat
                                last_message_id = target_message_id
                                continue  # Successfully edited, move to next chat
                            # If editing failed - fallback to sending new message
                        except Exception:
                            # If editing error - fallback to sending new message
                            pass
                    
                    # Send new message (either because not editing, or not first chat, or fallback on error)
                    if attachment:
                        # Send with attachments
                        msg_id = await self.attachment_handler.send_attachments(
                            bot_token, bot_id, current_chat_id, escaped_text, attachment, reply_markup, parse_mode, reply_to_message_id
                        )
                        if msg_id:
                            success_count += 1
                            # Save message ID only for first chat
                            if is_first_chat:
                                last_message_id = msg_id
                        else:
                            # If attachments failed to send, but text exists - send text message as fallback
                            # (main fallback already handled in attachment_handler.py, here is additional protection)
                            if escaped_text:
                                msg_id, error_msg = await self._send_text_message(
                                    bot_token, bot_id, current_chat_id, escaped_text, 
                                    parse_mode, reply_markup, reply_to_message_id
                                )
                                if msg_id:
                                    success_count += 1
                                    # Save message ID only for first chat
                                    if is_first_chat:
                                        last_message_id = msg_id
                                else:
                                    errors.append(f"Failed to send attachments and text message to chat {current_chat_id}: {error_msg}")
                            else:
                                errors.append(f"Failed to send attachments to chat {current_chat_id}")
                    else:
                        # Send text message
                        msg_id, error_msg = await self._send_text_message(
                            bot_token, bot_id, current_chat_id, escaped_text, 
                            parse_mode, reply_markup, reply_to_message_id
                        )
                        if msg_id:
                            success_count += 1
                            # Save message ID only for first chat
                            if is_first_chat:
                                last_message_id = msg_id
                        else:
                            errors.append(f"Error sending to chat {current_chat_id}: {error_msg}")
                except Exception as e:
                    errors.append(f"Exception processing chat {current_chat_id}: {str(e)}")
                finally:
                    # After processing first chat (regardless of result), others get new message
                    if is_first_chat:
                        is_first_chat = False
            
            # Build result based on number of successful sends
            if success_count > 0:
                if errors:
                    self.logger.warning(f"Partially successful processing: {success_count}/{len(target_chat_ids)} successful. Errors: {errors}")
                # Return only last_message_id of first successfully processed message
                return {"result": "success", "response_data": {"last_message_id": last_message_id}}
            else:
                error_msg = "Failed to process any chat. " + "; ".join(errors) if errors else "Unknown error"
                return {
                    "result": "error",
                    "error": {
                        "code": "API_ERROR",
                        "message": error_msg
                    }
                }
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
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
        Sends text message
        """
        try:
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            # Add reply_markup only if it's not None
            if reply_markup is not None:
                payload['reply_markup'] = reply_markup
            
            # Add reply_to_message_id if needed
            if reply_to_message_id:
                payload['reply_to_message_id'] = reply_to_message_id
            
            result = await self.api_client.make_request_with_limit(bot_token, "sendMessage", payload, bot_id)
            if result.get('result') == 'success':
                msg_id = result.get('response_data', {}).get('message_id')
                return msg_id, None
            else:
                error_msg = result.get('error', 'Unknown error')
                return None, error_msg
        except Exception as e:
            return None, str(e)
    
    def _parse_message_id(self, value: str) -> Optional[int]:
        """Parse string to message ID (integer). Returns None if invalid."""
        value = (value or "").strip()
        if not value:
            return None
        try:
            n = int(value)
            return n if n >= 1 else None
        except (TypeError, ValueError):
            return None

    def _escape_text_for_parse_mode(self, text: str, parse_mode: str) -> str:
        """
        Converts Markdown to MarkdownV2 using telegramify-markdown library
        
        This solves all problems with escaping and syntax conversion.
        """
        if not text:
            return text
        
        if parse_mode == 'MarkdownV2':
            try:
                import telegramify_markdown
                # Convert regular markdown to MarkdownV2
                text = telegramify_markdown.markdownify(text)
            except Exception as e:
                self.logger.error(f"Error converting markdown: {e}")
        
        return text
    
    async def delete_message(self, bot_token: str, bot_id: int, data: dict) -> Dict[str, Any]:
        """Delete message"""
        try:
            # Extract parameters from flat dictionary
            chat_id = data.get('chat_id')
            
            # Priority: delete_message_id, then message_id
            message_id = data.get('delete_message_id') or data.get('message_id')
            
            if not chat_id or not message_id:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "chat_id or message_id not specified"
                    }
                }
            
            # Build payload from parameters
            payload = {
                'chat_id': chat_id,
                'message_id': message_id
            }

            result = await self.api_client.make_request_with_limit(bot_token, "deleteMessage", payload, bot_id)
            
            # Process result and return only needed fields
            if result.get('result') == 'success':
                # According to config.yaml, on success return only result without response_data
                return {"result": "success"}
            else:
                # Return only result and error, without response_data
                error_data = result.get('error', {})
                if isinstance(error_data, dict):
                    error_obj = error_data
                else:
                    error_obj = {
                        "code": "API_ERROR",
                        "message": str(error_data) if error_data else "Unknown error"
                    }
                return {
                    "result": result.get('result', 'error'),
                    "error": error_obj
                }
            
        except Exception as e:
            self.logger.error(f"Error deleting message: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
