"""
Monitor - Real-time status monitoring.

Tracks:
- Active agents
- Crawl progress
- Stuck events
- Resource usage
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ProgressEvent:
    """Progress update event."""
    agent_id: str
    crawled: int
    total: int
    current_speed: Optional[float] = None
    stage: str = "crawling"
    message: Optional[str] = None


@dataclass
class StuckEvent:
    """Agent stuck event."""
    agent_id: str
    reason: str
    duration_sec: int
    suggestion: Optional[str] = None
    error_samples: Optional[List[Dict]] = None


class Monitor:
    """Real-time status monitoring."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.metrics: Dict[str, Any] = {}
        self.active_agents: Dict[str, Dict] = {}
        self.stuck_agents: List[str] = []
        self.events: List[Dict] = []

    def track_progress(self, event: ProgressEvent) -> None:
        """Track agent progress."""
        self.active_agents[event.agent_id] = {
            "crawled": event.crawled,
            "total": event.total,
            "speed": event.current_speed,
            "stage": event.stage,
            "updated_at": datetime.now().isoformat()
        }
        self._add_event("progress_update", event.agent_id, event)

    def track_stuck(self, event: StuckEvent) -> None:
        """Track stuck events."""
        if event.agent_id not in self.stuck_agents:
            self.stuck_agents.append(event.agent_id)
        self._add_event("agent_stuck", event.agent_id, event)

    def get_dashboard(self) -> Dict[str, Any]:
        """Get current dashboard state."""
        return {
            "active_agents": len(self.active_agents),
            "total_crawled": sum(a.get("crawled", 0) for a in self.active_agents.values()),
            "stuck_agents": self.stuck_agents.copy(),
            "recent_events": self.events[-20:],
            "resource_usage": self._get_resource_usage()
        }

    def _add_event(self, event_type: str, agent_id: str, data: Any) -> None:
        """Add event to history."""
        self.events.append({
            "type": event_type,
            "agent_id": agent_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })

    def _get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage."""
        # TODO: Implement actual resource monitoring
        return {"cpu": 0.0, "memory": 0.0, "bandwidth": 0.0}
