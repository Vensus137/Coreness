"""
Тесты идентификаторов без кавычек (после разворачивания плейсхолдеров)
"""
import pytest


class TestIdentifiersWithoutQuotes:
    """Тесты идентификаторов без кавычек"""

    @pytest.mark.asyncio
    async def test_identifier_null_without_quotes(self, parser):
        """Проверка идентификатора null без кавычек"""
        result = await parser.check_match('null == "null"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_none_without_quotes(self, parser):
        """Проверка идентификатора none без кавычек"""
        result = await parser.check_match('none == "none"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_text_without_quotes(self, parser):
        """Проверка идентификатора text без кавычек"""
        result = await parser.check_match('text == "text"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_both_sides_without_quotes(self, parser):
        """Проверка идентификаторов с обеих сторон без кавычек"""
        result = await parser.check_match('null == null', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_with_field_marker(self, parser):
        """Проверка идентификатора с маркером поля"""
        result = await parser.check_match('$field == value', {"field": "value"})
        assert result is True

    @pytest.mark.asyncio
    async def test_identifier_with_field_marker_not_equal(self, parser):
        """Проверка идентификатора с маркером поля - не равно"""
        result = await parser.check_match('$field == value', {"field": "other"})
        assert result is False

    @pytest.mark.asyncio
    async def test_identifier_null_with_field_marker(self, parser):
        """Проверка идентификатора null с маркером поля"""
        # null без кавычек интерпретируется как строка "null", а не как None
        result = await parser.check_match('$field == null', {"field": None})
        assert result is False  # None != "null"

    @pytest.mark.asyncio
    async def test_identifier_complex_condition(self, parser):
        """Проверка сложного условия с идентификаторами"""
        result = await parser.check_match('null == "null" or none == "none"', {})
        assert result is True

