"""
Evaluator - Data quality assessment implementation.

The Evaluator is responsible for:
1. Field Completeness (L1): Required fields present
2. Semantic Quality (L2): Content length, meaningfulness
3. Intent Satisfaction (L3): LLM scores relevance to user_goal

Returns quality_score (0-1) for each record and aggregate metrics.
"""

import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class QualityMetrics:
    """Aggregate quality metrics for a batch of records."""
    relevant_ratio: float  # Ratio of records matching user goal
    avg_quality_score: float  # Average quality across all records
    data_types_found: List[str]  # Types of data extracted
    field_completeness: Dict[str, float]  # Completeness per field

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "relevant_ratio": self.relevant_ratio,
            "avg_quality_score": self.avg_quality_score,
            "data_types_found": self.data_types_found,
            "field_completeness": self.field_completeness,
        }


@dataclass
class RecordQuality:
    """Quality assessment for a single record."""
    url: str
    quality_score: float
    l1_score: float  # Field completeness
    l2_score: float  # Semantic quality
    l3_score: float  # Intent satisfaction
    missing_fields: List[str]
    issues: List[str]


class Evaluator:
    """
    Data Quality Evaluator.

    Performs multi-level quality assessment:
    - L1: Field completeness check
    - L2: Semantic quality analysis
    - L3: Intent satisfaction scoring
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}

        # Required fields for L1 check
        self.required_fields = {"title", "content", "url"}

        # Optional but desired fields
        self.desired_fields = {"author", "date", "tags", "category"}

        # Quality thresholds
        self.min_title_length = config.get("min_title_length", 5)
        self.min_content_length = config.get("min_content_length", 100)
        self.max_content_ratio = config.get("max_content_ratio", 0.9)  # Max boilerplate ratio

        # Boilerplate indicators
        self.boilerplate_patterns = [
            r"© \d{4}",
            r"all rights reserved",
            r"cookies? policy",
            r"terms of service",
            r"privacy policy",
            r"subscribe to our",
            r"follow us on",
            r"view mobile site",
        ]

        # Meaningful content indicators
        self.content_indicators = [
            r"\.\s+[A-Z]",  # Sentence endings
            r"\d{4}",  # Years/dates
            r"[A-Z][a-z]+\s+[A-Z][a-z]+",  # Proper nouns
        ]

    async def evaluate_batch(
        self,
        records: List[Dict[str, Any]],
        user_goal: str,
    ) -> QualityMetrics:
        """
        Evaluate a batch of records and return aggregate metrics.

        Args:
            records: List of extracted data records
            user_goal: User's crawling intent for relevance scoring

        Returns:
            QualityMetrics with aggregate scores
        """
        if not records:
            return QualityMetrics(
                relevant_ratio=0.0,
                avg_quality_score=0.0,
                data_types_found=[],
                field_completeness={},
            )

        qualities = []
        field_completeness: Dict[str, List[float]] = defaultdict(list)
        data_types = set()

        for record in records:
            quality = await self.evaluate_record(record, user_goal)
            qualities.append(quality)

            # Track field completeness
            for field in self.required_fields | self.desired_fields:
                is_present = field in record and bool(record.get(field))
                field_completeness[field].append(float(is_present))

            # Detect data types
            data_types.update(self._detect_data_types(record))

        # Calculate aggregate metrics
        relevant_count = sum(1 for q in qualities if q.quality_score >= 0.6)
        relevant_ratio = relevant_count / len(qualities)

        avg_quality = sum(q.quality_score for q in qualities) / len(qualities)

        # Average field completeness
        avg_field_completeness = {
            field: (sum(scores) / len(scores) if scores else 0.0)
            for field, scores in field_completeness.items()
        }

        return QualityMetrics(
            relevant_ratio=relevant_ratio,
            avg_quality_score=avg_quality,
            data_types_found=list(data_types),
            field_completeness=avg_field_completeness,
        )

    async def evaluate_record(
        self,
        record: Dict[str, Any],
        user_goal: str,
    ) -> RecordQuality:
        """
        Evaluate a single record.

        Returns:
            RecordQuality with detailed scores
        """
        # L1: Field completeness
        l1_score, missing_fields = self._check_field_completeness(record)

        # L2: Semantic quality
        l2_score, issues = self._check_semantic_quality(record)

        # L3: Intent satisfaction
        l3_score = await self._check_intent_satisfaction(record, user_goal)

        # Combined score: 30% L1 + 40% L2 + 30% L3
        quality_score = 0.3 * l1_score + 0.4 * l2_score + 0.3 * l3_score

        return RecordQuality(
            url=record.get("url", ""),
            quality_score=quality_score,
            l1_score=l1_score,
            l2_score=l2_score,
            l3_score=l3_score,
            missing_fields=missing_fields,
            issues=issues,
        )

    def _check_field_completeness(self, record: Dict[str, Any]) -> tuple[float, List[str]]:
        """
        L1: Check field completeness.

        Returns:
            (score, list_of_missing_fields)
        """
        missing = []
        present_count = 0

        for field in self.required_fields:
            if field in record and bool(record.get(field)):
                present_count += 1
            else:
                missing.append(field)

        # Bonus for desired fields
        bonus_count = 0
        for field in self.desired_fields:
            if field in record and bool(record.get(field)):
                bonus_count += 1

        # Base score from required fields
        base_score = present_count / len(self.required_fields)

        # Add bonus (up to 0.2)
        bonus = min(bonus_count / len(self.desired_fields), 0.2)

        return min(base_score + bonus, 1.0), missing

    def _check_semantic_quality(self, record: Dict[str, Any]) -> tuple[float, List[str]]:
        """
        L2: Check semantic quality.

        Validates:
        - Title length and format
        - Content length and meaningfulness
        - Low boilerplate ratio
        """
        issues = []
        scores = []

        # Check title
        title = record.get("title", "")
        title_score = 1.0

        if len(title) < self.min_title_length:
            title_score = 0.3
            issues.append(f"Title too short: {len(title)} chars")
        elif len(title) > 200:
            title_score = 0.7
            issues.append(f"Title too long: {len(title)} chars")

        scores.append(title_score)

        # Check content
        content = record.get("content", "")
        content_score = 1.0

        if len(content) < self.min_content_length:
            content_score = 0.2
            issues.append(f"Content too short: {len(content)} chars")
        else:
            # Check for meaningful content
            meaningful = self._is_meaningful_content(content)
            if not meaningful:
                content_score = 0.5
                issues.append("Content lacks meaningful indicators")

            # Check boilerplate ratio
            boilerplate_ratio = self._calculate_boilerplate_ratio(content)
            if boilerplate_ratio > self.max_content_ratio:
                content_score = max(content_score - 0.3, 0.3)
                issues.append(f"High boilerplate ratio: {boilerplate_ratio:.1%}")

        scores.append(content_score)

        return sum(scores) / len(scores), issues

    async def _check_intent_satisfaction(self, record: Dict[str, Any], user_goal: str) -> float:
        """
        L3: Check intent satisfaction using LLM.

        In production, this would call an LLM to score relevance.
        For now, uses keyword matching.
        """
        if not user_goal:
            return 0.7  # Default score

        # Extract keywords from user goal
        keywords = self._extract_keywords(user_goal)

        if not keywords:
            return 0.7

        # Check keyword matches in record
        text = (
            record.get("title", "").lower() + " " +
            record.get("content", "").lower() + " " +
            str(record.get("metadata", {})).lower()
        )

        matches = sum(1 for kw in keywords if kw in text)

        # Score based on keyword coverage
        score = min(matches / len(keywords), 1.0)

        # Ensure minimum score
        return max(score, 0.3)

    def _is_meaningful_content(self, content: str) -> bool:
        """Check if content has meaningful indicators."""
        content_lower = content.lower()

        # Check for content indicators
        indicator_count = 0
        for pattern in self.content_indicators:
            if re.search(pattern, content_lower):
                indicator_count += 1

        return indicator_count >= 2

    def _calculate_boilerplate_ratio(self, content: str) -> float:
        """Calculate ratio of boilerplate content."""
        content_lower = content.lower()
        boilerplate_chars = 0

        for pattern in self.boilerplate_patterns:
            matches = re.findall(pattern, content_lower)
            boilerplate_chars += sum(len(m) for m in matches)

        return boilerplate_chars / len(content) if content else 0.0

    def _detect_data_types(self, record: Dict[str, Any]) -> List[str]:
        """Detect types of data in the record."""
        types = []

        # Check for structured data
        if record.get("metadata"):
            types.append("structured_metadata")

        # Check for media
        for field in record:
            if any(kw in field.lower() for kw in ["image", "video", "audio", "media"]):
                types.append("media")
                break

        # Check for dates
        if record.get("date") or record.get("published") or record.get("created"):
            types.append("temporal")

        # Check for author
        if record.get("author"):
            types.append("attributed")

        # Check for tags/categories
        if record.get("tags") or record.get("category"):
            types.append("categorized")

        return types or ["text"]

    def _extract_keywords(self, user_goal: str) -> List[str]:
        """Extract keywords from user goal."""
        # Simple keyword extraction
        common_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "about", "get", "fetch", "crawl",
            "all", "some", "data", "content", "pages", "site", "website",
            "的", "是", "爬取", "获取", "数据", "内容", "页面", "网站",
        }

        words = re.findall(r'\w+', user_goal.lower())
        keywords = [w for w in words if len(w) > 2 and w not in common_words]

        return keywords
