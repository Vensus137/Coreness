import re
from typing import Any, Dict, Optional


class TriggerProcessing:
    """
    Сервис для обработки триггеров (поиск сценария по событию или кнопке).
    Использует settings_manager для доступа к триггерам и сценариям.
    Включает проверку состояний пользователей с ленивой очисткой.
    """
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        self.scenarios_manager = kwargs['scenarios_manager']
        self.button_mapper = kwargs['button_mapper']
        self.database_service = kwargs['database_service']
        self.datetime_formatter = kwargs['datetime_formatter']

    def _get_triggers_for_event(self, event: dict) -> dict:
        """
        Возвращает нужный набор триггеров в зависимости от типа чата (групповой/приватный).
        Для групповых чатов (chat_id < 0) — group_triggers, иначе — обычные triggers.
        """
        chat_id = event.get('chat_id')
        if isinstance(chat_id, int) and chat_id < 0:
            return self.scenarios_manager.get_group_triggers()
        return self.scenarios_manager.get_triggers()

    def find_scenario_by_event(self, event: dict) -> Optional[str]:
        """
        Поиск сценария по событию (text/callback/new_member) с поддержкой состояний пользователей.
        Иерархия приоритетов для text: exact → state → regex → starts_with → contains
        """
        # Игнорируем не-приватные чаты
        if event.get('chat_type') == 'channel':

            return None
        triggers = self._get_triggers_for_event(event)
        event_type = event.get('source_type')

        if event_type == 'text':
            text = event.get('event_text')
            user_id = event.get('user_id')

            # 1. exact (case-insensitive) - ВСЕГДА ПРИОРИТЕТ
            if text:
                for key, val in triggers.get('text', {}).get('exact', {}).items():
                    if key.lower() == text.lower():
                        return val

            # 2. state - проверка состояния пользователя (с ленивой очисткой)
            # Проверяем состояние даже если нет текста, но есть вложения или пользователь в состоянии
            if user_id:
                state_match = self._find_state_match(user_id, text, triggers)
                if state_match:
                    return state_match

            # 3. regex - регулярные выражения (более специфичные паттерны)
            if text:
                for pattern, val in triggers.get('text', {}).get('regex', {}).items():
                    try:
                        if re.search(pattern, text, re.IGNORECASE):
                            return val
                    except re.error as e:
                        self.logger.error(f"Ошибка в регулярном выражении '{pattern}': {e}")

            # 4. starts_with (case-insensitive) - строка начинается с указанного текста (общий случай)
            if text:
                for key, val in triggers.get('text', {}).get('starts_with', {}).items():
                    if text.lower().startswith(key.lower()):
                        return val

            # 5. contains (case-insensitive) - только если есть текст
            if text:
                for key, val in triggers.get('text', {}).get('contains', {}).items():
                    if key.lower() in text.lower():
                        return val

            return None

        elif event_type == 'callback':

            callback_data = event.get('callback_data')
            if not callback_data or not self.button_mapper:
                return None

            # Явный переход по сценарию через callback_data вида ':scenario_name'
            if isinstance(callback_data, str) and callback_data.startswith(":"):
                return callback_data[1:]

            orig_text = self.button_mapper.get_button_text(callback_data)
            if not orig_text:
                return None
            norm_orig = self.button_mapper.normalize(orig_text)

            # exact (нормализованный)
            for key, val in triggers.get('callback', {}).get('exact', {}).items():
                if self.button_mapper.normalize(key) == norm_orig:
                    return val

            # contains (нормализованный)
            for key, val in triggers.get('callback', {}).get('contains', {}).items():
                norm_key = self.button_mapper.normalize(key)
                if norm_key in norm_orig:
                    return val
            return None

        elif event_type == 'new_member':
            triggers_new = triggers.get('new_member', {})
            # 1. group (по chat_title)
            group_triggers = triggers_new.get('group', {})
            chat_title = event.get('chat_title')
            if group_triggers and chat_title:
                for title, scenario in group_triggers.items():
                    if title.lower() == chat_title.lower():
                        return scenario
            # 2. link (по invite_link contains)
            invite_link = event.get('invite_link')
            link_triggers = triggers_new.get('link', {})
            if invite_link and link_triggers:
                for substr, scenario in link_triggers.items():
                    if substr.lower() in invite_link.lower():
                        return scenario
            # 3. creator (по username создателя ссылки)
            creator_username = event.get('invite_link_creator_username')
            creator_triggers = triggers_new.get('creator', {})
            if creator_username and creator_triggers:
                norm_username = creator_username.lstrip('@').lower()
                for key, scenario in creator_triggers.items():
                    norm_key = key.lstrip('@').lower()
                    if norm_username == norm_key:
                        return scenario
            # 4. initiator (по username инициатора добавления)
            initiator_username = event.get('initiator_username')
            initiator_triggers = triggers_new.get('initiator', {})
            if initiator_username and initiator_triggers:
                norm_initiator = initiator_username.lstrip('@').lower()
                for key, scenario in initiator_triggers.items():
                    norm_key = key.lstrip('@').lower()
                    if norm_initiator == norm_key:
                        return scenario
            # 5. default
            if 'default' in triggers_new:
                return triggers_new['default']
            return None

        return None

    def _find_state_match(self, user_id: int, text: str, triggers: dict) -> Optional[str]:
        """
        Проверка состояния пользователя с ленивой очисткой.
        Возвращает сценарий если состояние пользователя совпадает с триггером состояния.
        """
        if not user_id:
            return None

        # Получаем состояние пользователя (с ленивой очисткой)
        user_state = self._get_user_state_with_cleanup(user_id)
        if not user_state:
            return None

        # Проверяем триггеры состояния
        state_triggers = triggers.get('text', {}).get('state', {})
        state_type = user_state.get('state_type')

        for trigger_state, scenario in state_triggers.items():
            if trigger_state == state_type:
                return scenario

        return None

    def _get_user_state_with_cleanup(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить состояние пользователя с ленивой очисткой.
        Если состояние истекло - очищает его и возвращает None.
        """
        try:
            with self.database_service.session_scope('user_states') as (_, repos):
                user_states_repo = repos['user_states']

                # Получаем состояние пользователя одним запросом
                user_state = user_states_repo.get_user_state(user_id)
                if not user_state:
                    return None

                # Проверяем истечение по expired_at
                now = self.datetime_formatter.now_local()
                if user_state.get('expired_at') is not None:
                    if user_state['expired_at'] < now:
                        user_states_repo.clear_user_state(user_id)
                        return None

                # Данные состояния уже декодированы в ORMConverter
                state_data = user_state.get('state_data') or {}

                return {
                    'state_type': user_state.get('state_type'),
                    'data': state_data
                }

        except Exception as e:
            self.logger.error(f"Ошибка при получении состояния пользователя {user_id}: {e}")
            return None

    def find_scenario_by_button(self, button_text: Any, event: dict = None) -> Optional[str]:
        """
        Поиск сценария по inline-кнопке (для документации и визуализации).
        Если передан event — учитывает тип чата для выбора триггеров.
        """
        # Игнорируем не-приватные чаты
        if event and event.get('chat_type') != 'private':
            return None
        triggers = self._get_triggers_for_event(event) if event else self.settings_manager.get_settings_section('triggers')
        if not button_text:
            return None
        # Новый формат: dict {"Текст": "сценарий"}
        if isinstance(button_text, dict):
            return list(button_text.values())[0]
        norm_text = self.button_mapper.normalize(button_text) if self.button_mapper else str(button_text).lower()
        for key, val in triggers.get('callback', {}).get('exact', {}).items():
            norm_key = self.button_mapper.normalize(key) if self.button_mapper else key.lower()
            if norm_key == norm_text:
                return val
        for key, val in triggers.get('callback', {}).get('contains', {}).items():
            norm_key = self.button_mapper.normalize(key) if self.button_mapper else key.lower()
            if norm_key in norm_text:
                return val
        return None
