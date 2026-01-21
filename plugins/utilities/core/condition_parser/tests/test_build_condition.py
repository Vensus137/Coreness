"""
Tests for build_condition method
"""
import pytest


class TestBuildCondition:
    """Tests for build_condition method"""

    @pytest.mark.asyncio
    async def test_build_condition_simple_structure(self, parser):
        """Check build_condition - simple structure"""
        configs = [{"event_type": "message", "user_id": 123}]
        expected_pattern = "($event_type == 'message' and $user_id == 123)"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

    @pytest.mark.asyncio
    async def test_build_condition_two_structures_with_or(self, parser):
        """Check build_condition - two structures via OR"""
        configs = [{"event_type": "message"}, {"event_type": "callback"}]
        expected_pattern = "($event_type == 'message') or ($event_type == 'callback')"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

    @pytest.mark.asyncio
    async def test_build_condition_with_custom_condition(self, parser):
        """Check build_condition - with custom condition"""
        configs = [{"event_type": "message", "condition": "$user_id > 100"}]
        expected_pattern = "($event_type == 'message' and $user_id > 100)"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

    @pytest.mark.asyncio
    async def test_build_condition_fields_and_custom_condition(self, parser):
        """Check build_condition - fields + custom condition"""
        configs = [{"event_type": "message", "user_id": 123, "condition": "$role == 'admin'"}]
        expected_pattern = "($event_type == 'message' and $user_id == 123 and $role == 'admin')"
        result = await parser.build_condition(configs)
        assert expected_pattern in result or result == expected_pattern

