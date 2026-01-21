"""
Condition parsing tests
"""
import pytest


class TestParseConditionString:
    """Tests for parse_condition_string method"""

    @pytest.mark.asyncio
    async def test_parse_condition_string_simple(self, parser):
        """Check parsing of simple condition with == for search_path"""
        parsed = await parser.parse_condition_string("$event_type == 'message'")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

    @pytest.mark.asyncio
    async def test_parse_condition_string_with_and(self, parser):
        """Check parsing of condition with == and >"""
        parsed = await parser.parse_condition_string("$event_type == 'message' and $user_id > 100")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

    @pytest.mark.asyncio
    async def test_parse_condition_string_without_equality(self, parser):
        """Check parsing of condition without == (only compiled_function)"""
        parsed = await parser.parse_condition_string("$user_id > 100")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

    @pytest.mark.asyncio
    async def test_parse_condition_string_complex_with_parentheses(self, parser):
        """Check parsing of complex condition with parentheses"""
        parsed = await parser.parse_condition_string("($event_type == 'message' or $event_type == 'callback') and $user_id > 100")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

