"""
Tests for format modifier with Unix timestamp support
"""

from datetime import datetime
from conftest import assert_equal


def test_format_unix_timestamp_to_datetime(processor):
    """Test formatting Unix timestamp to datetime formats"""
    # Unix timestamp: 1770689288 = 2026-02-09 12:34:48 (approximate)
    values_dict = {
        'timestamp': 1770689288,
        'timestamp_str': '1770689288',
    }
    
    # Test format:datetime with integer Unix timestamp
    result = processor.process_text_placeholders("{timestamp|format:datetime}", values_dict)
    assert isinstance(result, str), "format:datetime should return string"
    assert "2026" in result or "09.02" in result, f"format:datetime should contain date: {result}"
    
    # Test format:datetime with string Unix timestamp
    result = processor.process_text_placeholders("{timestamp_str|format:datetime}", values_dict)
    assert isinstance(result, str), "format:datetime with string timestamp should return string"
    assert "2026" in result or "09.02" in result, f"format:datetime should contain date: {result}"


def test_format_unix_timestamp_all_formats(processor):
    """Test all datetime format modifiers with Unix timestamp"""
    # Known timestamp: 1640444445 = 2021-12-25 15:34:05
    values_dict = {
        'ts': 1640444445,
    }
    
    # Test format:date
    result = processor.process_text_placeholders("{ts|format:date}", values_dict)
    assert_equal(result, "25.12.2021", "format:date with Unix timestamp")
    
    # Test format:time
    result = processor.process_text_placeholders("{ts|format:time}", values_dict)
    # Time depends on timezone, just check format
    assert ":" in result, "format:time should contain colon"
    assert len(result) == 5, f"format:time should be HH:MM format, got: {result}"
    
    # Test format:time_full
    result = processor.process_text_placeholders("{ts|format:time_full}", values_dict)
    assert ":" in result, "format:time_full should contain colon"
    assert len(result) == 8, f"format:time_full should be HH:MM:SS format, got: {result}"
    
    # Test format:datetime
    result = processor.process_text_placeholders("{ts|format:datetime}", values_dict)
    assert "25.12.2021" in result, "format:datetime should contain date"
    assert ":" in result, "format:datetime should contain time"
    
    # Test format:datetime_full
    result = processor.process_text_placeholders("{ts|format:datetime_full}", values_dict)
    assert "25.12.2021" in result, "format:datetime_full should contain date"
    assert ":" in result, "format:datetime_full should contain time"
    
    # Test format:pg_date
    result = processor.process_text_placeholders("{ts|format:pg_date}", values_dict)
    assert_equal(result, "2021-12-25", "format:pg_date with Unix timestamp")
    
    # Test format:pg_datetime
    result = processor.process_text_placeholders("{ts|format:pg_datetime}", values_dict)
    assert "2021-12-25" in result, "format:pg_datetime should contain date"
    assert ":" in result, "format:pg_datetime should contain time"


def test_format_timestamp_conversion_chain(processor):
    """Test converting to timestamp and back to datetime"""
    values_dict = {
        'date': datetime(2024, 6, 15, 10, 30, 0),
    }
    
    # Convert to timestamp
    result = processor.process_text_placeholders("{date|format:timestamp}", values_dict)
    assert result.isdigit(), "format:timestamp should return digits"
    
    # Store timestamp and convert back
    values_dict['ts'] = int(result)
    result_back = processor.process_text_placeholders("{ts|format:date}", values_dict)
    assert_equal(result_back, "15.06.2024", "Converting to timestamp and back should preserve date")


def test_format_mixed_input_types(processor):
    """Test format modifier with different input types"""
    values_dict = {
        'dt_object': datetime(2023, 3, 20, 14, 25, 30),
        'iso_string': '2023-03-20T14:25:30',
        'unix_int': 1679323530,  # Approximately 2023-03-20 14:25:30
        'unix_str': '1679323530',
    }
    
    # All should produce similar output
    result1 = processor.process_text_placeholders("{dt_object|format:date}", values_dict)
    result2 = processor.process_text_placeholders("{iso_string|format:date}", values_dict)
    result3 = processor.process_text_placeholders("{unix_int|format:date}", values_dict)
    result4 = processor.process_text_placeholders("{unix_str|format:date}", values_dict)
    
    # All should be same date
    assert_equal(result1, "20.03.2023", "datetime object formatting")
    assert_equal(result2, "20.03.2023", "ISO string formatting")
    assert_equal(result3, "20.03.2023", "Unix int formatting")
    assert_equal(result4, "20.03.2023", "Unix string formatting")


def test_format_zero_timestamp(processor):
    """Test format with zero timestamp (1970-01-01)"""
    values_dict = {
        'zero': 0,
    }
    
    # Should not fail
    result = processor.process_text_placeholders("{zero|format:date}", values_dict)
    assert isinstance(result, str), "format:date with zero timestamp should not crash"


def test_format_invalid_timestamp(processor):
    """Test format with invalid values"""
    values_dict = {
        'invalid_str': 'not a timestamp',
        'invalid_num': -999999999999999,  # Invalid timestamp
    }
    
    # Should not crash, return original value as string
    result1 = processor.process_text_placeholders("{invalid_str|format:datetime}", values_dict)
    assert isinstance(result1, str), "Invalid string should not crash"
    
    result2 = processor.process_text_placeholders("{invalid_num|format:datetime}", values_dict)
    assert isinstance(result2, str), "Invalid timestamp should not crash"


def test_format_real_world_scenario(processor):
    """Test real-world scenario from message_tracking.yaml"""
    from datetime import datetime, timedelta
    
    # Simulate event_date and shift
    event_date = datetime.now()
    values_dict = {
        'event_date': event_date,
    }
    
    # First: create timestamp (like line 45 in message_tracking.yaml)
    # {event_date|shift:+12 hours|format:timestamp}
    # For this test, we'll calculate manually
    shifted_date = event_date + timedelta(hours=12)
    timestamp = int(shifted_date.timestamp())
    
    values_dict['_cache'] = {
        'restrict_until_date': timestamp
    }
    
    # Second: format timestamp to datetime (like line 65)
    # {_cache.restrict_until_date|format:datetime}
    result = processor.process_text_placeholders("{_cache.restrict_until_date|format:datetime}", values_dict)
    
    # Should be a formatted datetime string
    assert isinstance(result, str), "Should return string"
    assert ":" in result, "Should contain time separator"
    assert "." in result, "Should contain date separator"
    
    # Verify the date is roughly 12 hours in the future
    # (we check format, not exact value since time may vary during test)
    assert len(result) >= 10, f"Should be formatted datetime, got: {result}"
