"""
Тесты парсинга условий
"""
import pytest


class TestParseConditionString:
    """Тесты метода parse_condition_string"""

    @pytest.mark.asyncio
    async def test_parse_condition_string_simple(self, parser):
        """Проверка парсинга простого условия с == для search_path"""
        parsed = await parser.parse_condition_string("$event_type == 'message'")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

    @pytest.mark.asyncio
    async def test_parse_condition_string_with_and(self, parser):
        """Проверка парсинга условия с == и >"""
        parsed = await parser.parse_condition_string("$event_type == 'message' and $user_id > 100")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

    @pytest.mark.asyncio
    async def test_parse_condition_string_without_equality(self, parser):
        """Проверка парсинга условия без == (только compiled_function)"""
        parsed = await parser.parse_condition_string("$user_id > 100")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

    @pytest.mark.asyncio
    async def test_parse_condition_string_complex_with_parentheses(self, parser):
        """Проверка парсинга сложного условия со скобками"""
        parsed = await parser.parse_condition_string("($event_type == 'message' or $event_type == 'callback') and $user_id > 100")
        assert 'search_path' in parsed and parsed['search_path'] is not None
        assert 'compiled_function' in parsed and parsed['compiled_function'] is not None
        assert 'condition_hash' in parsed and parsed['condition_hash'] is not None

