"""
Tests for modifiers that convert dates to period start
"""

from conftest import assert_equal
import sys
from pathlib import Path

import pytest

# Dynamic import of conftest from current plugin directory
_test_dir = Path(__file__).parent
if str(_test_dir) not in sys.path:
    sys.path.insert(0, str(_test_dir))

# Use processor fixture from conftest
# If assert_equal needed, import it too
from conftest import processor  # noqa: F401


def test_to_date(processor):
    """Test conversion to start of day"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'date': '2024-12-25',
        'timestamp': 1735128045  # 2024-12-25 15:30:45
    }
    
    # Full date and time → start of day
    result = processor.process_text_placeholders("{datetime|to_date}", values_dict)
    assert result == "2024-12-25 00:00:00"
    
    # Date without time → start of day
    result = processor.process_text_placeholders("{date|to_date}", values_dict)
    assert result == "2024-12-25 00:00:00"
    
    # Timestamp → start of day
    result = processor.process_text_placeholders("{timestamp|to_date}", values_dict)
    assert result == "2024-12-25 00:00:00"
    
    # With formatting chain
    result = processor.process_text_placeholders("{datetime|to_date|format:datetime}", values_dict)
    assert "00:00" in result


def test_to_hour(processor):
    """Test conversion to start of hour"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'datetime_mid': '2024-12-25 15:00:00'
    }
    
    # Time 15:30:45 → 15:00:00
    result = processor.process_text_placeholders("{datetime|to_hour}", values_dict)
    assert result == "2024-12-25 15:00:00"
    
    # Time 15:00:00 → 15:00:00 (already start of hour)
    result = processor.process_text_placeholders("{datetime_mid|to_hour}", values_dict)
    assert result == "2024-12-25 15:00:00"


def test_to_minute(processor):
    """Test conversion to start of minute"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'datetime_mid': '2024-12-25 15:30:00'
    }
    
    # Time 15:30:45 → 15:30:00
    result = processor.process_text_placeholders("{datetime|to_minute}", values_dict)
    assert result == "2024-12-25 15:30:00"
    
    # Time 15:30:00 → 15:30:00 (already start of minute)
    result = processor.process_text_placeholders("{datetime_mid|to_minute}", values_dict)
    assert result == "2024-12-25 15:30:00"


def test_to_second(processor):
    """Test conversion to start of second"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'datetime_clean': '2024-12-25 15:30:45'
    }
    
    # Date → start of second (without microseconds)
    result = processor.process_text_placeholders("{datetime|to_second}", values_dict)
    assert result == "2024-12-25 15:30:45"
    
    # Date without microseconds → unchanged
    result = processor.process_text_placeholders("{datetime_clean|to_second}", values_dict)
    assert result == "2024-12-25 15:30:45"


def test_to_week(processor):
    """Test conversion to start of week (Monday)"""
    values_dict = {
        'monday': '2024-12-23 15:30:45',    # Monday
        'tuesday': '2024-12-24 15:30:45',   # Tuesday
        'wednesday': '2024-12-25 15:30:45', # Wednesday
        'sunday': '2024-12-29 15:30:45',    # Sunday
    }
    
    # Monday → Monday 00:00:00
    result = processor.process_text_placeholders("{monday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"
    
    # Tuesday → Monday 00:00:00
    result = processor.process_text_placeholders("{tuesday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"
    
    # Wednesday → Monday 00:00:00
    result = processor.process_text_placeholders("{wednesday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"
    
    # Sunday → Monday of previous week 00:00:00
    result = processor.process_text_placeholders("{sunday|to_week}", values_dict)
    assert result == "2024-12-23 00:00:00"


def test_to_month(processor):
    """Test conversion to start of month"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'first_day': '2024-12-01 15:30:45',
        'end_of_month': '2024-12-31 23:59:59'
    }
    
    # December 25 → December 1 00:00:00
    result = processor.process_text_placeholders("{datetime|to_month}", values_dict)
    assert result == "2024-12-01 00:00:00"
    
    # December 1 → December 1 00:00:00
    result = processor.process_text_placeholders("{first_day|to_month}", values_dict)
    assert result == "2024-12-01 00:00:00"
    
    # December 31 → December 1 00:00:00
    result = processor.process_text_placeholders("{end_of_month|to_month}", values_dict)
    assert result == "2024-12-01 00:00:00"


def test_to_year(processor):
    """Test conversion to start of year"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45',
        'january': '2024-01-15 15:30:45',
        'december': '2024-12-31 23:59:59'
    }
    
    # December 25, 2024 → January 1, 2024 00:00:00
    result = processor.process_text_placeholders("{datetime|to_year}", values_dict)
    assert result == "2024-01-01 00:00:00"
    
    # January 15, 2024 → January 1, 2024 00:00:00
    result = processor.process_text_placeholders("{january|to_year}", values_dict)
    assert result == "2024-01-01 00:00:00"
    
    # December 31, 2024 → January 1, 2024 00:00:00
    result = processor.process_text_placeholders("{december|to_year}", values_dict)
    assert result == "2024-01-01 00:00:00"


def test_to_period_with_literals(processor):
    """Test period conversion with literals"""
    # Literal date → start of day
    result = processor.process_text_placeholders("{'2024-12-25 15:30:45'|to_date}", {})
    assert result == "2024-12-25 00:00:00"
    
    # Literal date → start of week
    result = processor.process_text_placeholders("{'2024-12-25'|to_week}", {})
    assert "00:00:00" in result


def test_to_period_with_chains(processor):
    """Test period conversion with modifier chains"""
    values_dict = {
        'datetime': '2024-12-25 15:30:45'
    }
    
    # Start of day → formatting
    result = processor.process_text_placeholders("{datetime|to_date|format:datetime}", values_dict)
    assert "00:00" in result
    
    # Start of month → formatting
    result = processor.process_text_placeholders("{datetime|to_month|format:date}", values_dict)
    assert "01.12.2024" == result


def test_to_period_edge_cases(processor):
    """Test edge cases"""
    values_dict = {
        'invalid': 'invalid-date',
        'empty': '',
        'none': None
    }
    
    # Invalid date → returns original value (modifier cannot process)
    result = processor.process_text_placeholders("{invalid|to_date}", values_dict)
    assert result == "invalid-date"  # Returns original value
    
    # Empty string → returns original value
    result = processor.process_text_placeholders("{empty|to_date}", values_dict)
    assert result == ""  # Returns empty string
    
    # None → placeholder not resolved
    result = processor.process_text_placeholders("{none|to_date}", values_dict)
    assert result == "{none|to_date}"  # Placeholder not resolved (None not processed)
