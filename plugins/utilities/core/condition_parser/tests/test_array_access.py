"""
Array access tests
"""
import pytest


class TestArrayAccessBasic:
    """Basic array access tests"""

    @pytest.mark.asyncio
    async def test_array_access_first_element(self, parser):
        """Check array element access - first element"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_first_element_not_equal(self, parser):
        """Check array element access - not equal"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": [{"type": "document"}]})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_empty_array(self, parser):
        """Check array element access - empty array"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": []})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_multiple_elements(self, parser):
        """Check array element access - multiple elements"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}, {"type": "document"}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_second_element(self, parser):
        """Check array element access - second element"""
        result = await parser.check_match("$event_attachment[1].type == 'document'", 
                                          {"event_attachment": [{"type": "photo"}, {"type": "document"}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_negative_index(self, parser):
        """Check array element access - negative index"""
        result = await parser.check_match("$event_attachment[-1].type == 'document'", 
                                          {"event_attachment": [{"type": "photo"}, {"type": "document"}]})
        assert result is True


class TestArrayAccessSimple:
    """Simple array access tests"""

    @pytest.mark.asyncio
    async def test_array_access_simple_element(self, parser):
        """Check simple array element access"""
        result = await parser.check_match("$items[0] == 10", {"items": [10, 20, 30]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_simple_element_second(self, parser):
        """Check simple array element access - second"""
        result = await parser.check_match("$items[1] == 20", {"items": [10, 20, 30]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_simple_element_not_equal(self, parser):
        """Check simple array element access - not equal"""
        result = await parser.check_match("$items[0] == 20", {"items": [10, 20, 30]})
        assert result is False


class TestArrayAccessNested:
    """Tests for accessing nested structures through arrays"""

    @pytest.mark.asyncio
    async def test_array_access_nested_field(self, parser):
        """Check access through array to nested field"""
        result = await parser.check_match("$users[0].profile.name == 'John'", 
                                          {"users": [{"profile": {"name": "John"}}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_through_object(self, parser):
        """Check access through object to array to field"""
        result = await parser.check_match("$data.items[0].value == 100", 
                                          {"data": {"items": [{"value": 100}]}})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_nested_array(self, parser):
        """Check nested array access"""
        result = await parser.check_match("$matrix[0][1] == 2", {"matrix": [[1, 2, 3], [4, 5, 6]]})
        assert result is True


class TestArrayAccessEdgeCases:
    """Edge case tests for array access"""

    @pytest.mark.asyncio
    async def test_array_access_missing_array(self, parser):
        """Check array access - array missing in data"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_index_out_of_bounds(self, parser):
        """Check array access - index out of bounds"""
        result = await parser.check_match("$event_attachment[10].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}]})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_negative_index_out_of_bounds(self, parser):
        """Check array access - negative index out of bounds"""
        result = await parser.check_match("$event_attachment[-10].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}]})
        assert result is False

