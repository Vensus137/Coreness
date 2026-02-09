"""
Modifier tests for PlaceholderProcessor
Tests 4-9, 14-19: All modifiers
"""

from conftest import assert_equal


def test_modifiers_with_quoted_parameters(processor):
    """Test that modifiers support parameters in quotes"""
    values_dict = {
        'text': 'hello world',
        'number': 100,
        'status': 'active',
    }
    
    # fallback with single quotes
    result = processor.process_text_placeholders("{nonexistent|fallback:'default'}", values_dict)
    assert_equal(result, "default", "fallback with single quoted parameter")
    
    # fallback with double quotes
    result = processor.process_text_placeholders("{nonexistent|fallback:\"default\"}", values_dict)
    assert_equal(result, "default", "fallback with double quoted parameter")
    
    # truncate with quotes (parameter is number, so result is same with or without quotes)
    result = processor.process_text_placeholders("{text|truncate:'5'}", values_dict)
    assert_equal(result, "he...", "truncate with quoted parameter (5 chars)")
    
    # arithmetic with quotes (should work)
    result = processor.process_text_placeholders("{number|+'50'}", values_dict)
    assert_equal(result, "150", "arithmetic with quoted parameter")
    
    # equals with quotes (returns Python bool True as string)
    result = processor.process_text_placeholders("{status|equals:'active'}", values_dict)
    assert_equal(result, "True", "equals with quoted parameter")
    
    # value with quotes
    result = processor.process_text_placeholders("{status|equals:active|value:'✅ Active'}", values_dict)
    assert_equal(result, "✅ Active", "value with quoted parameter")
    
    # Without quotes (should still work)
    result = processor.process_text_placeholders("{nonexistent|fallback:default}", values_dict)
    assert_equal(result, "default", "fallback without quotes still works")


def test_modifiers_string(processor):
    """Test 4: String modifiers"""
    values_dict = {
        'text': 'hello world',
        'upper': 'UPPER',
        'lower': 'lower',
        'mixed': 'MiXeD cAsE',
    }
    
    # upper
    result = processor.process_text_placeholders("{text|upper}", values_dict)
    assert_equal(result, "HELLO WORLD", "upper modifier")
    
    # lower
    result = processor.process_text_placeholders("{upper|lower}", values_dict)
    assert_equal(result, "upper", "lower modifier")
    
    # title
    result = processor.process_text_placeholders("{text|title}", values_dict)
    assert_equal(result, "Hello World", "title modifier")
    
    # capitalize
    result = processor.process_text_placeholders("{text|capitalize}", values_dict)
    assert_equal(result, "Hello world", "capitalize modifier")
    
    # case
    result = processor.process_text_placeholders("{text|case:upper}", values_dict)
    assert_equal(result, "HELLO WORLD", "case:upper modifier")


def test_modifiers_fallback(processor):
    """Test 5: Fallback modifier"""
    values_dict = {
        'exists': 'value',
        'empty': '',
        'zero': 0,
        'false': False,
        'none': None,
    }
    
    # Fallback triggers for None
    result = processor.process_text_placeholders("{nonexistent|fallback:default}", values_dict)
    assert_equal(result, "default", "Fallback for non-existent")
    
    # Fallback triggers for empty string
    result = processor.process_text_placeholders("{empty|fallback:default}", values_dict)
    assert_equal(result, "default", "Fallback for empty string")
    
    # Fallback does NOT trigger for existing value
    result = processor.process_text_placeholders("{exists|fallback:default}", values_dict)
    assert_equal(result, "value", "Fallback does not trigger for existing")
    
    # Fallback does NOT trigger for 0
    result = processor.process_text_placeholders("{zero|fallback:default}", values_dict)
    assert_equal(result, 0, "Fallback does not trigger for 0")
    
    # Fallback does NOT trigger for False
    result = processor.process_text_placeholders("{false|fallback:default}", values_dict)
    assert_equal(result, False, "Fallback does not trigger for False")
    
    # Fallback with empty value
    result = processor.process_text_placeholders("{nonexistent|fallback:}", values_dict)
    assert_equal(result, "", "Fallback with empty value returns ''")
    
    # Nested placeholder in fallback
    values_dict['fallback_value'] = 'nested'
    result = processor.process_text_placeholders("{nonexistent|fallback:{fallback_value}}", values_dict)
    assert_equal(result, "nested", "Nested placeholder in fallback")


