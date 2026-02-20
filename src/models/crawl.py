"""
Crawl data models.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class CrawlStatus(Enum):
    """Status of a crawl task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    STUCK = "stuck"


class StrategyType(Enum):
    """Crawling strategy types."""
    HTTP = "http"
    BROWSER = "browser"
    API = "api"
    CUSTOM = "custom"


@dataclass
class CrawlRecord:
    """Single crawled record."""
    url: str
    url_hash: str
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    site_key: Optional[str] = None
    crawl_timestamp: Optional[datetime] = None
    strategy_used: Optional[StrategyType] = None
    quality_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "url_hash": self.url_hash,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "site_key": self.site_key,
            "crawl_timestamp": self.crawl_timestamp.isoformat() if self.crawl_timestamp else None,
            "strategy_used": self.strategy_used.value if self.strategy_used else None,
            "quality_score": self.quality_score
        }


@dataclass
class CrawlResult:
    """Result of a crawl operation."""
    success: bool
    records: List[CrawlRecord]
    agent_id: str
    site_url: str
    summary: Dict[str, Any]
    display_manifest: Optional["DisplayManifest"] = None
    stuck_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "agent_id": self.agent_id,
            "site_url": self.site_url,
            "records": [r.to_dict() for r in self.records],
            "display_manifest": self.display_manifest.to_dict() if self.display_manifest else None,
            "summary": self.summary,
            "stuck_info": self.stuck_info,
            "error": self.error
        }


@dataclass
class TaskParams:
    """Flexible task parameters (not fixed schema)."""
    site_url: str
    intent: str
    max_pages: Optional[int] = None
    depth_limit: Optional[int] = None
    proxy: Optional[str] = None
    custom_fields: Optional[List[str]] = None
    exploration_config: Optional[Dict[str, Any]] = None
    # Agent can add more fields as needed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "site_url": self.site_url,
            "intent": self.intent,
            "max_pages": self.max_pages,
            "depth_limit": self.depth_limit,
            "proxy": self.proxy,
            "custom_fields": self.custom_fields,
            "exploration_config": self.exploration_config,
        }


# ============================================================================
# Exploration Phase Models
# ============================================================================

class ExplorationStage(Enum):
    """Exploration stages for progress reporting."""
    INITIALIZING = "initializing"
    SITE_MAPPING = "site_mapping"
    SAMPLING = "sampling"
    EXTRACTING = "extracting"
    EVALUATING = "evaluating"
    GENERATING_REPORT = "generating_report"
    COMPLETED = "completed"


class SamplingStrategy(Enum):
    """Sampling strategy types."""
    REPRESENTATIVE = "representative"  # Cover different page types
    NEED_BASED = "need_based"          # Prioritize user_goal relevance
    HIGH_QUALITY = "high_quality"      # Focus on quality_score > 0.8
    HYBRID = "hybrid"                  # Combination of strategies


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
class QualityMetrics:
    """Aggregate quality metrics for exploration."""
    relevant_ratio: float  # Ratio of records matching user goal
    avg_quality_score: float  # Average quality across samples
    data_types_found: List[str]  # Types of data extracted
    field_completeness: Dict[str, float]  # Completeness per field


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage.value,
            "message": self.message,
            "urls_discovered": self.urls_discovered,
            "urls_sampled": self.urls_sampled,
            "pages_extracted": self.pages_extracted,
            "quality_score": self.quality_score,
            "current_url": self.current_url,
        }


@dataclass
class ExplorationReport:
    """
    Exploration Report - output of the Exploration Phase.

    Contains complete findings to support LLM decision on whether to proceed.
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


@dataclass
class CrawlResultWithReport:
    """
    Extended crawl result that includes exploration report.

    This is the new output format for two-phase agents.
    """
    success: bool
    records: List[CrawlRecord]
    agent_id: str
    site_url: str
    summary: Dict[str, Any]
    exploration_report: Optional[ExplorationReport] = None
    display_manifest: Optional["DisplayManifest"] = None
    stuck_info: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "agent_id": self.agent_id,
            "site_url": self.site_url,
            "records": [r.to_dict() for r in self.records],
            "exploration_report": self.exploration_report.to_dict() if self.exploration_report else None,
            "display_manifest": self.display_manifest.to_dict() if self.display_manifest else None,
            "summary": self.summary,
            "stuck_info": self.stuck_info,
            "error": self.error
        }
