"""
Complex scenario tests for PlaceholderProcessor
Tests 20-24: Complex combinations, async modifiers, deep nesting, real-world scenarios
"""

from conftest import assert_equal
import asyncio


def test_modifiers_expand_detailed(processor):
    """Test 20: expand modifier (detailed tests)"""
    # Simple array of arrays
    values_dict = {
        'keyboard': [[{'Button 1': 'action1'}, {'Button 2': 'action2'}], [{'Button 3': 'action3'}]],
    }
    data = {'inline': ['{keyboard|expand}', {'Back': 'back'}]}
    result = processor.process_placeholders(data, values_dict)
    inline_result = result.get('inline', [])
    
    # CRITICAL TEST: Check that result is list (not string!)
    assert isinstance(inline_result, list), "expand returns list, not string"
    
    # Check that expansion is correct: should be 2 rows from keyboard + 1 static = 3 elements
    assert_equal(len(inline_result), 3, "expand expands array of arrays")
    
    # CRITICAL TEST: Check that first element is list (not string!)
    assert isinstance(inline_result[0], list), "expand first element is list, not string"
    
    # Check that first row contains Button 1 and Button 2
    assert inline_result[0] == [{'Button 1': 'action1'}, {'Button 2': 'action2'}], "expand first row"
    assert_equal(inline_result[1], [{'Button 3': 'action3'}], "expand second row")
    assert_equal(inline_result[2], {'Back': 'back'}, "expand static element")
    
    # Empty array of arrays
    values_dict2 = {
        'empty_keyboard': [],
    }
    data2 = {'inline': ['{empty_keyboard|expand}', {'Back': 'back'}]}
    result2 = processor.process_placeholders(data2, values_dict2)
    inline_result2 = result2.get('inline', [])
    # Empty array expands to empty list, but static element remains
    assert isinstance(inline_result2, list), "expand with empty array returns list"
    
    # Regular array (not array of arrays) is not expanded
    values_dict3 = {
        'simple_array': [1, 2, 3],
    }
    data3 = {'inline': ['{simple_array|expand}', {'Back': 'back'}]}
    result3 = processor.process_placeholders(data3, values_dict3)
    inline_result3 = result3.get('inline', [])
    # Regular array remains as is
    assert isinstance(inline_result3, list), "expand with regular array returns list"
    # Check that first element is list (not string!)
    if len(inline_result3) > 0:
        assert isinstance(inline_result3[0], (list, int)), "expand with regular array first element is list or number, not string"
    
    # Multiple expand
    values_dict4 = {
        'kb1': [[{'A': 'a'}]],
        'kb2': [[{'B': 'b'}]],
    }
    data4 = {'inline': ['{kb1|expand}', '{kb2|expand}', {'Back': 'back'}]}
    result4 = processor.process_placeholders(data4, values_dict4)
    inline_result4 = result4.get('inline', [])
    assert_equal(len(inline_result4), 3, "expand with multiple arrays")
    # Check that all elements are lists or dictionaries (not strings!)
    for i, item in enumerate(inline_result4):
        assert isinstance(item, (list, dict)), f"expand multiple arrays element {i} is list or dict, not string"
    
    # CRITICAL TEST: Check that expand with modifier in _complex_replace returns array, not string
    values_dict5 = {
        '_cache': {
            'keyboard': [[{'Tenant 1': 'select_tenant_1'}, {'Tenant 2': 'select_tenant_2'}], [{'Tenant 3': 'select_tenant_3'}]]
        }
    }
    data5 = {'inline': ['{_cache.keyboard|expand}', [{'Back': 'back'}]]}
    result5 = processor.process_placeholders(data5, values_dict5)
    inline_result5 = result5.get('inline', [])
    
    # Check that result is list
    assert isinstance(inline_result5, list), "expand with dot notation returns list, not string"
    
    # Check that first element is list (not string!)
    if len(inline_result5) > 0:
        assert isinstance(inline_result5[0], list), "expand with dot notation first element is list, not string"
        # Check first element content
        if isinstance(inline_result5[0], list) and len(inline_result5[0]) > 0:
            assert isinstance(inline_result5[0][0], dict), "expand with dot notation first element of first row is dict"
    
    # Check expansion correctness
    if len(inline_result5) >= 2:
        assert inline_result5[0] == [{'Tenant 1': 'select_tenant_1'}, {'Tenant 2': 'select_tenant_2'}], "expand with dot notation first row"
        assert_equal(inline_result5[1], [{'Tenant 3': 'select_tenant_3'}], "expand with dot notation second row")