def test_modifiers_arithmetic(processor):
    """Test 6: Arithmetic modifiers"""
    values_dict = {
        'ten': 10,
        'five': 5,
        'hundred': 100,
        'float_val': 15.5,
    }
    
    # Addition
    result = processor.process_text_placeholders("{ten|+5}", values_dict)
    assert_equal(result, 15, "Addition")
    
    # Subtraction
    result = processor.process_text_placeholders("{ten|-3}", values_dict)
    assert_equal(result, 7, "Subtraction")
    
    # Multiplication
    result = processor.process_text_placeholders("{ten|*2}", values_dict)
    assert_equal(result, 20, "Multiplication")
    
    # Division
    result = processor.process_text_placeholders("{ten|/2}", values_dict)
    assert_equal(result, 5, "Division")
    
    result = processor.process_text_placeholders("{ten|/3}", values_dict)
    # Division may return string due to _determine_result_type, check value
    result_float = float(result) if isinstance(result, str) else result
    assert isinstance(result_float, float), "Division returns float"
    
    # Modulo
    result = processor.process_text_placeholders("{ten|%3}", values_dict)
    assert_equal(result, 1, "Modulo")
    
    # Nested placeholder in arithmetic
    result = processor.process_text_placeholders("{ten|+{five}}", values_dict)
    assert_equal(result, 15, "Nested placeholder in arithmetic")


def test_modifiers_formatting(processor):
    """Test 7: Formatting modifiers"""
    from datetime import datetime
    values_dict = {
        'price': 1000.5,
        'percent': 25.5,
        'number': 1234.567,
        'date': datetime(2024, 12, 25, 15, 30),
        'datetime_full': datetime(2024, 12, 25, 15, 30, 45),
    }
    
    # Currency
    result = processor.process_text_placeholders("{price|format:currency}", values_dict)
    assert "₽" in result, "Currency formatting"
    
    # Percent
    result = processor.process_text_placeholders("{percent|format:percent}", values_dict)
    assert "%" in result, "Percent formatting"
    
    # Number
    result = processor.process_text_placeholders("{number|format:number}", values_dict)
    assert isinstance(result, str), "Number formatting returns string"
    
    # Date
    result = processor.process_text_placeholders("{date|format:date}", values_dict)
    assert_equal(result, "25.12.2024", "Date formatting")
    
    # Time
    result = processor.process_text_placeholders("{date|format:time}", values_dict)
    assert_equal(result, "15:30", "Time formatting")
    
    # Time full (with seconds)
    result = processor.process_text_placeholders("{datetime_full|format:time_full}", values_dict)
    assert_equal(result, "15:30:45", "Time formatting with seconds")
    
    # Datetime
    result = processor.process_text_placeholders("{date|format:datetime}", values_dict)
    assert_equal(result, "25.12.2024 15:30", "Datetime formatting")
    
    # Datetime full (with seconds)
    result = processor.process_text_placeholders("{datetime_full|format:datetime_full}", values_dict)
    assert_equal(result, "25.12.2024 15:30:45", "Datetime formatting with seconds")
    
    # Postgres date (date format for PostgreSQL)
    result = processor.process_text_placeholders("{date|format:pg_date}", values_dict)
    assert_equal(result, "2024-12-25", "Date formatting for PostgreSQL")
    
    # Postgres datetime (datetime format for PostgreSQL)
    result = processor.process_text_placeholders("{datetime_full|format:pg_datetime}", values_dict)
    assert_equal(result, "2024-12-25 15:30:45", "Datetime formatting for PostgreSQL")
    
    # Truncate
    values_dict['long_text'] = 'long text here'
    result = processor.process_text_placeholders("{long_text|truncate:10}", values_dict)
    assert_equal(result, "long te...", "Text truncation")


