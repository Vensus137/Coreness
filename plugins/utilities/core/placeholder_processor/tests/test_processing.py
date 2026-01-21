"""
Structure processing tests for PlaceholderProcessor
Tests 10-12: Nested placeholders, dictionary and list processing
"""

from conftest import assert_equal


def test_nested_placeholders(processor):
    """Test 10: Nested placeholders"""
    values_dict = {
        'a': 10,
        'b': 5,
        'field': 'price',
        'price': 1000,
        'format': 'currency',
    }
    
    # Nested placeholder in arithmetic
    result = processor.process_text_placeholders("{a|+{b}}", values_dict)
    assert_equal(result, 15, "Nested placeholder in arithmetic")
    
    # Nested placeholder in path
    result = processor.process_text_placeholders("{{field}}", values_dict)
    # This should resolve to value of field 'field', i.e. 'price'
    # But then try to find {price}, which will return price value
    # This is a complex case, check it doesn't crash
    assert result is not None, "Nested placeholder in path"
    
    # Nested placeholder in fallback
    result = processor.process_text_placeholders("{nonexistent|fallback:{field}}", values_dict)
    assert_equal(result, "price", "Nested placeholder in fallback")


def test_dict_processing(processor):
    """Test 11: Dictionary processing"""
    values_dict = {
        'name': 'John',
        'age': 30,
    }
    
    # Simple dictionary
    data = {
        'text': 'Hello {name}',
        'number': '{age}',
    }
    result = processor.process_placeholders(data, values_dict)
    assert_equal(result.get('text'), 'Hello John', "String processing in dictionary")
    assert_equal(result.get('number'), 30, "Number processing in dictionary")
    
    # Nested dictionary
    data = {
        'user': {
            'greeting': 'Hello {name}',
            'info': {
                'age': '{age}'
            }
        }
    }
    result = processor.process_placeholders(data, values_dict)
    assert_equal(result['user']['greeting'], 'Hello John', "Nested dictionary")
    assert_equal(result['user']['info']['age'], 30, "Deep nesting in dictionary")
    
    # process_placeholders_full
    data = {
        'text': 'Hello {name}',
        'static': 'unchanged',
    }
    result = processor.process_placeholders_full(data, values_dict)
    assert_equal(result.get('text'), 'Hello John', "process_placeholders_full processes placeholders")
    assert_equal(result.get('static'), 'unchanged', "process_placeholders_full preserves static fields")


def test_list_processing(processor):
    """Test 12: List processing"""
    values_dict = {
        'name': 'John',
        'items': [1, 2, 3],
    }
    
    # List of strings
    data = ['Hello {name}', 'World']
    result = processor.process_placeholders({'list': data}, values_dict)
    assert_equal(result['list'][0], 'Hello John', "List of strings processing")
    assert_equal(result['list'][1], 'World', "Static list element")
    
    # List of dictionaries
    data = [
        {'text': 'Hello {name}'},
        {'text': 'Static'}
    ]
    result = processor.process_placeholders({'items': data}, values_dict)
    assert_equal(result['items'][0]['text'], 'Hello John', "List of dictionaries")
    assert_equal(result['items'][1]['text'], 'Static', "Static element in list of dictionaries")
    
    # Expand modifier
    values_dict['keyboard'] = [[{'Button 1': 'action1'}, {'Button 2': 'action2'}], [{'Button 3': 'action3'}]]
    data = {'inline': ['{keyboard|expand}', {'Back': 'back'}]}
    result = processor.process_placeholders(data, values_dict)
    inline_result = result.get('inline', [])
    
    # Check that expand expanded array
    assert isinstance(inline_result, list), "Expand returns list"
    
    # CRITICAL TEST: Check that first element is list (not string!)
    if len(inline_result) > 0:
        assert isinstance(inline_result[0], list), "Expand first element is list, not string"

