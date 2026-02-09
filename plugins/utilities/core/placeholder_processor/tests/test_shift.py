"""
Tests for shift modifier PlaceholderProcessor
Check date shifting by intervals (PostgreSQL style)
"""

from conftest import assert_equal


def test_shift_basic_days(processor):
    """Test basic day shifting"""
    # +1 day
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Shift +1 day")
    
    # -1 day
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-1 day}", {})
    assert_equal(result, "2024-12-24", "Shift -1 day")
    
    # +7 days
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+7 days}", {})
    assert_equal(result, "2025-01-01", "Shift +7 days (year transition)")


def test_shift_hours_minutes(processor):
    """Test hours and minutes shifting"""
    # +2 hours
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+2 hours}", {})
    assert_equal(result, "2024-12-25 17:30:00", "Shift +2 hours")
    
    # -3 hours
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:-3 hours}", {})
    assert_equal(result, "2024-12-25 12:30:00", "Shift -3 hours")
    
    # +30 minutes
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+30 minutes}", {})
    assert_equal(result, "2024-12-25 16:00:00", "Shift +30 minutes")


def test_shift_weeks(processor):
    """Test week shifting"""
    # +1 week
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 week}", {})
    assert_equal(result, "2025-01-01", "Shift +1 week")
    
    # -2 weeks
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-2 weeks}", {})
    assert_equal(result, "2024-12-11", "Shift -2 weeks")


def test_shift_months(processor):
    """Test month shifting"""
    # +1 month
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 month}", {})
    assert_equal(result, "2025-01-25", "Shift +1 month")
    
    # -3 months
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-3 months}", {})
    assert_equal(result, "2024-09-25", "Shift -3 months")
    
    # Month edge: January 31 + 1 month
    result = processor.process_text_placeholders("{'2024-01-31'|shift:+1 month}", {})
    # relativedelta correctly handles: January 31 + 1 month = February 29 (leap year)
    assert_equal(result, "2024-02-29", "Month edge: Jan 31 + 1 month")


def test_shift_years(processor):
    """Test year shifting"""
    # +1 year
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 year}", {})
    assert_equal(result, "2025-12-25", "Shift +1 year")
    
    # -2 years
    result = processor.process_text_placeholders("{'2024-12-25'|shift:-2 years}", {})
    assert_equal(result, "2022-12-25", "Shift -2 years")
    
    # Leap year: February 29 + 1 year
    result = processor.process_text_placeholders("{'2024-02-29'|shift:+1 year}", {})
    # relativedelta correctly handles: Feb 29 + 1 year = Feb 28 (non-leap year)
    assert_equal(result, "2025-02-28", "Leap year: Feb 29 + 1 year")


def test_shift_complex_intervals(processor):
    """Test complex intervals (multiple units)"""
    # +1 year 2 months
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 year 2 months}", {})
    assert_equal(result, "2026-02-25", "Shift +1 year 2 months")
    
    # +1 week 3 days
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 week 3 days}", {})
    assert_equal(result, "2025-01-04", "Shift +1 week 3 days")
    
    # -1 day 12 hours
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:-1 day 12 hours}", {})
    assert_equal(result, "2024-12-24 03:30:00", "Shift -1 day 12 hours")


def test_shift_different_input_formats(processor):
    """Test different input date formats"""
    # PostgreSQL format (YYYY-MM-DD)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "PostgreSQL date format")
    
    # Our format (dd.mm.yyyy)
    result = processor.process_text_placeholders("{'25.12.2024'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Our date format")
    
    # PostgreSQL format with time
    result = processor.process_text_placeholders("{'2024-12-25 15:30:45'|shift:+1 hour}", {})
    assert_equal(result, "2024-12-25 16:30:45", "PostgreSQL datetime format")
    
    # Our format with time
    result = processor.process_text_placeholders("{'25.12.2024 15:30'|shift:+2 hours}", {})
    assert_equal(result, "2024-12-25 17:30:00", "Our datetime format")
    
    # Unix timestamp
    # 1735128000 = 2024-12-25 12:00:00 UTC
    result = processor.process_text_placeholders("{'1735128000'|shift:+1 day}", {})
    # Result depends on timezone, check that original timestamp is not returned
    assert result != "1735128000", "Unix timestamp is processed"


def test_shift_case_insensitive(processor):
    """Test case-insensitive time unit parsing"""
    # Uppercase
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 DAY}", {})
    assert_equal(result, "2024-12-26", "Uppercase: DAY")
    
    # Mixed case
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 Month}", {})
    assert_equal(result, "2025-01-25", "Mixed case: Month")
    
    # Combination
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 YEAR 2 months}", {})
    assert_equal(result, "2026-02-25", "Mixed case: YEAR + months")


def test_shift_single_plural_forms(processor):
    """Test singular and plural forms"""
    # Singular
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Singular: day")
    
    # Plural
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+2 days}", {})
    assert_equal(result, "2024-12-27", "Plural: days")
    
    # Abbreviations
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 d}", {})
    assert_equal(result, "2024-12-26", "Abbreviation: d")
    
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 y}", {})
    assert_equal(result, "2025-12-25", "Abbreviation: y")


def test_shift_with_chain(processor):
    """Test modifier chain with shift"""
    # shift + format
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day|format:date}", {})
    assert_equal(result, "26.12.2024", "shift + format:date")
    
    # shift + shift (double shift)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 year|shift:+6 months}", {})
    assert_equal(result, "2026-06-25", "Double shift: +1.5 years")
    
    # shift + format:datetime
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+1 day|format:datetime}", {})
    assert_equal(result, "26.12.2024 15:30", "shift + format:datetime")


