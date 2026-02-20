"""
Explorer - Exploration Phase implementation.

The Explorer is responsible for:
1. Site Mapping: Discover URL structure and page types
2. Dynamic Sampling: Sample representative pages based on user_goal
3. Quality Assessment: Evaluate extracted data quality
4. Report Generation: Create structured Exploration Report
5. Stream Progress: Report detailed progress during exploration

Uses simplified SOOAL (max 2 iterations, sequential attempts).
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, urljoin

from .sampler import Sampler, SamplingStrategy
from .evaluator import Evaluator, QualityMetrics
from .scanner import SiteScanner
from .crawler import Crawler
from .soal.loop import SOOALLoop, SOOALMode


class ExplorationStage(Enum):
    """Exploration stages for progress reporting."""
    INITIALIZING = "initializing"
    SITE_MAPPING = "site_mapping"
    SAMPLING = "sampling"
    EXTRACTING = "extracting"
    EVALUATING = "evaluating"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"


@dataclass
class URLNode:
    """Represents a node in the URL tree."""
    url: str
    depth: int
    page_type: Optional[str] = None
    visited: bool = False
    children: List['URLNode'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteStructure:
    """Site structure mapping result."""
    total_estimated_pages: int
    page_types_found: List[str]
    url_tree: Dict[str, Any]
    recommended_paths: List[str]
    avg_depth: float
    max_depth_discovered: int


@dataclass
class ExplorationProgress:
    """Progress update during exploration."""
    stage: ExplorationStage
    message: str
    urls_discovered: int = 0
    urls_sampled: int = 0
    pages_extracted: int = 0
    quality_score: Optional[float] = None
    current_url: Optional[str] = None


@dataclass
class ExplorationReport:
    """
    Exploration Report - output of the Exploration Phase.

    Contains:
    - Site structure mapping
    - Quality metrics
    - Feasibility assessment
    - Sample data (high-value records)
    - Cost estimates
    - LLM decision
    """
    site_info: Dict[str, Any]
    site_structure: SiteStructure
    quality_metrics: QualityMetrics
    feasibility: Dict[str, Any]
    sample_data: Dict[str, Any]
    cost_estimate: Dict[str, Any]
    llm_decision: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "site_info": self.site_info,
            "site_structure": {
                "total_estimated_pages": self.site_structure.total_estimated_pages,
                "page_types_found": self.site_structure.page_types_found,
                "url_tree": self.site_structure.url_tree,
                "recommended_paths": self.site_structure.recommended_paths,
                "avg_depth": self.site_structure.avg_depth,
                "max_depth_discovered": self.site_structure.max_depth_discovered,
            },
            "quality_metrics": {
                "relevant_ratio": self.quality_metrics.relevant_ratio,
                "avg_quality_score": self.quality_metrics.avg_quality_score,
                "data_types_found": self.quality_metrics.data_types_found,
                "field_completeness": self.quality_metrics.field_completeness,
            },
            "feasibility": self.feasibility,
            "sample_data": self.sample_data,
            "cost_estimate": self.cost_estimate,
            "llm_decision": self.llm_decision,
        }


class Explorer:
    """
    Explorer - Exploration Phase implementation.

    Two-phase execution:
    1. Exploration Phase: Fast discovery and sampling
    2. Decision: LLM decides whether to proceed to Crawl Phase

    Uses simplified SOOAL for quick recovery during exploration.
    """

    def __init__(
        self,
        on_progress: Optional[Callable[[ExplorationProgress], None]] = None,
        exploration_config: Optional[Dict[str, Any]] = None,
    ):
        self.explorer_id = f"explorer_{uuid.uuid4().hex[:8]}"
        self.on_progress = on_progress

        # Configuration
        config = exploration_config or {}
        self.max_discovery_urls = config.get("max_discovery_urls", 200)
        self.max_sample_urls = config.get("max_sample_urls", 50)
        self.max_exploration_depth = config.get("max_exploration_depth", 3)
        self.quality_threshold = config.get("quality_threshold", 0.8)

        # Components
        self.scanner = SiteScanner()
        self.crawler = Crawler()
        self.sampler = Sampler()
        self.evaluator = Evaluator()
        self.soal = SOOALLoop(mode=SOOALMode.SIMPLIFIED)  # Simplified for exploration

        # State
        self._stopped = False
        self._discovered_urls: Dict[str, URLNode] = {}
        self._extracted_records: List[Dict] = []
        self._failures: List[Dict] = []

    async def explore(
        self,
        site_url: str,
        user_goal: str,
        task_params: Optional[Dict[str, Any]] = None,
    ) -> ExplorationReport:
        """
        Execute Exploration Phase.

        Args:
            site_url: Entry URL for the site
            user_goal: User's crawling intent
            task_params: Additional task parameters

        Returns:
            ExplorationReport with findings and LLM decision
        """
        task_params = task_params or {}
        self._emit_progress(ExplorationStage.INITIALIZING, f"Starting exploration of {site_url}")

        try:
            # Step 1: Site Mapping
            self._emit_progress(ExplorationStage.SITE_MAPPING, "Discovering site structure")
            site_structure = await self._map_site_structure(site_url)

            # Step 2: Select sampling strategy (LLM-assisted)
            self._emit_progress(ExplorationStage.SAMPLING, "Selecting sampling strategy")
            sampling_strategy = await self._select_sampling_strategy(
                site_structure, user_goal
            )

            # Step 3: Sample URLs
            sample_urls = await self.sampler.sample(
                list(self._discovered_urls.values()),
                strategy=sampling_strategy,
                max_count=self.max_sample_urls,
                user_goal=user_goal,
            )

            self._emit_progress(
                ExplorationStage.SAMPLING,
                f"Selected {len(sample_urls)} URLs for sampling",
                urls_sampled=len(sample_urls),
            )

            # Step 4: Extract data from samples
            self._emit_progress(ExplorationStage.EXTRACTING, "Extracting data from sampled pages")
            extracted_data = await self._extract_from_samples(sample_urls, task_params)

            # Handle failures with simplified SOOAL
            if self._failures and len(self._failures) >= 5:
                success_rate = len(extracted_data) / len(sample_urls)
                if success_rate < 0.5:
                    self._emit_progress(ExplorationStage.EXTRACTING, "Running simplified recovery")
                    await self._run_simplified_soal()

            # Step 5: Evaluate quality
            self._emit_progress(ExplorationStage.EVALUATING, "Evaluating data quality")
            quality_metrics = await self.evaluator.evaluate_batch(
                extracted_data, user_goal
            )

            # Step 6: Generate report
            self._emit_progress(ExplorationStage.GENERATING_REPORT, "Generating exploration report")
            report = await self._generate_report(
                site_url, user_goal, site_structure, quality_metrics, extracted_data
            )

            self._emit_progress(ExplorationStage.COMPLETED, "Exploration completed")
            return report

        except Exception as e:
            self._emit_progress(ExplorationStage.COMPLETED, f"Exploration failed: {str(e)}")
            raise

    async def _map_site_structure(self, entry_url: str) -> SiteStructure:
        """
        Map site structure by discovering URLs and page types.

        Uses BFS to discover URLs up to max_depth and max_urls.
        """
        parsed = urlparse(entry_url)
        base_domain = parsed.netloc
        visited: Set[str] = set()
        queue: List[Tuple[str, int]] = [(entry_url, 0)]

        page_types: Set[str] = set()
        url_tree: Dict[str, Any] = {}
        path_counts: Dict[str, int] = {}

        while queue and not self._stopped:
            url, depth = queue.pop(0)

            if url in visited or depth > self.max_exploration_depth:
                continue

            if len(visited) >= self.max_discovery_urls:
                break

            visited.add(url)
            self._emit_progress(
                ExplorationStage.SITE_MAPPING,
                f"Discovered {len(visited)} URLs",
                urls_discovered=len(visited),
                current_url=url,
            )

            # Fetch page and detect page type
            try:
                result = await self.crawler.crawl(url, strategy="http")
                if result.get("success"):
                    page_type = self._detect_page_type(url, result)
                    page_types.add(page_type)

                    # Store URL node
                    node = URLNode(
                        url=url,
                        depth=depth,
                        page_type=page_type,
                        visited=True,
                        metadata={"title": result.get("title", "")},
                    )
                    self._discovered_urls[url] = node

                    # Track path patterns
                    path = self._get_url_pattern(url, base_domain)
                    path_counts[path] = path_counts.get(path, 0) + 1

                    # Discover links
                    if depth < self.max_exploration_depth:
                        links = await self.crawler.discover_links(url, strategy="http")
                        for link in links:
                            link_parsed = urlparse(link)
                            if link_parsed.netloc == base_domain and link not in visited:
                                queue.append((link, depth + 1))

            except Exception as e:
                self._failures.append({"url": url, "error": str(e), "stage": "mapping"})

        # Build URL tree structure
        url_tree = self._build_url_tree(self._discovered_urls)

        # Calculate recommended paths (high-frequency patterns)
        recommended_paths = sorted(
            path_counts.items(), key=lambda x: x[1], reverse=True
        )[:5]
        recommended_paths = [path for path, _ in recommended_paths]

        # Calculate depth statistics
        depths = [node.depth for node in self._discovered_urls.values()]
        avg_depth = sum(depths) / len(depths) if depths else 0
        max_depth = max(depths) if depths else 0

        return SiteStructure(
            total_estimated_pages=len(visited) * 3,  # Rough estimate
            page_types_found=list(page_types),
            url_tree=url_tree,
            recommended_paths=recommended_paths,
            avg_depth=avg_depth,
            max_depth_discovered=max_depth,
        )

    def _detect_page_type(self, url: str, crawl_result: Dict) -> str:
        """Detect page type from URL and content."""
        url_lower = url.lower()

        # Pattern-based detection
        if any(p in url_lower for p in ["/article/", "/post/", "/news/", "/blog/", "/detail/"]):
            return "article"
        elif any(p in url_lower for p in ["/category/", "/tag/", "/type/"]):
            return "category"
        elif any(p in url_lower for p in ["page", "p=", "/page/"]):
            return "pagination"
        elif any(p in url_lower for p in ["/list/", "/index", "/search/"]):
            return "listing"
        elif any(p in url_lower for p in ["/about", "/contact", "/info"]):
            return "static"
        else:
            return "unknown"

    def _get_url_pattern(self, url: str, base_domain: str) -> str:
        """Extract URL pattern for classification."""
        parsed = urlparse(url)
        path = parsed.path

        # Replace IDs and numbers with placeholders
        import re
        pattern = re.sub(r'/\d+', '/{id}', path)
        pattern = re.sub(r'/[a-f0-9]{8,}', '/{uuid}', pattern)

        return pattern

    def _build_url_tree(self, url_nodes: Dict[str, URLNode]) -> Dict[str, Any]:
        """Build hierarchical tree from discovered URLs."""
        # Simplified tree representation
        tree = {"root": []}

        for url, node in url_nodes.items():
            path = urlparse(url).path
            parts = [p for p in path.split('/') if p]

            current = tree
            for i, part in enumerate(parts):
                if part not in current:
                    current[part] = {}
                current = current[part]

        return tree

    async def _select_sampling_strategy(
        self,
        site_structure: SiteStructure,
        user_goal: str,
    ) -> SamplingStrategy:
        """
        Select sampling strategy based on site structure and user goal.

        Uses LLM to decide between:
        - REPRESENTATIVE: Cover different page types
        - NEED_BASED: Prioritize pages matching user_goal
        - HIGH_QUALITY: Focus on quality indicators
        """
        # For now, use heuristic-based selection
        # In production, this would use LLM

        page_types = site_structure.page_types_found

        if "article" in page_types and "listing" in page_types:
            return SamplingStrategy.REPRESENTATIVE
        elif "article" in page_types:
            return SamplingStrategy.NEED_BASED
        else:
            return SamplingStrategy.REPRESENTATIVE

    async def _extract_from_samples(
        self,
        sample_urls: List[str],
        task_params: Dict[str, Any],
    ) -> List[Dict]:
        """Extract data from sampled URLs."""
        extracted = []

        for url in sample_urls:
            if self._stopped:
                break

            self._emit_progress(
                ExplorationStage.EXTRACTING,
                f"Extracting from {url}",
                pages_extracted=len(extracted),
                current_url=url,
            )

            try:
                result = await self.crawler.crawl(url, strategy="http")
                if result.get("success"):
                    record = {
                        "url": url,
                        "url_hash": hashlib.md5(url.encode()).hexdigest(),
                        "title": result.get("title", ""),
                        "content": result.get("content", ""),
                        "metadata": result.get("metadata", {}),
                        "crawl_timestamp": datetime.now().isoformat(),
                    }
                    extracted.append(record)
                    self._extracted_records.append(record)
                else:
                    self._failures.append({"url": url, "error": result.get("error", "Unknown")})
            except Exception as e:
                self._failures.append({"url": url, "error": str(e)})

        return extracted

    async def _run_simplified_soal(self) -> None:
        """
        Run simplified SOOAL for exploration phase.

        Sequential attempts (max 2):
        1. Switch strategy (http -> browser)
        2. Change user agent
        3. Add proxy
        4. Slow down
        """
        # Simplified recovery: just try browser strategy
        # Full SOOAL is too expensive for exploration
        retries = [
            {"strategy": "browser"},
            {"strategy": "browser", "delay": 2},
        ]

        for retry_config in retries:
            if self._stopped:
                break

            # Retry failed URLs with new config
            for failure in self._failures[:]:
                url = failure.get("url")
                if not url or url in [r.get("url") for r in self._extracted_records]:
                    continue

                try:
                    result = await self.crawler.crawl(url, strategy=retry_config["strategy"])
                    if result.get("success"):
                        record = {
                            "url": url,
                            "url_hash": hashlib.md5(url.encode()).hexdigest(),
                            "title": result.get("title", ""),
                            "content": result.get("content", ""),
                            "metadata": result.get("metadata", {}),
                            "crawl_timestamp": datetime.now().isoformat(),
                        }
                        self._extracted_records.append(record)
                        self._failures.remove(failure)
                except Exception:
                    continue

    async def _generate_report(
        self,
        site_url: str,
        user_goal: str,
        site_structure: SiteStructure,
        quality_metrics: QualityMetrics,
        extracted_data: List[Dict],
    ) -> ExplorationReport:
        """Generate final Exploration Report."""
        # Get site key
        parsed = urlparse(site_url)
        site_key = parsed.netloc

        # Feasibility assessment
        feasibility = await self._assess_feasibility(site_structure, quality_metrics)

        # Sample data (high-value records)
        high_value_samples = [
            r for r in extracted_data
            if r.get("quality_score", 0) > self.quality_threshold
        ]

        sample_data = {
            "high_value_samples": high_value_samples[:10],  # Top 10 for preview
            "sample_count": len(extracted_data),
            "preview": extracted_data[:5],  # First 5 for quick preview
        }

        # Cost estimate
        estimated_time = (site_structure.total_estimated_pages / 10)  # 10 pages/min
        cost_estimate = {
            "estimated_time_minutes": int(estimated_time),
            "estimated_tokens": site_structure.total_estimated_pages * 500,
            "estimated_cost_usd": round(site_structure.total_estimated_pages * 0.001, 2),
        }

        # LLM decision
        llm_decision = await self._make_llm_decision(
            site_structure, quality_metrics, feasibility, cost_estimate
        )

        # Site info
        site_info = {
            "site_key": site_key,
            "entry_url": site_url,
            "exploration_timestamp": datetime.now().isoformat(),
            "explorer_id": self.explorer_id,
        }

        return ExplorationReport(
            site_info=site_info,
            site_structure=site_structure,
            quality_metrics=quality_metrics,
            feasibility=feasibility,
            sample_data=sample_data,
            cost_estimate=cost_estimate,
            llm_decision=llm_decision,
        )

    async def _assess_feasibility(
        self,
        site_structure: SiteStructure,
        quality_metrics: QualityMetrics,
    ) -> Dict[str, Any]:
        """Assess crawling feasibility."""
        return {
            "anti_bot_level": self._assess_anti_bot(),
            "js_render_ratio": self._estimate_js_ratio(),
            "login_required": self._check_login_required(),
            "rate_limit_detected": len(self._failures) > 0,
            "recommended_strategy": self._recommend_strategy(),
        }

    def _assess_anti_bot(self) -> str:
        """Assess anti-bot level."""
        failure_rate = len(self._failures) / max(len(self._discovered_urls), 1)
        if failure_rate > 0.5:
            return "extreme"
        elif failure_rate > 0.2:
            return "high"
        elif failure_rate > 0.05:
            return "medium"
        return "low"

    def _estimate_js_ratio(self) -> float:
        """Estimate ratio of pages requiring JS rendering."""
        # Simplified: based on browser strategy success rate
        return 0.0  # TODO: Implement actual detection

    def _check_login_required(self) -> bool:
        """Check if login is required."""
        # Look for login redirects or authentication prompts
        for failure in self._failures:
            error = failure.get("error", "").lower()
            if "login" in error or "auth" in error or "unauthorized" in error:
                return True
        return False

    def _recommend_strategy(self) -> str:
        """Recommend crawling strategy."""
        if self._assess_anti_bot() in ["high", "extreme"]:
            return "browser"
        return "http"

    async def _make_llm_decision(
        self,
        site_structure: SiteStructure,
        quality_metrics: QualityMetrics,
        feasibility: Dict[str, Any],
        cost_estimate: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Make LLM-based decision on whether to proceed to Crawl Phase.

        Decision logic:
        - relevant_ratio < 0.3 → terminate (low relevance)
        - avg_quality_score < 0.6 → terminate (poor quality)
        - total_pages > 10000 → sampled crawl
        - Otherwise → full crawl
        """
        # Decision rules (could be LLM-based in production)
        relevant_ratio = quality_metrics.relevant_ratio
        quality_score = quality_metrics.avg_quality_score
        total_pages = site_structure.total_estimated_pages

        if relevant_ratio < 0.3:
            return {
                "should_crawl": False,
                "crawl_mode": "none",
                "reasoning": f"Low relevance ({relevant_ratio:.1%}) - site content doesn't match user goal",
            }
        elif quality_score < 0.6:
            return {
                "should_crawl": False,
                "crawl_mode": "none",
                "reasoning": f"Poor data quality ({quality_score:.2f}) - extraction not working well",
            }
        elif feasibility["anti_bot_level"] == "extreme":
            return {
                "should_crawl": False,
                "crawl_mode": "none",
                "reasoning": "Extreme anti-bot measures - crawling not feasible",
            }
        elif total_pages > 10000:
            return {
                "should_crawl": True,
                "crawl_mode": "sampled",
                "recommended_limit": 2000,
                "reasoning": f"Large site ({total_pages} pages) - recommend sampled crawl of 2000 pages",
            }
        else:
            return {
                "should_crawl": True,
                "crawl_mode": "full",
                "recommended_limit": total_pages,
                "reasoning": f"Good match ({relevant_ratio:.1%}, quality {quality_score:.2f}) - proceed with full crawl",
            }

    def _emit_progress(
        self,
        stage: ExplorationStage,
        message: str,
        **kwargs
    ) -> None:
        """Emit progress update."""
        if self.on_progress:
            progress = ExplorationProgress(
                stage=stage,
                message=message,
                **kwargs
            )
            self.on_progress(progress)

    def cancel(self) -> None:
        """Cancel exploration."""
        self._stopped = True


import hashlib
