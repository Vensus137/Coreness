"""
Tests for literal values in quotes PlaceholderProcessor
Check all modifiers work with explicit values without values_dict
"""

from conftest import assert_equal


def test_literals_basic(processor):
    """Test basic literal values in quotes"""
    # Single quotes
    result = processor.process_text_placeholders("{'hello'}", {})
    assert_equal(result, "hello", "Literal in single quotes")
    
    # Double quotes
    result = processor.process_text_placeholders('{"world"}', {})
    assert_equal(result, "world", "Literal in double quotes")
    
    # Literal with spaces
    result = processor.process_text_placeholders("{'hello world'}", {})
    assert_equal(result, "hello world", "Literal with spaces")
    
    # Literal with digits
    result = processor.process_text_placeholders("{'123'}", {})
    assert_equal(result, "123", "Literal with digits")


def test_literals_string_modifiers(processor):
    """Test string modifiers with literals"""
    # upper
    result = processor.process_text_placeholders("{'hello'|upper}", {})
    assert_equal(result, "HELLO", "Literal with upper")
    
    # lower
    result = processor.process_text_placeholders("{'WORLD'|lower}", {})
    assert_equal(result, "world", "Literal with lower")
    
    # title
    result = processor.process_text_placeholders("{'hello world'|title}", {})
    assert_equal(result, "Hello World", "Literal with title")
    
    # capitalize
    result = processor.process_text_placeholders("{'hello world'|capitalize}", {})
    assert_equal(result, "Hello world", "Literal with capitalize")
    
    # case:upper
    result = processor.process_text_placeholders("{'test'|case:upper}", {})
    assert_equal(result, "TEST", "Literal with case:upper")


def test_literals_arithmetic_modifiers(processor):
    """Test arithmetic modifiers with literals"""
    # Addition
    result = processor.process_text_placeholders("{'100'|+50}", {})
    assert_equal(result, 150, "Literal with +50")
    
    # Subtraction
    result = processor.process_text_placeholders("{'100'|-30}", {})
    assert_equal(result, 70, "Literal with -30")
    
    # Multiplication
    result = processor.process_text_placeholders("{'10'|*5}", {})
    assert_equal(result, 50, "Literal with *5")
    
    # Division
    result = processor.process_text_placeholders("{'100'|/4}", {})
    assert_equal(result, 25, "Literal with /4")
    
    # Modulo
    result = processor.process_text_placeholders("{'10'|%3}", {})
    assert_equal(result, 1, "Literal with %3")


def test_literals_seconds_modifier(processor):
    """Test seconds modifier with literals"""
    # Simple time: 2h 30m = 2*3600 + 30*60 = 9000 seconds
    result = processor.process_text_placeholders("{'2h 30m'|seconds}", {})
    assert_equal(result, 9000, "Literal '2h 30m' -> seconds")
    
    # Days and weeks: 1d 2w = 1*86400 + 2*604800 = 1296000 seconds
    result = processor.process_text_placeholders("{'1d 2w'|seconds}", {})
    assert_equal(result, 1296000, "Literal '1d 2w' -> seconds")
    
    # Only minutes: 30m = 30*60 = 1800 seconds
    result = processor.process_text_placeholders("{'30m'|seconds}", {})
    assert_equal(result, 1800, "Literal '30m' -> seconds")
    
    # Complex time: 1w 2d 3h 4m 5s
    # 1w = 604800, 2d = 172800, 3h = 10800, 4m = 240, 5s = 5
    # Total: 788645
    result = processor.process_text_placeholders("{'1w 2d 3h 4m 5s'|seconds}", {})
    assert_equal(result, 788645, "Literal complex time -> seconds")


def test_literals_formatting_modifiers(processor):
    """Test formatting modifiers with literals"""
    # truncate
    result = processor.process_text_placeholders("{'long text here'|truncate:10}", {})
    assert_equal(result, "long te...", "Literal with truncate:10")
    
    # length
    result = processor.process_text_placeholders("{'hello world'|length}", {})
    assert_equal(result, 11, "Literal with length")
    
    # format:number
    result = processor.process_text_placeholders("{'1234.567'|format:number}", {})
    assert isinstance(result, str), "format:number returns string"
    assert "1234.5" in result, "Literal with format:number"
    
    # format:currency
    result = processor.process_text_placeholders("{'1000.5'|format:currency}", {})
    assert "₽" in result, "Literal with format:currency"
    
    # format:percent
    result = processor.process_text_placeholders("{'25.5'|format:percent}", {})
    assert "%" in result, "Literal with format:percent"


def test_literals_conditional_modifiers(processor):
    """Test conditional modifiers with literals"""
    # equals
    result = processor.process_text_placeholders("{'active'|equals:active}", {})
    assert_equal(result, True, "Literal with equals (true)")
    
    result = processor.process_text_placeholders("{'active'|equals:inactive}", {})
    assert_equal(result, False, "Literal with equals (false)")
    
    # in_list
    result = processor.process_text_placeholders("{'apple'|in_list:apple,orange,banana}", {})
    assert_equal(result, True, "Literal with in_list (true)")
    
    result = processor.process_text_placeholders("{'grape'|in_list:apple,orange,banana}", {})
    assert_equal(result, False, "Literal with in_list (false)")
    
    # exists
    result = processor.process_text_placeholders("{'value'|exists}", {})
    assert_equal(result, True, "Literal with exists (true)")
    
    # is_null for empty string
    result = processor.process_text_placeholders("{''|is_null}", {})
    assert_equal(result, True, "Empty literal with is_null")


