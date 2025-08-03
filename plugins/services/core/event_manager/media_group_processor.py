import asyncio
from typing import Any, Callable, Dict, List

# Logger будет передан через конструктор


class MediaGroupProcessor:
    """
    Вспомогательный обработчик Media Group сообщений от Telegram API.
    Группирует сообщения с одинаковым media_group_id и возвращает объединенное событие.
    """

    def __init__(self, timeout: float = 1.0, logger=None):
        self.timeout = timeout
        self.logger = logger
        self.group_cache: Dict[str, List[Dict]] = {}
        self._background_tasks: List[asyncio.Task] = []

    async def process_event(self, event: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Обрабатывает событие. Если это Media Group - группирует, иначе сразу вызывает callback.
        """
        if event.get('media_group_id'):
            await self._handle_media_group(event, callback)
        else:
            # Обычное событие - сразу вызываем callback асинхронно
            await callback(event)

    async def _handle_media_group(self, event: Dict[str, Any], callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Обрабатывает событие как часть Media Group.
        """
        group_id = event['media_group_id']

        if group_id not in self.group_cache:
            self.group_cache[group_id] = []
    
            # Запускаем таймер для обработки группы
            task = asyncio.create_task(self._process_group_after_timeout(group_id, callback))
            self._background_tasks.append(task)

        self.group_cache[group_id].append(event)

    async def _process_group_after_timeout(self, group_id: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Обрабатывает группу после истечения таймера.
        """
        await asyncio.sleep(self.timeout)

        if group_id in self.group_cache:
            events = self.group_cache[group_id]
            combined_event = self._merge_group_events(events)

    
            # Вызываем callback с объединенным событием асинхронно
            await callback(combined_event)

            del self.group_cache[group_id]

    def _merge_group_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Объединяет события группы в одно событие.
        """
        if not events:
            return None

        # Берем первое событие как основу
        combined = events[0].copy()

        # Объединяем attachments из всех событий
        all_attachments = []
        # Ищем event_text (caption) в любом из событий группы
        event_text = None
        for event in events:
            all_attachments.extend(event.get('attachments', []))
            # Если еще не нашли текст, ищем в текущем событии
            if not event_text and event.get('event_text'):
                event_text = event['event_text']

        combined['attachments'] = all_attachments
        # Обновляем event_text если нашли в группе
        if event_text:
            combined['event_text'] = event_text

        # Проверяем консистентность данных
        for event in events[1:]:
            if event['user_id'] != combined['user_id']:
                self.logger.warning(f"⚠️ Разные user_id в группе {combined['media_group_id']}: {combined['user_id']} vs {event['user_id']}")

            if event['chat_id'] != combined['chat_id']:
                self.logger.warning(f"⚠️ Разные chat_id в группе {combined['media_group_id']}: {combined['chat_id']} vs {event['chat_id']}")

        return combined

    async def cleanup(self):
        """
        Очищает все незавершенные группы и отменяет задачи.
        """
        for task in self._background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        if self.group_cache:
            self.logger.warning(f"⚠️ Очищено {len(self.group_cache)} незавершенных групп")
            self.group_cache.clear()
