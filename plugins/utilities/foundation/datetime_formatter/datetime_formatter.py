from typing import Any, Dict, List, Optional, Union


class DatetimeFormatter:

    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        # Get settings via settings_manager
        settings = self.settings_manager.get_plugin_settings("datetime_formatter")
        self.timezone = settings.get('timezone', 'Europe/Moscow')
        self.format_name = settings.get('format', 'iso')
        self._tz = None  # Lazy initialization

    def _get_timezone(self):
        """Lazy timezone initialization"""
        if self._tz is None:
            from zoneinfo import ZoneInfo
            self._tz = ZoneInfo(self.timezone)
        return self._tz

    def _normalize_to_utc_datetime(self, dt):
        """
        Normalize datetime or Unix timestamp to UTC datetime.
        
        IMPORTANT: If naive datetime is passed, consider it local time (not UTC).
        This allows correct processing of datetime from to_local() and now_local(),
        which return naive datetime in local timezone.
        """
        import datetime
        
        # If Unix timestamp is passed (int or float)
        if isinstance(dt, (int, float)):
            # Convert timestamp to UTC datetime
            return datetime.datetime.fromtimestamp(dt, tz=datetime.timezone.utc)
        
        # If naive datetime, consider it local time (not UTC!)
        # Convert to UTC via local timezone
        if dt.tzinfo is None:
            # First add local timezone
            local_dt = dt.replace(tzinfo=self._get_timezone())
            # Then convert to UTC
            return local_dt.astimezone(datetime.timezone.utc)
        
        # If already timezone-aware, convert to UTC
        return dt.astimezone(datetime.timezone.utc)

    async def now_utc(self):
        """Get current time in UTC (naive datetime)"""
        import datetime
        # Returns naive UTC, but gets time via timezone-aware method
        return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    async def now_utc_tz(self):
        """Get current time in UTC (timezone-aware datetime)"""
        import datetime
        return datetime.datetime.now(datetime.timezone.utc)

    async def now_local(self):
        """Get current time in local timezone (naive datetime)"""
        import datetime
        return datetime.datetime.now(self._get_timezone()).replace(tzinfo=None)

    async def now_local_tz(self):
        """Get current time in local timezone (timezone-aware datetime)"""
        import datetime
        return datetime.datetime.now(self._get_timezone())

    async def to_utc(self, dt):
        """Convert datetime or Unix timestamp to UTC (naive)"""
        # Normalize to UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        
        # Remove tzinfo for naive UTC
        return utc_dt.replace(tzinfo=None)

    async def to_utc_tz(self, dt):
        """Convert datetime or Unix timestamp to UTC (timezone-aware)"""
        # Normalize to UTC datetime
        return self._normalize_to_utc_datetime(dt)

    async def to_local(self, dt):
        """Convert datetime or Unix timestamp to local timezone (naive)"""
        # Normalize to UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        
        # Convert to local timezone and remove tzinfo
        return utc_dt.astimezone(self._get_timezone()).replace(tzinfo=None)

    async def to_local_tz(self, dt):
        """Convert datetime or Unix timestamp to local timezone (timezone-aware)"""
        # Normalize to UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        
        # Convert to local timezone
        return utc_dt.astimezone(self._get_timezone())

    async def format(self, dt) -> str:
        """Format datetime to string according to settings"""
        if self.format_name == 'iso':
            return dt.isoformat()
        # Can add other formats as needed
        return dt.isoformat()

    async def to_string(self, dt, fmt: Optional[str] = None) -> str:
        """
        Convert datetime to string by format (ISO by default).
        fmt: 'iso' (default), or any strftime format.
        """
        if fmt is None:
            fmt = self.format_name
        if fmt == 'iso':
            return dt.isoformat()
        return dt.strftime(fmt)

    async def to_iso_string(self, dt) -> str:
        """
        Short alias for ISO string in UTC.
        Supports datetime and Unix timestamp.
        """
        # Normalize to UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        return utc_dt.isoformat()
    
    async def to_iso_local_string(self, dt) -> str:
        """
        Convert datetime to ISO string in local timezone.
        Supports datetime and Unix timestamp.
        Useful for event_date, so placeholders correctly format the date.
        """
        # Normalize to UTC datetime
        utc_dt = self._normalize_to_utc_datetime(dt)
        # Convert to local timezone
        local_dt = utc_dt.astimezone(self._get_timezone())
        return local_dt.isoformat()

    async def to_datetime_string(self, dt: Union[Any, str]) -> str:
        """
        Convert datetime or ISO string to readable format YYYY-MM-DD HH:MM:SS.
        Universal method: accepts datetime.datetime or ISO format string.
        """
        import datetime
        if isinstance(dt, str):
            # If string is passed - parse it to datetime
            dt = await self.parse(dt)
        elif not isinstance(dt, datetime.datetime):
            self.logger.error(f"Expected datetime or ISO string, got: {type(dt)}")
            return None
        
        return dt.strftime('%Y-%m-%d %H:%M:%S')

    async def to_date_string(self, dt: Union[Any, str]) -> str:
        """
        Convert datetime or ISO string to date format YYYY-MM-DD.
        Universal method: accepts datetime.datetime or ISO format string.
        """
        import datetime
        if isinstance(dt, str):
            # If string is passed - parse it to datetime
            dt = await self.parse(dt)
        elif not isinstance(dt, datetime.datetime):
            self.logger.error(f"Expected datetime or ISO string, got: {type(dt)}")
            return None
        
        return dt.strftime('%Y-%m-%d')

    async def to_serializable(self, obj: Union[Dict, List, Any]) -> Union[Dict, List, str, Any]:
        """
        Recursively convert all datetime to string (ISO) for JSON serialization.
        """
        import datetime
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                result[k] = await self.to_serializable(v)
            return result
        elif isinstance(obj, list):
            return [await self.to_serializable(i) for i in obj]
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return obj

    async def parse(self, dt_str: str) -> Any:
        """Parse ISO string to datetime"""
        import datetime
        dt = datetime.datetime.fromisoformat(dt_str)
        # Return as is: if string has tzinfo - will be aware, if not - naive
        return dt

    async def parse_to_local(self, dt_str: str) -> Any:
        """
        Parse date string and return datetime in local time (naive).
        Assumes input string is in local time.
        Supports formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO format.
        """
        dt = await self.parse_date_string(dt_str)  # Use universal parser
        # If datetime naive - consider it local
        if dt.tzinfo is None:
            return dt
        # If datetime aware - convert to local time
        return await self.to_local(dt)

    async def parse_to_local_tz(self, dt_str: str) -> Any:
        """
        Parse date string and return datetime in local time with timezone.
        Assumes input string is in local time.
        Supports formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO format.
        """
        dt = await self.parse_date_string(dt_str)  # Use universal parser
        # If datetime naive - consider it local and add timezone
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self._get_timezone())
        # If datetime aware - convert to local time
        return await self.to_local_tz(dt)

    async def parse_to_utc(self, dt_str: str) -> Any:
        """
        Parse date string and return datetime in UTC (naive).
        If datetime naive - consider it LOCAL time and convert to UTC.
        If datetime aware - convert to UTC.
        Supports formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO format.
        """
        dt = await self.parse_date_string(dt_str)  # Use universal parser
        # If datetime naive - consider it LOCAL time and convert to UTC
        import datetime
        if dt.tzinfo is None:
            # Add local timezone and convert to UTC
            dt_local = dt.replace(tzinfo=self._get_timezone())
            return dt_local.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        # If datetime aware - convert to UTC
        return await self.to_utc(dt)

    async def parse_to_utc_tz(self, dt_str: str) -> Any:
        """
        Parse date string and return datetime in UTC with timezone.
        If datetime naive - consider it LOCAL time and convert to UTC.
        If datetime aware - convert to UTC.
        Supports formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO format.
        """
        dt = await self.parse_date_string(dt_str)  # Use universal parser
        # If datetime naive - consider it LOCAL time and convert to UTC
        import datetime
        if dt.tzinfo is None:
            # Add local timezone and convert to UTC
            dt_local = dt.replace(tzinfo=self._get_timezone())
            return dt_local.astimezone(datetime.timezone.utc)
        # If datetime aware - convert to UTC
        return await self.to_utc_tz(dt)

    async def parse_date_string(self, date_str: str) -> Any:
        """
        Universal method for parsing dates from strings in various formats.
        
        Supported formats:
        - YYYY-MM-DD (e.g., "2025-01-15")
        - YYYY-MM-DD HH:MM:SS (e.g., "2025-01-15 14:30:00")
        - ISO format with timezone (e.g., "2025-01-15T14:30:00+03:00")
        - ISO format without timezone (e.g., "2025-01-15T14:30:00")
        - ISO format with microseconds (e.g., "2025-01-15T14:30:00.123456")
        """
        if not date_str or not isinstance(date_str, str):
            self.logger.error(f"Expected non-empty string, got: {date_str}")
            return None
        
        date_str = date_str.strip()
        
        # List of formats to try parsing (in priority order)
        formats = [
            # ISO format with timezone and microseconds
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%f",
            # ISO format with timezone
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            # Regular format with seconds
            "%Y-%m-%d %H:%M:%S",
            # Date only
            "%Y-%m-%d",
        ]
        
        import datetime
        # First try standard ISO parser (it handles timezones better)
        try:
            return datetime.datetime.fromisoformat(date_str)
        except ValueError:
            pass
        
        # Then try our formats
        for fmt in formats:
            try:
                dt = datetime.datetime.strptime(date_str, fmt)
                return dt
            except ValueError:
                continue
        
        # If nothing matched, try more flexible options
        try:
            # Try parsing as ISO, but with space replaced by T
            if ' ' in date_str and 'T' not in date_str:
                iso_str = date_str.replace(' ', 'T')
                return datetime.datetime.fromisoformat(iso_str)
        except ValueError:
            pass
        
        # If all attempts failed
        self.logger.error(f"Failed to parse date '{date_str}'. "
                         f"Supported formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO format")
        return None

    async def time_diff(self, dt1: Union[Any, str], dt2: Union[Any, str]) -> Any:
        """
        Calculate difference between two datetime objects considering timezones.
        """
        # Parse strings to datetime if needed
        if isinstance(dt1, str):
            dt1 = await self.parse(dt1)
        if isinstance(dt2, str):
            dt2 = await self.parse(dt2)
        
        # Convert to UTC for correct comparison
        dt1_utc = await self.to_utc_tz(dt1)
        dt2_utc = await self.to_utc_tz(dt2)
        
        return dt2_utc - dt1_utc

    async def is_older_than(self, dt: Union[Any, str], seconds: int) -> bool:
        """
        Check if more than specified seconds have passed since dt.
        """
        time_diff = await self.time_diff(dt, await self.now_local())
        return time_diff.total_seconds() > seconds

    async def is_newer_than(self, dt: Union[Any, str], seconds: int) -> bool:
        """
        Check if less than specified seconds have passed since dt.
        """
        time_diff = await self.time_diff(dt, await self.now_local())
        return time_diff.total_seconds() < seconds

    async def subtract_seconds(self, dt: Union[Any, str], seconds: int) -> Any:
        """
        Subtract specified number of seconds from datetime.
        Supports datetime and ISO strings.
        """
        import datetime
        
        # Parse string to datetime if needed
        if isinstance(dt, str):
            dt = await self.parse(dt)
        
        # Subtract seconds
        return dt - datetime.timedelta(seconds=seconds)


