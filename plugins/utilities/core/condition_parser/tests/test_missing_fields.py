"""
Tests for missing fields in data
"""
import pytest


class TestMissingFieldsComparison:
    """Tests for missing field comparison"""

    @pytest.mark.asyncio
    async def test_missing_field_equals_should_be_false(self, parser):
        """Check missing field - should be False"""
        result = await parser.check_match("$field == 'value'", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_field_not_equals_should_be_true(self, parser):
        """Check missing field - != should be True"""
        result = await parser.check_match("$field != 'value'", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_field_comparison_should_be_false(self, parser):
        """Check missing field - comparison should be False"""
        result = await parser.check_match("$field > 100", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_field_equals_none_should_be_true(self, parser):
        """Check missing field - == None should be True"""
        result = await parser.check_match("$field == None", {})
        assert result is True


class TestMissingFieldsNullOperators:
    """Tests for is_null operators for missing fields"""

    @pytest.mark.asyncio
    async def test_missing_field_is_null_should_be_true(self, parser):
        """Check missing field - is_null should be True"""
        result = await parser.check_match("$field is_null", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_field_not_is_null_should_be_false(self, parser):
        """Check missing field - not is_null should be False"""
        result = await parser.check_match("$field not is_null", {})
        assert result is False


class TestMissingFieldsStringOperators:
    """Tests for string operators for missing fields"""

    @pytest.mark.asyncio
    async def test_missing_field_contains_should_be_false(self, parser):
        """Check missing field - ~ should be False"""
        result = await parser.check_match("$field ~ 'text'", {})
        assert result is False


class TestMissingFieldsListOperators:
    """Tests for list operators for missing fields"""

    @pytest.mark.asyncio
    async def test_missing_field_in_should_be_false(self, parser):
        """Check missing field - in should be False"""
        result = await parser.check_match("$field in ['value']", {})
        assert result is False

