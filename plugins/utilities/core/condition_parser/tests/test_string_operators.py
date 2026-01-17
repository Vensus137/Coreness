"""
Тесты операторов строк (~, !~, regex)
"""
import pytest


class TestContainsOperator:
    """Тесты оператора содержит (~)"""

    @pytest.mark.asyncio
    async def test_string_contains_operator(self, parser):
        """Проверка оператора содержит подстроку (~)"""
        result = await parser.check_match('$event_text ~ "start"', {"event_text": "/start command"})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_contains_operator_not_contains(self, parser):
        """Проверка оператора содержит подстроку (~) - не содержит"""
        result = await parser.check_match('$event_text ~ "start"', {"event_text": "/help"})
        assert result is False


class TestNotContainsOperator:
    """Тесты оператора не содержит (!~)"""

    @pytest.mark.asyncio
    async def test_string_not_contains_operator(self, parser):
        """Проверка оператора не содержит подстроку (!~)"""
        result = await parser.check_match('$event_text !~ "start"', {"event_text": "/help"})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_not_contains_operator_contains(self, parser):
        """Проверка оператора не содержит подстроку (!~) - содержит"""
        result = await parser.check_match('$event_text !~ "start"', {"event_text": "/start"})
        assert result is False


class TestRegexOperator:
    """Тесты оператора регулярных выражений (regex)"""

    @pytest.mark.asyncio
    async def test_string_regex_operator(self, parser):
        """Проверка регулярного выражения (regex)"""
        result = await parser.check_match(r'$event_text regex "\\d+"', {"event_text": "user123"})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_regex_operator_start_of_string(self, parser):
        """Проверка регулярного выражения (regex) - начало строки"""
        result = await parser.check_match(r'$event_text regex "^/\\w+"', {"event_text": "/start"})
        assert result is True

