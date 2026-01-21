import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional


@dataclass
class QueueConfig:
    """Queue configuration"""
    name: str
    max_concurrent: int
    timeout: float
    retry_count: int
    retry_delay: float

@dataclass
class TaskItem:
    """Task item in queue"""
    id: str
    coro: Callable
    config: QueueConfig
    created_at: datetime
    retry_count: int = 0
    future: Optional['asyncio.Future'] = None  # Add Future for returning result
