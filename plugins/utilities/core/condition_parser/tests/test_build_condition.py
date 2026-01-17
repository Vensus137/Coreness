"""
Тесты метода build_condition
"""
import pytest


class TestBuildCondition:
    """Тесты метода build_condition"""

    @pytest.mark.asyncio
    async def test_build_condition_simple_structure(self, parser):
        """Проверка build_condition - простая структура"""
        configs = [{"event_type": "message", "user_id": 123}]
        expected_pattern = "($event_type == 'message' and $user_id == 123)"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

    @pytest.mark.asyncio
    async def test_build_condition_two_structures_with_or(self, parser):
        """Проверка build_condition - две структуры через OR"""
        configs = [{"event_type": "message"}, {"event_type": "callback"}]
        expected_pattern = "($event_type == 'message') or ($event_type == 'callback')"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

    @pytest.mark.asyncio
    async def test_build_condition_with_custom_condition(self, parser):
        """Проверка build_condition - с кастомным условием"""
        configs = [{"event_type": "message", "condition": "$user_id > 100"}]
        expected_pattern = "($event_type == 'message' and $user_id > 100)"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

    @pytest.mark.asyncio
    async def test_build_condition_fields_and_custom_condition(self, parser):
        """Проверка build_condition - поля + кастомное условие"""
        configs = [{"event_type": "message", "user_id": 123, "condition": "$role == 'admin'"}]
        expected_pattern = "($event_type == 'message' and $user_id == 123 and $role == 'admin')"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