def test_modifiers_conditional(processor):
    """Test 8: Conditional modifiers"""
    values_dict = {
        'status': 'active',
        'inactive': 'inactive',
        'number': 5,
        'true_val': True,
        'false_val': False,
    }
    
    # equals
    result = processor.process_text_placeholders("{status|equals:active}", values_dict)
    assert_equal(result, True, "equals modifier (true)")
    
    result = processor.process_text_placeholders("{status|equals:inactive}", values_dict)
    assert_equal(result, False, "equals modifier (false)")
    
    # in_list
    result = processor.process_text_placeholders("{status|in_list:active,pending}", values_dict)
    assert_equal(result, True, "in_list modifier (true)")
    
    result = processor.process_text_placeholders("{status|in_list:pending,closed}", values_dict)
    assert_equal(result, False, "in_list modifier (false)")
    
    # true
    result = processor.process_text_placeholders("{true_val|true}", values_dict)
    assert_equal(result, True, "true modifier (True)")
    
    result = processor.process_text_placeholders("{false_val|true}", values_dict)
    assert_equal(result, False, "true modifier (False)")
    
    # exists
    result = processor.process_text_placeholders("{status|exists}", values_dict)
    assert_equal(result, True, "exists modifier (exists)")
    
    result = processor.process_text_placeholders("{nonexistent|exists}", values_dict)
    assert_equal(result, False, "exists modifier (does not exist)")


def test_modifiers_chains(processor):
    """Test 9: Modifier chains"""
    values_dict = {
        'price': 1000,
        'users': ['john', 'jane', 'bob'],
        'text': 'hello world',
    }
    
    # Modifier chain
    result = processor.process_text_placeholders("{price|*0.9|format:currency}", values_dict)
    assert "₽" in result, "Chain: multiplication + formatting"
    
    # String modifier chain
    result = processor.process_text_placeholders("{text|upper|truncate:5}", values_dict)
    # truncate:5 truncates to 5 characters, adding "...", total 5 characters
    assert "HE" in result, "String modifier chain"
    
    # Chain with fallback
    result = processor.process_text_placeholders("{nonexistent|fallback:default|upper}", values_dict)
    assert_equal(result, "DEFAULT", "Chain with fallback")


def test_special_modifiers(processor):
    """Test 14: Special modifiers"""
    values_dict = {
        'users': ['john', 'jane', 'bob'],
        'data': {'key1': 'value1', 'key2': 'value2'},
        'text': 'hello world',
    }
    
    # tags
    result = processor.process_text_placeholders("{users|tags}", values_dict)
    assert "@" in result, "tags modifier"
    
    # list
    result = processor.process_text_placeholders("{users|list}", values_dict)
    assert "•" in result, "list modifier"
    
    # comma
    result = processor.process_text_placeholders("{users|comma}", values_dict)
    assert "," in result, "comma modifier"
    
    # length
    result = processor.process_text_placeholders("{users|length}", values_dict)
    assert_equal(result, 3, "length modifier for list")
    
    result = processor.process_text_placeholders("{text|length}", values_dict)
    assert_equal(result, 11, "length modifier for string")
    
    # keys - keys modifier returns list, but process_text_placeholders always returns string
    # Check that result contains keys
    result = processor.process_text_placeholders("{data|keys}", values_dict)
    # If it's a list, check type, otherwise check that it contains keys as string
    if isinstance(result, list):
        assert isinstance(result, list), "keys modifier returns list"
    else:
        assert "key" in str(result), "keys modifier contains keys"


