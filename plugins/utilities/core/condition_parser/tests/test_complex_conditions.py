"""
Тесты сложных условий с множественными операторами
"""
import pytest


class TestComplexOrWithAnd:
    """Тесты сложного OR с AND"""

    @pytest.mark.asyncio
    async def test_complex_or_with_and_first_condition(self, parser):
        """Проверка сложного OR с AND - первое условие"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)", 
                                          {"event_type": "message", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_complex_or_with_and_second_condition(self, parser):
        """Проверка сложного OR с AND - второе условие"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)", 
                                          {"event_type": "callback", "user_id": 30})
        assert result is True

    @pytest.mark.asyncio
    async def test_complex_or_with_and_both_false(self, parser):
        """Проверка сложного OR с AND - оба ложны"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)", 
                                          {"event_type": "message", "user_id": 50})
        assert result is False


class TestNestedParentheses:
    """Тесты вложенных скобок"""

    @pytest.mark.asyncio
    async def test_nested_parentheses_user_id_greater(self, parser):
        """Проверка вложенных скобок - user_id > 100"""
        result = await parser.check_match("$event_type == 'message' and ($user_id > 100 or $role in ['admin', 'moderator'])", 
                                          {"event_type": "message", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_parentheses_role_in_list(self, parser):
        """Проверка вложенных скобок - role в списке"""
        result = await parser.check_match("$event_type == 'message' and ($user_id > 100 or $role in ['admin', 'moderator'])", 
                                          {"event_type": "message", "user_id": 50, "role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_parentheses_both_false(self, parser):
        """Проверка вложенных скобок - оба ложны"""
        result = await parser.check_match("$event_type == 'message' and ($user_id > 100 or $role in ['admin', 'moderator'])", 
                                          {"event_type": "message", "user_id": 50, "role": "user"})
        assert result is False


class TestNotWithAndInParentheses:
    """Тесты NOT с AND в скобках"""

    @pytest.mark.asyncio
    async def test_not_with_and_in_parentheses(self, parser):
        """Проверка NOT с AND в скобках"""
        result = await parser.check_match("not ($event_type == 'message' and $user_id > 100)", 
                                          {"event_type": "callback", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_with_and_in_parentheses_one_false(self, parser):
        """Проверка NOT с AND в скобках - одно ложно"""
        result = await parser.check_match("not ($event_type == 'message' and $user_id > 100)", 
                                          {"event_type": "message", "user_id": 50})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_with_and_in_parentheses_both_true(self, parser):
        """Проверка NOT с AND в скобках - оба истинны"""
        result = await parser.check_match("not ($event_type == 'message' and $user_id > 100)", 
                                          {"event_type": "message", "user_id": 150})
        assert result is False


class TestVeryComplexConditions:
    """Тесты очень сложных условий"""

    @pytest.mark.asyncio
    async def test_very_complex_multilevel_parentheses_all_true(self, parser):
        """Проверка многоуровневых скобок - все истинно"""
        result = await parser.check_match("(($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)) and $role in ['admin', 'moderator']", 
                                          {"event_type": "message", "user_id": 150, "role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_very_complex_multilevel_parentheses_role_not_in_list(self, parser):
        """Проверка многоуровневых скобок - role не в списке"""
        result = await parser.check_match("(($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)) and $role in ['admin', 'moderator']", 
                                          {"event_type": "message", "user_id": 150, "role": "user"})
        assert result is False

    @pytest.mark.asyncio
    async def test_very_complex_not_with_nested_or_and(self, parser):
        """Проверка NOT с вложенными OR и AND"""
        result = await parser.check_match("not (($event_type == 'message' and $user_id > 100) or ($event_type == 'callback'))", 
                                          {"event_type": "callback"})
        assert result is False

    @pytest.mark.asyncio
    async def test_very_complex_not_with_nested_or_and_both_false(self, parser):
        """Проверка NOT с вложенными OR и AND - оба ложны"""
        result = await parser.check_match("not (($event_type == 'message' and $user_id > 100) or ($event_type == 'callback'))", 
                                          {"event_type": "message", "user_id": 50})
        assert result is True

    @pytest.mark.asyncio
    async def test_very_complex_three_level_nesting(self, parser):
        """Проверка трехуровневой вложенности"""
        result = await parser.check_match("($event_type == 'message' and ($user_id > 100 or ($role in ['admin'] and $user_id > 50))) or ($event_type == 'callback' and $event_text ~ 'start')", 
                                          {"event_type": "message", "user_id": 60, "role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_very_complex_three_level_nesting_second_condition(self, parser):
        """Проверка трехуровневой вложенности - второе условие"""
        result = await parser.check_match("($event_type == 'message' and ($user_id > 100 or ($role in ['admin'] and $user_id > 50))) or ($event_type == 'callback' and $event_text ~ 'start')", 
                                          {"event_type": "callback", "event_text": "start command"})
        assert result is True

