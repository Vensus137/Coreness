"""
Core module for processing events from Telegram polling
Contains main logic for processing and forwarding events
"""

from typing import Any, Dict


class EventHandler:
    """
    Main event handler for Telegram polling
    - Parsing raw events into standard format
    - Processing media groups (merging events)
    - Forwarding processed events
    """
    
    def __init__(self, logger, action_hub, datetime_formatter, settings_manager, database_manager, user_manager, data_converter, cache_manager):
        self.logger = logger
        self.action_hub = action_hub
        self.datetime_formatter = datetime_formatter
        self.settings_manager = settings_manager
        
        # Get time filtering settings
        settings = self.settings_manager.get_plugin_settings('event_processor')
        self.enable_time_comparison = settings.get('enable_time_comparison', False)
        self.startup_time_offset = settings.get('startup_time_offset', 0)
        
        # Initialize utilities
        from ..utils.event_parser import EventParser
        from ..utils.media_group_processor import MediaGroupProcessor
        
        self.event_parser = EventParser(
            logger=self.logger,
            datetime_formatter=self.datetime_formatter,
            data_converter=data_converter,
            database_manager=database_manager,
            user_manager=user_manager,
            cache_manager=cache_manager
        )
        self.media_group_processor = MediaGroupProcessor(
            logger=self.logger,
            settings_manager=self.settings_manager
        )
    
    async def handle_raw_event(self, raw_event: Dict[str, Any]) -> None:
        """
        Process raw event from polling
        Called from telegram_polling_service via event_callback
        """
        try:
            # Parse event into standard format
            parsed_event = await self.event_parser.parse_event(raw_event)
            
            if not parsed_event:
                # Event was not recognized or parsing error occurred
                return
            
            # Filter by time relative to polling start
            if await self._should_ignore_event_by_time(parsed_event, raw_event):
                return
            
            # Process media groups (if any)
            await self.media_group_processor.process_event(
                parsed_event, 
                self._forward_processed_event
            )
                    
        except Exception as e:
            self.logger.error(f"Error processing raw event: {e}")
    
    async def _forward_processed_event(self, processed_event: Dict[str, Any]) -> None:
        """
        Forward processed event to scenario_processor via ActionHub
        """
        try:
            # Send event to scenario_processor for scenario processing
            await self.action_hub.execute_action(
                'process_scenario_event',
                processed_event
            )
                
        except Exception as e:
            self.logger.error(f"Error forwarding processed event to scenario_processor: {e}")
    
    async def _should_ignore_event_by_time(self, parsed_event: dict, raw_event: dict) -> bool:
        """
        Determine whether to ignore event by time
        """
        # If time comparison disabled, don't ignore events
        if not self.enable_time_comparison:
            return False
        
        try:
            # Get polling start time from raw_event system data
            polling_start_time = raw_event.get('system', {}).get('polling_start_time')
            if not polling_start_time:
                # If no start time, don't filter
                return False
            
            # Get event time from parsed_event (already in local time)
            event_date = parsed_event.get('event_date')
            if not event_date:
                # If no event time, don't filter
                return False
            
            # Calculate time difference between polling start and event
            time_diff = await self.datetime_formatter.time_diff(event_date, polling_start_time)
            time_diff_seconds = time_diff.total_seconds()
            
            # Ignore events if difference is greater than startup_time_offset
            return time_diff_seconds > self.startup_time_offset
                
        except Exception as e:
            self.logger.warning(f"Error checking event time: {e}")
            return False
    
    async def cleanup(self) -> None:
        """
        Clean up resources
        """
        try:
            await self.media_group_processor.cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up: {e}")
