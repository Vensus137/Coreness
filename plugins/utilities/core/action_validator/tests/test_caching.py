"""
Tests for validation model caching
"""


class TestCaching:
    """Caching tests"""

    def test_caching(self, validator):
        """Check that validation works correctly on repeated calls (caching)"""
        # First call
        result1 = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test'})
        assert result1.get('result') == 'success', "First call should be successful"
        
        # Second call with different data (should use model cache, but this is implementation detail)
        result2 = validator.validate_action_input('test_service', 'simple_action', {'name': 'Test2'})
        assert result2.get('result') == 'success', "Second call should be successful"
        
        # Third call with invalid data
        result3 = validator.validate_action_input('test_service', 'simple_action', {})
        assert result3.get('result') == 'error', "Call without required fields should return error"

