"""
Validation Node - Pre-execution Code Validator

This node validates selectors and code patterns before execution,
implementing the "Verification-Before-Execution" pattern from the
2026 Agent Architecture Improvement Plan.

Key Features:
1. Live DOM selector testing
2. Validation confidence scoring
3. Early failure detection
4. Selector suggestion
"""

from typing import Dict, Any, List, Optional, Tuple
import json
import re

from .performance import track_performance


@track_performance("validate")
async def validate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate Node: Pre-execution code validator

    Validates selectors and code patterns against live DOM before
    actual code execution in the Act node.

    Args:
        state: Current agent state

    Returns:
        Updated state with validation_report
    """
    from .tools import SelectorValidator
    from .prompts import get_validation_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox
    import os

    try:
        # Get HTML from sense phase
        html = state.get("html_snapshot", "")
        if not html:
            # Fallback: fetch HTML if not available
            from .tools import BrowserTool
            browser = BrowserTool()
            browse_result = await browser.browse(state["site_url"])
            html = browse_result.get("html", "")
            await browser.close()

        # Get suggested selectors from sense analysis
        sense_analysis = state.get("sense_analysis", {})
        suggested_selectors = []

        # Extract selectors from sense analysis
        if sense_analysis.get("valid_selectors"):
            suggested_selectors = sense_analysis["valid_selectors"]
        elif sense_analysis.get("article_selector"):
            suggested_selectors.append(sense_analysis["article_selector"])
        if sense_analysis.get("title_selector"):
            suggested_selectors.append(sense_analysis["title_selector"])
        if sense_analysis.get("link_selector"):
            suggested_selectors.append(sense_analysis["link_selector"])

        # ========== 修复: 如果没有建议选择器，使用选择器库 ==========
        if not suggested_selectors:
            from .selector_library import suggest_selectors
            website_type = state.get("website_type", "unknown")
            suggested_selectors = suggest_selectors(
                state["user_goal"],
                website_type,
                state["site_url"]
            )

        # Use SelectorValidator to test selectors on live HTML
        validator = SelectorValidator(html)

        # Test all suggested selectors
        validation_results = []
        for selector in suggested_selectors:
            result = validator.test_selector(selector)
            validation_results.append(result)

        # ========== 修复: 确保 validation_results 非空，至少测试通用选择器 ==========
        if not validation_results:
            generic_selectors = ["article", ".item", ".card", "[data-id]"]
            for selector in generic_selectors:
                result = validator.test_selector(selector)
                validation_results.append(result)

        # Calculate validation confidence
        confidence = calculate_validation_confidence(validation_results)

        # Generate validation report
        validation_report = {
            "confidence": confidence,
            "selector_results": validation_results,
            "valid_selectors": [r["selector"] for r in validation_results if r.get("valid", False)],
            "invalid_selectors": [r["selector"] for r in validation_results if not r.get("valid", True)],
            "recommendations": generate_validation_recommendations(validation_results),
            "html_length": len(html),
            "total_selectors_tested": len(validation_results),
        }

        state["validation_report"] = validation_report
        state["validated_selectors"] = validation_report["valid_selectors"]

        # If confidence is low, ask LLM to suggest alternative selectors
        if confidence < get_verification_confidence_threshold():
            # Generate alternative selector suggestions
            client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

            prompt = get_validation_prompt(
                url=state["site_url"],
                user_goal=state["user_goal"],
                failed_selectors=validation_report["invalid_selectors"],
                html=html[:10000],
            )

            llm_response = await client.generate_code(prompt)
            alternative_code = extract_python_code(llm_response)

            # Execute alternative selector generation code
            sandbox = create_sandbox(use_docker=False)
            alt_result = await sandbox.run_python_code(alternative_code, timeout=30)

            if alt_result["success"] and isinstance(alt_result["output"], dict):
                alt_selectors = alt_result["output"].get("alternative_selectors", [])
                validation_report["alternative_selectors"] = alt_selectors

                # Test alternative selectors
                alt_results = []
                for selector in alt_selectors:
                    result = validator.test_selector(selector)
                    alt_results.append(result)

                validation_report["alternative_results"] = alt_results

                # Add valid alternatives to validated selectors
                valid_alt = [r["selector"] for r in alt_results if r.get("valid", False)]
                state["validated_selectors"].extend(valid_alt)

                # Recalculate confidence
                new_confidence = calculate_validation_confidence(validation_results + alt_results)
                validation_report["confidence"] = new_confidence

    except Exception as e:
        state["validation_report"] = {
            "confidence": 0.0,
            "error": str(e),
            "selector_results": [],
            "valid_selectors": [],
            "recommendations": ["Validation failed, proceeding with caution"],
        }
        state["validated_selectors"] = []

    return state


def calculate_validation_confidence(results: List[Dict[str, Any]]) -> float:
    """
    Calculate validation confidence based on selector test results

    Args:
        results: List of selector validation results

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not results:
        return 0.0

    total = len(results)
    valid_count = sum(1 for r in results if r.get("valid", False))

    # Base score: ratio of valid selectors
    base_score = valid_count / total

    # Bonus: if we have at least one selector with good match count
    has_good_match = any(
        r.get("valid", False) and 3 <= r.get("count", 0) <= 50
        for r in results
    )

    # Penalty: if all selectors match too many elements (>100)
    all_overmatched = all(
        r.get("count", 0) > 100
        for r in results if r.get("valid", False)
    )

    confidence = base_score

    if has_good_match:
        confidence = min(1.0, confidence + 0.2)

    if all_overmatched:
        confidence = max(0.0, confidence - 0.1)

    return round(confidence, 2)


def generate_validation_recommendations(results: List[Dict[str, Any]]) -> List[str]:
    """
    Generate recommendations based on validation results

    Args:
        results: List of selector validation results

    Returns:
        List of recommendation strings
    """
    recommendations = []

    valid_count = sum(1 for r in results if r.get("valid", False))
    total = len(results)

    if valid_count == 0:
        recommendations.append("No valid selectors found. Consider using more generic selectors or check if page structure changed.")
    elif valid_count < total / 2:
        recommendations.append("Less than half of selectors are valid. LLM should use alternative selection strategies.")
    elif valid_count == total:
        recommendations.append("All selectors validated successfully. High confidence for execution.")

    # Check for overmatching selectors
    overmatched = [r for r in results if r.get("count", 0) > 100]
    if overmatched:
        recommendations.append(f"Warning: {len(overmatched)} selector(s) match too many elements (>100). Consider adding more specificity.")

    # Check for undermatching selectors
    undermatched = [r for r in results if r.get("count", 0) == 0]
    if undermatched:
        recommendations.append(f"{len(undermatched)} selector(s) matched zero elements. These should be replaced.")

    return recommendations


def get_verification_confidence_threshold() -> float:
    """
    Get the verification confidence threshold from environment

    Returns:
        Confidence threshold (default 0.7)
    """
    import os
    return float(os.getenv("VERIFICATION_CONFIDENCE_THRESHOLD", "0.7"))


def should_skip_verification(state: Dict[str, Any]) -> bool:
    """
    Check if verification should be skipped based on feature flag

    Args:
        state: Current agent state

    Returns:
        True if verification should be skipped
    """
    import os
    return os.getenv("ENABLE_VERIFICATION_NODE", "true").lower() != "true"
