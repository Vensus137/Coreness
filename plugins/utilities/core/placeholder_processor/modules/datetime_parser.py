"""
Utilities for parsing dates and time intervals
"""
import re
from datetime import datetime
from typing import Dict, Optional, Tuple


def parse_datetime_value(value) -> Tuple[Optional[datetime], bool]:
    """
    Converts any date format to datetime
    """
    if value is None:
        return None, False
    
    # Already datetime object
    if isinstance(value, datetime):
        # Check if time is present (not 00:00:00)
        has_time = value.hour != 0 or value.minute != 0 or value.second != 0
        return value, has_time
    
    # Convert to string
    value_str = str(value).strip()
    
    if not value_str:
        return None, False
    
    # Unix timestamp (digits only)
    if value_str.isdigit():
        try:
            return datetime.fromtimestamp(int(value_str)), True
        except (ValueError, OSError):
            pass
    
    # Try parsing ISO format with timezone first (most complex)
    # ISO format with timezone requires special handling
    if 'T' in value_str:
        try:
            # Try fromisoformat (supports ISO with timezone, microseconds, etc.)
            # This handles formats like: 2026-02-09T16:02:36.609797+03:00
            dt = datetime.fromisoformat(value_str.replace('Z', '+00:00'))
            return dt, True
        except (ValueError, AttributeError):
            pass
    
    # Try different formats
    # Format: (pattern, has_time)
    formats = [
        # PostgreSQL formats
        ('%Y-%m-%d %H:%M:%S', True),
        ('%Y-%m-%d %H:%M', True),
        ('%Y-%m-%d', False),
        
        # Our formats (dd.mm.yyyy)
        ('%d.%m.%Y %H:%M:%S', True),
        ('%d.%m.%Y %H:%M', True),
        ('%d.%m.%Y', False),
        
        # ISO formats (without timezone)
        ('%Y-%m-%dT%H:%M:%S', True),
        ('%Y-%m-%dT%H:%M', True),
    ]
    
    for fmt, has_time in formats:
        try:
            dt = datetime.strptime(value_str, fmt)
            return dt, has_time
        except ValueError:
            continue
    
    # Failed to parse
    return None, False


def parse_interval_string(interval: str) -> Dict[str, int]:
    """
    Parses interval in PostgreSQL style
    """
    # Pattern: number + spaces + time unit
    # (?i) at start makes pattern case-insensitive
    pattern = r'(\d+)\s+(year|years|y|month|months|mon|week|weeks|w|day|days|d|hour|hours|h|minute|minutes|min|m|second|seconds|sec|s)\b'
    
    result = {
        'years': 0,
        'months': 0,
        'weeks': 0,
        'days': 0,
        'hours': 0,
        'minutes': 0,
        'seconds': 0
    }
    
    # Find all matches (case-insensitive)
    matches = re.findall(pattern, interval, re.IGNORECASE)
    
    if not matches:
        return result
    
    for value, unit in matches:
        value = int(value)
        unit_lower = unit.lower()
        
        # Map time units to dictionary keys
        if unit_lower in ['year', 'years', 'y']:
            result['years'] += value
        elif unit_lower in ['month', 'months', 'mon']:
            result['months'] += value
        elif unit_lower in ['week', 'weeks', 'w']:
            result['weeks'] += value
        elif unit_lower in ['day', 'days', 'd']:
            result['days'] += value
        elif unit_lower in ['hour', 'hours', 'h']:
            result['hours'] += value
        elif unit_lower in ['minute', 'minutes', 'min', 'm']:
            result['minutes'] += value
        elif unit_lower in ['second', 'seconds', 'sec', 's']:
            result['seconds'] += value
    
    return result
