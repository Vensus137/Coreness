"""
Telegram Polling Utility - utility for polling multiple Telegram bots
"""

import asyncio
from typing import Any, Callable, Dict, List

from .core.bot_poller import BotPoller
from .core.polling_manager import PollingManager


class TelegramPollingUtility:
    """
    Utility for polling multiple Telegram bots
    Direct HTTP API for working with Telegram Bot API
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        self.datetime_formatter = kwargs['datetime_formatter']
        
        # Get settings
        self.settings = self.settings_manager.get_plugin_settings('telegram_polling')
        
        # Create polling manager
        self.polling_manager = PollingManager(
            self.settings, 
            self.logger, 
            BotPoller, 
            self.datetime_formatter
        )
    
    def shutdown(self):
        """Synchronous graceful shutdown of utility"""
        self.polling_manager.shutdown()

    def _create_event_callback(self, bot_id: int, event_callback: Callable):
        """Creates internal callback for processing events with bound bot_id"""
        async def internal_event_callback(raw_event):
            try:
                # Add system fields (for protection)
                if 'system' not in raw_event:
                    raw_event['system'] = {}
                raw_event['system']['bot_id'] = bot_id
                
                # Add fields to flat dictionary (for use in actions)
                raw_event['bot_id'] = bot_id
                
                # Call passed callback
                if asyncio.iscoroutinefunction(event_callback):
                    await event_callback(raw_event)
                else:
                    event_callback(raw_event)
                
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
        
        return internal_event_callback

    # === Public methods for use in services ===
    
    async def start_bot_polling(self, bot_id: int, token: str) -> bool:
        """Start polling for specific bot (automatically stops existing)"""
        try:
            # Create callback for sending events to event_processor via ActionHub
            async def bot_event_callback(raw_event):
                try:
                    # Send event to event_processor via ActionHub (fire_and_forget for parallelism)
                    await self.action_hub.execute_action('process_event', raw_event, fire_and_forget=True)
                except Exception as e:
                    self.logger.error(f"Error sending event to event_processor: {e}")
            
            # Create internal callback for processing events with bound bot_id
            internal_callback = self._create_event_callback(bot_id, bot_event_callback)
            
            # Use PollingManager to start (it will automatically stop existing)
            return await self.polling_manager.start_bot_polling(bot_id, token, internal_callback)
            
        except Exception as e:
            self.logger.error(f"Error starting polling: {e}")
            return False
    
    async def stop_bot_polling(self, bot_id: int) -> bool:
        """Stop polling for specific bot"""
        try:
            return await self.polling_manager.stop_bot_polling(bot_id)
        except Exception as e:
            self.logger.error(f"Error stopping polling: {e}")
            return False
    
    def is_bot_polling(self, bot_id: int) -> bool:
        """Check polling activity for specific bot"""
        try:
            if bot_id not in self.polling_manager.active_pollers:
                return False
            
            poller = self.polling_manager.active_pollers[bot_id]
            return poller.is_running
            
        except Exception as e:
            self.logger.error(f"Error checking polling activity: {e}")
            return False
    
    async def stop_all_polling(self) -> bool:
        """Stop polling for all bots"""
        try:
            return await self.polling_manager.stop_all_polling()
        except Exception as e:
            self.logger.error(f"Error stopping polling for all bots: {e}")
            return False
    
    async def start_all_polling(self, bots_list: List[Dict[str, Any]]) -> int:
        """Start polling for list of bots"""
        try:
            started_count = 0
            
            for bot_info in bots_list:
                bot_id = bot_info.get('bot_id')
                bot_token = bot_info.get('bot_token')
                is_active = bot_info.get('is_active', False)
                
                if bot_id and bot_token and is_active:
                    success = await self.start_bot_polling(bot_id, bot_token)
                    if success:
                        started_count += 1
                        self.logger.info(f"[Bot-{bot_id}] Bot startup successful")
                    else:
                        self.logger.warning(f"[Bot-{bot_id}] Failed to start bot")
            
            self.logger.info(f"Startup of all bots completed. Started {started_count} bots")
            return started_count
            
        except Exception as e:
            self.logger.error(f"Error starting all bots: {e}")
            return 0
    
    
