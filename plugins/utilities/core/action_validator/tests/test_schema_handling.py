"""
Tests for handling missing schemas
"""


class TestSchemaHandling:
    """Tests for schema handling"""

    def test_skip_validation_no_schema(self, validator):
        """Check validation skip: no schema"""
        result = validator.validate_action_input('test_service', 'action_no_schema', {'any': 'data'})
        assert result.get('result') == 'success'

    def test_skip_validation_unknown_service(self, validator):
        """Check validation skip: unknown service"""
        result = validator.validate_action_input('unknown_service', 'unknown_action', {'any': 'data'})
        assert result.get('result') == 'success'

