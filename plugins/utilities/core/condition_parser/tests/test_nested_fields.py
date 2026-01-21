"""
Tests for working with nested fields
"""
import pytest


class TestNestedFields:
    """Nested field tests"""

    @pytest.mark.asyncio
    async def test_nested_field_one_level(self, parser):
        """Check nested field - one level"""
        result = await parser.check_match("$message.text == 'hello'", {"message": {"text": "hello"}})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_field_one_level_not_equal(self, parser):
        """Check nested field - not equal"""
        result = await parser.check_match("$message.text == 'hello'", {"message": {"text": "world"}})
        assert result is False

    @pytest.mark.asyncio
    async def test_nested_field_two_levels(self, parser):
        """Check nested field - two levels"""
        result = await parser.check_match("$user.profile.name == 'John'", 
                                          {"user": {"profile": {"name": "John"}}})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_field_missing(self, parser):
        """Check nested field - missing"""
        result = await parser.check_match("$message.text == 'hello'", {"message": {}})
        assert result is False

