"""
Execution Layer - Crawling strategies and plugins.

Components:
- strategies: Different crawling approaches (http, browser, api)
- plugins: Site-specific extraction rules
"""

from .strategies import HttpStrategy, BrowserStrategy, ApiStrategy

__all__ = ["HttpStrategy", "BrowserStrategy", "ApiStrategy"]