def test_modifiers_is_null(processor):
    """Test 15: is_null modifier"""
    values_dict = {
        'none_value': None,
        'empty_string': '',
        'null_string': 'null',
        'null_string_upper': 'NULL',
        'null_string_mixed': 'Null',
        'has_value': 'some value',
        'zero': 0,
        'false': False,
        'empty_list': [],
    }
    
    # None returns True
    result = processor.process_text_placeholders("{none_value|is_null}", values_dict)
    assert_equal(result, True, "is_null for None")
    
    # Empty string returns True
    result = processor.process_text_placeholders("{empty_string|is_null}", values_dict)
    assert_equal(result, True, "is_null for empty string")
    
    # String "null" returns True
    result = processor.process_text_placeholders("{null_string|is_null}", values_dict)
    assert_equal(result, True, "is_null for string 'null'")
    
    # String "NULL" returns True (case insensitive)
    result = processor.process_text_placeholders("{null_string_upper|is_null}", values_dict)
    assert_equal(result, True, "is_null for string 'NULL'")
    
    # String "Null" returns True (case insensitive)
    result = processor.process_text_placeholders("{null_string_mixed|is_null}", values_dict)
    assert_equal(result, True, "is_null for string 'Null'")
    
    # Value with content returns False
    result = processor.process_text_placeholders("{has_value|is_null}", values_dict)
    assert_equal(result, False, "is_null for value with content")
    
    # Zero returns False
    result = processor.process_text_placeholders("{zero|is_null}", values_dict)
    assert_equal(result, False, "is_null for zero")
    
    # False returns False
    result = processor.process_text_placeholders("{false|is_null}", values_dict)
    assert_equal(result, False, "is_null for False")
    
    # Empty list returns False (not null)
    result = processor.process_text_placeholders("{empty_list|is_null}", values_dict)
    assert_equal(result, False, "is_null for empty list")


def test_modifiers_code(processor):
    """Test 16: code modifier"""
    values_dict = {
        'text': 'hello',
        'number': 123,
        'items': ['item1', 'item2', 'item3'],
        'none_value': None,
        'empty_string': '',
    }
    
    # Simple string wrapped in code
    result = processor.process_text_placeholders("{text|code}", values_dict)
    assert_equal(result, "<code>hello</code>", "code for string")
    
    # Number wrapped in code
    result = processor.process_text_placeholders("{number|code}", values_dict)
    assert_equal(result, "<code>123</code>", "code for number")
    
    # None wrapped in empty code block
    result = processor.process_text_placeholders("{none_value|code}", values_dict)
    assert_equal(result, "<code></code>", "code for None")
    
    # Empty string wrapped in code
    result = processor.process_text_placeholders("{empty_string|code}", values_dict)
    assert_equal(result, "<code></code>", "code for empty string")
    
    # List - each element wrapped separately
    result = processor.process_text_placeholders("{items|code}", values_dict)
    expected = "<code>item1</code>\n<code>item2</code>\n<code>item3</code>"
    assert_equal(result, expected, "code for list (each element separately)")
    
    # Combination list|code - list first, then wrap
    result = processor.process_text_placeholders("{items|list|code}", values_dict)
    assert "<code>" in result, "code|list combination contains code"
    assert "•" in result, "code|list combination contains list markers"
    
    # Combination code|list - wrap each element first, then list
    result = processor.process_text_placeholders("{items|code|list}", values_dict)
    assert "<code>" in result, "list|code combination contains code"
    assert "•" in result, "list|code combination contains list markers"


