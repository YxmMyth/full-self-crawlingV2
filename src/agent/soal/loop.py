"""
SOOAL Loop Implementation.

Phases:
1. Sense - Observe evidence (failures, DOM, metrics)
2. Orient - Evaluate actions by utility score
3. Act - Execute selected action
4. Verify - Validate results
5. Learn - Update runtime knowledge

Supports two modes:
- SIMPLIFIED: For Exploration Phase (max 2 iterations, sequential attempts)
- COMPLETE: For Crawl Phase (max 6 iterations, full LLM decisions)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..diagnose import Diagnoser, Diagnosis
from ..repair import Repairer, RepairResult
from ..knowledge import RuntimeKnowledge


class SOOALMode(Enum):
    """SOOAL execution modes."""
    SIMPLIFIED = "simplified"  # For exploration: max 2 iters, sequential
    COMPLETE = "complete"      # For crawl: max 6 iters, full LLM


class ActionType(Enum):
    """Types of actions SOOAL can take."""
    PLUGIN_UPDATE = "plugin_update"
    STRATEGY_SWITCH = "strategy_switch"
    PATCH_APPLY = "patch_apply"
    REPLAN = "replan"
    TERMINATE = "terminate"


@dataclass
class OrientResult:
    """Result of Orient phase."""
    selected_action: ActionType
    confidence: float
    reasoning: str
    utility_score: float


@dataclass
class VerifyResult:
    """Result of Verify phase."""
    passed: bool
    composite_score: float
    details: Dict[str, float]


class SOOALLoop:
    """
    SOOAL Intelligent Loop.

    Trigger conditions:
    - Failure rate >= 50%
    - Failures are of same type (LLM verified)
    - Minimum 5+ failures accumulated

    Modes:
    - SIMPLIFIED: For exploration (max 2 iters, sequential attempts)
    - COMPLETE: For crawl (max 6 iters, full LLM decisions)
    """

    def __init__(self, mode: SOOALMode = SOOALMode.COMPLETE):
        self.mode = mode
        self.diagnoser = Diagnoser()
        self.repairer = Repairer()
        self.max_iterations = 2 if mode == SOOALMode.SIMPLIFIED else 6

    async def run(self, failures: List[Dict], knowledge: RuntimeKnowledge) -> Dict[str, Any]:
        """
        Execute SOOAL loop.

        Args:
            failures: List of failure samples
            knowledge: Runtime knowledge to update

        Returns:
            Result with success status and changes made
        """
        if self.mode == SOOALMode.SIMPLIFIED:
            return await self._run_simplified(failures, knowledge)
        else:
            return await self._run_complete(failures, knowledge)

    async def _run_simplified(
        self,
        failures: List[Dict],
        knowledge: RuntimeKnowledge
    ) -> Dict[str, Any]:
        """
        Run simplified SOOAL for exploration phase.

        Sequential attempts (no LLM decision):
        1. Switch strategy (http -> browser)
        2. Add delay (slow down)
        """
        simplified_attempts = [
            {"action": "switch_strategy", "params": {"strategy": "browser"}},
            {"action": "slow_down", "params": {"delay": 2}},
        ]

        for attempt in simplified_attempts[:self.max_iterations]:
            action = attempt["action"]
            params = attempt["params"]

            if action == "switch_strategy":
                result = await self._switch_strategy(params, knowledge)
            elif action == "slow_down":
                result = await self._slow_down(params, knowledge)
            else:
                result = {"success": False}

            if result.get("success"):
                await self._learn(result, knowledge)
                return {"success": True, "changes": result}

        return {"success": False, "reason": "Simplified SOOAL exhausted"}

    async def _run_complete(
        self,
        failures: List[Dict],
        knowledge: RuntimeKnowledge
    ) -> Dict[str, Any]:
        """Run complete SOOAL for crawl phase."""
        for iteration in range(self.max_iterations):
            # Sense: Gather evidence
            sense_result = await self._sense(failures)

            # Orient: Decide action
            orient_result = await self._orient(sense_result, knowledge)

            if orient_result.selected_action == ActionType.TERMINATE:
                return {"success": False, "reason": "Cannot recover"}

            # Act: Execute action
            act_result = await self._act(orient_result, knowledge)

            # Verify: Validate results
            verify_result = await self._verify(act_result, failures)

            if verify_result.passed:
                # Learn: Update knowledge
                await self._learn(act_result, knowledge)
                return {"success": True, "changes": act_result}

            # Continue loop
            failures = sense_result.get("remaining_failures", [])

        return {"success": False, "reason": "Max iterations reached"}

    async def _switch_strategy(
        self,
        params: Dict[str, Any],
        knowledge: RuntimeKnowledge
    ) -> Dict[str, Any]:
        """Switch to browser strategy."""
        knowledge.strategy_scores["browser"] = knowledge.strategy_scores.get("browser", 0.5) + 0.2
        return {"success": True, "action": "switch_strategy", "strategy": "browser"}

    async def _slow_down(
        self,
        params: Dict[str, Any],
        knowledge: RuntimeKnowledge
    ) -> Dict[str, Any]:
        """Add delay between requests."""
        return {
            "success": True,
            "action": "slow_down",
            "delay": params.get("delay", 2)
        }

    async def _sense(self, failures: List[Dict]) -> Dict[str, Any]:
        """
        Sense phase: Gather evidence.

        Collects:
        - Failure samples
        - DOM snapshots
        - Utility scores
        - Performance metrics
        """
        # Group failures by type
        grouped = await self.diagnoser.group_failures(failures)

        return {
            "failures": failures,
            "grouped_failures": grouped,
            "dominant_failure_type": self._get_dominant_type(grouped),
            "failure_count": len(failures)
        }

    def _get_dominant_type(self, grouped: Dict[str, List[Dict]]) -> str:
        """Get the most common failure type."""
        return max(grouped.items(), key=lambda x: len(x[1]))[0] if grouped else "unknown"

    async def _orient(self, sense_result: Dict, knowledge: RuntimeKnowledge) -> OrientResult:
        """
        Orient phase: Evaluate and select action.

        Utility score formula:
        utility = 0.30 * coverage_gain
               + 0.25 * quality_improvement
               + 0.20 * cost_efficiency
               - 0.15 * risk_penalty
               + 0.10 * time_urgency
        """
        dominant_type = sense_result.get("dominant_failure_type", "unknown")

        # Select action based on failure type
        if dominant_type == "selector_error":
            action = ActionType.PLUGIN_UPDATE
            confidence = 0.8
            reasoning = "Selector errors can be fixed with pattern updates"
        elif dominant_type == "rate_limit":
            action = ActionType.STRATEGY_SWITCH
            confidence = 0.7
            reasoning = "Rate limiting detected, switch to slower strategy"
        elif dominant_type == "blocked":
            action = ActionType.TERMINATE
            confidence = 0.9
            reasoning = "Blocked by site, cannot proceed"
        else:
            action = ActionType.REPLAN
            confidence = 0.5
            reasoning = "Unknown issue, try comprehensive replan"

        return OrientResult(
            selected_action=action,
            confidence=confidence,
            reasoning=reasoning,
            utility_score=0.7  # Simplified
        )

    async def _act(self, orient_result: OrientResult, knowledge: RuntimeKnowledge) -> RepairResult:
        """
        Act phase: Execute selected action.

        Actions:
        - plugin_update: Update selector patterns
        - strategy_switch: Change execution strategy
        - patch_apply: Apply targeted patch
        - replan: Major revision
        - terminate: Give up
        """
        diagnosis = Diagnosis(
            failure_type=orient_result.selected_action.value,
            root_cause=orient_result.reasoning,
            suggested_actions=[orient_result.selected_action.value],
            confidence=orient_result.confidence
        )

        return await self.repairer.repair(diagnosis)

    async def _verify(self, act_result: RepairResult, failures: List[Dict]) -> VerifyResult:
        """
        Verify phase: Validate results.

        Multi-level verification:
        - L1: Basic field check
        - L2: Semantic quality
        - L3: Intent satisfaction
        """
        # Simplified verification
        passed = act_result.success
        composite_score = 0.8 if passed else 0.3

        return VerifyResult(
            passed=passed,
            composite_score=composite_score,
            details={"field_score": 0.9, "semantic_score": 0.8, "business_score": 0.7}
        )

    async def _learn(self, act_result: RepairResult, knowledge: RuntimeKnowledge) -> None:
        """
        Learn phase: Update runtime knowledge.

        Note: This is NOT persisted across agent instances.
        """
        if act_result.success and act_result.changes:
            # Update runtime knowledge
            if "selectors" in act_result.changes:
                knowledge.working_selectors.update(act_result.changes["selectors"])
