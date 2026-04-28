from dataclasses import dataclass
from enum import Enum


class CaptureStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class CaptureRun:
    id: int
    started_at: str
    status: CaptureStatus
    hero_count: int = 0
    completed_at: str = None
    error_message: str = None
