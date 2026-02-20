"""
Sampler - Dynamic sampling strategy implementation.

The Sampler is responsible for:
1. Representative Sampling: Cover different page types
2. Need-based Sampling: Prioritize pages matching user_goal
3. High-quality Sampling: Focus on quality_score > 0.8 pages

The sampling strategy is selected by LLM based on:
- Site structure (page types discovered)
- User goal (what data is needed)
- Quality indicators (which pages look promising)
"""

import random
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
from urllib.parse import urlparse

from .explorer import URLNode


class SamplingStrategy(Enum):
    """Sampling strategy types."""
    REPRESENTATIVE = "representative"  # Cover different page types
    NEED_BASED = "need_based"          # Prioritize user_goal relevance
    HIGH_QUALITY = "high_quality"      # Focus on high-quality indicators
    HYBRID = "hybrid"                  # Combination of strategies


@dataclass
class SamplingConfig:
    """Configuration for sampling."""
    max_count: int = 50
    min_per_type: int = 5
    diversity_weight: float = 0.5
    relevance_weight: float = 0.3
    quality_weight: float = 0.2


@dataclass
class SampledURL:
    """A URL selected for sampling with metadata."""
    url: str
    page_type: str
    depth: int
    priority: float
    reason: str


class Sampler:
    """
    Dynamic URL Sampler.

    Selects URLs for crawling based on the chosen strategy.
    """

    def __init__(self, config: Optional[SamplingConfig] = None):
        self.config = config or SamplingConfig()

        # Quality indicators (URL patterns suggesting good content)
        self.quality_patterns = {
            "article": ["article", "post", "news", "blog", "story", "detail"],
            "media": ["photo", "image", "video", "gallery"],
            "product": ["product", "item", "shop", "buy"],
        }

        # Low-quality patterns to avoid
        self.skip_patterns = [
            "/login", "/register", "/account", "/admin",
            "/search", "/tag", "/category/", "page=",
            ".pdf", ".jpg", ".png", ".gif", ".css", ".js",
        ]

    async def sample(
        self,
        url_nodes: List[URLNode],
        strategy: SamplingStrategy,
        max_count: Optional[int] = None,
        user_goal: Optional[str] = None,
    ) -> List[str]:
        """
        Sample URLs based on the selected strategy.

        Args:
            url_nodes: Discovered URL nodes
            strategy: Sampling strategy to use
            max_count: Maximum URLs to return
            user_goal: User's crawling intent (for need-based sampling)

        Returns:
            List of selected URLs (as strings)
        """
        max_count = max_count or self.config.max_count

        # Filter out low-quality URLs
        filtered_nodes = self._filter_urls(url_nodes)

        # Apply sampling strategy
        if strategy == SamplingStrategy.REPRESENTATIVE:
            sampled = await self._representative_sample(filtered_nodes, max_count)
        elif strategy == SamplingStrategy.NEED_BASED:
            sampled = await self._need_based_sample(filtered_nodes, user_goal or "", max_count)
        elif strategy == SamplingStrategy.HIGH_QUALITY:
            sampled = await self._high_quality_sample(filtered_nodes, max_count)
        else:  # HYBRID
            sampled = await self._hybrid_sample(filtered_nodes, user_goal or "", max_count)

        return [s.url for s in sampled]

    def _filter_urls(self, url_nodes: List[URLNode]) -> List[URLNode]:
        """Filter out low-quality URLs."""
        filtered = []

        for node in url_nodes:
            url_lower = node.url.lower()

            # Skip if matches skip patterns
            if any(pattern in url_lower for pattern in self.skip_patterns):
                continue

            filtered.append(node)

        return filtered

    async def _representative_sample(
        self,
        url_nodes: List[URLNode],
        max_count: int,
    ) -> List[SampledURL]:
        """
        Representative sampling: Cover different page types.

        Ensures diversity by selecting URLs from each page type.
        """
        # Group by page type
        by_type: Dict[str, List[URLNode]] = defaultdict(list)
        for node in url_nodes:
            by_type[node.page_type or "unknown"].append(node)

        sampled: List[SampledURL] = []

        # First, ensure minimum per type
        min_per_type = min(self.config.min_per_type, max_count // len(by_type))

        for page_type, nodes in by_type.items():
            count = min(min_per_type, len(nodes))
            selected = self._select_diverse_nodes(nodes, count)
            sampled.extend([
                SampledURL(
                    url=node.url,
                    page_type=page_type,
                    depth=node.depth,
                    priority=0.7,
                    reason=f"Representative of {page_type} type",
                )
                for node in selected
            ])

        # Fill remaining slots proportionally
        remaining = max_count - len(sampled)
        if remaining > 0:
            # Distribute based on type frequency
            type_counts = {pt: len(nodes) for pt, nodes in by_type.items()}
            total = sum(type_counts.values())

            for page_type, nodes in by_type.items():
                if len(sampled) >= max_count:
                    break
                additional = int(remaining * type_counts[page_type] / total)
                additional = min(additional, len(nodes))

                # Skip already selected (by URL)
                selected_urls = {s.url for s in sampled}
                available = [n for n in nodes if n.url not in selected_urls]

                for node in available[:additional]:
                    if len(sampled) >= max_count:
                        break
                    sampled.append(SampledURL(
                        url=node.url,
                        page_type=page_type,
                        depth=node.depth,
                        priority=0.6,
                        reason=f"Additional representative of {page_type}",
                    ))

        return sampled[:max_count]

    async def _need_based_sample(
        self,
        url_nodes: List[URLNode],
        user_goal: str,
        max_count: int,
    ) -> List[SampledURL]:
        """
        Need-based sampling: Prioritize pages matching user_goal.

        Uses keyword matching and pattern recognition to find relevant URLs.
        """
        # Extract keywords from user goal
        keywords = self._extract_keywords(user_goal)

        scored_nodes: List[tuple[URLNode, float]] = []

        for node in url_nodes:
            score = self._calculate_relevance_score(node, keywords)
            scored_nodes.append((node, score))

        # Sort by relevance score
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        # Select top URLs
        sampled: List[SampledURL] = []
        for node, score in scored_nodes[:max_count]:
            sampled.append(SampledURL(
                url=node.url,
                page_type=node.page_type or "unknown",
                depth=node.depth,
                priority=score,
                reason=f"Relevance score: {score:.2f}",
            ))

        return sampled

    async def _high_quality_sample(
        self,
        url_nodes: List[URLNode],
        max_count: int,
    ) -> List[SampledURL]:
        """
        High-quality sampling: Focus on quality indicators.

        Prioritizes URLs with patterns suggesting rich content.
        """
        scored_nodes: List[tuple[URLNode, float]] = []

        for node in url_nodes:
            score = self._calculate_quality_score(node)
            scored_nodes.append((node, score))

        # Sort by quality score
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        # Select top URLs
        sampled: List[SampledURL] = []
        for node, score in scored_nodes[:max_count]:
            sampled.append(SampledURL(
                url=node.url,
                page_type=node.page_type or "unknown",
                depth=node.depth,
                priority=score,
                reason=f"Quality score: {score:.2f}",
            ))

        return sampled

    async def _hybrid_sample(
        self,
        url_nodes: List[URLNode],
        user_goal: str,
        max_count: int,
    ) -> List[SampledURL]:
        """
        Hybrid sampling: Combine multiple strategies.

        Weights:
        - 50% diversity (representative)
        - 30% relevance (need-based)
        - 20% quality (high-quality)
        """
        keywords = self._extract_keywords(user_goal)

        scored_nodes: List[tuple[URLNode, Dict[str, float]]] = []

        for node in url_nodes:
            diversity_score = self._calculate_diversity_score(node, url_nodes)
            relevance_score = self._calculate_relevance_score(node, keywords)
            quality_score = self._calculate_quality_score(node)

            # Combined score
            combined = (
                self.config.diversity_weight * diversity_score +
                self.config.relevance_weight * relevance_score +
                self.config.quality_weight * quality_score
            )

            scored_nodes.append((node, {
                "combined": combined,
                "diversity": diversity_score,
                "relevance": relevance_score,
                "quality": quality_score,
            }))

        # Sort by combined score
        scored_nodes.sort(key=lambda x: x[1]["combined"], reverse=True)

        # Select top URLs
        sampled: List[SampledURL] = []
        for node, scores in scored_nodes[:max_count]:
            dominant = max(scores.items(), key=lambda x: x[1])[0]
            sampled.append(SampledURL(
                url=node.url,
                page_type=node.page_type or "unknown",
                depth=node.depth,
                priority=scores["combined"],
                reason=f"Hybrid (dominant: {dominant})",
            ))

        return sampled

    def _select_diverse_nodes(self, nodes: List[URLNode], count: int) -> List[URLNode]:
        """
        Select diverse nodes from a list.

        Uses depth and URL pattern diversity to ensure variety.
        """
        if len(nodes) <= count:
            return nodes

        selected = []
        remaining = nodes.copy()

        # First, pick from different depth levels
        depth_groups: Dict[int, List[URLNode]] = defaultdict(list)
        for node in remaining:
            depth_groups[node.depth].append(node)

        # Pick at least one from each depth
        for depth, depth_nodes in sorted(depth_groups.items()):
            if selected and len(selected) >= count:
                break
            if depth_nodes:
                selected.append(depth_nodes[0])
                remaining.remove(depth_nodes[0])

        # Fill remaining with diverse URL patterns
        patterns_seen: Set[str] = set()
        for node in remaining:
            if len(selected) >= count:
                break

            pattern = self._get_url_pattern(node.url)
            if pattern not in patterns_seen:
                selected.append(node)
                patterns_seen.add(pattern)

        return selected[:count]

    def _calculate_diversity_score(self, node: URLNode, all_nodes: List[URLNode]) -> float:
        """Calculate diversity score for a node."""
        # Score based on uniqueness of page type and depth
        page_type_counts: Dict[str, int] = defaultdict(int)
        depth_counts: Dict[int, int] = defaultdict(int)

        for n in all_nodes:
            page_type_counts[n.page_type or "unknown"] += 1
            depth_counts[n.depth] += 1

        # Rarer types get higher scores
        type_score = 1.0 / (page_type_counts.get(node.page_type or "unknown", 1))
        depth_score = 1.0 / (depth_counts.get(node.depth, 1))

        return (type_score + depth_score) / 2

    def _calculate_relevance_score(self, node: URLNode, keywords: List[str]) -> float:
        """Calculate relevance score based on keywords."""
        if not keywords:
            return 0.5

        url_lower = node.url.lower()
        metadata_lower = str(node.metadata).lower()

        matches = sum(1 for kw in keywords if kw in url_lower or kw in metadata_lower)
        return min(matches / len(keywords), 1.0)

    def _calculate_quality_score(self, node: URLNode) -> float:
        """Calculate quality score based on URL patterns."""
        url_lower = node.url.lower()

        # Check quality patterns
        for quality_type, patterns in self.quality_patterns.items():
            if any(p in url_lower for p in patterns):
                return 0.9  # High quality indicator

        # Check for content pages (has ID/slug pattern)
        if self._has_content_pattern(url_lower):
            return 0.7

        # Default score
        return 0.5

    def _has_content_pattern(self, url: str) -> bool:
        """Check if URL has content page pattern."""
        # Look for patterns like /123, /article-title, etc.
        import re
        return bool(
            re.search(r'/\d+', url) or  # Numeric ID
            re.search(r'/[a-z]+-[a-z]+', url)  # Slug pattern
        )

    def _extract_keywords(self, user_goal: str) -> List[str]:
        """Extract keywords from user goal."""
        # Simple keyword extraction (could use LLM in production)
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "about", "get", "fetch", "crawl",
            "all", "some", "data", "content", "pages", "site", "website",
            "的", "是", "爬取", "获取", "数据", "内容", "页面", "网站",
        }

        words = user_goal.lower().split()
        keywords = [w for w in words if len(w) > 2 and w not in common_words]

        return keywords

    def _get_url_pattern(self, url: str) -> str:
        """Extract URL pattern for comparison."""
        parsed = urlparse(url)
        path = parsed.path

        # Normalize path
        import re
        pattern = re.sub(r'/\d+', '/{id}', path)
        pattern = re.sub(r'/[a-f0-9]{8,}', '/{uuid}', pattern)

        return pattern
