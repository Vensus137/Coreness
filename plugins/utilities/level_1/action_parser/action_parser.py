import re
from typing import Optional


class ActionParser:
    """
    Универсальный парсер действия из базы: объединяет prev_data, action_data и основные поля в один плоский dict.
    Используется всеми сервисами для получения "плоского" action.
    """
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']

    def parse_action(self, action: dict) -> dict:
        
        # 1. Безопасный мердж всех данных с правильным приоритетом
        # Приоритет: prev_data (высший) > action_data (средний) > action (низший)
        merged = action.copy()
        
        # Добавляем action_data (средний приоритет, затирает flat атрибуты)
        action_data = action.get('action_data', {})
        if action_data:
            merged.update(action_data)
        
        # Добавляем prev_data (высший приоритет, затирает все остальное)
        prev_data = action.get('prev_data')
        if prev_data:
            merged.update(prev_data)

        # 2. Убираем служебные поля
        merged.pop('action_data', None)
        merged.pop('prev_data', None)

        # 3. Обрабатываем временные атрибуты (expire, unexpired, duration)
        self._process_time_attributes(merged)

        return merged

    def _parse_time_string(self, time_string: Optional[str]) -> Optional[int]:
        """Универсальный парсер временных строк в секунды (например, '1w 5d 4h 30m 15s')"""
        if not time_string:
            return None
        pattern = r"(\d+)\s*(w|d|h|m|s)"
        total_seconds = 0
        for value, unit in re.findall(pattern, time_string):
            value = int(value)
            if unit == 'w':
                total_seconds += value * 604800
            elif unit == 'd':
                total_seconds += value * 86400
            elif unit == 'h':
                total_seconds += value * 3600
            elif unit == 'm':
                total_seconds += value * 60
            elif unit == 's':
                total_seconds += value
        return total_seconds if total_seconds > 0 else None

    def _process_time_attributes(self, action: dict):
        """Обрабатывает временные атрибуты в действии, добавляя _seconds версии"""
        for time_attr in ['expire', 'unexpired', 'duration']:
            if time_attr in action and isinstance(action[time_attr], str):
                seconds = self._parse_time_string(action[time_attr])
                if seconds is not None:
                    action[f'{time_attr}_seconds'] = seconds
