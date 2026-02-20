"""
Data Models - Core data structures for the crawling system.

Defines:
- Crawl result models
- Display manifest models
- Task models
"""

from .crawl import CrawlRecord, CrawlResult, TaskParams
from .display import DisplayManifest, DisplayLayout

__all__ = [
    "CrawlRecord", "CrawlResult", "TaskParams",
    "DisplayManifest", "DisplayLayout"
]
