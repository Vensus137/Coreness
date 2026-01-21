"""
Tests for is_null operators
"""
import pytest


class TestIsNullOperator:
    """Tests for is_null operator"""

    @pytest.mark.asyncio
    async def test_is_null_operator_none(self, parser):
        """Check is_null operator - None"""
        result = await parser.check_match("$field is_null", {"field": None})
        assert result is True

    @pytest.mark.asyncio
    async def test_is_null_operator_empty_string(self, parser):
        """Check is_null operator - empty string"""
        result = await parser.check_match("$field is_null", {"field": ""})
        assert result is True

    @pytest.mark.asyncio
    async def test_is_null_operator_has_value(self, parser):
        """Check is_null operator - has value"""
        result = await parser.check_match("$field is_null", {"field": "value"})
        assert result is False


class TestNotIsNullOperator:
    """Tests for not is_null operator"""

    @pytest.mark.asyncio
    async def test_not_is_null_operator_has_value(self, parser):
        """Check not is_null operator - has value"""
        result = await parser.check_match("$field not is_null", {"field": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_is_null_operator_none(self, parser):
        """Check not is_null operator - None"""
        result = await parser.check_match("$field not is_null", {"field": None})
        assert result is False

    @pytest.mark.asyncio
    async def test_not_is_null_operator_empty_string(self, parser):
        """Check not is_null operator - empty string"""
        result = await parser.check_match("$field not is_null", {"field": ""})
        assert result is False

