"""
Stealth Configuration - Anti-bot Detection and Evasion

This module provides stealth configuration for web scraping,
implementing the "Stealth-First Default" pattern from the
2026 Agent Architecture Improvement Plan.

Key Features:
1. Anti-bot level detection (none/low/medium/high)
2. Configurable stealth levels
3. Auto-detection of anti-bot features
4. Stealth template generation
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import re


class StealthLevel(Enum):
    """
    Stealth Level Enumeration

    Levels:
    - NONE: No stealth measures
    - LOW: Basic stealth (random UA)
    - MEDIUM: Moderate stealth (UA + anti-detection)
    - HIGH: Maximum stealth (all measures)
    """
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AntiBotDetector:
    """
    Anti-bot Feature Detector

    Detects anti-bot measures on target websites.
    """

    # Known anti-bot patterns
    ANTI_BOT_PATTERNS = {
        "cloudflare": [
            r"cloudflare",
            r"cf-challenge",
            r"cf_clearance",
            r"__cf_bm",
        ],
        "akamai": [
            r"akamai",
            r"ak_bmsc",
        ],
        "distil": [
            r"distil",
            r"distilId",
            r"distilCID",
        ],
        "perimeterx": [
            r"perimeterx",
            r"px-",
            r"_pxvid",
        ],
        "datadome": [
            r"datadome",
            r"dd_",
        ],
        "captcha": [
            r"captcha",
            r"recaptcha",
            r"hcaptcha",
            r"turnstile",
            r"challenge-platform",
        ],
        "rate_limiting": [
            r"rate.?limit",
            r"too.?many.?requests",
            r"429",
        ],
        "bot_detection": [
            r"bot.?detector",
            r"webdriver",
            r"automation",
            r"fingerprint",
        ],
    }

    @classmethod
    def detect_from_html(cls, html: str) -> Dict[str, Any]:
        """
        Detect anti-bot features from HTML content

        Args:
            html: HTML content

        Returns:
            Detection result with detected features and level
        """
        html_lower = html.lower()

        detected = []
        for category, patterns in cls.ANTI_BOT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, html_lower):
                    detected.append(category)
                    break

        return {
            "detected_features": detected,
            "level": cls._calculate_level(detected),
        }

    @classmethod
    def detect_from_headers(cls, headers: Dict[str, str]) -> Dict[str, Any]:
        """
        Detect anti-bot features from HTTP headers

        Args:
            headers: HTTP response headers

        Returns:
            Detection result
        """
        detected = []

        header_str = str(headers).lower()

        if "cloudflare" in header_str or "cf-ray" in header_str:
            detected.append("cloudflare")

        if "akamai" in header_str:
            detected.append("akamai")

        if "x-bot" in header_str or "bot-protection" in header_str:
            detected.append("bot_detection")

        return {
            "detected_features": detected,
            "level": cls._calculate_level(detected),
        }

    @classmethod
    def _calculate_level(cls, detected: List[str]) -> str:
        """
        Calculate anti-bot level from detected features

        Args:
            detected: List of detected features

        Returns:
            Stealth level: none/low/medium/high
        """
        if not detected:
            return StealthLevel.NONE.value

        # High level indicators
        high_indicators = {"cloudflare", "captcha", "perimeterx", "datadome"}
        if any(f in detected for f in high_indicators):
            return StealthLevel.HIGH.value

        # Medium level indicators
        medium_indicators = {"akamai", "distil", "bot_detection"}
        if any(f in detected for f in medium_indicators):
            return StealthLevel.MEDIUM.value

        # Low level (rate limiting, basic detection)
        return StealthLevel.LOW.value


class StealthConfig:
    """
    Stealth Configuration Manager

    Manages stealth settings for web scraping.
    """

    DEFAULT_CONFIGS = {
        StealthLevel.NONE: {
            "use_stealth": False,
            "random_ua": False,
            "use_playwright_stealth": False,
            "delay_range": (0, 0),
            "wait_for_stability": False,
        },
        StealthLevel.LOW: {
            "use_stealth": True,
            "random_ua": True,
            "use_playwright_stealth": False,
            "delay_range": (1, 2),
            "wait_for_stability": False,
        },
        StealthLevel.MEDIUM: {
            "use_stealth": True,
            "random_ua": True,
            "use_playwright_stealth": True,
            "delay_range": (2, 4),
            "wait_for_stability": True,
        },
        StealthLevel.HIGH: {
            "use_stealth": True,
            "random_ua": True,
            "use_playwright_stealth": True,
            "delay_range": (3, 6),
            "wait_for_stability": True,
        },
    }

    def __init__(self, level: str = StealthLevel.MEDIUM.value):
        """
        Initialize stealth configuration

        Args:
            level: Stealth level (none/low/medium/high)
        """
        self.level = StealthLevel(level)
        self.config = self.DEFAULT_CONFIGS[self.level].copy()

    def get_launch_args(self) -> List[str]:
        """
        Get browser launch arguments for this stealth level

        Returns:
            List of launch arguments
        """
        args = []

        if self.config["use_stealth"]:
            args.extend([
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ])

        return args

    def get_delay_range(self) -> Tuple[int, int]:
        """
        Get delay range for human-like behavior

        Returns:
            Tuple of (min_delay, max_delay) in seconds
        """
        return self.config["delay_range"]

    def should_use_playwright_stealth(self) -> bool:
        """
        Check if playwright-stealth should be used

        Returns:
            True if playwright-stealth should be used
        """
        return self.config["use_playwright_stealth"]

    def should_randomize_ua(self) -> bool:
        """
        Check if User-Agent should be randomized

        Returns:
            True if UA should be randomized
        """
        return self.config["random_ua"]

    def get_stealth_script(self) -> str:
        """
        Get stealth JavaScript injection script

        Returns:
            JavaScript code for stealth injection
        """
        if self.level == StealthLevel.NONE:
            return ""

        # Base stealth script
        script = """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });

        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        """

        # Add additional stealth for medium/high levels
        if self.level in [StealthLevel.MEDIUM, StealthLevel.HIGH]:
            script += """
        // Override permissions API
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // Mock canvas fingerprint
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png') {
                // Add slight noise to canvas
                const context = this.getContext('2d');
                if (context) {
                    const imageData = context.getImageData(0, 0, this.width, this.height);
                    for (let i = 0; i < imageData.data.length; i += 4) {
                        imageData.data[i] = Math.min(255, imageData.data[i] + Math.random() * 2);
                    }
                    context.putImageData(imageData, 0, 0);
                }
            }
            return originalToDataURL.apply(this, arguments);
        };
        """

        return script

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary

        Returns:
            Configuration dictionary
        """
        return {
            "level": self.level.value,
            **self.config,
        }


