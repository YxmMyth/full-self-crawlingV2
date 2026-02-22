"""
Deep Reflection Memory - Enhanced Reflection for Agent Learning

This module provides enhanced reflection memory capabilities for the
Deep Reflection Memory pattern from the 2026 Agent Architecture Improvement Plan.

Key Features:
1. Website pattern tracking
2. Domain insights storage
3. Attempted strategies recording
4. Partial success data analysis
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import hashlib
from pathlib import Path


class DeepReflectionMemory:
    """
    Deep Reflection Memory

    Stores comprehensive reflection data including:
    - Website classification
    - Domain-specific insights
    - Attempted strategies
    - Partial success patterns
    - Working/non-working approaches
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize deep reflection memory

        Args:
            storage_path: Path to store reflection data (optional)
        """
        self.storage_path = storage_path or "./data/reflections.db"
        self.reflections: List[Dict[str, Any]] = []
        self.domain_insights: Dict[str, Dict[str, Any]] = {}
        self.strategy_effectiveness: Dict[str, Dict[str, float]] = {}

        # Load existing data if available
        self._load()

    def add_reflection(
        self,
        url: str,
        website_type: str,
        anti_bot_level: str,
        failure_type: str,
        root_cause: str,
        suggested_fix: str,
        attempted_strategies: List[str],
        partial_success_data: Optional[Dict[str, Any]] = None,
        execution_result: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a comprehensive reflection to memory

        Args:
            url: Target URL
            website_type: Classified website type
            anti_bot_level: Detected anti-bot level
            failure_type: Type of failure
            root_cause: Root cause analysis
            suggested_fix: Suggested fix
            attempted_strategies: Strategies that were tried
            partial_success_data: Data about partial successes
            execution_result: Full execution result
        """
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc

        reflection = {
            "timestamp": datetime.now().isoformat(),
            "url": url,
            "domain": domain,
            "website_type": website_type,
            "anti_bot_level": anti_bot_level,
            "failure_type": failure_type,
            "root_cause": root_cause,
            "suggested_fix": suggested_fix,
            "attempted_strategies": attempted_strategies,
            "partial_success_data": partial_success_data or {},
            "execution_success": execution_result.get("success", False) if execution_result else False,
            "data_extracted": execution_result.get("data_count", 0) if execution_result else 0,
        }

        self.reflections.append(reflection)

        # Update domain insights
        self._update_domain_insights(domain, reflection)

        # Update strategy effectiveness
        for strategy in attempted_strategies:
            self._update_strategy_effectiveness(
                strategy,
                website_type,
                anti_bot_level,
                execution_result.get("success", False) if execution_result else False,
            )

        # Save to disk
        self._save()

    def _update_domain_insights(self, domain: str, reflection: Dict[str, Any]) -> None:
        """
        Update domain-specific insights

        Args:
            domain: Domain name
            reflection: Reflection data
        """
        if domain not in self.domain_insights:
            self.domain_insights[domain] = {
                "domain": domain,
                "website_type": reflection["website_type"],
                "anti_bot_level": reflection["anti_bot_level"],
                "attempt_count": 0,
                "success_count": 0,
                "common_failures": {},
                "working_strategies": [],
                "non_working_strategies": [],
            }

        insights = self.domain_insights[domain]
        insights["attempt_count"] += 1

        if reflection["execution_success"]:
            insights["success_count"] += 1

        # Track common failures
        failure_type = reflection["failure_type"]
        if failure_type not in insights["common_failures"]:
            insights["common_failures"][failure_type] = 0
        insights["common_failures"][failure_type] += 1

        # Track strategies
        for strategy in reflection["attempted_strategies"]:
            if reflection["execution_success"]:
                if strategy not in insights["working_strategies"]:
                    insights["working_strategies"].append(strategy)
            else:
                if strategy not in insights["non_working_strategies"]:
                    insights["non_working_strategies"].append(strategy)

    def _update_strategy_effectiveness(
        self,
        strategy: str,
        website_type: str,
        anti_bot_level: str,
        success: bool,
    ) -> None:
        """
        Update strategy effectiveness tracking

        Args:
            strategy: Strategy name
            website_type: Website type
            anti_bot_level: Anti-bot level
            success: Whether the strategy succeeded
        """
        key = f"{website_type}:{anti_bot_level}:{strategy}"

        if key not in self.strategy_effectiveness:
            self.strategy_effectiveness[key] = {
                "success_count": 0,
                "total_count": 0,
                "website_type": website_type,
                "anti_bot_level": anti_bot_level,
                "strategy": strategy,
            }

        stats = self.strategy_effectiveness[key]
        stats["total_count"] += 1
        if success:
            stats["success_count"] += 1

    def get_domain_insights(self, domain: str) -> Optional[Dict[str, Any]]:
        """
        Get insights for a specific domain

        Args:
            domain: Domain name

        Returns:
            Domain insights or None
        """
        return self.domain_insights.get(domain)

    def get_website_type_insights(self, website_type: str) -> Dict[str, Any]:
        """
        Get insights for a specific website type

        Args:
            website_type: Website type

        Returns:
            Aggregated insights for the website type
        """
        relevant = [
            r for r in self.reflections
            if r["website_type"] == website_type
        ]

        if not relevant:
            return {
                "website_type": website_type,
                "total_attempts": 0,
                "success_rate": 0.0,
                "common_failures": [],
                "recommended_strategies": [],
            }

        # Calculate statistics
        total = len(relevant)
        successes = sum(1 for r in relevant if r["execution_success"])

        # Count failure types
        failure_counts = {}
        for r in relevant:
            ft = r["failure_type"]
            if ft not in failure_counts:
                failure_counts[ft] = 0
            failure_counts[ft] += 1

        # Find working strategies
        working_strategies = []
        for r in relevant:
            if r["execution_success"]:
                working_strategies.extend(r["attempted_strategies"])

        return {
            "website_type": website_type,
            "total_attempts": total,
            "success_rate": successes / total if total > 0 else 0.0,
            "common_failures": sorted(
                failure_counts.items(),
                key=lambda x: x[1],
                reverse=True
            ),
            "recommended_strategies": list(set(working_strategies)),
        }

    def get_strategy_recommendation(
        self,
        website_type: str,
        anti_bot_level: str,
    ) -> List[str]:
        """
        Get recommended strategies for a website

        Args:
            website_type: Website type
            anti_bot_level: Anti-bot level

        Returns:
            List of recommended strategies
        """
        # Find relevant strategy stats
        relevant = [
            stats for key, stats in self.strategy_effectiveness.items()
            if stats["website_type"] == website_type
            and stats["anti_bot_level"] == anti_bot_level
        ]

        if not relevant:
            # Return default recommendations based on anti-bot level
            return self._get_default_strategies(anti_bot_level)

        # Sort by success rate
        sorted_strategies = sorted(
            relevant,
            key=lambda x: x["success_count"] / x["total_count"] if x["total_count"] > 0 else 0,
            reverse=True
        )

        # Return top strategies
        return [s["strategy"] for s in sorted_strategies[:3]]

    def _get_default_strategies(self, anti_bot_level: str) -> List[str]:
        """
        Get default strategies based on anti-bot level

        Args:
            anti_bot_level: Anti-bot level

        Returns:
            List of default strategies
        """
        default_strategies = {
            "none": [
                "Use basic Playwright browser",
                "Wait for page load with wait_for_selector",
                "Extract data with standard selectors",
            ],
            "low": [
                "Use random User-Agent",
                "Add small delays (1-2s)",
                "Use standard CSS selectors",
            ],
            "medium": [
                "Use stealth browser with anti-detection",
                "Add random delays (2-4s)",
                "Use more specific selectors",
                "Wait for dynamic content",
            ],
            "high": [
                "Use maximum stealth configuration",
                "Add longer random delays (3-6s)",
                "Use XPath or complex selectors",
                "Handle CAPTCHA challenges",
                "Rotate IP addresses if needed",
            ],
        }

        return default_strategies.get(anti_bot_level, default_strategies["medium"])

    def get_recent_reflections(
        self,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get recent reflections

        Args:
            domain: Filter by domain (optional)
            limit: Maximum number of reflections

        Returns:
            List of recent reflections
        """
        if domain:
            relevant = [r for r in self.reflections if r["domain"] == domain]
        else:
            relevant = self.reflections

        # Sort by timestamp (most recent first)
        sorted_reflections = sorted(
            relevant,
            key=lambda x: x["timestamp"],
            reverse=True
        )

        return sorted_reflections[:limit]

    def should_retry_with_different_strategy(
        self,
        current_strategies: List[str],
        domain: str,
    ) -> bool:
        """
        Check if a different strategy should be tried

        Args:
            current_strategies: Strategies already tried
            domain: Target domain

        Returns:
            True if a different strategy should be tried
        """
        insights = self.get_domain_insights(domain)

        if not insights:
            # No prior experience, try new strategies
            return True

        # Check if all current strategies are in non-working list
        non_working = set(insights.get("non_working_strategies", []))
        current_set = set(current_strategies)

        # If all current strategies are known to fail, recommend different
        return current_set.issubset(non_working) and len(insights.get("working_strategies", [])) > 0

    def _save(self) -> None:
        """Save reflection data to disk"""
        try:
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)

            data = {
                "reflections": self.reflections,
                "domain_insights": self.domain_insights,
                "strategy_effectiveness": self.strategy_effectiveness,
            }

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Don't fail if saving fails
            pass

    def _load(self) -> None:
        """Load reflection data from disk"""
        try:
            if Path(self.storage_path).exists():
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.reflections = data.get("reflections", [])
                self.domain_insights = data.get("domain_insights", {})
                self.strategy_effectiveness = data.get("strategy_effectiveness", {})
        except Exception:
            # Start fresh if loading fails
            pass

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of reflection memory

        Returns:
            Summary statistics
        """
        total_reflections = len(self.reflections)
        total_domains = len(self.domain_insights)
        total_strategies = len(self.strategy_effectiveness)

        # Success rate
        if total_reflections > 0:
            success_count = sum(1 for r in self.reflections if r["execution_success"])
            success_rate = success_count / total_reflections
        else:
            success_rate = 0.0

        # Website type distribution
        type_counts = {}
        for r in self.reflections:
            wt = r["website_type"]
            if wt not in type_counts:
                type_counts[wt] = 0
            type_counts[wt] += 1

        return {
            "total_reflections": total_reflections,
            "total_domains": total_domains,
            "total_strategies_tracked": total_strategies,
            "overall_success_rate": success_rate,
            "website_type_distribution": type_counts,
        }


def analyze_partial_success(
    execution_result: Dict[str, Any],
    sample_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Analyze partial success for reflection memory

    Args:
        execution_result: Execution result
        sample_data: Extracted sample data

    Returns:
        Partial success analysis
    """
    analysis = {
        "partial_success": False,
        "success_rate": 0.0,
        "issues": [],
        "strengths": [],
        "recommendations": [],
    }

    # Check if execution succeeded
    if execution_result.get("success"):
        analysis["partial_success"] = True
        analysis["success_rate"] = 1.0
        analysis["strengths"].append("Code executed successfully")
    else:
        # Check if any data was extracted despite error
        if sample_data and len(sample_data) > 0:
            analysis["partial_success"] = True
            analysis["success_rate"] = 0.5
            analysis["strengths"].append(f"Extracted {len(sample_data)} items despite error")
            analysis["issues"].append(f"Execution failed: {execution_result.get('error', 'Unknown')[:100]}")

    # Analyze data quality
    if sample_data:
        # Check for empty fields
        empty_count = 0
        total_fields = 0

        for item in sample_data:
            for value in item.values():
                total_fields += 1
                if not value or value == "" or value is None:
                    empty_count += 1

        if total_fields > 0:
            completeness = 1.0 - (empty_count / total_fields)
            analysis["completeness"] = completeness

            if completeness < 0.5:
                analysis["issues"].append(f"Low data completeness: {completeness:.1%}")
            else:
                analysis["strengths"].append(f"Good data completeness: {completeness:.1%}")

        # Check for duplicates
        if len(sample_data) > 1:
            unique_items = len(set(str(item) for item in sample_data))
            if unique_items < len(sample_data):
                dup_rate = 1.0 - (unique_items / len(sample_data))
                analysis["duplicate_rate"] = dup_rate

                if dup_rate > 0.3:
                    analysis["issues"].append(f"High duplicate rate: {dup_rate:.1%}")
                else:
                    analysis["strengths"].append(f"Low duplicate rate: {dup_rate:.1%}")

    return analysis
