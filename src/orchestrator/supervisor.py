"""
Supervisor - Main controller for the Orchestrator.

Coordinates all components: Parser, Scanner, Agent Manager, Monitor.
"""

from typing import Dict, Any, Optional
from .parser import IntentParser
from .scanner import SiteScanner
from .agent_manager import AgentManager
from .monitor import Monitor


class Supervisor:
    """
    Main orchestrator controller.

    Responsibilities:
    - Receive user requests
    - Coordinate intent parsing, site scanning, feasibility decision
    - Manage agent lifecycle
    - Handle result presentation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.parser = IntentParser(self.config.get("intent_parser", {}))
        self.scanner = SiteScanner(self.config.get("scanner", {}))
        self.agent_manager = AgentManager(self.config.get("agent_manager", {}))
        self.monitor = Monitor(self.config.get("monitor", {}))

    async def process_request(self, user_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a user crawling request.

        Args:
            user_request: {
                "user_intent": str,
                "site_url": str,
                "constraints": Optional[Dict]
            }

        Returns:
            Result with records and display manifest
        """
        # Step 1: Parse intent
        intent_result = await self.parser.parse(user_request)
        if not intent_result["should_proceed"]:
            return {"status": "declined", "reason": intent_result.get("reason")}

        # Step 2: Scan site
        scan_result = await self.scanner.scan(
            user_request["site_url"],
            intent_result.get("intent_contract")
        )

        # Step 3: Feasibility decision
        if not self._is_feasible(intent_result, scan_result):
            return {"status": "declined", "reason": "Site not crawlable"}

        # Step 4: Create and run agent
        agent_id = self.agent_manager.create_agent(
            user_request["site_url"],
            {**user_request, "intent_contract": intent_result.get("intent_contract")}
        )

        result = await self.agent_manager.run_agent(agent_id)

        return result

    def _is_feasible(self, intent_result: Dict, scan_result: Dict) -> bool:
        """Decide if crawling is feasible."""
        # Composite score calculation
        composite = (
            0.30 * intent_result.get("intent_fit", 0.5)
            + 0.25 * scan_result.get("field_completeness", 0.5)
            + 0.20 * intent_result.get("confidence", 0.5)
            + 0.15 * scan_result.get("resource_coverage", 0.5)
            - 0.10 * scan_result.get("risk_score", 0.0)
        )
        return composite >= 0.6