def detect_anti_bot_level(html: str, headers: Optional[Dict[str, str]] = None) -> str:
    """
    Detect anti-bot level from HTML and headers

    Args:
        html: HTML content
        headers: HTTP headers (optional)

    Returns:
        Detected stealth level: none/low/medium/high
    """
    html_detection = AntiBotDetector.detect_from_html(html)
    html_level = html_detection["level"]

    if headers:
        header_detection = AntiBotDetector.detect_from_headers(headers)
        header_level = header_detection["level"]

        # Use the higher level
        levels = [StealthLevel.NONE.value, StealthLevel.LOW.value,
                  StealthLevel.MEDIUM.value, StealthLevel.HIGH.value]

        html_rank = levels.index(html_level)
        header_rank = levels.index(header_level)

        return levels[max(html_rank, header_rank)]

    return html_level


def get_stealth_template(level: str = "medium") -> str:
    """
    Get stealth browser template for code generation

    Args:
        level: Stealth level

    Returns:
        Python code template with stealth configuration
    """
    config = StealthConfig(level)

    launch_args = ", ".join(f'"{arg}"' for arg in config.get_launch_args())
    delay_min, delay_max = config.get_delay_range()

    stealth_script_comment = ""
    if config.get_stealth_script():
        stealth_script_comment = """
        # Apply stealth script
        page.add_init_script(\"\"\"
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}, loadTimes: function() {}};
        \"\"\")"""

    return f"""
from playwright.sync_api import sync_playwright
import random
import time

# Stealth Configuration
STEALTH_LEVEL = "{level}"
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

def scrape_with_stealth(url: str) -> dict:
    \"\"\"Scrape with stealth configuration\"\"\"
    with sync_playwright() as p:
        # Browser launch with stealth args
        browser = p.chromium.launch(
            headless=True,
            args=[{launch_args}]
        )

        # Random User-Agent
        page = browser.new_page(
            user_agent=random.choice(USER_AGENTS),
            viewport={{"width": 1920, "height": 1080}},
        )
{stealth_script_comment}

        # Navigate to URL
        page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # Human-like delay
        time.sleep(random.uniform({delay_min}, {delay_max}))

        # Your scraping logic here
        results = []

        browser.close()

        return {{"results": results}}
"""