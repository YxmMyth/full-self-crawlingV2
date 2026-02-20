"""
Agent Manager - Manages SiteAgent lifecycle.

Responsibilities:
- Create agent instances
- Start/cancel/pause/resume agents
- Handle agent callbacks (progress, stuck, result)
"""

from typing import Dict, Any, Optional, Callable
import uuid


class AgentManager:
    """Manage SiteAgent lifecycle."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.agents: Dict[str, "SiteAgent"] = {}
        self.agent_states: Dict[str, str] = {}  # agent_id -> state

    def create_agent(self, site_url: str, task_params: Dict[str, Any]) -> str:
        """
        Create new agent instance.

        Returns:
            agent_id: Unique identifier for the agent
        """
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"

        # Import here to avoid circular dependency
        from agent.agent import SiteAgent

        self.agents[agent_id] = SiteAgent(
            site_url=site_url,
            on_progress=lambda data: self._handle_progress(agent_id, data),
            on_stuck=lambda reason: self._handle_stuck(agent_id, reason),
            on_result=lambda data: self._handle_result(agent_id, data)
        )
        self.agent_states[agent_id] = "idle"

        return agent_id

    async def start_agent(self, agent_id: str) -> None:
        """Start agent execution."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")

        self.agent_states[agent_id] = "running"
        agent = self.agents[agent_id]
        # TODO: Run agent with task params
        # await agent.run(task_params)

    def cancel_agent(self, agent_id: str, reason: str = "user_cancelled") -> None:
        """Cancel running agent."""
        if agent_id in self.agents:
            self.agents[agent_id].cancel(reason)
            self.agent_states[agent_id] = "cancelled"

    def pause_agent(self, agent_id: str) -> None:
        """Pause agent."""
        if agent_id in self.agents:
            self.agents[agent_id].pause()
            self.agent_states[agent_id] = "paused"

    def resume_agent(self, agent_id: str) -> None:
        """Resume paused agent."""
        if agent_id in self.agents:
            self.agents[agent_id].resume()
            self.agent_states[agent_id] = "running"

    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """Get current agent status."""
        if agent_id not in self.agents:
            raise ValueError(f"Agent {agent_id} not found")
        return self.agents[agent_id].get_status()

    async def run_agent(self, agent_id: str) -> Dict[str, Any]:
        """Run agent and wait for result."""
        # TODO: Implement actual agent execution
        return {"success": True, "records": []}

    def _handle_progress(self, agent_id: str, data: Dict) -> None:
        """Handle progress updates from agent."""
        # Update monitor/UI
        pass

    def _handle_stuck(self, agent_id: str, reason: str) -> None:
        """Handle agent stuck event."""
        # Notify user/monitor
        pass

    def _handle_result(self, agent_id: str, result: Dict) -> None:
        """Handle final result from agent."""
        # Process and display results
        pass
