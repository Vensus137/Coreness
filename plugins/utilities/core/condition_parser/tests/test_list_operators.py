"""
Тесты операторов списков (in, not in)
"""
import pytest


class TestInOperator:
    """Тесты оператора вхождения в список (in)"""

    @pytest.mark.asyncio
    async def test_list_in_operator(self, parser):
        """Проверка оператора вхождения в список (in)"""
        result = await parser.check_match("$role in ['admin', 'moderator']", {"role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_list_in_operator_not_in(self, parser):
        """Проверка оператора вхождения в список (in) - не входит"""
        result = await parser.check_match("$role in ['admin', 'moderator']", {"role": "user"})
        assert result is False

    @pytest.mark.asyncio
    async def test_list_in_operator_number(self, parser):
        """Проверка вхождения числа в список"""
        result = await parser.check_match("$user_id in [100, 200, 300]", {"user_id": 200})
        assert result is True

    @pytest.mark.asyncio
    async def test_list_in_operator_number_not_in(self, parser):
        """Проверка вхождения числа в список - не входит"""
        result = await parser.check_match("$user_id in [100, 200, 300]", {"user_id": 150})
        assert result is False


class TestNotInOperator:
    """Тесты оператора не входит в список (not in)"""

    @pytest.mark.asyncio
    async def test_list_not_in_operator(self, parser):
        """Проверка оператора не входит в список (not in)"""
        result = await parser.check_match("$role not in ['admin', 'moderator']", {"role": "user"})
        assert result is True

    @pytest.mark.asyncio
    async def test_list_not_in_operator_in(self, parser):
        """Проверка оператора не входит в список (not in) - входит"""
        result = await parser.check_match("$role not in ['admin', 'moderator']", {"role": "admin"})
        assert result is False

