"""
Site Knowledge Base - General rules and runtime learning.

Since Agent is disposable (用完即弃):
- General rules: Pre-configured anti-crawler patterns, common selectors
- Runtime learning: Learned during single task (not persisted)
"""

from typing import Dict, Any, List, Optional


# General Rules (pre-configured)
GENERAL_SELECTORS = {
    "article": {
        "title": ["h1", ".title", "#title", "article h1", "[itemprop='headline']"],
        "content": ["article", ".content", "#content", ".article-content", "[itemprop='articleBody']"],
        "author": [".author", "[itemprop='author']", ".byline"],
        "date": ["time", "[datetime]", ".date", ".publish-date"],
        "url": ["link", "[itemprop='url']", "canonical"],
    },
    "news": {
        "list": [".news-list", ".article-list", "ul.news"],
        "item": ["li", ".news-item", ".article-item"],
        "pagination": [".pagination", "nav", ".pager"],
    },
    "ecommerce": {
        "product": [".product", "[itemtype='Product']"],
        "price": [".price", "[itemprop='price']"],
        "description": [".description", "[itemprop='description']"],
    }
}

ANTI_BOT_PATTERNS = {
    "rate_limit": {
        "indicators": ["429", "rate limit", "too many requests"],
        "response": "slow_down"
    },
    "captcha": {
        "indicators": ["captcha", "recaptcha", "hcaptcha", "challenge"],
        "response": "switch_to_browser"
    },
    "blocked": {
        "indicators": ["403", "access denied", "blocked"],
        "response": "rotate_proxy"
    },
    "js_challenge": {
        "indicators": ["javascript", "enable js", "challenge platform"],
        "response": "switch_to_browser"
    }
}

LINK_PATTERNS = {
    "content": ["/article/", "/post/", "/news/", "/blog/", "/detail/", "/story/"],
    "pagination": ["?page=", "/page/", "/p/", "next", "prev"],
    "category": ["/category/", "/tag/", "/topic/"],
    "blacklist": ["/login", "/admin", "/register", "/account", "/user/"]
}


class RuntimeKnowledge:
    """
    Runtime knowledge accumulated during single task execution.

    This is NOT persisted across agent instances.
    """

    def __init__(self):
        self.working_selectors: Dict[str, str] = {}
        self.failed_patterns: List[str] = []
        self.strategy_scores: Dict[str, float] = {}
        self.identified_anti_bot: List[str] = []

    def record_success(self, field: str, selector: str) -> None:
        """Record a working selector."""
        self.working_selectors[field] = selector

    def record_failure(self, pattern: str) -> None:
        """Record a failed pattern."""
        if pattern not in self.failed_patterns:
            self.failed_patterns.append(pattern)

    def update_strategy_score(self, strategy: str, success: bool) -> None:
        """Update strategy performance score."""
        if strategy not in self.strategy_scores:
            self.strategy_scores[strategy] = 0.5

        # Simple EMA
        alpha = 0.3
        observed = 1.0 if success else 0.0
        old_score = self.strategy_scores[strategy]
        self.strategy_scores[strategy] = alpha * observed + (1 - alpha) * old_score

    def get_best_selector(self, field: str, content_type: str = "article") -> Optional[str]:
        """Get best selector for a field."""
        # Check runtime learned first
        if field in self.working_selectors:
            return self.working_selectors[field]

        # Fall back to general rules
        if content_type in GENERAL_SELECTORS:
            return GENERAL_SELECTORS[content_type].get(field, [None])[0]

        return None

    def get_anti_bot_response(self, indicators: List[str]) -> Optional[str]:
        """Get recommended response for anti-bot indicators."""
        for indicator in indicators:
            for bot_type, config in ANTI_BOT_PATTERNS.items():
                if any(ind.lower() in str(indicator).lower() for ind in config["indicators"]):
                    if bot_type not in self.identified_anti_bot:
                        self.identified_anti_bot.append(bot_type)
                    return config["response"]
        return None

    def should_filter_link(self, url: str, intent: str = "") -> bool:
        """
        Decide if a link should be filtered out.

        Returns True if link should be skipped.
        """
        # Check blacklist
        for pattern in LINK_PATTERNS["blacklist"]:
            if pattern in url:
                return True

        return False
