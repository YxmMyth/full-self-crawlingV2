"""
Agent Layer - Single-site intelligent crawling agent.

Components:
- agent: Main agent entry point
- callbacks: Callback definitions
- scanner: Site detection
- crawler: Crawl execution
- soal: SOOAL intelligent loop
- diagnose: Failure diagnosis
- repair: Auto-repair execution
- knowledge: Site knowledge base (general rules only)
"""

from .agent import SiteAgent
from .callbacks import ProgressCallback, StuckCallback, ResultCallback

__all__ = ["SiteAgent", "ProgressCallback", "StuckCallback", "ResultCallback"]
