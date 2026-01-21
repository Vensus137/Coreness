"""
BotPoller - individual polling for one bot
"""

import asyncio
from typing import Callable, Optional

import aiohttp


class BotPoller:
    """
    Simple polling for one bot without metrics and health check
    """
    
    def __init__(self, bot_id: int, token: str, settings: dict, logger, datetime_formatter):
        self.bot_id = bot_id
        self.token = token
        self.logger = logger
        self.datetime_formatter = datetime_formatter
        
        # Polling settings (standard for Telegram Bot API)
        self.polling_timeout = settings.get('polling_timeout', 20)
        self.polling_relax = settings.get('polling_relax', 0.1)
        self.polling_limit = settings.get('polling_limit', 100)
        self.polling_start_delay = settings.get('polling_start_delay', 0.5)
        self.allowed_updates = settings.get('allowed_updates', ['message', 'callback_query'])
        
        # Retry settings
        self.retry_delay = settings.get('retry_delay', 5)
        self.retry_after_rate_limit = settings.get('retry_after_rate_limit', 30)
        
        # HTTP client
        self.request_timeout = settings.get('request_timeout', 35)
        
        # Polling stop timeouts
        self.stop_polling_timeout = settings.get('stop_polling_timeout', 2.0)
        self.session_close_timeout = settings.get('session_close_timeout', 0.5)
        
        # State
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        self.offset = 0
        
        # Polling start time for event filtering
        self.polling_start_time = None
        
        # Callback for events
        self.event_callback: Optional[Callable] = None
        
        # Main polling loop task
        self._polling_task: Optional[asyncio.Task] = None
        
        # Critical errors counter
        self.consecutive_critical_errors = 0
        self.max_critical_errors = settings.get('max_critical_errors', 3)
        self.critical_error_codes = settings.get('critical_error_codes', [401, 403])
    
    async def reset_bot_settings(self):
        """
        CRITICALLY IMPORTANT: Reset bot settings and set allowed_updates for polling
        
        Telegram caches allowed_updates settings from previous webhooks.
        Without explicit setting via setWebhook with empty URL we may not receive
        needed events (e.g., pre_checkout_query) even if we pass them in getUpdates.
        
        This method should be called ONCE on first bot startup, not on every polling restart.
        """
        try:
            api_url = f"https://api.telegram.org/bot{self.token}"
            
            self.logger.info(f"[Bot-{self.bot_id}] 🔄 Setting allowed_updates for polling: {self.allowed_updates}")
            
            # Create temporary session for resetting settings
            async with aiohttp.ClientSession() as session:
                # 1. Delete webhook WITHOUT drop_pending_updates to preserve accumulated updates
                delete_url = f"{api_url}/deleteWebhook"
                async with session.post(delete_url, json={}) as response:
                    data = await response.json()
                    if not data.get('ok'):
                        self.logger.warning(f"[Bot-{self.bot_id}] Warning when deleting webhook: {data.get('description', 'Unknown error')}")
                
                # 2. Set allowed_updates via setWebhook with empty URL
                # This sets allowed_updates for getUpdates mode
                # CRITICALLY IMPORTANT: without this Telegram may ignore allowed_updates in getUpdates
                set_webhook_url = f"{api_url}/setWebhook"
                payload = {
                    "url": "",  # Empty URL disables webhook and activates getUpdates
                    "allowed_updates": self.allowed_updates
                }
                async with session.post(set_webhook_url, json=payload) as response:
                    data = await response.json()
                    if data.get('ok'):
                        self.logger.info(f"[Bot-{self.bot_id}] ✅ allowed_updates set: {self.allowed_updates}")
                    else:
                        error_msg = data.get('description', 'Unknown error')
                        self.logger.error(f"[Bot-{self.bot_id}] ❌ ERROR setting allowed_updates: {error_msg}")
                        # This is critical - without correct allowed_updates we may not receive events
                        raise Exception(f"Failed to set allowed_updates: {error_msg}")
                        
        except Exception as e:
            # This is critical - without correct settings we may not receive events
            self.logger.error(f"[Bot-{self.bot_id}] ❌ CRITICAL ERROR setting allowed_updates: {e}")
            # Continue work, but log as critical error
            raise
    
    async def start_polling(self, event_callback: Callable):
        """
        Start polling for this bot
        """
        try:
            # Save callback
            self.event_callback = event_callback
            
            # Set polling start time
            self.polling_start_time = await self.datetime_formatter.now_local()
            
            # Reset critical errors counter on startup
            self.consecutive_critical_errors = 0
            
            # Create HTTP session
            self.session = await self._create_session()
            
            # Mark as running immediately (race condition protection)
            self.is_running = True
            
            # Startup delay to prevent conflicts
            start_delay = self.polling_start_delay
            if start_delay > 0:
                await asyncio.sleep(start_delay)
            
            # Start main polling loop in separate task
            self._polling_task = asyncio.create_task(self._polling_loop())
            
            # Wait for task completion
            await self._polling_task
            
        except Exception as e:
            self.logger.error(f"[Bot-{self.bot_id}] Error starting polling: {e}")
            await self.stop_polling()
            raise
    
    def _handle_network_error(self, error: Exception, context: str):
        """Handle network errors with detailed logging"""
        error_str = str(error)
        if "APPLICATION_DATA_AFTER_CLOSE_NOTIFY" in error_str:
            # This is an error on restart - log as warning
            self.logger.warning(f"[Bot-{self.bot_id}] SSL connection closed at {context} (race condition)")
        elif "Errno 1" in error_str:
            # Errno 1 - operation not permitted, usually when closing connection
            self.logger.warning(f"[Bot-{self.bot_id}] Connection closed by system at {context} (race condition)")
        else:
            # Other network errors - log as warning
            self.logger.warning(f"[Bot-{self.bot_id}] Network error at {context}: {error}")
    
    def _handle_critical_error(self, error_code: int, description: str):
        """Handle critical errors with automatic polling shutdown"""
        self.consecutive_critical_errors += 1
        
        if self.consecutive_critical_errors >= self.max_critical_errors:
            self.logger.error(f"[Bot-{self.bot_id}] Critical HTTP error {error_code}: {description}, polling stopped after {self.consecutive_critical_errors} attempts")
            # Disable polling BEFORE raising exception
            self.is_running = False

    async def _create_session(self) -> aiohttp.ClientSession:
        """Create new HTTP session"""
        timeout = aiohttp.ClientTimeout(total=self.request_timeout)
        return aiohttp.ClientSession(timeout=timeout)
    
    async def _recreate_session(self):
        """Recreate session after network errors"""
        if self.session:
            try:
                if not self.session.closed:
                    await self._close_session_safely(self.session)
            except Exception as e:
                # Log only if unexpected error occurred when closing
                self.logger.warning(f"[Bot-{self.bot_id}] Error closing old session before recreation: {e}")
            finally:
                self.session = None
        
        # Create new session (always create new, even if old didn't close)
        try:
            self.session = await self._create_session()
        except Exception as e:
            # Failed to create new session - this is critical
            self.logger.error(f"[Bot-{self.bot_id}] Critical error: failed to create new session: {e}")
            raise

    async def _close_session_safely(self, session, timeout=None):
        """Safely close session with error handling"""
        if timeout is None:
            timeout = self.session_close_timeout
        
        # Check if session is already closed
        if session.closed:
            return
            
        # Try to close session
        try:
            await asyncio.wait_for(session.close(), timeout=timeout)
            return  # Successfully closed
        except asyncio.TimeoutError:
            # Session didn't close in time, try to close connector
            pass
        except Exception:
            # Error when closing, try to close connector
            pass
        
        # If session didn't close, try to close connector forcibly
        if hasattr(session, '_connector') and session._connector:
            try:
                if not session._connector._closed:
                    session._connector.close()
                    return  # Connector closed, problem solved
            except Exception:
                pass  # Connector also didn't close, problem not solved
        
        # Failed to close both session and connector - log
        self.logger.warning(f"[Bot-{self.bot_id}] Failed to close session and connector")

    def stop_polling_sync(self):
        """Synchronous polling stop (for shutdown)"""
        try:
            self.is_running = False
            
            if self.session and not self.session.closed:
                try:
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(self._close_session_safely(self.session))
                    loop.run_until_complete(task)
                except RuntimeError:
                    # If no event loop - create new one
                    asyncio.run(self._close_session_safely(self.session))
                
                self.session = None
            
            self.logger.info(f"[Bot-{self.bot_id}] Polling stopped")
            
        except Exception as e:
            self.logger.error(f"[Bot-{self.bot_id}] Error in synchronous polling stop: {e}")

    async def stop_polling(self):
        """Stop polling"""
        try:
            self.is_running = False
            
            # Close session BEFORE waiting for task completion to avoid creating new sessions
            if self.session:
                await self._close_session_safely(self.session)
                self.session = None
            
            # Wait for main polling loop completion
            if hasattr(self, '_polling_task') and self._polling_task and not self._polling_task.done():
                try:
                    await asyncio.wait_for(self._polling_task, timeout=self.stop_polling_timeout)
                except asyncio.TimeoutError:
                    self.logger.warning(f"[Bot-{self.bot_id}] Polling didn't stop within {self.stop_polling_timeout} seconds, forcing termination")
                    # Force cancel task
                    self._polling_task.cancel()
                    try:
                        await self._polling_task
                    except asyncio.CancelledError:
                        pass
                except Exception as e:
                    self.logger.warning(f"[Bot-{self.bot_id}] Error waiting for polling completion: {e}")
            
            # CRITICAL: After task completion check and close session again
            # This is needed because _polling_loop may create new session via _recreate_session()
            if self.session and not self.session.closed:
                try:
                    await self._close_session_safely(self.session)
                except Exception as e:
                    self.logger.warning(f"[Bot-{self.bot_id}] Error in final session close: {e}")
                finally:
                    self.session = None
            
            self.logger.info(f"[Bot-{self.bot_id}] Polling stopped")
            
        except Exception as e:
            self.logger.error(f"[Bot-{self.bot_id}] Error stopping polling: {e}")
    
    async def _polling_loop(self):
        """Main polling loop"""
        while self.is_running:
            try:
                # Get updates
                updates = await self._get_updates()
                
                # Process each update
                for update in updates:
                    self.offset = update['update_id'] + 1
                    
                    # Add system data with polling start time
                    if 'system' not in update:
                        update['system'] = {}
                    
                    update['system'].update({
                        'bot_id': self.bot_id,
                        'polling_start_time': self.polling_start_time
                    })
                    
                    # Pass event to callback
                    if self.event_callback:
                        try:
                            if asyncio.iscoroutinefunction(self.event_callback):
                                await self.event_callback(update)
                            else:
                                self.event_callback(update)
                        except Exception as e:
                            self.logger.error(f"[Bot-{self.bot_id}] Error processing event: {e}")
                            # Continue processing other events
                
                # Delay between requests (standard for Telegram Bot API)
                if self.is_running:
                    try:
                        await asyncio.sleep(self.polling_relax)
                    except asyncio.CancelledError:
                        self.logger.info(f"[Bot-{self.bot_id}] Cancellation signal received during delay")
                        break
                
            except asyncio.CancelledError:
                self.logger.info(f"[Bot-{self.bot_id}] Cancellation signal received, finishing polling")
                break
                
            except aiohttp.ClientError as e:
                # Handle network errors
                self._handle_network_error(e, "getting updates")
                
                # Recreate session after network error
                try:
                    await self._recreate_session()
                except Exception as recreate_error:
                    self.logger.warning(f"[Bot-{self.bot_id}] Error recreating session: {recreate_error}")
                    # Continue work, session may still be working
                
                # Wait before retry
                if self.is_running:
                    await asyncio.sleep(self.retry_delay)
                
            except Exception as e:
                # Don't log critical errors here - they are logged in _handle_critical_error when limit is reached
                error_msg = str(e)
                if not error_msg.startswith("Critical error"):
                    # Check that error is not empty and contains information
                    if error_msg:
                        self.logger.error(f"[Bot-{self.bot_id}] Unexpected error in polling: {error_msg}")
                    else:
                        # If error is empty, output exception type
                        exception_type = type(e).__name__
                        self.logger.error(f"[Bot-{self.bot_id}] Unexpected error in polling ({exception_type}): {repr(e)}")
                
                # If polling disabled due to critical errors, don't wait
                if not self.is_running:
                    break
                # Wait before retry only if polling is still active
                if self.is_running:
                    await asyncio.sleep(self.retry_delay)
    
    async def _get_updates(self):
        """Get updates via Telegram API with filtering"""
        try:
            # Check session state before use
            if not self.session or self.session.closed:
                self.session = await self._create_session()
            
            url = f"https://api.telegram.org/bot{self.token}/getUpdates"
            # IMPORTANT: Explicitly specify allowed_updates with pre_checkout_query to receive payment events
            # According to Telegram docs, if allowed_updates not specified, some event types may not arrive
            params = {
                'offset': self.offset,
                'timeout': self.polling_timeout,
                'limit': self.polling_limit,
                'allowed_updates': ['message', 'callback_query', 'pre_checkout_query']  # Explicitly specify event types
            }
            
            async with self.session.get(url, params=params) as response:
                try:
                    data = await response.json()
                except Exception:
                    # If JSON doesn't parse but HTTP status is critical - handle as critical error
                    if response.status in self.critical_error_codes:
                        status_code = response.status
                        description = f'HTTP {status_code} - {response.reason}'
                        self._handle_critical_error(status_code, description)
                        raise Exception(f"Critical error {status_code}: {description}") from None
                    raise
                
                if data.get('ok'):
                    updates = data.get('result', [])
                    # Reset error counter on successful request
                    self.consecutive_critical_errors = 0
                    return updates
                else:
                    # Handle specific Telegram API errors
                    error_code = data.get('error_code')
                    description = data.get('description', 'Unknown error')
                    
                    # Check criticality by error_code (main case for Telegram API)
                    if error_code in self.critical_error_codes:
                        self._handle_critical_error(error_code, description)
                        raise Exception(f"Critical error {error_code}: {description}")
                    elif error_code == 429:
                        self.logger.warning(f"[Bot-{self.bot_id}] Rate limit: {description}")
                        
                        # Get retry_after from response (if exists)
                        retry_after = data.get('retry_after', self.retry_after_rate_limit)
                        self.logger.info(f"[Bot-{self.bot_id}] Waiting {retry_after} seconds before retry")
                        
                        # Wait specified time
                        await asyncio.sleep(retry_after)
                        raise Exception(f"Rate limited: {description}")
                    elif error_code == 409:
                        self.logger.warning(f"[Bot-{self.bot_id}] Webhook conflict: {description}")
                        raise Exception(f"Webhook conflict: {description}")
                    else:
                        self.logger.error(f"[Bot-{self.bot_id}] API error: {error_code} - {description}")
                        raise Exception(f"API Error {error_code}: {description}")
                    
        except aiohttp.ClientError as e:
            # Handle network errors
            self._handle_network_error(e, "getting updates")
            raise
            