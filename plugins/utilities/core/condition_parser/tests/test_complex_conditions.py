"""
Tests for complex conditions with multiple operators
"""
import pytest


class TestComplexOrWithAnd:
    """Tests for complex OR with AND"""

    @pytest.mark.asyncio
    async def test_complex_or_with_and_first_condition(self, parser):
        """Check complex OR with AND - first condition"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)", 
                                          {"event_type": "message", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_complex_or_with_and_second_condition(self, parser):
        """Check complex OR with AND - second condition"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)", 
                                          {"event_type": "callback", "user_id": 30})
        assert result is True

    @pytest.mark.asyncio
    async def test_complex_or_with_and_both_false(self, parser):
        """Check complex OR with AND - both false"""
        result = await parser.check_match("($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)", 
                                          {"event_type": "message", "user_id": 50})
        assert result is False


class TestNestedParentheses:
    """Tests for nested parentheses"""

    @pytest.mark.asyncio
    async def test_nested_parentheses_user_id_greater(self, parser):
        """Check nested parentheses - user_id > 100"""
        result = await parser.check_match("$event_type == 'message' and ($user_id > 100 or $role in ['admin', 'moderator'])", 
                                          {"event_type": "message", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_parentheses_role_in_list(self, parser):
        """Check nested parentheses - role in list"""
        result = await parser.check_match("$event_type == 'message' and ($user_id > 100 or $role in ['admin', 'moderator'])", 
                                          {"event_type": "message", "user_id": 50, "role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_parentheses_both_false(self, parser):
        """Check nested parentheses - both false"""
        result = await parser.check_match("$event_type == 'message' and ($user_id > 100 or $role in ['admin', 'moderator'])", 
                                          {"event_type": "message", "user_id": 50, "role": "user"})
        assert result is False


class TestNotWithAndInParentheses:
    """Tests for NOT with AND in parentheses"""

    @pytest.mark.asyncio
    async def test_not_with_and_in_parentheses(self, parser):
        """Check NOT with AND in parentheses"""
        result = await parser.check_match("not ($event_type == 'message' and $user_id > 100)", 
                                          {"event_type": "callback", "user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_with_and_in_parentheses_one_false(self, parser):
        """Check NOT with AND in parentheses - one false"""
        result = await parser.check_match("not ($event_type == 'message' and $user_id > 100)", 
                                          {"event_type": "message", "user_id": 50})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_with_and_in_parentheses_both_true(self, parser):
        """Check NOT with AND in parentheses - both true"""
        result = await parser.check_match("not ($event_type == 'message' and $user_id > 100)", 
                                          {"event_type": "message", "user_id": 150})
        assert result is False


class TestVeryComplexConditions:
    """Tests for very complex conditions"""

    @pytest.mark.asyncio
    async def test_very_complex_multilevel_parentheses_all_true(self, parser):
        """Check multilevel parentheses - all true"""
        result = await parser.check_match("(($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)) and $role in ['admin', 'moderator']", 
                                          {"event_type": "message", "user_id": 150, "role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_very_complex_multilevel_parentheses_role_not_in_list(self, parser):
        """Check multilevel parentheses - role not in list"""
        result = await parser.check_match("(($event_type == 'message' and $user_id > 100) or ($event_type == 'callback' and $user_id < 50)) and $role in ['admin', 'moderator']", 
                                          {"event_type": "message", "user_id": 150, "role": "user"})
        assert result is False

    @pytest.mark.asyncio
    async def test_very_complex_not_with_nested_or_and(self, parser):
        """Check NOT with nested OR and AND"""
        result = await parser.check_match("not (($event_type == 'message' and $user_id > 100) or ($event_type == 'callback'))", 
                                          {"event_type": "callback"})
        assert result is False

    @pytest.mark.asyncio
    async def test_very_complex_not_with_nested_or_and_both_false(self, parser):
        """Check NOT with nested OR and AND - both false"""
        result = await parser.check_match("not (($event_type == 'message' and $user_id > 100) or ($event_type == 'callback'))", 
                                          {"event_type": "message", "user_id": 50})
        assert result is True

    @pytest.mark.asyncio
    async def test_very_complex_three_level_nesting(self, parser):
        """Check three-level nesting"""
        result = await parser.check_match("($event_type == 'message' and ($user_id > 100 or ($role in ['admin'] and $user_id > 50))) or ($event_type == 'callback' and $event_text ~ 'start')", 
                                          {"event_type": "message", "user_id": 60, "role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_very_complex_three_level_nesting_second_condition(self, parser):
        """Check three-level nesting - second condition"""
        result = await parser.check_match("($event_type == 'message' and ($user_id > 100 or ($role in ['admin'] and $user_id > 50))) or ($event_type == 'callback' and $event_text ~ 'start')", 
                                          {"event_type": "callback", "event_text": "start command"})
        assert result is True

