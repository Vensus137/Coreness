"""
Tests for identifiers without quotes (after placeholder expansion)
"""
import pytest


class TestIdentifiersWithoutQuotes:
    """Tests for identifiers without quotes"""

    @pytest.mark.asyncio
    async def test_identifier_null_without_quotes(self, parser):
        """Check null identifier without quotes"""
        result = await parser.check_match('null == "null"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_none_without_quotes(self, parser):
        """Check none identifier without quotes"""
        result = await parser.check_match('none == "none"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_text_without_quotes(self, parser):
        """Check text identifier without quotes"""
        result = await parser.check_match('text == "text"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_both_sides_without_quotes(self, parser):
        """Check identifiers on both sides without quotes"""
        result = await parser.check_match('null == null', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_with_field_marker(self, parser):
        """Check identifier with field marker"""
        result = await parser.check_match('$field == value', {"field": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_with_field_marker_not_equal(self, parser):
        """Check identifier with field marker - not equal"""
        result = await parser.check_match('$field == value', {"field": "other"})
        assert result is False

    @pytest.mark.asyncio
    async def test_identifier_null_with_field_marker(self, parser):
        """Check null identifier with field marker"""
        # null without quotes is interpreted as string "null", not as None
        result = await parser.check_match('$field == null', {"field": None})
        assert result is False  # None != "null"

    @pytest.mark.asyncio
    async def test_identifier_complex_condition(self, parser):
        """Check complex condition with identifiers"""
        result = await parser.check_match('null == "null" or none == "none"', {})
        assert result is True