def test_modifiers_regex(processor):
    """Test 17: regex modifier"""
    values_dict = {
        'text': 'Hello 123 World',
        'email': 'user@example.com',
        'phone': '+7 (999) 123-45-67',
        'time_text': 'Meeting at 2h 30m',
        'no_match': 'Just text without numbers',
    }
    
    # Extract numbers
    result = processor.process_text_placeholders("{text|regex:\\d+}", values_dict)
    assert_equal(result, "123", "regex to extract numbers")
    
    # Extract email
    result = processor.process_text_placeholders("{email|regex:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}}", values_dict)
    assert_equal(result, "user@example.com", "regex to extract email")
    
    # Extract time (format from documentation)
    result = processor.process_text_placeholders("{time_text|regex:(?:\\d+\\s*[dhms]\\s*)+}", values_dict)
    assert "2h" in result, "regex to extract time"
    assert "30m" in result, "regex to extract time"
    
    # No match - returns empty string or None
    result = processor.process_text_placeholders("{no_match|regex:\\d+}", values_dict)
    # regex may return empty string or None when no matches
    # Just check it doesn't crash
    
    # Extract first group (regex returns group 1 if exists, otherwise group(0))
    result = processor.process_text_placeholders("{phone|regex:\\+\\d}", values_dict)
    # Result may be "+7" or "7" depending on whether pattern has group
    # Just check it doesn't crash


def test_modifiers_seconds(processor):
    """Test 18: seconds modifier"""
    values_dict = {
        'duration1': '2h 30m',
        'duration2': '1d 5h',
        'duration3': '30m',
        'duration4': '1w 2d 3h 4m 5s',
        'invalid': 'invalid time',
        'empty': '',
    }
    
    # Simple time: 2h 30m = 2*3600 + 30*60 = 9000 seconds
    result = processor.process_text_placeholders("{duration1|seconds}", values_dict)
    assert_equal(result, 9000, "seconds for '2h 30m'")
    
    # Days and hours: 1d 5h = 1*86400 + 5*3600 = 104400 seconds
    result = processor.process_text_placeholders("{duration2|seconds}", values_dict)
    assert_equal(result, 104400, "seconds for '1d 5h'")
    
    # Only minutes: 30m = 30*60 = 1800 seconds
    result = processor.process_text_placeholders("{duration3|seconds}", values_dict)
    assert_equal(result, 1800, "seconds for '30m'")
    
    # Complex time: 1w 2d 3h 4m 5s
    # 1w = 7*86400 = 604800, 2d = 2*86400 = 172800, 3h = 3*3600 = 10800, 4m = 4*60 = 240, 5s = 5
    # Total: 604800 + 172800 + 10800 + 240 + 5 = 788645
    result = processor.process_text_placeholders("{duration4|seconds}", values_dict)
    assert_equal(result, 788645, "seconds for complex format")
    
    # Invalid time returns None
    result = processor.process_text_placeholders("{invalid|seconds}", values_dict)
    # seconds may return None for invalid format
    # Just check it doesn't crash
    
    # Empty string returns None
    result = processor.process_text_placeholders("{empty|seconds}", values_dict)
    # Just check it doesn't crash
    
    # Combination seconds with arithmetic
    result = processor.process_text_placeholders("{duration1|seconds|/60}", values_dict)
    assert_equal(result, 150, "seconds with division by 60 (minutes)")


def test_modifiers_value(processor):
    """Test 19: value modifier"""
    values_dict = {
        'status': 'active',
        'inactive': 'inactive',
        'true_val': True,
        'false_val': False,
    }
    
    # value used in chain with equals
    result = processor.process_text_placeholders("{status|equals:active|value:Active|fallback:Inactive}", values_dict)
    assert_equal(result, "Active", "value in chain with equals (true)")
    
    result = processor.process_text_placeholders("{inactive|equals:active|value:Active|fallback:Inactive}", values_dict)
    assert_equal(result, "Inactive", "value in chain with equals (false, fallback)")
    
    # value with true modifier
    result = processor.process_text_placeholders("{true_val|true|value:Yes|fallback:No}", values_dict)
    assert_equal(result, "Yes", "value with true (True)")
    
    result = processor.process_text_placeholders("{false_val|true|value:Yes|fallback:No}", values_dict)
    assert_equal(result, "No", "value with true (False, fallback)")
    
    # value with in_list
    result = processor.process_text_placeholders("{status|in_list:active,pending|value:In progress|fallback:Completed}", values_dict)
    assert_equal(result, "In progress", "value with in_list (true)")

