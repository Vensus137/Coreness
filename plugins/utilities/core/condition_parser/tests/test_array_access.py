"""
Тесты доступа к массивам
"""
import pytest


class TestArrayAccessBasic:
    """Тесты базового доступа к массивам"""

    @pytest.mark.asyncio
    async def test_array_access_first_element(self, parser):
        """Проверка доступа к элементу массива - первый элемент"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_first_element_not_equal(self, parser):
        """Проверка доступа к элементу массива - не равно"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": [{"type": "document"}]})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_empty_array(self, parser):
        """Проверка доступа к элементу массива - пустой массив"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": []})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_multiple_elements(self, parser):
        """Проверка доступа к элементу массива - несколько элементов"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}, {"type": "document"}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_second_element(self, parser):
        """Проверка доступа к элементу массива - второй элемент"""
        result = await parser.check_match("$event_attachment[1].type == 'document'", 
                                          {"event_attachment": [{"type": "photo"}, {"type": "document"}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_negative_index(self, parser):
        """Проверка доступа к элементу массива - отрицательный индекс"""
        result = await parser.check_match("$event_attachment[-1].type == 'document'", 
                                          {"event_attachment": [{"type": "photo"}, {"type": "document"}]})
        assert result is True


class TestArrayAccessSimple:
    """Тесты доступа к простым массивам"""

    @pytest.mark.asyncio
    async def test_array_access_simple_element(self, parser):
        """Проверка доступа к простому элементу массива"""
        result = await parser.check_match("$items[0] == 10", {"items": [10, 20, 30]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_simple_element_second(self, parser):
        """Проверка доступа к простому элементу массива - второй"""
        result = await parser.check_match("$items[1] == 20", {"items": [10, 20, 30]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_simple_element_not_equal(self, parser):
        """Проверка доступа к простому элементу массива - не равно"""
        result = await parser.check_match("$items[0] == 20", {"items": [10, 20, 30]})
        assert result is False


class TestArrayAccessNested:
    """Тесты доступа к вложенным структурам через массивы"""

    @pytest.mark.asyncio
    async def test_array_access_nested_field(self, parser):
        """Проверка доступа через массив к вложенному полю"""
        result = await parser.check_match("$users[0].profile.name == 'John'", 
                                          {"users": [{"profile": {"name": "John"}}]})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_through_object(self, parser):
        """Проверка доступа через объект к массиву к полю"""
        result = await parser.check_match("$data.items[0].value == 100", 
                                          {"data": {"items": [{"value": 100}]}})
        assert result is True

    @pytest.mark.asyncio
    async def test_array_access_nested_array(self, parser):
        """Проверка доступа к вложенному массиву"""
        result = await parser.check_match("$matrix[0][1] == 2", {"matrix": [[1, 2, 3], [4, 5, 6]]})
        assert result is True


class TestArrayAccessEdgeCases:
    """Тесты граничных случаев доступа к массивам"""

    @pytest.mark.asyncio
    async def test_array_access_missing_array(self, parser):
        """Проверка доступа к массиву - массив отсутствует в данных"""
        result = await parser.check_match("$event_attachment[0].type == 'photo'", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_index_out_of_bounds(self, parser):
        """Проверка доступа к массиву - индекс вне границ"""
        result = await parser.check_match("$event_attachment[10].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}]})
        assert result is False

    @pytest.mark.asyncio
    async def test_array_access_negative_index_out_of_bounds(self, parser):
        """Проверка доступа к массиву - отрицательный индекс вне границ"""
        result = await parser.check_match("$event_attachment[-10].type == 'photo'", 
                                          {"event_attachment": [{"type": "photo"}]})
        assert result is False

