"""
Tests for logical operators (AND, OR, NOT)
"""
import pytest


class TestAndOperator:
    """Tests for AND operator"""

    @pytest.mark.asyncio
    async def test_and_operator_both_true(self, parser):
        """Check AND operator - both conditions true"""
        result = await parser.check_match("$event_type == 'message' and $user_id > 100", 
                                          {"event_type": "message", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_and_operator_one_false(self, parser):
        """Check AND operator - one condition false"""
        result = await parser.check_match("$event_type == 'message' and $user_id > 100", 
                                          {"event_type": "message", "user_id": 50})
        assert result is False


class TestOrOperator:
    """Tests for OR operator"""

    @pytest.mark.asyncio
    async def test_or_operator_second_true(self, parser):
        """Check OR operator - second condition true"""
        result = await parser.check_match("$event_type == 'message' or $user_id > 100", 
                                          {"event_type": "callback", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_or_operator_both_false(self, parser):
        """Check OR operator - both conditions false"""
        result = await parser.check_match("$event_type == 'message' or $user_id > 100", 
                                          {"event_type": "callback", "user_id": 50})
        assert result is False


class TestNotOperator:
    """Tests for NOT operator"""

    @pytest.mark.asyncio
    async def test_not_operator_inversion(self, parser):
        """Check NOT operator - inversion"""
        result = await parser.check_match("not $event_type == 'message'", {"event_type": "callback"})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_operator_inversion_false(self, parser):
        """Check NOT operator - inversion of false"""
        result = await parser.check_match("not $event_type == 'message'", {"event_type": "message"})
        assert result is False


class TestParentheses:
    """Tests for operation priority with parentheses"""

    @pytest.mark.asyncio
    async def test_parentheses_operator_priority(self, parser):
        """Check parentheses - operation priority"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or $event_type == 'callback'", 
                                          {"event_type": "callback", "user_id": 50})
        assert result is True

