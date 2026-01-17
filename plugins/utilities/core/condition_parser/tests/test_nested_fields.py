"""
Тесты работы с вложенными полями
"""
import pytest


class TestNestedFields:
    """Тесты вложенных полей"""

    @pytest.mark.asyncio
    async def test_nested_field_one_level(self, parser):
        """Проверка вложенного поля - один уровень"""
        result = await parser.check_match("$message.text == 'hello'", {"message": {"text": "hello"}})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_field_one_level_not_equal(self, parser):
        """Проверка вложенного поля - не равно"""
        result = await parser.check_match("$message.text == 'hello'", {"message": {"text": "world"}})
        assert result is False

    @pytest.mark.asyncio
    async def test_nested_field_two_levels(self, parser):
        """Проверка вложенного поля - два уровня"""
        result = await parser.check_match("$user.profile.name == 'John'", 
                                          {"user": {"profile": {"name": "John"}}})
        assert result is True

    @pytest.mark.asyncio
    async def test_nested_field_missing(self, parser):
        """Проверка вложенного поля - отсутствует"""
        result = await parser.check_match("$message.text == 'hello'", {"message": {}})
        assert result is False

