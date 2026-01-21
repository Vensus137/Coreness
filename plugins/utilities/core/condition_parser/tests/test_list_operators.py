"""
Tests for list operators (in, not in)
"""
import pytest


class TestInOperator:
    """Tests for list membership operator (in)"""

    @pytest.mark.asyncio
    async def test_list_in_operator(self, parser):
        """Check list membership operator (in)"""
        result = await parser.check_match("$role in ['admin', 'moderator']", {"role": "admin"})
        assert result is True

    @pytest.mark.asyncio
    async def test_list_in_operator_not_in(self, parser):
        """Check list membership operator (in) - not in"""
        result = await parser.check_match("$role in ['admin', 'moderator']", {"role": "user"})
        assert result is False

    @pytest.mark.asyncio
    async def test_list_in_operator_number(self, parser):
        """Check number membership in list"""
        result = await parser.check_match("$user_id in [100, 200, 300]", {"user_id": 200})
        assert result is True

    @pytest.mark.asyncio
    async def test_list_in_operator_number_not_in(self, parser):
        """Check number membership in list - not in"""
        result = await parser.check_match("$user_id in [100, 200, 300]", {"user_id": 150})
        assert result is False


class TestNotInOperator:
    """Tests for not in list operator (not in)"""

    @pytest.mark.asyncio
    async def test_list_not_in_operator(self, parser):
        """Check not in list operator (not in)"""
        result = await parser.check_match("$role not in ['admin', 'moderator']", {"role": "user"})
        assert result is True

    @pytest.mark.asyncio
    async def test_list_not_in_operator_in(self, parser):
        """Check not in list operator (not in) - in"""
        result = await parser.check_match("$role not in ['admin', 'moderator']", {"role": "admin"})
        assert result is False

