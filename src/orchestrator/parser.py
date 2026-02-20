"""
Intent Parser - Understands what the user wants to crawl.

Uses LLM to extract:
- Target fields to extract
- Content type (article, image, video, etc.)
- Scope (full site, partial, custom)
- User constraints
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class IntentContract:
    """Parsed user intent."""
    target_fields: List[str]
    content_type: Optional[str]  # article, image, video, product, etc.
    scope: str  # full, partial, custom
    constraints: Dict[str, Any]


class IntentParser:
    """Parse user intent using LLM."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.min_confidence = config.get("min_confidence", 0.7)
        self.llm_model = config.get("llm_model", "GLM-4.7")

    async def parse(self, user_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse user intent.

        Args:
            user_request: {
                "user_intent": str,
                "site_url": str,
                "constraints": Optional[Dict]
            }

        Returns:
            {
                "should_proceed": bool,
                "confidence": float,
                "intent_contract": Optional[IntentContract],
                "estimated_cost": Optional[Dict],
                "reason": Optional[str]  # if not proceeding
            }
        """
        # TODO: Implement LLM-based intent parsing
        return {
            "should_proceed": True,
            "confidence": 0.8,
            "intent_contract": IntentContract(
                target_fields=["title", "content", "url"],
                content_type="article",
                scope="full",
                constraints={}
            ),
            "estimated_cost": {"pages": 100, "tokens": 10000}
        }
