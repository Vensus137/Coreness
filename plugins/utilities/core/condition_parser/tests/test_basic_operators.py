"""
Тесты базовых операторов сравнения (==, !=, >, <, >=, <=)
"""
import pytest


class TestEqualityOperators:
    """Тесты оператора равенства (==)"""

    @pytest.mark.asyncio
    async def test_equality_string_operator(self, parser):
        """Проверка оператора равенства для строк"""
        result = await parser.check_match("$event_type == 'message'", {"event_type": "message"})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_string_operator_not_equal(self, parser):
        """Проверка оператора равенства для строк - не равно"""
        result = await parser.check_match("$event_type == 'message'", {"event_type": "callback"})
        assert result is False

    @pytest.mark.asyncio
    async def test_equality_number_operator(self, parser):
        """Проверка оператора равенства для чисел"""
        result = await parser.check_match("$user_id == 123", {"user_id": 123})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_number_operator_not_equal(self, parser):
        """Проверка оператора равенства для чисел - не равно"""
        result = await parser.check_match("$user_id == 123", {"user_id": 456})
        assert result is False

    @pytest.mark.asyncio
    async def test_equality_boolean_true_operator(self, parser):
        """Проверка оператора равенства для boolean True"""
        result = await parser.check_match("$is_active == True", {"is_active": True})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_boolean_false_operator(self, parser):
        """Проверка оператора равенства для boolean False"""
        result = await parser.check_match("$is_active == False", {"is_active": False})
        assert result is True

    @pytest.mark.asyncio
    async def test_equality_none_operator(self, parser):
        """Проверка оператора равенства для None"""
        result = await parser.check_match("$field == None", {"field": None})
        assert result is True


class TestInequalityOperators:
    """Тесты оператора неравенства (!=)"""

    @pytest.mark.asyncio
    async def test_inequality_operator(self, parser):
        """Проверка оператора неравенства"""
        result = await parser.check_match("$event_type != 'message'", {"event_type": "callback"})
        assert result is True

    @pytest.mark.asyncio
    async def test_inequality_operator_equal(self, parser):
        """Проверка оператора неравенства - равно"""
        result = await parser.check_match("$event_type != 'message'", {"event_type": "message"})
        assert result is False

    @pytest.mark.asyncio
    async def test_inequality_number_operator(self, parser):
        """Проверка оператора неравенства для чисел"""
        result = await parser.check_match("$user_id != 123", {"user_id": 456})
        assert result is True


class TestComparisonOperators:
    """Тесты операторов сравнения (>, <, >=, <=)"""

    @pytest.mark.asyncio
    async def test_greater_than_operator(self, parser):
        """Проверка оператора больше"""
        result = await parser.check_match("$user_id > 100", {"user_id": 150})
        assert result is True

    @pytest.mark.asyncio
    async def test_greater_than_operator_less(self, parser):
        """Проверка оператора больше - меньше"""
        result = await parser.check_match("$user_id > 100", {"user_id": 50})
        assert result is False

    @pytest.mark.asyncio
    async def test_less_than_operator(self, parser):
        """Проверка оператора меньше"""
        result = await parser.check_match("$user_id < 100", {"user_id": 50})
        assert result is True

    @pytest.mark.asyncio
    async def test_greater_or_equal_operator(self, parser):
        """Проверка оператора больше или равно"""
        result = await parser.check_match("$user_id >= 100", {"user_id": 100})
        assert result is True

    @pytest.mark.asyncio
    async def test_less_or_equal_operator(self, parser):
        """Проверка оператора меньше или равно"""
        result = await parser.check_match("$user_id <= 100", {"user_id": 100})
        assert result is True

