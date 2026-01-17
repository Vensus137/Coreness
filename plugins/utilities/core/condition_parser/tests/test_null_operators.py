"""
Тесты операторов is_null
"""
import pytest


class TestIsNullOperator:
    """Тесты оператора is_null"""

    @pytest.mark.asyncio
    async def test_is_null_operator_none(self, parser):
        """Проверка оператора is_null - None"""
        result = await parser.check_match("$field is_null", {"field": None})
        assert result is True

    @pytest.mark.asyncio
    async def test_is_null_operator_empty_string(self, parser):
        """Проверка оператора is_null - пустая строка"""
        result = await parser.check_match("$field is_null", {"field": ""})
        assert result is True

    @pytest.mark.asyncio
    async def test_is_null_operator_has_value(self, parser):
        """Проверка оператора is_null - есть значение"""
        result = await parser.check_match("$field is_null", {"field": "value"})
        assert result is False


class TestNotIsNullOperator:
    """Тесты оператора not is_null"""

    @pytest.mark.asyncio
    async def test_not_is_null_operator_has_value(self, parser):
        """Проверка оператора not is_null - есть значение"""
        result = await parser.check_match("$field not is_null", {"field": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_not_is_null_operator_none(self, parser):
        """Проверка оператора not is_null - None"""
        result = await parser.check_match("$field not is_null", {"field": None})
        assert result is False

    @pytest.mark.asyncio
    async def test_not_is_null_operator_empty_string(self, parser):
        """Проверка оператора not is_null - пустая строка"""
        result = await parser.check_match("$field not is_null", {"field": ""})
        assert result is False