def test_literals_chains(processor):
    """Test modifier chains with literals"""
    # Chain: arithmetic + formatting
    result = processor.process_text_placeholders("{'1000'|*0.9|format:currency}", {})
    assert "₽" in result, "Literal with chain *0.9|format:currency"
    
    # Chain: string modifiers
    result = processor.process_text_placeholders("{'hello world'|upper|truncate:5}", {})
    assert "HE" in result, "Literal with chain upper|truncate:5"
    
    # Chain: seconds + arithmetic
    result = processor.process_text_placeholders("{'2h 30m'|seconds|/60}", {})
    assert_equal(result, 150, "Literal with chain seconds|/60 (minutes)")
    
    # Chain: fallback + upper
    result = processor.process_text_placeholders("{'default'|fallback:other|upper}", {})
    assert_equal(result, "DEFAULT", "Literal with fallback (not triggered) + upper")


def test_literals_fallback(processor):
    """Test fallback modifier with literals"""
    # Literal with fallback (should not trigger for non-empty literal)
    result = processor.process_text_placeholders("{'value'|fallback:default}", {})
    assert_equal(result, "value", "Literal with fallback (not triggered)")
    
    # Empty literal with fallback
    result = processor.process_text_placeholders("{''|fallback:default}", {})
    assert_equal(result, "default", "Empty literal with fallback (triggered)")


def test_literals_mixed_with_placeholders(processor):
    """Test combination of literals and regular placeholders"""
    values_dict = {
        'name': 'John',
        'age': 25,
    }
    
    # Literal + placeholder in one string
    result = processor.process_text_placeholders("Hello, {'world'}! My name is {name}.", values_dict)
    assert result == "Hello, world! My name is John.", "Literal + placeholder in string"
    
    # Literal with modifier + placeholder
    result = processor.process_text_placeholders("{'test'|upper} - {age}", values_dict)
    assert_equal(result, "TEST - 25", "Literal with modifier + placeholder")


def test_literals_with_special_characters(processor):
    """Test literals with special characters"""
    # Literal with escaped single quote
    result = processor.process_text_placeholders("{'it\\'s working'}", {})
    assert_equal(result, "it's working", "Literal with escaped single quote")
    
    # Literal with escaped double quote
    result = processor.process_text_placeholders('{" say \\"hi\\" "}', {})
    assert_equal(result, ' say "hi" ', "Literal with escaped double quote")


def test_literals_code_modifier(processor):
    """Test code modifier with literals"""
    # Simple string wrapped in code
    result = processor.process_text_placeholders("{'hello'|code}", {})
    assert_equal(result, "<code>hello</code>", "Literal with code")
    
    # Number wrapped in code
    result = processor.process_text_placeholders("{'123'|code}", {})
    assert_equal(result, "<code>123</code>", "Number literal with code")


def test_literals_regex_modifier(processor):
    """Test regex modifier with literals"""
    # Extract numbers
    result = processor.process_text_placeholders("{'Hello 123 World'|regex:\\d+}", {})
    assert_equal(result, "123", "Literal with regex to extract numbers")
    
    # Extract time
    result = processor.process_text_placeholders("{'Meeting at 2h 30m'|regex:(?:\\d+\\s*[dhms]\\s*)+}", {})
    assert "2h" in result, "Literal with regex to extract time"
    assert "30m" in result, "Literal with regex to extract time"


def test_literals_edge_cases(processor):
    """Test edge cases with literals"""
    # Empty string in quotes
    result = processor.process_text_placeholders("{''}", {})
    assert_equal(result, "", "Empty literal")
    
    # Literal with only spaces
    result = processor.process_text_placeholders("{'   '}", {})
    assert_equal(result, "   ", "Literal with spaces")
    
    # Literal with newline (if supported)
    result = processor.process_text_placeholders("{'line1\\nline2'}", {})
    # Check it doesn't crash and returns something meaningful
    assert isinstance(result, str), "Literal with newline"


def test_literals_type_preservation(processor):
    """Test type preservation when using literals"""
    # Number literal returns number (after _determine_result_type processing)
    result = processor.process_text_placeholders("{'123'}", {})
    # _determine_result_type converts '123' to int(123)
    assert_equal(result, 123, "Number literal returns int")
    
    # Float literal
    result = processor.process_text_placeholders("{'123.45'}", {})
    # _determine_result_type converts '123.45' to float(123.45)
    assert_equal(result, 123.45, "Float literal returns float")
    
    # Boolean literal
    result = processor.process_text_placeholders("{'true'}", {})
    # _determine_result_type converts 'true' to True
    assert_equal(result, True, "Literal 'true' returns True")
    
    result = processor.process_text_placeholders("{'false'}", {})
    # _determine_result_type converts 'false' to False
    assert_equal(result, False, "Literal 'false' returns False")
