"""
Тесты граничных случаев с типами данных
"""
import pytest


class TestNumericTypes:
    """Тесты числовых типов"""

    @pytest.mark.asyncio
    async def test_data_type_equals_zero(self, parser):
        """Проверка сравнения с нулем"""
        result = await parser.check_match("$value == 0", {"value": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_equals_zero_not_equal(self, parser):
        """Проверка сравнения с нулем - не равно"""
        result = await parser.check_match("$value == 0", {"value": 1})
        assert result is False

    @pytest.mark.asyncio
    async def test_data_type_greater_than_negative(self, parser):
        """Проверка сравнения с отрицательным числом"""
        result = await parser.check_match("$value > -1", {"value": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_int_equals_float(self, parser):
        """Проверка сравнения int с float (автопреобразование)"""
        result = await parser.check_match("$value == 0.0", {"value": 0})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_float_equals_int(self, parser):
        """Проверка сравнения float с int (автопреобразование)"""
        result = await parser.check_match("$value == 0", {"value": 0.0})
        assert result is True


class TestStringTypes:
    """Тесты строковых типов"""

    @pytest.mark.asyncio
    async def test_data_type_equals_empty_string(self, parser):
        """Проверка сравнения с пустой строкой"""
        result = await parser.check_match("$text == ''", {"text": ""})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_equals_empty_string_with_space(self, parser):
        """Проверка сравнения с пустой строкой - пробел"""
        result = await parser.check_match("$text == ''", {"text": " "})
        assert result is False

    @pytest.mark.asyncio
    async def test_data_type_contains_empty_string(self, parser):
        """Проверка содержит пустую строку (всегда True)"""
        result = await parser.check_match("$text ~ ''", {"text": "anything"})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_not_contains_empty_string(self, parser):
        """Проверка не содержит пустую строку (всегда False)"""
        result = await parser.check_match("$text !~ ''", {"text": "anything"})
        assert result is False


class TestBooleanTypes:
    """Тесты булевых типов"""

    @pytest.mark.asyncio
    async def test_data_type_boolean_true(self, parser):
        """Проверка Boolean True"""
        result = await parser.check_match("$flag == True", {"flag": True})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_boolean_false(self, parser):
        """Проверка Boolean False"""
        result = await parser.check_match("$flag == False", {"flag": False})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_boolean_true_lowercase(self, parser):
        """Проверка Boolean true (lowercase)"""
        result = await parser.check_match("$flag == true", {"flag": True})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_boolean_false_lowercase(self, parser):
        """Проверка Boolean false (lowercase)"""
        result = await parser.check_match("$flag == false", {"flag": False})
        assert result is True


class TestNoneType:
    """Тесты типа None"""

    @pytest.mark.asyncio
    async def test_data_type_equals_none(self, parser):
        """Проверка сравнения с None"""
        result = await parser.check_match("$field == None", {"field": None})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_not_equals_none(self, parser):
        """Проверка неравенства с None"""
        result = await parser.check_match("$field != None", {"field": None})
        assert result is False

    @pytest.mark.asyncio
    async def test_data_type_not_equals_none_has_value(self, parser):
        """Проверка неравенства с None - есть значение"""
        result = await parser.check_match("$field != None", {"field": "value"})
        assert result is True


class TestTypeConversion:
    """Тесты автоматического преобразования типов"""

    @pytest.mark.asyncio
    async def test_data_type_number_equals_string(self, parser):
        """Проверка сравнения числа со строкой (автопреобразование)"""
        result = await parser.check_match("$value == '123'", {"value": 123})
        assert result is True

    @pytest.mark.asyncio
    async def test_data_type_string_equals_number(self, parser):
        """Проверка сравнения строки с числом (автопреобразование)"""
        result = await parser.check_match("$value == 123", {"value": "123"})
        assert result is True

