"""
Тесты сравнения дат в условиях
Проверяет корректную обработку дат в формате dd.mm.yyyy (после разворачивания плейсхолдеров)
"""
import pytest


class TestDateComparison:
    """Тесты сравнения дат в формате dd.mm.yyyy"""

    @pytest.mark.asyncio
    async def test_date_equals_date_without_quotes(self, parser):
        """
        Проверка сравнения дат без кавычек (как после разворачивания плейсхолдеров)
        Условие: "02.12.2012 == 02.12.2012" (после разворачивания плейсхолдеров)
        Ожидается: True (строковое сравнение)
        """
        # Симулируем условие после разворачивания плейсхолдеров
        # В реальном случае: condition = "{_cache.last_fast_prediction.last_prediction_date} == {event_date|format:date}"
        # После разворачивания: "02.12.2012 == 02.12.2012"
        result = await parser.check_match("02.12.2012 == 02.12.2012", {})
        assert result is True, "Даты должны сравниваться как строки и быть равными"

    @pytest.mark.asyncio
    async def test_date_equals_date_from_field(self, parser):
        """
        Проверка сравнения даты из поля с датой без кавычек
        Симулирует реальный случай: {_cache.last_fast_prediction.last_prediction_date} == {event_date|format:date}
        """
        result = await parser.check_match("$date_field == 02.12.2012", {"date_field": "02.12.2012"})
        assert result is True, "Дата из поля должна сравниваться со строкой даты"

    @pytest.mark.asyncio
    async def test_date_not_equals_different_date(self, parser):
        """
        Проверка оператора != для разных дат
        """
        result = await parser.check_match("02.12.2012 != 03.12.2012", {})
        assert result is True, "Разные даты должны быть не равны"

    @pytest.mark.asyncio
    async def test_datetime_format(self, parser):
        """
        Проверка сравнения дат с временем (format:datetime)
        """
        result = await parser.check_match("25.12.2024 15:30 == 25.12.2024 15:30", {})
        assert result is True, "Даты с временем должны сравниваться как строки"

    @pytest.mark.asyncio
    async def test_datetime_full_format(self, parser):
        """
        Проверка сравнения дат с полным временем (format:datetime_full)
        """
        result = await parser.check_match("25.12.2024 15:30:45 == 25.12.2024 15:30:45", {})
        assert result is True, "Даты с полным временем должны сравниваться как строки"

    @pytest.mark.asyncio
    async def test_ip_address_comparison(self, parser):
        """
        Проверка сравнения IP-адресов (универсальное решение должно работать и для них)
        """
        result = await parser.check_match("192.168.1.1 == 192.168.1.1", {})
        assert result is True, "IP-адреса должны сравниваться как строки"

    @pytest.mark.asyncio
    async def test_version_comparison(self, parser):
        """
        Проверка сравнения версий (универсальное решение должно работать и для них)
        """
        result = await parser.check_match("1.2.3.4 == 1.2.3.4", {})
        assert result is True, "Версии должны сравниваться как строки"

