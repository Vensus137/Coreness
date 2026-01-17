"""
Тесты логических операторов (AND, OR, NOT)
"""
import pytest


class TestAndOperator:
    """Тесты оператора AND"""

    @pytest.mark.asyncio
    async def test_and_operator_both_true(self, parser):
        """Проверка оператора AND - оба условия истинны"""
        result = await parser.check_match("$event_type == 'message' and $user_id > 100", 
                                          {"event_type": "message", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_and_operator_one_false(self, parser):
        """Проверка оператора AND - одно условие ложно"""
        result = await parser.check_match("$event_type == 'message' and $user_id > 100", 
                                          {"event_type": "message", "user_id": 50})
        assert result is False


class TestOrOperator:
    """Тесты оператора OR"""

    @pytest.mark.asyncio
    async def test_or_operator_second_true(self, parser):
        """Проверка оператора OR - второе условие истинно"""
        result = await parser.check_match("$event_type == 'message' or $user_id > 100", 
                                          {"event_type": "callback", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_or_operator_both_false(self, parser):
        """Проверка оператора OR - оба условия ложны"""
        result = await parser.check_match("$event_type == 'message' or $user_id > 100", 
                                          {"event_type": "callback", "user_id": 50})
        assert result is False


class TestNotOperator:
    """Тесты оператора NOT"""

    @pytest.mark.asyncio
    async def test_not_operator_inversion(self, parser):
        """Проверка оператора NOT - инверсия"""
        result = await parser.check_match("not $event_type == 'message'", {"event_type": "callback"})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_operator_inversion_false(self, parser):
        """Проверка оператора NOT - инверсия ложного"""
        result = await parser.check_match("not $event_type == 'message'", {"event_type": "message"})
        assert result is False


class TestParentheses:
    """Тесты приоритета операций со скобками"""

    @pytest.mark.asyncio
    async def test_parentheses_operator_priority(self, parser):
        """Проверка скобок - приоритет операций"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or $event_type == 'callback'", 
                                          {"event_type": "callback", "user_id": 50})
        assert result is True

