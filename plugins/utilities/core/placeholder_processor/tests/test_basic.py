"""
Basic PlaceholderProcessor tests
Tests 1-3: Basic placeholders, nesting, arrays
"""

from conftest import assert_equal


def test_basic_placeholders(processor):
    """Test 1: Basic placeholders"""
    values_dict = {
        'name': 'John',
        'age': 30,
        'active': True,
        'count': 0,
        'empty': '',
        'none': None,
    }
    
    # Simple replacement
    result = processor.process_text_placeholders("{name}", values_dict)
    assert_equal(result, "John", "Simple string replacement")
    
    result = processor.process_text_placeholders("{age}", values_dict)
    assert_equal(result, 30, "Simple number replacement")
    
    result = processor.process_text_placeholders("{active}", values_dict)
    assert_equal(result, True, "Simple boolean replacement")
    
    # Unresolved placeholder
    result = processor.process_text_placeholders("{nonexistent}", values_dict)
    assert "{nonexistent}" in str(result), "Unresolved placeholder returned as string"
    
    # Mixed text
    result = processor.process_text_placeholders("Hello {name}, age {age}", values_dict)
    assert result == "Hello John, age 30", "Mixed text"
    
    # Empty value
    result = processor.process_text_placeholders("{empty}", values_dict)
    assert_equal(result, "", "Empty value")
    
    # None value
    result = processor.process_text_placeholders("{none}", values_dict)
    assert "{none}" in str(result), "None value returns placeholder"
    
    # Zero
    result = processor.process_text_placeholders("{count}", values_dict)
    assert_equal(result, 0, "Zero as valid value")


def test_nested_access(processor):
    """Test 2: Dot notation and nested access"""
    values_dict = {
        'user': {
            'name': 'John',
            'profile': {
                'age': 30,
                'email': 'john@example.com',
                'settings': {
                    'theme': 'dark'
                }
            }
        },
        'data': {
            'items': [1, 2, 3],
            'meta': {
                'count': 42
            }
        }
    }
    
    # Simple dot notation
    result = processor.process_text_placeholders("{user.name}", values_dict)
    assert_equal(result, "John", "Simple dot notation")
    
    # Deep nesting
    result = processor.process_text_placeholders("{user.profile.age}", values_dict)
    assert_equal(result, 30, "Deep nesting")
    
    result = processor.process_text_placeholders("{user.profile.settings.theme}", values_dict)
    assert_equal(result, "dark", "Very deep nesting")
    
    # Non-existent path
    result = processor.process_text_placeholders("{user.nonexistent}", values_dict)
    assert "{user.nonexistent}" in str(result), "Non-existent path"
    
    # Nested access in dictionary
    result = processor.process_text_placeholders("{data.meta.count}", values_dict)
    assert_equal(result, 42, "Nested access in dictionary")


def test_array_access(processor):
    """Test 3: Array access"""
    values_dict = {
        'items': [10, 20, 30, 40, 50],
        'users': [
            {'name': 'John', 'id': 1},
            {'name': 'Jane', 'id': 2},
            {'name': 'Bob', 'id': 3}
        ],
        'matrix': [[1, 2], [3, 4]],
        'empty': [],
    }
    
    # Positive index
    result = processor.process_text_placeholders("{items[0]}", values_dict)
    assert_equal(result, 10, "Access by positive index")
    
    result = processor.process_text_placeholders("{items[2]}", values_dict)
    assert_equal(result, 30, "Access by middle index")
    
    # Negative index
    result = processor.process_text_placeholders("{items[-1]}", values_dict)
    assert_equal(result, 50, "Access by negative index (-1")
    
    result = processor.process_text_placeholders("{items[-2]}", values_dict)
    assert_equal(result, 40, "Access by negative index (-2")
    
    # Access to object field in array
    result = processor.process_text_placeholders("{users[0].name}", values_dict)
    assert_equal(result, "John", "Access to object field in array")
    
    result = processor.process_text_placeholders("{users[-1].id}", values_dict)
    assert_equal(result, 3, "Access to last object field")
    
    # Multiple indices
    result = processor.process_text_placeholders("{matrix[0][1]}", values_dict)
    assert_equal(result, 2, "Multiple indices")
    
    # Out of bounds
    result = processor.process_text_placeholders("{items[10]}", values_dict)
    assert "{items[10]}" in str(result), "Array out of bounds"
    
    # Empty array
    result = processor.process_text_placeholders("{empty[0]}", values_dict)
    assert "{empty[0]}" in str(result), "Access to empty array"

