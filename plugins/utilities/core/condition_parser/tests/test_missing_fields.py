"""
Тесты отсутствующих полей в data
"""
import pytest


class TestMissingFieldsComparison:
    """Тесты сравнения отсутствующих полей"""

    @pytest.mark.asyncio
    async def test_missing_field_equals_should_be_false(self, parser):
        """Проверка отсутствующего поля - должно быть False"""
        result = await parser.check_match("$field == 'value'", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_field_not_equals_should_be_true(self, parser):
        """Проверка отсутствующего поля - != должно быть True"""
        result = await parser.check_match("$field != 'value'", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_field_comparison_should_be_false(self, parser):
        """Проверка отсутствующего поля - сравнение должно быть False"""
        result = await parser.check_match("$field > 100", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_missing_field_equals_none_should_be_true(self, parser):
        """Проверка отсутствующего поля - == None должно быть True"""
        result = await parser.check_match("$field == None", {})
        assert result is True


class TestMissingFieldsNullOperators:
    """Тесты операторов is_null для отсутствующих полей"""

    @pytest.mark.asyncio
    async def test_missing_field_is_null_should_be_true(self, parser):
        """Проверка отсутствующего поля - is_null должно быть True"""
        result = await parser.check_match("$field is_null", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_field_not_is_null_should_be_false(self, parser):
        """Проверка отсутствующего поля - not is_null должно быть False"""
        result = await parser.check_match("$field not is_null", {})
        assert result is False


class TestMissingFieldsStringOperators:
    """Тесты строковых операторов для отсутствующих полей"""

    @pytest.mark.asyncio
    async def test_missing_field_contains_should_be_false(self, parser):
        """Проверка отсутствующего поля - ~ должно быть False"""
        result = await parser.check_match("$field ~ 'text'", {})
        assert result is False


class TestMissingFieldsListOperators:
    """Тесты операторов списков для отсутствующих полей"""

    @pytest.mark.asyncio
    async def test_missing_field_in_should_be_false(self, parser):
        """Проверка отсутствующего поля - in должно быть False"""
        result = await parser.check_match("$field in ['value']", {})
        assert result is False

