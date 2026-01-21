"""
Module for working with scenario schedules (cron)
"""

from datetime import datetime
from typing import Optional

from croniter import croniter


class ScenarioScheduler:
    """
    Scheduler for scheduled scenarios
    - Parse cron expressions
    - Check launch time
    - Calculate next launch time
    """
    
    def __init__(self, logger, datetime_formatter):
        self.logger = logger
        self.datetime_formatter = datetime_formatter
    
    def is_valid_cron(self, cron_string: str) -> bool:
        """
        Check validity of cron expression
        """
        if not cron_string or not isinstance(cron_string, str):
            return False
        
        try:
            croniter(cron_string)
            return True
        except Exception:
            return False
    
    async def get_next_run_time(self, cron_string: str, from_time: Optional[datetime] = None) -> Optional[datetime]:
        """
        Get next launch time by cron expression
        """
        if not self.is_valid_cron(cron_string):
            return None
        
        try:
            # If time not specified - use current local time
            if from_time is None:
                from_time = await self.datetime_formatter.now_local()
            
            # Create croniter from specified time
            cron = croniter(cron_string, from_time)
            next_run = cron.get_next(datetime)
            
            return next_run
            
        except Exception as e:
            self.logger.error(f"Error calculating next launch time for cron '{cron_string}': {e}")
            return None

