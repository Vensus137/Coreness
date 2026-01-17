"""
Утилита для обработки Media Group сообщений от Telegram API
"""

import asyncio
from typing import Any, Callable, Dict, List


class MediaGroupProcessor:
    """
    Сервис для обработки Media Group сообщений от Telegram API.
    Группирует сообщения с одинаковым media_group_id и возвращает объединенное событие.
    """

    def __init__(self, logger, settings_manager):
        self.logger = logger
        self.settings_manager = settings_manager
        
        # Получаем настройки
        settings = self.settings_manager.get_plugin_settings("event_processor")
        self.timeout = settings.get('media_group_timeout', 0.5)
        
        self.group_cache: Dict[str, List[Dict]] = {}
        self._background_tasks: List[asyncio.Task] = []

    async def process_event(self, event: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Обрабатывает событие. Если это Media Group - группирует, иначе сразу вызывает callback.
        """
        if event.get('media_group_id'):
            await self._handle_media_group(event, callback)
        else:
            # Обычное событие - сразу вызываем callback
            await callback(event)

    async def _handle_media_group(self, event: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Обрабатывает событие как часть Media Group.
        """
        group_id = event['media_group_id']

        # Добавляем событие в кэш группы
        if group_id not in self.group_cache:
            self.group_cache[group_id] = []
        
        self.group_cache[group_id].append(event)

        # Если это первое событие в группе, запускаем таймер
        if len(self.group_cache[group_id]) == 1:
            task = asyncio.create_task(self._process_group_after_timeout(group_id, callback))
            self._background_tasks.append(task)

    async def _process_group_after_timeout(self, group_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Обрабатывает группу событий после таймаута.
        """
        try:
            # Ждем таймаут
            await asyncio.sleep(self.timeout)

            # Получаем все события группы
            group_events = self.group_cache.get(group_id, [])
            if not group_events:
                return

            # Объединяем события в одно
            merged_event = self._merge_group_events(group_events)
            
            # Вызываем callback с объединенным событием
            await callback(merged_event)

            # Очищаем кэш группы
            if group_id in self.group_cache:
                del self.group_cache[group_id]

        except Exception as e:
            self.logger.error(f"Ошибка обработки медиагруппы {group_id}: {e}")

    def _merge_group_events(self, group_events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Объединяет события медиагруппы в одно событие.
        """
        if not group_events:
            return {}

        # Берем первое событие как основу
        merged_event = group_events[0].copy()

        # Объединяем вложения из всех событий
        all_attachments = []
        for event in group_events:
            attachments = event.get('event_attachment', [])
            all_attachments.extend(attachments)

        merged_event['event_attachment'] = all_attachments

        # Обновляем текст (берем из последнего события с текстом)
        for event in reversed(group_events):
            if event.get('event_text'):
                merged_event['event_text'] = event['event_text']
                break

        # Добавляем информацию о группе
        merged_event['media_group_count'] = len(group_events)
        merged_event['media_group_events'] = len(group_events)

        return merged_event

    async def cleanup(self):
        """
        Очищает ресурсы и отменяет фоновые задачи.
        """
        # Отменяем все фоновые задачи
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # Ждем завершения отмененных задач
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Очищаем кэш
        self.group_cache.clear()
        self._background_tasks.clear()
