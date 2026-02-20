"""
Site-Specific Plugins.

Each plugin contains extraction rules for a specific site or site type.

Plugins are dynamically loaded based on site detection results.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class PluginConfig:
    """Plugin configuration for a site."""
    site_key: str
    selectors: Dict[str, str]
    pagination: Optional[Dict[str, Any]] = None
    custom_logic: Optional[str] = None


# Pre-configured plugins for common site types
COMMON_PLUGINS = {
    "generic_article": PluginConfig(
        site_key="generic_article",
        selectors={
            "title": "h1",
            "content": "article, .content, #content, .post-content",
            "author": ".author, [itemprop='author']",
            "date": "time, .date, [itemprop='datePublished']"
        }
    ),
    "generic_news_list": PluginConfig(
        site_key="generic_news_list",
        selectors={
            "list_items": "ul.news-list li, .article-item, article",
            "title": "h2, h3, .title",
            "link": "a[href]"
        },
        pagination={
            "next_selector": "a.next, .pagination .next, nav[aria-label='Pagination'] a:last-child"
        }
    )
}


class PluginManager:
    """Manage site-specific plugins."""

    @staticmethod
    def get_plugin(site_key: str) -> Optional[PluginConfig]:
        """Get plugin for a specific site."""
        # TODO: Implement plugin loading from files
        return None

    @staticmethod
    def match_plugin(url: str, page_type: str) -> Optional[PluginConfig]:
        """Match appropriate plugin based on URL and page type."""
        if page_type == "article":
            return COMMON_PLUGINS.get("generic_article")
        elif page_type == "listing":
            return COMMON_PLUGINS.get("generic_news_list")
        return None
