"""
Edge case tests for PlaceholderProcessor
Tests 13, 25: Edge cases
"""

from conftest import assert_equal


def test_edge_cases(processor):
    """Test 13: Edge cases"""
    values_dict = {
        'empty': '',
        'zero': 0,
        'false': False,
        'none': None,
        'empty_list': [],
        'empty_dict': {},
    }
    
    # Empty string
    result = processor.process_text_placeholders("{empty}", values_dict)
    assert_equal(result, "", "Empty string")
    
    # Zero
    result = processor.process_text_placeholders("{zero}", values_dict)
    assert_equal(result, 0, "Zero")
    
    # False
    result = processor.process_text_placeholders("{false}", values_dict)
    assert_equal(result, False, "False")
    
    # None
    result = processor.process_text_placeholders("{none}", values_dict)
    assert "{none}" in str(result), "None returns placeholder"
    
    # Empty list (process_text_placeholders returns string representation)
    result = processor.process_text_placeholders("{empty_list}", values_dict)
    assert result == "[]", "Empty list returned as string"
    
    # Empty dictionary (process_text_placeholders returns string representation)
    result = processor.process_text_placeholders("{empty_dict}", values_dict)
    assert result == "{}", "Empty dictionary returned as string"
    
    # Empty placeholder
    result = processor.process_text_placeholders("{}", values_dict)
    # Just check it doesn't crash
    assert result is not None, "Empty placeholder"
    
    # Only opening brace
    result = processor.process_text_placeholders("{", values_dict)
    assert_equal(result, "{", "Only opening brace")
    
    # Only closing brace
    result = processor.process_text_placeholders("}", values_dict)
    assert_equal(result, "}", "Only closing brace")
    
    # Text without placeholders
    result = processor.process_text_placeholders("Just text", values_dict)
    assert_equal(result, "Just text", "Text without placeholders")


def test_edge_cases_advanced(processor):
    """Test 25: Advanced edge cases"""
    # Very long modifier chain
    values_dict = {
        'text': 'hello world',
    }
    result = processor.process_text_placeholders("{text|upper|truncate:5|code}", values_dict)
    assert "<code>" in result, "Very long modifier chain"
    
    # Placeholder with multiple nesting
    values_dict2 = {
        'a': 'field',
        'field': 'value',
        'value': 'final',
    }
    result = processor.process_text_placeholders("{{{{a}}}}", values_dict2)
    # Just check it doesn't crash
    assert result is not None, "Multiple nesting"
    
    # Empty placeholder with fallback
    result = processor.process_text_placeholders("{|fallback:default}", {})
    assert_equal(result, "default", "Empty placeholder with fallback")
    
    # Placeholder with only modifiers without field
    result = processor.process_text_placeholders("{|upper}", {})
    # Just check it doesn't crash
    assert result is not None, "Placeholder with only modifiers"
    
    # Special characters in values
    values_dict3 = {
        'text': 'Hello "world" & <tags>',
    }
    result = processor.process_text_placeholders("{text|code}", values_dict3)
    assert "<code>" in result, "Special characters in values"
    
    # Very large number
    values_dict4 = {
        'big_number': 999999999999,
    }
    result = processor.process_text_placeholders("{big_number|format:number}", values_dict4)
    assert isinstance(result, str), "Very large number is formatted"
    
    # Negative numbers
    values_dict5 = {
        'negative': -100,
    }
    result = processor.process_text_placeholders("{negative|abs}", values_dict5)
    # abs may not be a modifier, check it doesn't crash
    assert result is not None, "Negative numbers"
    
    # Unicode characters
    values_dict6 = {
        'unicode': 'Hello 世界 🌍',
    }
    result = processor.process_text_placeholders("{unicode|upper}", values_dict6)
    assert "HELLO" in result, "Unicode characters are processed"

