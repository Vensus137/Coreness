"""
Submodule for handling attachments
"""

from typing import Dict, List, Optional

# Maximum number of files in media group
MAX_MEDIA_GROUP = 10


class AttachmentHandler:
    """
    Submodule for handling Telegram attachments
    """
    
    def __init__(self, api_client, **kwargs):
        self.logger = kwargs['logger']
        self.api_client = api_client
    
    def _create_media_item(self, media_type: str, file_id: str, caption: str = None, parse_mode: str = 'HTML') -> dict:
        """Creates correct media object for sendMediaGroup"""
        media_item = {"type": media_type, "media": file_id}
        if caption:
            media_item["caption"] = caption
            media_item["parse_mode"] = parse_mode
        return media_item
    
    def _group_attachments(self, attachments: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
        """
        Groups attachments: media (photo+video), animation (animations only), document (documents only).
        Animations, audio, voice messages, stickers and video notes are sent separately.
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
        """Sends attachments with correct grouping"""
        
        if not attachments:
            return None
        
        # Group attachments
        groups = self._group_attachments(attachments)
        text_sent = False
        any_sent = False
        first_group = True
        last_message_id = None
        
        for group_type in ("media", "animation", "document", "audio", "voice", "sticker", "video_note"):
            files = groups.get(group_type, [])
            if not files:
                continue
            
            # Single attachment (only for types that can be in groups)
            if len(files) == 1 and group_type in ('media', 'document'):
                att = files[0]
                file_id = att['file_id']
                
                try:
                    caption = text if not text_sent else None
                    
                    # Prepare parameters for sending
                    payload = {
                        'chat_id': chat_id,
                        'reply_markup': reply_markup,
                        'parse_mode': parse_mode
                    }
                    
                    # Add reply_to_message_id if needed
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
                            self.logger.warning(f"Reply to message failed for chat_id={chat_id}, message_id={reply_to_message_id}: {e}. Sending attachment without reply_to_message_id.")
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
                        # If sending failed, log warning (fallback to text will be later)
                        if result:
                            self.logger.warning(f"[Bot-{bot_id}] Failed to send attachment {file_id}: {result.get('error', 'Unknown error')}")
                        else:
                            self.logger.warning(f"[Bot-{bot_id}] Failed to send attachment {file_id}: result is empty")
                except Exception as e:
                    self.logger.warning(f"Error sending attachment {file_id}: {e}")
                continue  # don't process as group
            
            # Animations, audio, voice messages, stickers and video notes are always sent separately
            if group_type in ('animation', 'audio', 'voice', 'sticker', 'video_note'):
                for att in files:
                    try:
                        file_id = att['file_id']
                        caption = text if not text_sent else None
                        
                        # Prepare parameters for sending
                        payload = {
                            'chat_id': chat_id,
                            'reply_markup': reply_markup,
                            'parse_mode': parse_mode
                        }
                        
                        # Add reply_to_message_id if needed
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
                                self.logger.warning(f"Reply to message failed for chat_id={chat_id}, message_id={reply_to_message_id}: {e}. Sending attachment without reply_to_message_id.")
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
                            self.logger.warning(f"[Bot-{bot_id}] Failed to send attachment {file_id}: {result.get('error', 'Unknown error') if result else 'Result is empty'}")
                    except Exception as e:
                        self.logger.warning(f"Error sending attachment {file_id}: {e}")
                continue  # don't process as group

            # Multiple attachments (media groups)
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
                        self.logger.warning(f"Error preparing media {file_id}: {e}")
                if media:
                    try:
                        # Prepare parameters for sending media group
                        payload = {'chat_id': chat_id, 'media': media}
                        
                        # Add reply_to_message_id if needed
                        if reply_to_message_id:
                            payload['reply_to_message_id'] = reply_to_message_id
                        
                        try:
                            result = await self.api_client.make_request_with_limit(bot_token, "sendMediaGroup", payload, bot_id)
                        except Exception as e:
                            if 'message to reply not found' in str(e).lower() and reply_to_message_id:
                                self.logger.warning(f"Reply to message failed for chat_id={chat_id}, message_id={reply_to_message_id}: {e}. Sending media group without reply_to_message_id.")
                                payload.pop('reply_to_message_id', None)
                                result = await self.api_client.make_request_with_limit(bot_token, "sendMediaGroup", payload, bot_id)
                            else:
                                raise
                        if result and result.get('result') == 'success':
                            text_sent = True
                            any_sent = True
                            first_group = False
                            
                            # For media groups use last file as approximation for last_message_id
                            # Telegram API doesn't return array of messages, so this is the best approximation
                            if media:
                                last_message_id = None  # Media groups don't give exact message_id
                        else:
                            self.logger.warning(f"[Bot-{bot_id}] Failed to send media group: {result.get('error', 'Unknown error') if result else 'Result is empty'}")
                    except Exception as e:
                        self.logger.warning(f"Error sending media group: {e}")
        
        # If no attachment was sent, but text exists — send text message
        if not any_sent and text:
            self.logger.warning(f"[Bot-{bot_id}] Failed to send attachments to chat {chat_id}, sending text message")
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
                # If text also failed to send - this is an error
                self.logger.error(f"[Bot-{bot_id}] Failed to send attachments and text message to chat {chat_id}: {result.get('error', 'Unknown error') if result else 'Result is empty'}")
                return None
        elif not any_sent and not text:
            # No attachments and no text - this is an error
            self.logger.error(f"[Bot-{bot_id}] No attachments or text sent to chat {chat_id}")
            return None
        
        return last_message_id
