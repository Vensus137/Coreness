"""
Tests for real-world patterns from scenarios
"""
import pytest


class TestIsNullCombinations:
    """Tests for is_null combinations"""

    @pytest.mark.asyncio
    async def test_real_world_is_null_combination_username(self, parser):
        """Check is_null combination - username exists"""
        result = await parser.check_match("$username not is_null or $first_name not is_null", 
                                          {"username": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_is_null_combination_first_name(self, parser):
        """Check is_null combination - first_name exists"""
        result = await parser.check_match("$username not is_null or $first_name not is_null", 
                                          {"first_name": "Test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_is_null_combination_both_none(self, parser):
        """Check is_null combination - both None"""
        result = await parser.check_match("$username not is_null or $first_name not is_null", 
                                          {"username": None, "first_name": None})
        assert result is False


class TestEmptyListPatterns:
    """Tests for patterns with empty lists"""

    @pytest.mark.asyncio
    async def test_real_world_empty_list_technically_false(self, parser):
        """Check empty list in condition (technically False)"""
        result = await parser.check_match("$is_group == True and $chat_id in []", 
                                          {"is_group": True, "chat_id": 123})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_empty_list_is_group_false(self, parser):
        """Check empty list - is_group False"""
        result = await parser.check_match("$is_group == True and $chat_id in []", 
                                          {"is_group": False, "chat_id": 123})
        assert result is False


class TestRegexPatterns:
    """Tests for regex patterns"""

    @pytest.mark.asyncio
    async def test_real_world_regex_escaped_matches(self, parser):
        """Check regex with escaping - matches"""
        result = await parser.check_match(r'$event_text regex "^@vensus_test_bot\\s+"', 
                                          {"event_text": "@vensus_test_bot hello"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_regex_escaped_no_space(self, parser):
        """Check regex with escaping - no space"""
        result = await parser.check_match(r'$event_text regex "^@vensus_test_bot\\s+"', 
                                          {"event_text": "@vensus_test_bot"})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_regex_escaped_not_start(self, parser):
        """Check regex with escaping - not start"""
        result = await parser.check_match(r'$event_text regex "^@vensus_test_bot\\s+"', 
                                          {"event_text": "hello @vensus_test_bot"})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_regex_command_matches(self, parser):
        """Check regex command - matches"""
        result = await parser.check_match(r'$event_text regex "^/add\\s+\\S+"', 
                                          {"event_text": "/add user"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_regex_command_no_argument(self, parser):
        """Check regex command - no argument"""
        result = await parser.check_match(r'$event_text regex "^/add\\s+\\S+"', 
                                          {"event_text": "/add"})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_regex_command_del_matches(self, parser):
        """Check regex command del - matches"""
        result = await parser.check_match(r'$event_text regex "^/del\\s+\\S+"', 
                                          {"event_text": "/del user"})
        assert result is True


class TestComplexCombinations:
    """Tests for complex combinations"""

    @pytest.mark.asyncio
    async def test_real_world_complex_combination_is_group_and_username(self, parser):
        """Check complex combination - is_group and username"""
        result = await parser.check_match("$is_group == True and ($username not is_null or $first_name not is_null)", 
                                          {"is_group": True, "username": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_complex_combination_is_group_and_first_name(self, parser):
        """Check complex combination - is_group and first_name"""
        result = await parser.check_match("$is_group == True and ($username not is_null or $first_name not is_null)", 
                                          {"is_group": True, "first_name": "Test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_complex_combination_is_group_false(self, parser):
        """Check complex combination - is_group False"""
        result = await parser.check_match("$is_group == True and ($username not is_null or $first_name not is_null)", 
                                          {"is_group": False, "username": "test"})
        assert result is False


class TestDeepNesting:
    """Tests for deep nesting"""

    @pytest.mark.asyncio
    async def test_real_world_nested_three_levels(self, parser):
        """Check 3-level nesting"""
        result = await parser.check_match("$user.profile.settings.notifications == True", 
                                          {"user": {"profile": {"settings": {"notifications": True}}}})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_nested_three_levels_missing(self, parser):
        """Check 3-level nesting - missing"""
        result = await parser.check_match("$user.profile.settings.notifications == True", 
                                          {"user": {"profile": {"settings": {}}}})
        assert result is False

