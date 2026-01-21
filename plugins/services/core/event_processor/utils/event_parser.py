"""
Utility for parsing raw Telegram events into standard format
"""

from typing import Any, Dict, List, Optional


class EventParser:
    """
    Parser for raw Telegram events into standard event format.
    """

    def __init__(self, logger, datetime_formatter, data_converter, database_manager, user_manager, cache_manager):
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        self.data_converter = data_converter
        self.database_manager = database_manager
        self.user_manager = user_manager
        self.cache_manager = cache_manager
        
        # Local cache for tenant_id by bot_id (permanent)
        self._bot_tenant_cache: Dict[int, int] = {}

    async def parse_event(self, telegram_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse Telegram event into standard event format
        """
        try:
            # Get bot_id from system field
            bot_id = telegram_event.get('system', {}).get('bot_id')
            if not bot_id:
                self.logger.warning("bot_id missing in event system field")
                return None
            
            # Get tenant_id by bot_id (with caching)
            tenant_id = await self._get_tenant_by_bot_id(bot_id)
            if not tenant_id:
                self.logger.warning(f"tenant_id not found for bot_id {bot_id}")
                return None
            
            # Determine event type
            if 'message' in telegram_event:
                message = telegram_event['message']
                # Check if this is a member join/leave event
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
                # Ignore unknown event types
                return None
            
            if event:
                # Add bot_id and tenant_id to event system field (for protection)
                event['system'] = {
                    'bot_id': bot_id,
                    'tenant_id': tenant_id
                }
                
                # Add bot_id and tenant_id to flat dictionary (for use in actions)
                event['bot_id'] = bot_id
                event['tenant_id'] = tenant_id
                
                # Add tenant config to event
                tenant_config = await self._get_tenant_config(tenant_id)
                if tenant_config:
                    # Put entire config in _config (actions will extract needed attributes from there)
                    event['_config'] = tenant_config
                
                # Automatically save user data
                await self._save_user_data(event)
            
            return event
                
        except Exception as e:
            self.logger.error(f"Error parsing update: {e}")
            return None

    async def _parse_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse message into standard event format"""
        try:
            # Basic information
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

            # User information
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

            # Chat information
            if message.get('chat'):
                chat = message['chat']
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })

            # Flags
            event.update({
                'is_reply': bool(message.get('reply_to_message')),
                'is_forward': bool(message.get('forward_from') or message.get('forward_from_chat'))
            })

            # Process reply messages
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

            # Process forward messages
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

            # Process inline keyboard
            inline_keyboard = self._extract_inline_keyboard(message)
            if inline_keyboard:
                event['inline_keyboard'] = inline_keyboard

            # Convert to safe dictionary
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Error parsing message: {e}")
            return None

    async def _parse_callback_query(self, callback: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse callback_query into standard event format"""
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

            # User information
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

            # Chat information
            if callback.get('message') and callback['message'].get('chat'):
                chat = callback['message']['chat']
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })

            # Process inline keyboard from callback message
            if callback.get('message'):
                inline_keyboard = self._extract_inline_keyboard(callback['message'])
                if inline_keyboard:
                    event['inline_keyboard'] = inline_keyboard

            # Convert to safe dictionary
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Error parsing callback: {e}")
            return None

    async def _parse_member_joined_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse member joined event from message with new_chat_member"""
        try:
            new_member = message.get('new_chat_member')
            if not new_member:
                self.logger.warning("new_chat_member not found in join message")
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
            
            # User information
            event.update({
                'username': new_member.get('username'),
                'first_name': new_member.get('first_name'),
                'last_name': new_member.get('last_name'),
                'language_code': new_member.get('language_code'),
                'is_bot': new_member.get('is_bot', False),
                'is_premium': new_member.get('is_premium', False)
            })
            
            # Chat information
            if chat:
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })
            
            # Convert to safe dictionary
            return await self.data_converter.to_safe_dict(event)
            
        except Exception as e:
            self.logger.error(f"Error parsing member_joined from message: {e}")
            return None

    async def _parse_member_left_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse member left event from message with left_chat_member"""
        try:
            left_member = message.get('left_chat_member')
            if not left_member:
                self.logger.warning("left_chat_member not found in leave message")
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
            
            # User information
            event.update({
                'username': left_member.get('username'),
                'first_name': left_member.get('first_name'),
                'last_name': left_member.get('last_name'),
                'language_code': left_member.get('language_code'),
                'is_bot': left_member.get('is_bot', False),
                'is_premium': left_member.get('is_premium', False)
            })
            
            # Chat information
            if chat:
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })
            
            # Convert to safe dictionary
            return await self.data_converter.to_safe_dict(event)
            
        except Exception as e:
            self.logger.error(f"Error parsing member_left from message: {e}")
            return None

    async def _parse_pre_checkout_query(self, pre_checkout_query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse pre_checkout_query into standard event format"""
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

            # User information
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

            # Convert to safe dictionary
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Error parsing pre_checkout_query: {e}")
            return None

    async def _parse_successful_payment_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Parse successful_payment from message into standard event format"""
        try:
            successful_payment = message.get('successful_payment')
            if not successful_payment:
                self.logger.warning("successful_payment not found in message")
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

            # User information
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

            # Chat information
            if chat:
                event.update({
                    'chat_title': chat.get('title'),
                    'chat_username': chat.get('username')
                })

            # Convert to safe dictionary
            return await self.data_converter.to_safe_dict(event)

        except Exception as e:
            self.logger.error(f"Error parsing successful_payment from message: {e}")
            return None

    def _extract_inline_keyboard(self, message: Dict[str, Any]) -> Optional[List[List[Dict[str, str]]]]:
        """
        Extract inline keyboard from message and convert to our format.
        
        Telegram format: [[{text, callback_data}, ...], ...]
        Our format: [[{"Text": "callback_data"}, ...], ...]
        
        Returns array of arrays, where each inner array is a row of buttons.
        Each button is represented as a dictionary in format {"Button text": "callback_data"}.
        """
        try:
            reply_markup = message.get('reply_markup', {})
            if not reply_markup:
                return None
            
            inline_keyboard = reply_markup.get('inline_keyboard')
            if not inline_keyboard or not isinstance(inline_keyboard, list):
                return None
            
            # Convert to our format: {"Text": "callback_data"}
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
                    
                    # Priority: callback_data > url > empty string
                    button_value = button.get('callback_data')
                    if not button_value:
                        button_value = button.get('url', '')
                    
                    # Convert to project format: {"Text": "value"}
                    if button_value:
                        button_data = {button_text: button_value}
                        parsed_row.append(button_data)
                
                # Add row only if it has buttons
                if parsed_row:
                    parsed_keyboard.append(parsed_row)
            
            return parsed_keyboard if parsed_keyboard else None
            
        except Exception as e:
            self.logger.warning(f"Error extracting inline keyboard: {e}")
            return None

    def _extract_attachments(self, message: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachments from message"""
        attachments = []

        # Photo
        if message.get('photo'):
            largest_photo = message['photo'][-1]  # Take the largest one
            attachments.append({
                'type': 'photo',
                'file_id': largest_photo.get('file_id')
            })

        # Document
        if message.get('document'):
            attachments.append({
                'type': 'document',
                'file_id': message['document'].get('file_id')
            })

        # Video
        if message.get('video'):
            attachments.append({
                'type': 'video',
                'file_id': message['video'].get('file_id')
            })

        # Audio
        if message.get('audio'):
            attachments.append({
                'type': 'audio',
                'file_id': message['audio'].get('file_id')
            })

        # Voice message
        if message.get('voice'):
            attachments.append({
                'type': 'voice',
                'file_id': message['voice'].get('file_id')
            })

        # Sticker
        if message.get('sticker'):
            attachments.append({
                'type': 'sticker',
                'file_id': message['sticker'].get('file_id')
            })

        # Animation
        if message.get('animation'):
            attachments.append({
                'type': 'animation',
                'file_id': message['animation'].get('file_id')
            })

        # Video note
        if message.get('video_note'):
            attachments.append({
                'type': 'video_note',
                'file_id': message['video_note'].get('file_id')
            })

        return attachments
    
    async def _get_tenant_by_bot_id(self, bot_id: int) -> Optional[int]:
        """
        Get tenant_id by bot_id from database with caching
        """
        try:
            # Check cache
            if bot_id in self._bot_tenant_cache:
                return self._bot_tenant_cache[bot_id]
            
            # Get from database
            master_repo = self.database_manager.get_master_repository()
            bot_data = await master_repo.get_bot_by_id(bot_id)
            
            if bot_data and 'tenant_id' in bot_data:
                tenant_id = bot_data['tenant_id']
                # Save to cache
                self._bot_tenant_cache[bot_id] = tenant_id
                return tenant_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting tenant_id by bot_id {bot_id}: {e}")
            return None
    
    async def _save_user_data(self, event: Dict[str, Any]) -> None:
        """
        Automatically save user data when parsing event
        """
        try:
            user_id = event.get('user_id')
            tenant_id = event.get('tenant_id')
            
            if not user_id or not tenant_id:
                # No user data to save
                return
            
            # Prepare user data
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
            
            # Save user data (with caching)
            await self.user_manager.save_user_data(user_data)
            
            # Get state with expiration check
            state_data = await self.user_manager.get_user_state(user_id, tenant_id)
            if state_data:
                event['user_state'] = state_data.get('user_state')
                event['user_state_expired_at'] = state_data.get('user_state_expired_at')
            
        except Exception as e:
            self.logger.error(f"Error automatically saving user data: {e}")
    
    def _get_tenant_config_key(self, tenant_id: int) -> str:
        """Generate cache key for tenant config (matches TenantCache)"""
        return f"tenant:{tenant_id}:config"
    
    async def _get_tenant_config(self, tenant_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tenant config from shared cache (cache_manager) with DB fallback
        Uses the same key as TenantCache, so always synchronized
        Returns dictionary with config (e.g., {"ai_token": "..."})
        
        Logic: first check cache, if not found - load from DB and save to cache.
        This solves the desynchronization problem when updating config.
        """
        try:
            # Step 1: Check cache
            cache_key = self._get_tenant_config_key(tenant_id)
            cached_config = await self.cache_manager.get(cache_key)
            
            if cached_config is not None:
                return cached_config
            
            # Step 2: Cache not found - load from DB (fallback to solve desynchronization problem)
            self.logger.warning(f"[Tenant-{tenant_id}] Tenant config not found in cache, loading from DB")
            
            master_repo = self.database_manager.get_master_repository()
            tenant_data = await master_repo.get_tenant_by_id(tenant_id)
            
            if not tenant_data:
                return None
            
            # Form config dictionary from all DB fields (exclude system fields)
            # System fields: id, processed_at (and relationship fields, but they don't get into dictionary)
            config = {}
            excluded_fields = {'id', 'processed_at'}
            for key, value in tenant_data.items():
                if key not in excluded_fields and value is not None:
                    config[key] = value
            
            # Don't save to cache - TenantCache manages it
            # This is a rare case when cache is missing, so just return data from DB
            return config
            
        except Exception as e:
            self.logger.error(f"[Tenant-{tenant_id}] Error getting tenant config: {e}")
            return None
