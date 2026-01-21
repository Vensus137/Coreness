"""
PollingManager - management of polling for multiple bots
"""

import asyncio
from typing import Any, Callable, Dict, Type


class PollingManager:
    """
    Simple management of polling for multiple bots without monitoring
    """
    
    def __init__(self, settings: dict, logger, bot_poller_class: Type, datetime_formatter):
        self.settings = settings
        self.logger = logger
        self.bot_poller_class = bot_poller_class
        self.datetime_formatter = datetime_formatter
        
        # Active pollers
        self.active_pollers: Dict[int, Any] = {}  # bot_id -> poller
        
        # Track bots for which settings reset was already performed
        # This is a global bot setting on Telegram server, don't need to do on every polling restart
        self._bots_settings_reset: set[int] = set()
    
    async def start_bot_polling(self, bot_id: int, token: str, event_callback: Callable) -> bool:
        """Start polling for specific bot"""
        try:
            # Stop existing polling if any
            if bot_id in self.active_pollers:
                await self.stop_bot_polling(bot_id)
            
            # Reset bot settings only on first startup (global setting on Telegram server)
            # This should be done once on application startup, not on every polling restart
            if bot_id not in self._bots_settings_reset:
                # Create temporary poller only for resetting settings
                temp_poller = self.bot_poller_class(bot_id, token, self.settings, self.logger, self.datetime_formatter)
                try:
                    await temp_poller.reset_bot_settings()
                    self._bots_settings_reset.add(bot_id)
                    self.logger.info(f"[Bot-{bot_id}] Bot settings set (once on startup)")
                except Exception as e:
                    # If failed to set settings - log, but continue work
                    # Settings may already be set or there's a temporary problem
                    self.logger.warning(f"[Bot-{bot_id}] Failed to set bot settings (continuing work): {e}")
            
            # Create new poller and immediately add to active_pollers
            poller = self.bot_poller_class(bot_id, token, self.settings, self.logger, self.datetime_formatter)
            self.active_pollers[bot_id] = poller
            
            # Start polling in background task (non-blocking)
            # Polling will be in infinite loop, if token is valid - works, if not - stops itself
            self.logger.info(f"[Bot-{bot_id}] Polling started in background")
            asyncio.create_task(poller.start_polling(event_callback))
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting polling: {e}")
            return False

    async def stop_bot_polling(self, bot_id: int) -> bool:
        """Stop polling for specific bot"""
        try:
            if bot_id not in self.active_pollers:
                return True
            
            poller = self.active_pollers[bot_id]
            
            # Stop polling with timeout
            stop_timeout = self.settings.get('stop_polling_manager_timeout', 3.0)
            try:
                await asyncio.wait_for(poller.stop_polling(), timeout=stop_timeout)
            except asyncio.TimeoutError:
                self.logger.warning(f"[Bot-{bot_id}] Polling didn't stop within {stop_timeout} seconds, forcing removal")
            
            # Remove from active_pollers ONLY after stopping
            del self.active_pollers[bot_id]
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping polling: {e}")
            return False
    
    async def stop_all_polling(self) -> bool:
        """Stop polling for all bots"""
        try:
            self.logger.info("Stopping polling for all bots")
            
            # Stop all pollers
            tasks = []
            for bot_id in list(self.active_pollers.keys()):
                tasks.append(self.stop_bot_polling(bot_id))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            self.logger.info("Polling for all bots stopped")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping polling for all bots: {e}")
            return False
    
    def shutdown(self):
        """Synchronous graceful shutdown of polling manager"""
        # Stop all pollers synchronously
        for bot_id in list(self.active_pollers.keys()):
            try:
                if bot_id in self.active_pollers:
                    poller = self.active_pollers[bot_id]
                    # Use synchronous method to stop poller
                    poller.stop_polling_sync()
                    del self.active_pollers[bot_id]
            except Exception as e:
                self.logger.error(f"Error stopping polling: {e}")
    
    