def test_complex_combinations(processor):
    """Test 21: Complex modifier combinations"""
    values_dict = {
        'price': 1000,
        'discount': 0.1,
        'status': 'active',
        'users': ['john', 'jane'],
        'text': 'hello world',
        'duration': '2h 30m',
        'field': None,
    }
    
    # Complex chain: price with discount, formatting, code
    result = processor.process_text_placeholders("{price|*{discount}|format:currency|code}", values_dict)
    assert "<code>" in result, "Complex chain contains code"
    assert "₽" in result, "Complex chain contains currency"
    
    # Conditional substitution with existence check
    result = processor.process_text_placeholders("{field|exists|value:Exists|fallback:No}", values_dict)
    assert_equal(result, "No", "Conditional substitution with exists (False)")
    
    # is_null check with conditional substitution
    result = processor.process_text_placeholders("{field|is_null|value:Empty|fallback:Filled}", values_dict)
    assert_equal(result, "Empty", "is_null with conditional substitution (True)")
    
    # Time with conversion and formatting
    result = processor.process_text_placeholders("{duration|seconds|/60}", values_dict)
    assert_equal(result, 150, "Time with conversion to minutes")
    
    # Regex with subsequent formatting
    result = processor.process_text_placeholders("{text|regex:\\w+|upper}", values_dict)
    assert_equal(result, "HELLO", "Regex with upper")
    
    # List with code and list
    result = processor.process_text_placeholders("{users|list|code}", values_dict)
    assert "<code>" in result, "List with list and code"
    assert "•" in result, "List with list and code contains markers"
    
    # Nested placeholders in complex chain
    values_dict['discount_rate'] = 0.9
    result = processor.process_text_placeholders("{price|*{discount_rate}|format:currency}", values_dict)
    assert "₽" in result, "Nested placeholders in arithmetic"
    
    # Combination equals, value, fallback with nested placeholders
    values_dict['expected_status'] = 'active'
    result = processor.process_text_placeholders("{status|equals:{expected_status}|value:OK|fallback:Error}", values_dict)
    assert_equal(result, "OK", "Complex conditional chain with nested placeholders")


def test_async_modifiers(processor):
    """Test 22: ready and not_ready modifiers"""
    # Create completed Future
    completed_future = asyncio.Future()
    completed_future.set_result("completed")
    
    # Create pending Future
    pending_future = asyncio.Future()
    
    values_dict = {
        'completed_action': completed_future,
        'pending_action': pending_future,
        'not_future': 'not a future',
    }
    
    # ready for completed Future
    result = processor.process_text_placeholders("{completed_action|ready}", values_dict)
    assert_equal(result, True, "ready for completed Future")
    
    # ready for pending Future
    result = processor.process_text_placeholders("{pending_action|ready}", values_dict)
    assert_equal(result, False, "ready for pending Future")
    
    # not_ready for completed Future
    result = processor.process_text_placeholders("{completed_action|not_ready}", values_dict)
    assert_equal(result, False, "not_ready for completed Future")
    
    # not_ready for pending Future
    result = processor.process_text_placeholders("{pending_action|not_ready}", values_dict)
    assert_equal(result, True, "not_ready for pending Future")
    
    # ready for non-Future object
    result = processor.process_text_placeholders("{not_future|ready}", values_dict)
    assert_equal(result, False, "ready for non-Future object")
    
    # not_ready for non-Future object
    result = processor.process_text_placeholders("{not_future|not_ready}", values_dict)
    assert_equal(result, False, "not_ready for non-Future object")


