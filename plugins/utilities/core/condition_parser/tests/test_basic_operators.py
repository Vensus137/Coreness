"""
Tests for basic comparison operators (==, !=, >, <, >=, <=)
"""
import pytest


class TestEqualityOperators:
    """Tests for equality operator (==)"""

    @pytest.mark.asyncio
    async def test_equality_string_operator(self, parser):
        """Check equality operator for strings"""
        result = await parser.check_match("$event_type == 'message'", {"event_type": "message"})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_string_operator_not_equal(self, parser):
        """Check equality operator for strings - not equal"""
        result = await parser.check_match("$event_type == 'message'", {"event_type": "callback"})
        assert result is False

    @pytest.mark.asyncio
    async def test_equality_number_operator(self, parser):
        """Check equality operator for numbers"""
        result = await parser.check_match("$user_id == 123", {"user_id": 123})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_number_operator_not_equal(self, parser):
        """Check equality operator for numbers - not equal"""
        result = await parser.check_match("$user_id == 123", {"user_id": 456})
        assert result is False

    @pytest.mark.asyncio
    async def test_equality_boolean_true_operator(self, parser):
        """Check equality operator for boolean True"""
        result = await parser.check_match("$is_active == True", {"is_active": True})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_boolean_false_operator(self, parser):
        """Check equality operator for boolean False"""
        result = await parser.check_match("$is_active == False", {"is_active": False})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_none_operator(self, parser):
        """Check equality operator for None"""
        result = await parser.check_match("$field == None", {"field": None})
        assert result is True


class TestInequalityOperators:
    """Tests for inequality operator (!=)"""

    @pytest.mark.asyncio
    async def test_inequality_operator(self, parser):
        """Check inequality operator"""
        result = await parser.check_match("$event_type != 'message'", {"event_type": "callback"})
        assert result is True

    @pytest.mark.asyncio
    async def test_inequality_operator_equal(self, parser):
        """Check inequality operator - equal"""
        result = await parser.check_match("$event_type != 'message'", {"event_type": "message"})
        assert result is False

    @pytest.mark.asyncio
    async def test_inequality_number_operator(self, parser):
        """Check inequality operator for numbers"""
        result = await parser.check_match("$user_id != 123", {"user_id": 456})
        assert result is True


class TestComparisonOperators:
    """Tests for comparison operators (>, <, >=, <=)"""

    @pytest.mark.asyncio
    async def test_greater_than_operator(self, parser):
        """Check greater than operator"""
        result = await parser.check_match("$user_id > 100", {"user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_greater_than_operator_less(self, parser):
        """Check greater than operator - less"""
        result = await parser.check_match("$user_id > 100", {"user_id": 50})
        assert result is False

    @pytest.mark.asyncio
    async def test_less_than_operator(self, parser):
        """Check less than operator"""
        result = await parser.check_match("$user_id < 100", {"user_id": 50})
        assert result is True

    @pytest.mark.asyncio
    async def test_greater_or_equal_operator(self, parser):
        """Check greater or equal operator"""
        result = await parser.check_match("$user_id >= 100", {"user_id": 100})
        assert result is True

    @pytest.mark.asyncio
    async def test_less_or_equal_operator(self, parser):
        """Check less or equal operator"""
        result = await parser.check_match("$user_id <= 100", {"user_id": 100})
        assert result is True

