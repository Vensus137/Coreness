"""
Event Processor - service for processing events from polling
Wrapper over core modules for ActionHub integration
"""

from typing import Any, Dict

from .core.event_handler import EventHandler


class EventProcessor:
    """
    Service for processing events from polling
    Wrapper over core modules for ActionHub integration
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.action_hub = kwargs['action_hub']
        
        # Create event handler
        self.event_handler = EventHandler(
            logger=self.logger,
            action_hub=self.action_hub,
            datetime_formatter=kwargs['datetime_formatter'],
            settings_manager=self.settings_manager,
            database_manager=kwargs['database_manager'],
            user_manager=kwargs['user_manager'],
            data_converter=kwargs['data_converter'],
            cache_manager=kwargs['cache_manager']
        )
        
        # Register ourselves in ActionHub
        self.action_hub.register('event_processor', self)
    
    def shutdown(self):
        """Synchronous graceful service shutdown"""
        self.logger.info("Stopping service...")
        # Clean up resources through event_handler
        import asyncio
        try:
            # Try to clean up resources in existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop running, create task for cleanup
                loop.create_task(self.event_handler.cleanup())
            else:
                # If loop not running, run it for cleanup
                loop.run_until_complete(self.event_handler.cleanup())
        except RuntimeError:
            # If no event loop, create new one
            asyncio.run(self.event_handler.cleanup())
        except Exception as e:
            self.logger.warning(f"Error cleaning up resources: {e}")
        
        self.logger.info("Service stopped")
    
    # === Actions for ActionHub ===
    
    async def process_event(self, data: dict) -> Dict[str, Any]:
        """
        Process event from polling
        """
        try:
            # Validation is done centrally in ActionRegistry
            # Process event through event_handler
            await self.event_handler.handle_raw_event(data)
            
            return {"result": "success"}
                
        except Exception as e:
            self.logger.error(f"Error processing event: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Internal error: {str(e)}"
                }
            }
