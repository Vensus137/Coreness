"""
Tests for string operators (~, !~, regex)
"""
import pytest


class TestContainsOperator:
    """Tests for contains operator (~)"""

    @pytest.mark.asyncio
    async def test_string_contains_operator(self, parser):
        """Check contains substring operator (~)"""
        result = await parser.check_match('$event_text ~ "start"', {"event_text": "/start command"})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_contains_operator_not_contains(self, parser):
        """Check contains substring operator (~) - not contains"""
        result = await parser.check_match('$event_text ~ "start"', {"event_text": "/help"})
        assert result is False


class TestNotContainsOperator:
    """Tests for not contains operator (!~)"""

    @pytest.mark.asyncio
    async def test_string_not_contains_operator(self, parser):
        """Check not contains substring operator (!~)"""
        result = await parser.check_match('$event_text !~ "start"', {"event_text": "/help"})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_not_contains_operator_contains(self, parser):
        """Check not contains substring operator (!~) - contains"""
        result = await parser.check_match('$event_text !~ "start"', {"event_text": "/start"})
        assert result is False


class TestRegexOperator:
    """Tests for regex operator (regex)"""

    @pytest.mark.asyncio
    async def test_string_regex_operator(self, parser):
        """Check regular expression (regex)"""
        result = await parser.check_match(r'$event_text regex "\\d+"', {"event_text": "user123"})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_regex_operator_start_of_string(self, parser):
        """Check regular expression (regex) - start of string"""
        result = await parser.check_match(r'$event_text regex "^/\\w+"', {"event_text": "/start"})
        assert result is True