def test_shift_with_dict_values(processor):
    """Test shift with regular placeholders (not literals)"""
    values = {
        "created": "2024-12-25",
        "updated": "2024-12-25 15:30:00"
    }
    
    result = processor.process_text_placeholders("{created|shift:+1 day}", values)
    assert_equal(result, "2024-12-26", "shift with dict value (date)")
    
    result = processor.process_text_placeholders("{updated|shift:+2 hours}", values)
    assert_equal(result, "2024-12-25 17:30:00", "shift with dict value (datetime)")


def test_shift_error_handling(processor):
    """Test error handling"""
    # No + or - sign
    result = processor.process_text_placeholders("{'2024-12-25'|shift:1 day}", {})
    assert_equal(result, "2024-12-25", "Without sign returns original value")
    
    # Invalid date format
    result = processor.process_text_placeholders("{'invalid-date'|shift:+1 day}", {})
    assert_equal(result, "invalid-date", "Invalid date returns original value")
    
    # Invalid interval
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 invalid}", {})
    assert_equal(result, "2024-12-25", "Invalid interval returns original value")


def test_shift_preserves_time_presence(processor):
    """Test preserving time presence in output"""
    # If input date without time, output also without time
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Date without time remains without time")
    
    # If input date with time, output also with time
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26 15:30:00", "Date with time remains with time")


def test_shift_abbreviated_units(processor):
    """Test abbreviated time units"""
    # y (year)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 y}", {})
    assert_equal(result, "2025-12-25", "Abbreviation: y")
    
    # mon (month)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+2 mon}", {})
    assert_equal(result, "2025-02-25", "Abbreviation: mon")
    
    # w (week)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 w}", {})
    assert_equal(result, "2025-01-01", "Abbreviation: w")
    
    # d (day)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+3 d}", {})
    assert_equal(result, "2024-12-28", "Abbreviation: d")
    
    # h (hour)
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+2 h}", {})
    assert_equal(result, "2024-12-25 17:30:00", "Abbreviation: h")
    
    # min (minute)
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+45 min}", {})
    assert_equal(result, "2024-12-25 16:15:00", "Abbreviation: min")
    
    # sec (second)
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:+30 sec}", {})
    assert_equal(result, "2024-12-25 15:30:30", "Abbreviation: sec")


def test_shift_iso_with_timezone(processor):
    """Test shift with ISO format dates with timezone"""
    # ISO format with timezone and microseconds
    result = processor.process_text_placeholders("{'2026-02-09T16:02:36.609797+03:00'|shift:+1 day}", {})
    # Check that result is valid date (not original value)
    assert result != "2026-02-09T16:02:36.609797+03:00", "ISO with timezone should be parsed"
    assert "2026-02-10" in result, "Should shift by 1 day"
    
    # ISO format with Z timezone
    result = processor.process_text_placeholders("{'2024-12-25T15:30:00Z'|shift:+2 hours}", {})
    assert result != "2024-12-25T15:30:00Z", "ISO with Z timezone should be parsed"
    # Result depends on local timezone, just check it's processed
    assert "2024-12-25" in result or "2024-12-26" in result, "Date should be present in result"
    
    # ISO format with positive offset
    result = processor.process_text_placeholders("{'2024-12-25T15:30:00+05:00'|shift:+1 hour}", {})
    assert result != "2024-12-25T15:30:00+05:00", "ISO with +offset should be parsed"
    
    # ISO format with negative offset
    result = processor.process_text_placeholders("{'2024-12-25T15:30:00-08:00'|shift:-3 hours}", {})
    assert result != "2024-12-25T15:30:00-08:00", "ISO with -offset should be parsed"


def test_shift_iso_with_microseconds(processor):
    """Test shift with ISO format dates with microseconds"""
    # ISO format with microseconds (no timezone)
    result = processor.process_text_placeholders("{'2024-12-25T15:30:45.123456'|shift:+1 day}", {})
    # fromisoformat should handle this
    assert result != "2024-12-25T15:30:45.123456", "ISO with microseconds should be parsed"
    assert "2024-12-26" in result, "Should shift by 1 day"


def test_shift_with_quoted_parameters(processor):
    """Test shift with parameters in quotes (support for user convenience)"""
    # Single quotes around parameter
    result = processor.process_text_placeholders("{'2024-12-25'|shift:'+1 day'}", {})
    assert_equal(result, "2024-12-26", "Shift with single quoted parameter")
    
    # Double quotes around parameter
    result = processor.process_text_placeholders("{'2024-12-25'|shift:\"+1 day\"}", {})
    assert_equal(result, "2024-12-26", "Shift with double quoted parameter")
    
    # Negative shift with single quotes
    result = processor.process_text_placeholders("{'2024-12-25'|shift:'-1 day'}", {})
    assert_equal(result, "2024-12-24", "Shift with negative single quoted parameter")
    
    # Complex interval with quotes
    result = processor.process_text_placeholders("{'2024-12-25'|shift:'+1 year 2 months'}", {})
    assert_equal(result, "2026-02-25", "Shift with complex quoted parameter")
    
    # Hours with quotes (real case from yaml)
    result = processor.process_text_placeholders("{'2024-12-25 15:30:00'|shift:'-1 hours'}", {})
    assert_equal(result, "2024-12-25 14:30:00", "Shift hours with quoted parameter")
    
    # Without quotes (should still work)
    result = processor.process_text_placeholders("{'2024-12-25'|shift:+1 day}", {})
    assert_equal(result, "2024-12-26", "Shift without quotes still works")
