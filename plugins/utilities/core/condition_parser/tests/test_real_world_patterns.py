"""
Тесты реальных паттернов из сценариев
"""
import pytest


class TestIsNullCombinations:
    """Тесты комбинаций is_null"""

    @pytest.mark.asyncio
    async def test_real_world_is_null_combination_username(self, parser):
        """Проверка комбинации is_null - username есть"""
        result = await parser.check_match("$username not is_null or $first_name not is_null", 
                                          {"username": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_is_null_combination_first_name(self, parser):
        """Проверка комбинации is_null - first_name есть"""
        result = await parser.check_match("$username not is_null or $first_name not is_null", 
                                          {"first_name": "Test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_is_null_combination_both_none(self, parser):
        """Проверка комбинации is_null - оба None"""
        result = await parser.check_match("$username not is_null or $first_name not is_null", 
                                          {"username": None, "first_name": None})
        assert result is False


class TestEmptyListPatterns:
    """Тесты паттернов с пустыми списками"""

    @pytest.mark.asyncio
    async def test_real_world_empty_list_technically_false(self, parser):
        """Проверка пустого списка в условии (технически False)"""
        result = await parser.check_match("$is_group == True and $chat_id in []", 
                                          {"is_group": True, "chat_id": 123})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_empty_list_is_group_false(self, parser):
        """Проверка пустого списка - is_group False"""
        result = await parser.check_match("$is_group == True and $chat_id in []", 
                                          {"is_group": False, "chat_id": 123})
        assert result is False


class TestRegexPatterns:
    """Тесты regex паттернов"""

    @pytest.mark.asyncio
    async def test_real_world_regex_escaped_matches(self, parser):
        """Проверка regex с экранированием - совпадает"""
        result = await parser.check_match(r'$event_text regex "^@vensus_test_bot\\s+"', 
                                          {"event_text": "@vensus_test_bot hello"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_regex_escaped_no_space(self, parser):
        """Проверка regex с экранированием - нет пробела"""
        result = await parser.check_match(r'$event_text regex "^@vensus_test_bot\\s+"', 
                                          {"event_text": "@vensus_test_bot"})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_regex_escaped_not_start(self, parser):
        """Проверка regex с экранированием - не начало"""
        result = await parser.check_match(r'$event_text regex "^@vensus_test_bot\\s+"', 
                                          {"event_text": "hello @vensus_test_bot"})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_regex_command_matches(self, parser):
        """Проверка regex команды - совпадает"""
        result = await parser.check_match(r'$event_text regex "^/add\\s+\\S+"', 
                                          {"event_text": "/add user"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_regex_command_no_argument(self, parser):
        """Проверка regex команды - нет аргумента"""
        result = await parser.check_match(r'$event_text regex "^/add\\s+\\S+"', 
                                          {"event_text": "/add"})
        assert result is False

    @pytest.mark.asyncio
    async def test_real_world_regex_command_del_matches(self, parser):
        """Проверка regex команды del - совпадает"""
        result = await parser.check_match(r'$event_text regex "^/del\\s+\\S+"', 
                                          {"event_text": "/del user"})
        assert result is True


class TestComplexCombinations:
    """Тесты сложных комбинаций"""

    @pytest.mark.asyncio
    async def test_real_world_complex_combination_is_group_and_username(self, parser):
        """Проверка сложной комбинации - is_group и username"""
        result = await parser.check_match("$is_group == True and ($username not is_null or $first_name not is_null)", 
                                          {"is_group": True, "username": "test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_complex_combination_is_group_and_first_name(self, parser):
        """Проверка сложной комбинации - is_group и first_name"""
        result = await parser.check_match("$is_group == True and ($username not is_null or $first_name not is_null)", 
                                          {"is_group": True, "first_name": "Test"})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_complex_combination_is_group_false(self, parser):
        """Проверка сложной комбинации - is_group False"""
        result = await parser.check_match("$is_group == True and ($username not is_null or $first_name not is_null)", 
                                          {"is_group": False, "username": "test"})
        assert result is False


class TestDeepNesting:
    """Тесты глубокой вложенности"""

    @pytest.mark.asyncio
    async def test_real_world_nested_three_levels(self, parser):
        """Проверка вложенности 3 уровня"""
        result = await parser.check_match("$user.profile.settings.notifications == True", 
                                          {"user": {"profile": {"settings": {"notifications": True}}}})
        assert result is True

    @pytest.mark.asyncio
    async def test_real_world_nested_three_levels_missing(self, parser):
        """Проверка вложенности 3 уровня - отсутствует"""
        result = await parser.check_match("$user.profile.settings.notifications == True", 
                                          {"user": {"profile": {"settings": {}}}})
        assert result is False

