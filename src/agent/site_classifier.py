"""
Site Classifier - Website Type Classification

This module provides website classification for the Deep Reflection Memory
pattern from the 2026 Agent Architecture Improvement Plan.

Key Features:
1. Website type classification (ecommerce/news/social_media/etc.)
2. Domain pattern recognition
3. Feature-based classification
4. URL-based heuristics
"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import re
from urllib.parse import urlparse


class WebsiteType(Enum):
    """
    Website Type Enumeration

    Common website types for web scraping classification.
    """
    ECOMMERCE = "ecommerce"
    NEWS = "news"
    SOCIAL_MEDIA = "social_media"
    BLOG = "blog"
    FORUM = "forum"
    WIKI = "wiki"
    JOB_BOARD = "job_board"
    REAL_ESTATE = "real_estate"
    TRAVEL = "travel"
    DIRECTORY = "directory"
    PORTFOLIO = "portfolio"
    CORPORATE = "corporate"
    GOVERNMENT = "government"
    EDUCATION = "education"
    UNKNOWN = "unknown"


class SiteClassifier:
    """
    Website Classifier

    Classifies websites based on URL patterns, HTML features, and content analysis.
    """

    # Known domain patterns by type
    DOMAIN_PATTERNS = {
        WebsiteType.ECOMMERCE: [
            r"amazon",
            r"ebay",
            r"alibaba",
            r"taobao",
            r"jd\.com",
            r"shopify",
            r"etsy",
            r"walmart",
            r"target",
            r"bestbuy",
        ],
        WebsiteType.NEWS: [
            r"cnn",
            r"bbc",
            r"reuters",
            r"nytimes",
            r"theguardian",
            r"washingtonpost",
            r"wsj",
            r"bloomberg",
            r"apnews",
            r"news",
        ],
        WebsiteType.SOCIAL_MEDIA: [
            r"facebook",
            r"twitter",
            r"instagram",
            r"linkedin",
            r"tiktok",
            r"reddit",
            r"pinterest",
            r"youtube",
        ],
        WebsiteType.JOB_BOARD: [
            r"indeed",
            r"linkedin",
            r"glassdoor",
            r"monster",
            r"careerbuilder",
            r"ziprecruiter",
            r"simplyhired",
        ],
        WebsiteType.REAL_ESTATE: [
            r"zillow",
            r"realtor",
            r"redfin",
            r"trulia",
            r"rightmove",
            r"zoopla",
        ],
        WebsiteType.TRAVEL: [
            r"expedia",
            r"booking",
            r"airbnb",
            r"tripadvisor",
            r"kayak",
            r"priceline",
        ],
        WebsiteType.WIKI: [
            r"wikipedia",
            r"wiki",
            r"fandom",
        ],
        WebsiteType.FORUM: [
            r"reddit",
            r"discourse",
            r"phpbb",
            r"vbulletin",
            r"xenforo",
        ],
        WebsiteType.GOVERNMENT: [
            r"\.gov$",
            r"\.gov\.",
            r"\.go\.",
        ],
        WebsiteType.EDUCATION: [
            r"\.edu$",
            r"\.edu\.",
            r"\.ac\.",
            r"university",
            r"college",
        ],
    }

    # Feature patterns for classification
    FEATURE_PATTERNS = {
        WebsiteType.ECOMMERCE: [
            "add to cart",
            "buy now",
            "price",
            "product",
            "shipping",
            "checkout",
            "wishlist",
            "review",
        ],
        WebsiteType.NEWS: [
            "article",
            "breaking news",
            "editorial",
            "journalist",
            "published",
            "byline",
            "comment",
        ],
        WebsiteType.SOCIAL_MEDIA: [
            "follow",
            "like",
            "share",
            "comment",
            "profile",
            "message",
            "friend",
            "post",
        ],
        WebsiteType.JOB_BOARD: [
            "apply",
            "job",
            "resume",
            "salary",
            "employer",
            "candidate",
            "interview",
        ],
        WebsiteType.BLOG: [
            "blog",
            "post",
            "author",
            "comment",
            "subscribe",
            "rss",
        ],
    }

    @classmethod
    def classify_from_url(cls, url: str) -> Tuple[WebsiteType, float]:
        """
        Classify website from URL

        Args:
            url: Target URL

        Returns:
            Tuple of (WebsiteType, confidence)
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Check against known domain patterns
        for site_type, patterns in cls.DOMAIN_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, domain):
                    return site_type, 0.9

        # Check URL path patterns
        path = parsed.path.lower()

        if "/product" in path or "/item" in path or "/shop" in path:
            return WebsiteType.ECOMMERCE, 0.7

        if "/news" in path or "/article" in path:
            return WebsiteType.NEWS, 0.7

        if "/job" in path or "/career" in path:
            return WebsiteType.JOB_BOARD, 0.7

        if "/blog" in path or "/post" in path:
            return WebsiteType.BLOG, 0.6

        if "/forum" in path or "/thread" in path:
            return WebsiteType.FORUM, 0.7

        if "/property" in path or "/home" in path or "/real-estate" in path:
            return WebsiteType.REAL_ESTATE, 0.7

        return WebsiteType.UNKNOWN, 0.0

    @classmethod
    def classify_from_html(cls, html: str) -> Dict[str, Any]:
        """
        Classify website from HTML content

        Args:
            html: HTML content

        Returns:
            Classification result with type and confidence
        """
        html_lower = html.lower()

        scores = {}

        # Score based on feature patterns
        for site_type, features in cls.FEATURE_PATTERNS.items():
            score = 0
            for feature in features:
                # Count occurrences
                count = html_lower.count(feature)
                score += count

            if score > 0:
                scores[site_type] = score

        # Find the highest scoring type
        if scores:
            max_type = max(scores, key=scores.get)
            max_score = scores[max_type]

            # Normalize confidence based on score
            confidence = min(1.0, max_score / 100)

            return {
                "type": max_type.value,
                "confidence": confidence,
                "scores": {k.value: v for k, v in scores.items()},
            }

        return {
            "type": WebsiteType.UNKNOWN.value,
            "confidence": 0.0,
            "scores": {},
        }

    @classmethod
    def classify(cls, url: str, html: Optional[str] = None) -> Dict[str, Any]:
        """
        Comprehensive website classification

        Combines URL and HTML classification for better accuracy.

        Args:
            url: Target URL
            html: HTML content (optional)

        Returns:
            Classification result
        """
        url_type, url_confidence = cls.classify_from_url(url)

        if html:
            html_result = cls.classify_from_html(html)
            html_type = WebsiteType(html_result["type"])
            html_confidence = html_result["confidence"]

            # Combine results
            if url_type == WebsiteType.UNKNOWN:
                return {
                    "type": html_type.value,
                    "confidence": html_confidence,
                    "method": "html_only",
                }

            if html_type == WebsiteType.UNKNOWN:
                return {
                    "type": url_type.value,
                    "confidence": url_confidence,
                    "method": "url_only",
                }

            # If both agree, high confidence
            if url_type == html_type:
                return {
                    "type": url_type.value,
                    "confidence": max(url_confidence, html_confidence),
                    "method": "combined_agreement",
                }

            # If they disagree, use higher confidence
            if url_confidence > html_confidence:
                return {
                    "type": url_type.value,
                    "confidence": url_confidence * 0.8,  # Reduce confidence on disagreement
                    "method": "url_primary",
                    "alternative": html_type.value,
                }
            else:
                return {
                    "type": html_type.value,
                    "confidence": html_confidence * 0.8,
                    "method": "html_primary",
                    "alternative": url_type.value,
                }
        else:
            return {
                "type": url_type.value,
                "confidence": url_confidence,
                "method": "url_only",
            }

    @classmethod
    def extract_features(cls, html: str, url: str = "") -> List[str]:
        """
        Extract website features for reflection memory

        Args:
            html: HTML content
            url: Target URL (optional)

        Returns:
            List of detected features
        """
        features = []
        html_lower = html.lower()

        # Common feature detection
        feature_patterns = {
            "pagination": ["pagination", "next", "previous", "page 1"],
            "infinite_scroll": ["load more", "scroll", "infinite"],
            "search": ["search", "query", "filter"],
            "login_required": ["login", "sign in", "authenticate"],
            "javascript_heavy": ["<script", "react", "vue", "angular"],
            "images": ["<img", "image", "photo"],
            "videos": ["<video", "youtube", "vimeo"],
            "tables": ["<table", "tbody", "thead"],
            "forms": ["<form", "input", "submit"],
            "ads": ["advertisement", "ad-", "banner"],
            "comments": ["comment", "review", "rating"],
        }

        for feature, patterns in feature_patterns.items():
            if any(pattern in html_lower for pattern in patterns):
                features.append(feature)

        # URL-based features
        if url:
            parsed = urlparse(url)
            if parsed.scheme == "https":
                features.append("https")

            if parsed.netloc.startswith("www."):
                features.append("www_subdomain")

        return features

    @classmethod
    def get_domain_insights(cls, url: str, html: Optional[str] = None) -> Dict[str, Any]:
        """
        Get domain-level insights for reflection memory

        Args:
            url: Target URL
            html: HTML content (optional)

        Returns:
            Domain insights dictionary
        """
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        insights = {
            "domain": domain,
            "tld": parsed.path.split("/")[-1] if "." in parsed.path else "",
            "has_www": domain.startswith("www."),
            "protocol": parsed.scheme,
        }

        # Classify
        classification = cls.classify(url, html)
        insights["classification"] = classification

        # Extract features
        if html:
            features = cls.extract_features(html, url)
            insights["features"] = features

        return insights


def classify_website(url: str, html: Optional[str] = None) -> str:
    """
    Convenience function to classify a website

    Args:
        url: Target URL
        html: HTML content (optional)

    Returns:
        Website type string
    """
    result = SiteClassifier.classify(url, html)
    return result["type"]


def get_website_features(url: str, html: str) -> List[str]:
    """
    Convenience function to extract website features

    Args:
        url: Target URL
        html: HTML content

    Returns:
        List of detected features
    """
    return SiteClassifier.extract_features(html, url)