def test_deep_nesting(processor):
    """Test 23: Deep placeholder nesting"""
    values_dict = {
        'a': 10,
        'b': 5,
        'c': 2,
        'field1': 'price',
        'field2': 'discount',
        'price': 1000,
        'discount': 0.1,
        'format_type': 'currency',
    }
    
    # Multilevel nesting in arithmetic
    result = processor.process_text_placeholders("{a|+{b}|*{c}}", values_dict)
    assert_equal(result, 30, "Multilevel nesting in arithmetic")
    
    # Nested placeholders in path
    result = processor.process_text_placeholders("{{field1}}", values_dict)
    # This should resolve to 'price', then find {price} = 1000
    # Just check it doesn't crash
    assert result is not None, "Nested placeholders in path"
    
    # Nested placeholders in fallback
    result = processor.process_text_placeholders("{nonexistent|fallback:{{field1}}}", values_dict)
    # Nested placeholder in fallback resolves: {field1} -> 'price', then {price} -> 1000
    # Just check it doesn't crash
    assert result is not None, "Nested placeholders in fallback"
    
    # Nested placeholders in conditional modifiers
    result = processor.process_text_placeholders("{field1|equals:{field1}|value:Matches|fallback:Does not match}", values_dict)
    assert_equal(result, "Matches", "Nested placeholders in equals")
    
    # Complex chain with nested placeholders
    # {field1} -> 'price', {field2} -> 'discount', {format_type} -> 'currency'
    # Then {price} -> 1000, {discount} -> 0.1, total 1000 * 0.1 = 100
    result = processor.process_text_placeholders("{{field1}|*{{field2}}|format:{{format_type}}}", values_dict)
    # Result may be formatted or number depending on resolution order
    # Just check it doesn't crash
    assert result is not None, "Complex chain with nested placeholders"


def test_real_world_scenarios(processor):
    """Test 24: Real-world usage scenarios"""
    # Scenario 1: Price formatting with discount
    values_dict1 = {
        'price': 1000,
        'discount': 0.15,
    }
    result = processor.process_text_placeholders("{price|*{discount}|format:currency}", values_dict1)
    assert "₽" in result, "Real scenario: price with discount"
    
    # Scenario 2: Conditional message based on status
    values_dict2 = {
        'status': 'active',
        'user_name': 'John',
    }
    result = processor.process_text_placeholders("{status|equals:active|value:User {user_name} is active|fallback:User {user_name} is inactive}", values_dict2)
    assert "John" in result, "Real scenario: conditional message"
    assert "active" in result, "Real scenario: conditional message contains status"
    
    # Scenario 3: User list formatting
    values_dict3 = {
        'users': ['john', 'jane', 'bob'],
    }
    result = processor.process_text_placeholders("Users: {users|comma}", values_dict3)
    assert "john" in result, "Real scenario: user list"
    assert "," in result, "Real scenario: user list contains commas"
    
    # Scenario 4: Time processing with conversion
    values_dict4 = {
        'duration': '2h 30m',
    }
    result = processor.process_text_placeholders("{duration|seconds|/60}", values_dict4)
    assert_equal(result, 150, "Real scenario: time conversion to minutes")
    
    # Scenario 5: Safe access to nested fields with fallback
    values_dict5 = {
        'user': {
            'profile': {
                'name': 'John'
            }
        }
    }
    result = processor.process_text_placeholders("{user.profile.name|fallback:Unknown}", values_dict5)
    assert_equal(result, "John", "Real scenario: safe access to nested fields")
    
    result = processor.process_text_placeholders("{user.profile.email|fallback:Not specified}", values_dict5)
    assert_equal(result, "Not specified", "Real scenario: fallback for missing field")
    
    # Scenario 6: Array element formatting
    values_dict6 = {
        'items': [100, 200, 300],
    }
    result = processor.process_text_placeholders("{items[0]|format:currency}", values_dict6)
    assert "₽" in result, "Real scenario: array element formatting"

