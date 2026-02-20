"""
SiteAgent - Single-site intelligent crawling agent with Two-Phase Architecture.

Positioning:
- Disposable (用完即弃): Each instance is new, no persistent state
- Two-Phase Execution: Exploration Phase → LLM Decision → Crawl Phase (optional)
- Goal-Oriented: Explores site, evaluates quality, decides whether to crawl
- Autonomous: Makes decisions independently without asking user
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from .callbacks import ProgressEvent, StuckEvent, ResultEvent
from .scanner import SiteScanner
from .crawler import Crawler
from .explorer import Explorer, ExplorationReport, ExplorationStage, ExplorationProgress
from .sampler import SamplingStrategy
from .evaluator import Evaluator
from .soal.loop import SOOALLoop, SOOALMode
from .knowledge import RuntimeKnowledge

from models.crawl import CrawlResultWithReport, ExplorationReport as ModelExplorationReport


class AgentState(Enum):
    """Agent states."""
    IDLE = "idle"
    EXPLORING = "exploring"
    EXPLORATION_COMPLETED = "exploration_completed"
    CRAWLING = "crawling"
    PAUSED = "paused"
    STUCK = "stuck"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TERMINATED = "terminated"  # Terminated after exploration (LLM decision)


@dataclass
class AgentStatus:
    """Current agent status."""
    state: AgentState
    crawled: int = 0
    total: int = 0
    current_url: Optional[str] = None
    error_count: int = 0
    exploration_stage: Optional[str] = None


class SiteAgent:
    """
    Single-site intelligent crawling agent with Two-Phase Architecture.

    Phase 1 - Exploration Phase:
    - Site mapping (discover URL structure)
    - Dynamic sampling (based on user goal)
    - Quality assessment (L1+L2+L3)
    - Generate Exploration Report

    LLM Decision:
    - Analyze Exploration Report
    - Decide: terminate / sampled crawl / full crawl

    Phase 2 - Crawl Phase (if LLM decides yes):
    - Deep crawling with complete SOOAL
    - Final quality verification
    - Return results

    Communication via callbacks:
    - on_progress: Progress updates (including exploration progress)
    - on_stuck: When agent is stuck and may need external intervention
    - on_result: Final result (success or failure)
    """

    def __init__(
        self,
        site_url: str,
        on_progress: Optional[Callable[[Dict], None]] = None,
        on_stuck: Optional[Callable[[str], None]] = None,
        on_result: Optional[Callable[[Dict], None]] = None,
        on_exploration_progress: Optional[Callable[[Dict], None]] = None,
        **kwargs
    ):
        self.site_url = site_url
        self.agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        self._callbacks = {
            "on_progress": on_progress,
            "on_stuck": on_stuck,
            "on_result": on_result,
            "on_exploration_progress": on_exploration_progress,
        }

        # State
        self._state = AgentState.IDLE
        self._stopped = False
        self._paused = False

        # Components
        self.scanner = SiteScanner()
        self.crawler = Crawler()
        self.explorer = Explorer(on_progress=self._on_exploration_progress)
        self.evaluator = Evaluator()
        self.soal_complete = SOOALLoop(mode=SOOALMode.COMPLETE)
        self.knowledge = RuntimeKnowledge()

        # Tracking
        self.status = AgentStatus(state=AgentState.IDLE)
        self._records: List[Dict] = []
        self._failures: List[Dict] = []
        self._exploration_report: Optional[ExplorationReport] = None

    async def run(self, task_params: Dict[str, Any]) -> Dict:
        """
        Execute two-phase crawling task.

        Args:
            task_params: {
                "site_url": str,
                "intent": str,  # User goal
                "max_pages": Optional[int],
                "depth_limit": Optional[int],
                "exploration_config": Optional[Dict],
                ...
            }

        Returns:
            Result dictionary with records, exploration report, and summary
        """
        self._state = AgentState.RUNNING
        user_goal = task_params.get("intent", "")
        max_pages = task_params.get("max_pages", 100)
        depth_limit = task_params.get("depth_limit", 3)
        exploration_config = task_params.get("exploration_config", {})

        try:
            # ===================================================================
            # Phase 1: Exploration Phase
            # ===================================================================
            self._state = AgentState.EXPLORING
            self._emit_progress("Exploration Phase: Starting site exploration")

            exploration_report = await self.explorer.explore(
                site_url=self.site_url,
                user_goal=user_goal,
                task_params=task_params,
            )

            # Convert to model format
            from models.crawl import (
                SiteStructure, QualityMetrics, ExplorationReport as ModelExplorationReport
            )

            model_report = ModelExplorationReport(
                site_info=exploration_report.site_info,
                site_structure=SiteStructure(**exploration_report.site_structure.__dict__),
                quality_metrics=QualityMetrics(**exploration_report.quality_metrics.__dict__),
                feasibility=exploration_report.feasibility,
                sample_data=exploration_report.sample_data,
                cost_estimate=exploration_report.cost_estimate,
                llm_decision=exploration_report.llm_decision,
            )

            self._exploration_report = exploration_report
            self._state = AgentState.EXPLORATION_COMPLETED

            # ===================================================================
            # LLM Decision: Analyze report and decide next action
            # ===================================================================
            llm_decision = exploration_report.llm_decision
            should_crawl = llm_decision.get("should_crawl", False)
            crawl_mode = llm_decision.get("crawl_mode", "none")
            reasoning = llm_decision.get("reasoning", "")

            self._emit_progress(f"LLM Decision: {reasoning}")

            if not should_crawl:
                # Terminate after exploration
                self._state = AgentState.TERMINATED
                result = self._build_result(
                    success=True,  # Exploration completed successfully
                    exploration_report=model_report,
                    termination_reason=reasoning,
                )
                self._emit_result(result)
                return result

            # ===================================================================
            # Phase 2: Crawl Phase (if LLM decided to proceed)
            # ===================================================================
            self._state = AgentState.CRAWLING
            self._emit_progress(f"Crawl Phase: Starting {crawl_mode} crawl")

            # Determine limit based on LLM decision
            if crawl_mode == "sampled":
                crawl_limit = min(llm_decision.get("recommended_limit", 2000), max_pages)
            else:  # full
                crawl_limit = max_pages

            # Execute crawl
            await self._execute_crawl(
                intent=user_goal,
                max_pages=crawl_limit,
                depth_limit=depth_limit,
                strategy=exploration_report.feasibility.get("recommended_strategy", "http"),
            )

            # Check if SOOAL is needed
            if self._should_trigger_soal():
                self._emit_progress("Running complete SOOAL for recovery")
                await self.soal_complete.run(self._failures, self.knowledge)

            # Success
            self._state = AgentState.COMPLETED
            result = self._build_result(
                success=True,
                exploration_report=model_report,
            )
            self._emit_result(result)
            return result

        except Exception as e:
            self._state = AgentState.FAILED
            result = self._build_result(
                success=False,
                error=str(e),
                exploration_report=self._exploration_report,
            )
            self._emit_result(result)
            return result

    async def _execute_crawl(
        self,
        intent: str,
        max_pages: int,
        depth_limit: int,
        strategy: str,
    ) -> None:
        """
        Execute the crawl phase with deep exploration.

        Uses discovered URLs from exploration and applies full SOOAL.
        """
        # Use URLs discovered during exploration as starting point
        if self._exploration_report:
            # Get high-value paths from exploration
            recommended_paths = self._exploration_report.site_structure.recommended_paths

            # Start with recommended paths
            start_urls = self._generate_urls_from_paths(recommended_paths)
        else:
            start_urls = [self.site_url]

        visited = set()
        queue = [(url, 0) for url in start_urls]

        while queue and len(self._records) < max_pages and not self._stopped:
            url, depth = queue.pop(0)

            if url in visited or depth > depth_limit:
                continue

            visited.add(url)
            self.status.current_url = url

            # Crawl current page
            try:
                result = await self.crawler.crawl(url, strategy=strategy)
                if result.get("success"):
                    record = {
                        "url": url,
                        "url_hash": self._hash_url(url),
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                        "metadata": result.get("metadata", {}),
                        "crawl_timestamp": datetime.now().isoformat(),
                        "strategy_used": strategy,
                    }
                    self._records.append(record)
                    self.status.crawled += 1
                    self._emit_progress()
                else:
                    self._failures.append(result)
                    self.status.error_count += 1
            except Exception as e:
                self._failures.append({"url": url, "error": str(e)})
                self.status.error_count += 1

            # Discover links for deeper crawling
            if depth < depth_limit and len(self._records) < max_pages:
                try:
                    links = await self.crawler.discover_links(url, strategy=strategy)
                    filtered_links = self._filter_links(links, intent, visited)
                    for link in filtered_links[:10]:  # Limit per page
                        queue.append((link, depth + 1))
                except Exception:
                    pass

    def _generate_urls_from_paths(self, paths: List[str]) -> List[str]:
        """Generate full URLs from path patterns."""
        base_url = self.site_url.rstrip("/")
        return [f"{base_url}{path}" for path in paths if path]

    def _filter_links(self, links: List[str], intent: str, visited: set) -> List[str]:
        """Filter links worth crawling."""
        filtered = []
        blacklist = ["/login", "/admin", "/register", "/account", "/search"]

        for link in links:
            if link in visited:
                continue

            # Check same domain
            if not link.startswith(self.site_url.split("/")[2]):
                continue

            # Skip blacklisted
            if any(path in link.lower() for path in blacklist):
                continue

            filtered.append(link)

        return filtered

    def _hash_url(self, url: str) -> str:
        """Generate URL hash for deduplication."""
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()

    def _should_trigger_soal(self) -> bool:
        """Check if SOOAL should be triggered."""
        if self.status.error_count < 5:
            return False

        total_attempts = self.status.crawled + self.status.error_count
        failure_rate = self.status.error_count / total_attempts if total_attempts > 0 else 0

        return failure_rate >= 0.5

    def _build_result(
        self,
        success: bool,
        exploration_report: Optional[Any] = None,
        termination_reason: Optional[str] = None,
        error: Optional[str] = None,
    ) -> Dict:
        """Build result dictionary."""
        summary = {
            "total_records": len(self._records),
            "error_count": self.status.error_count,
            "state": self._state.value,
            "phase": "exploration" if self._state == AgentState.TERMINATED else "crawl",
        }

        if termination_reason:
            summary["termination_reason"] = termination_reason

        return {
            "success": success,
            "agent_id": self.agent_id,
            "site_url": self.site_url,
            "records": self._records,
            "exploration_report": exploration_report.to_dict() if exploration_report else None,
            "summary": summary,
            "error": error
        }

    def _on_exploration_progress(self, progress: ExplorationProgress) -> None:
        """Handle exploration progress updates."""
        self.status.exploration_stage = progress.stage.value

        if self._callbacks["on_exploration_progress"]:
            self._callbacks["on_exploration_progress"](progress.to_dict())

        # Also emit as general progress
        self._emit_progress(f"[{progress.stage.value.upper()}] {progress.message}")

    def _emit_progress(self, message: Optional[str] = None) -> None:
        """Emit progress callback."""
        if self._callbacks["on_progress"]:
            data = {
                "agent_id": self.agent_id,
                "crawled": self.status.crawled,
                "total": self.status.total,
                "state": self._state.value,
                "exploration_stage": self.status.exploration_stage,
            }
            if message:
                data["message"] = message
            self._callbacks["on_progress"](data)

    def _emit_stuck(self, reason: str) -> None:
        """Emit stuck callback."""
        if self._callbacks["on_stuck"]:
            self._callbacks["on_stuck"](reason)

    def _emit_result(self, result: Dict) -> None:
        """Emit result callback."""
        if self._callbacks["on_result"]:
            self._callbacks["on_result"](result)

    def cancel(self, reason: str = "user_cancelled") -> None:
        """Cancel the running task."""
        self._stopped = True
        self.explorer.cancel()
        self._state = AgentState.CANCELLED

    def pause(self) -> None:
        """Pause the current task."""
        self._paused = True
        self._state = AgentState.PAUSED

    def resume(self) -> None:
        """Resume a paused task."""
        self._paused = False
        if self._state == AgentState.PAUSED:
            self._state = AgentState.RUNNING

    def get_status(self) -> Dict:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "state": self._state.value,
            "crawled": self.status.crawled,
            "total": self.status.total,
            "current_url": self.status.current_url,
            "error_count": self.status.error_count,
            "exploration_stage": self.status.exploration_stage,
        }
