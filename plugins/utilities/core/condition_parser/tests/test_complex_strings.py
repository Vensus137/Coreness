"""
Тесты для сложных строк с дефисами и специальными символами (токены, UUID и т.д.)
"""
import pytest


class TestComplexStrings:
    """Тесты для сложных строк с дефисами и специальными символами"""

    @pytest.mark.asyncio
    async def test_string_with_hyphens(self, parser):
        """Проверка строки с дефисами (токен OpenRouter)"""
        # Пример: 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
        token = "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"
        result = await parser.check_match(f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_colon(self, parser):
        """Проверка строки с двоеточием (формат токена: число:строка)"""
        token = "123:abc-def-ghi"
        result = await parser.check_match(f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_colon(self, parser):
        """Проверка строки с дефисами и двоеточием"""
        token = "123:sk-or-v1-token"
        result = await parser.check_match(f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_comparison(self, parser):
        """Проверка сравнения строки с дефисами"""
        token = "sk-or-v1-token"
        result = await parser.check_match(f'{token} == "sk-or-v1-token"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_not_equal(self, parser):
        """Проверка неравенства строки с дефисами"""
        token = "sk-or-v1-token"
        result = await parser.check_match(f'{token} == "other-token"', {})
        assert result is False

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_field(self, parser):
        """Проверка сравнения строки с дефисами с полем"""
        token = "sk-or-v1-token"
        result = await parser.check_match(f'$field == {token}', {"field": token})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_condition(self, parser):
        """Проверка условия с or для строк с дефисами"""
        token1 = "sk-or-v1-token"
        token2 = "sk-or-v2-token"
        result = await parser.check_match(f'{token1} == "{token1}" or {token2} == "{token2}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_condition(self, parser):
        """Проверка условия с and для строк с дефисами"""
        token = "sk-or-v1-token"
        result = await parser.check_match(f'{token} == "{token}" and "test" == "test"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_lowercase_comparison(self, parser):
        """Проверка сравнения строки с дефисами после lower (как в реальном сценарии)"""
        # Симулируем ситуацию из сценария: {event_text|lower} == "null"
        # После раскрытия плейсхолдера может быть: sk-or-v1-token == "null"
        token = "sk-or-v1-token"
        result = await parser.check_match(f'{token} == "null"', {})
        assert result is False  # sk-or-v1-token != "null"

    @pytest.mark.asyncio
    async def test_string_with_hyphens_lowercase_none_comparison(self, parser):
        """Проверка сравнения строки с дефисами с none (как в реальном сценарии)"""
        token = "sk-or-v1-token"
        result = await parser.check_match(f'{token} == "none"', {})
        assert result is False  # sk-or-v1-token != "none"

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_null_none(self, parser):
        """Проверка условия or null or none для строки с дефисами (как в реальном сценарии)"""
        # Симулируем: {event_text|lower} == "null" or {event_text|lower} == "none"
        # После раскрытия: sk-or-v1-token == "null" or sk-or-v1-token == "none"
        token = "sk-or-v1-token"
        result = await parser.check_match(f'{token} == "null" or {token} == "none"', {})
        assert result is False  # Оба условия false

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_null_none_true(self, parser):
        """Проверка условия or null or none для строки null (должно быть true)"""
        token = "null"
        result = await parser.check_match(f'{token} == "null" or {token} == "none"', {})
        assert result is True  # Первое условие true

    @pytest.mark.asyncio
    async def test_string_with_hyphens_or_null_none_true_none(self, parser):
        """Проверка условия or null or none для строки none (должно быть true)"""
        token = "none"
        result = await parser.check_match(f'{token} == "null" or {token} == "none"', {})
        assert result is True  # Второе условие true

    @pytest.mark.asyncio
    async def test_uuid_like_string(self, parser):
        """Проверка UUID-подобной строки с дефисами"""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        result = await parser.check_match(f'{uuid} == "{uuid}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_multiple_hyphens(self, parser):
        """Проверка строки с множественными дефисами"""
        token = "a-b-c-d-e-f-g"
        result = await parser.check_match(f'{token} == "{token}"', {})
        assert result is True

    @pytest.mark.asyncio
    async def test_string_with_hyphens_and_numbers(self, parser):
        """Проверка строки с дефисами и числами"""
        token = "token-123-456-789"
        result = await parser.check_match(f'{token} == "{token}"', {})
        assert result is True

