"""
Callback definitions for Agent-Orchestrator communication.
"""

from typing import Callable, Dict, Any, Optional, List
from dataclasses import dataclass


# Callback type aliases
ProgressCallback = Callable[[Dict], None]
StuckCallback = Callable[[str], None]
ResultCallback = Callable[[Dict], None]


@dataclass
class ProgressEvent:
    """Progress update event."""
    agent_id: str
    crawled: int              # Pages/items crawled
    total: int                # Estimated total
    current_speed: Optional[float] = None  # Items per second
    stage: str = "crawling"   # Current stage: scanning, crawling, verifying
    message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for callback."""
        return {
            "agent_id": self.agent_id,
            "crawled": self.crawled,
            "total": self.total,
            "current_speed": self.current_speed,
            "stage": self.stage,
            "message": self.message
        }


@dataclass
class StuckEvent:
    """Agent stuck event."""
    agent_id: str
    reason: str               # Why stuck
    duration_sec: int         # How long stuck
    suggestion: Optional[str] = None  # Suggested action
    error_samples: Optional[List[Dict]] = None  # Error samples

    def to_dict(self) -> Dict:
        """Convert to dictionary for callback."""
        return {
            "agent_id": self.agent_id,
            "reason": self.reason,
            "duration_sec": self.duration_sec,
            "suggestion": self.suggestion,
            "error_samples": self.error_samples
        }


@dataclass
class ResultEvent:
    """Final result event."""
    agent_id: str
    success: bool             # Whether task succeeded
    records: List[Dict]       # Crawled records
    summary: Dict[str, Any]   # Summary statistics
    stuck_info: Optional[StuckEvent] = None  # If failed due to stuck
    error: Optional[str] = None  # Error message if failed

    def to_dict(self) -> Dict:
        """Convert to dictionary for callback."""
        return {
            "agent_id": self.agent_id,
            "success": self.success,
            "records": self.records,
            "summary": self.summary,
            "stuck_info": self.stuck_info.to_dict() if self.stuck_info else None,
            "error": self.error
        }
