"""
Date comparison tests in conditions
Checks correct handling of dates in dd.mm.yyyy format (after placeholder expansion)
"""
import pytest


class TestDateComparison:
    """Tests for date comparison in dd.mm.yyyy format"""

    @pytest.mark.asyncio
    async def test_date_equals_date_without_quotes(self, parser):
        """
        Check date comparison without quotes (as after placeholder expansion)
        Condition: "02.12.2012 == 02.12.2012" (after placeholder expansion)
        Expected: True (string comparison)
        """
        # Simulate condition after placeholder expansion
        # In real case: condition = "{_cache.last_fast_prediction.last_prediction_date} == {event_date|format:date}"
        # After expansion: "02.12.2012 == 02.12.2012"
        result = await parser.check_match("02.12.2012 == 02.12.2012", {})
        assert result is True, "Dates should be compared as strings and be equal"

    @pytest.mark.asyncio
    async def test_date_equals_date_from_field(self, parser):
        """
        Check date from field comparison with date without quotes
        Simulates real case: {_cache.last_fast_prediction.last_prediction_date} == {event_date|format:date}
        """
        result = await parser.check_match("$date_field == 02.12.2012", {"date_field": "02.12.2012"})
        assert result is True, "Date from field should be compared with date string"

    @pytest.mark.asyncio
    async def test_date_not_equals_different_date(self, parser):
        """
        Check != operator for different dates
        """
        result = await parser.check_match("02.12.2012 != 03.12.2012", {})
        assert result is True, "Different dates should be not equal"

    @pytest.mark.asyncio
    async def test_datetime_format(self, parser):
        """
        Check date comparison with time (format:datetime)
        """
        result = await parser.check_match("25.12.2024 15:30 == 25.12.2024 15:30", {})
        assert result is True, "Dates with time should be compared as strings"

    @pytest.mark.asyncio
    async def test_datetime_full_format(self, parser):
        """
        Check date comparison with full time (format:datetime_full)
        """
        result = await parser.check_match("25.12.2024 15:30:45 == 25.12.2024 15:30:45", {})
        assert result is True, "Dates with full time should be compared as strings"

    @pytest.mark.asyncio
    async def test_ip_address_comparison(self, parser):
        """
        Check IP address comparison (universal solution should work for them too)
        """
        result = await parser.check_match("192.168.1.1 == 192.168.1.1", {})
        assert result is True, "IP addresses should be compared as strings"

    @pytest.mark.asyncio
    async def test_version_comparison(self, parser):
        """
        Check version comparison (universal solution should work for them too)
        """
        result = await parser.check_match("1.2.3.4 == 1.2.3.4", {})
        assert result is True, "Versions should be compared as strings"

