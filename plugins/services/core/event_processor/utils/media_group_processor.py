"""
Utility for processing Media Group messages from Telegram API
"""

import asyncio
from typing import Any, Callable, Dict, List


class MediaGroupProcessor:
    """
    Service for processing Media Group messages from Telegram API.
    Groups messages with the same media_group_id and returns merged event.
    """

    def __init__(self, logger, settings_manager):
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Get settings
        settings = self.settings_manager.get_plugin_settings("event_processor")
        self.timeout = settings.get('media_group_timeout', 0.5)
        
        self.group_cache: Dict[str, List[Dict]] = {}
        self._background_tasks: List[asyncio.Task] = []

    async def process_event(self, event: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Process event. If it's a Media Group - group it, otherwise immediately call callback.
        """
        if event.get('media_group_id'):
            await self._handle_media_group(event, callback)
        else:
            # Regular event - immediately call callback
            await callback(event)

    async def _handle_media_group(self, event: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Process event as part of Media Group.
        """
        group_id = event['media_group_id']

        # Add event to group cache
        if group_id not in self.group_cache:
            self.group_cache[group_id] = []
        
        self.group_cache[group_id].append(event)

        # If this is first event in group, start timer
        if len(self.group_cache[group_id]) == 1:
            task = asyncio.create_task(self._process_group_after_timeout(group_id, callback))
            self._background_tasks.append(task)

    async def _process_group_after_timeout(self, group_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Process group of events after timeout.
        """
        try:
            # Wait for timeout
            await asyncio.sleep(self.timeout)

            # Get all group events
            group_events = self.group_cache.get(group_id, [])
            if not group_events:
                return

            # Merge events into one
            merged_event = self._merge_group_events(group_events)
            
            # Call callback with merged event
            await callback(merged_event)

            # Clear group cache
            if group_id in self.group_cache:
                del self.group_cache[group_id]

        except Exception as e:
            self.logger.error(f"Error processing media group {group_id}: {e}")

    def _merge_group_events(self, group_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge media group events into one event.
        """
        if not group_events:
            return {}

        # Take first event as base
        merged_event = group_events[0].copy()

        # Merge attachments from all events
        all_attachments = []
        for event in group_events:
            attachments = event.get('event_attachment', [])
            all_attachments.extend(attachments)

        merged_event['event_attachment'] = all_attachments

        # Update text (take from last event with text)
        for event in reversed(group_events):
            if event.get('event_text'):
                merged_event['event_text'] = event['event_text']
                break

        # Add group information
        merged_event['media_group_count'] = len(group_events)
        merged_event['media_group_events'] = len(group_events)

        return merged_event

    async def cleanup(self):
        """
        Clean up resources and cancel background tasks.
        """
        # Cancel all background tasks
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for cancelled tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Clear cache
        self.group_cache.clear()
        self._background_tasks.clear()
