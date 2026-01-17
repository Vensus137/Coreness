"""
Тесты граничных случаев
"""
import pytest


class TestSimpleValues:
    """Тесты простых значений"""

    @pytest.mark.asyncio
    async def test_edge_case_simple_true(self, parser):
        """Проверка простого True"""
        result = await parser.check_match("True", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_simple_false(self, parser):
        """Проверка простого False"""
        result = await parser.check_match("False", {})
        assert result is False


class TestFieldEqualsItself:
    """Тесты сравнения поля с самим собой"""

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_string(self, parser):
        """Проверка сравнения поля с самим собой - строка"""
        result = await parser.check_match("$event_type == $event_type", {"event_type": "message"})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_number(self, parser):
        """Проверка сравнения числа с самим собой"""
        result = await parser.check_match("$user_id == $user_id", {"user_id": 123})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_none(self, parser):
        """Проверка сравнения None с самим собой"""
        result = await parser.check_match("$field == $field", {"field": None})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_empty_string(self, parser):
        """Проверка сравнения пустой строки с самой собой"""
        result = await parser.check_match("$field == $field", {"field": ""})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_zero(self, parser):
        """Проверка сравнения нуля с самим собой"""
        result = await parser.check_match("$field == $field", {"field": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_edge_case_field_equals_itself_false(self, parser):
        """Проверка сравнения False с самим собой"""
        result = await parser.check_match("$field == $field", {"field": False})
        assert result is True

