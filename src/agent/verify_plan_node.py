"""
Verify Plan Node - Sandbox Dry-runner

This node performs a dry-run of generated code with timeout protection,
implementing the "Verification-Before-Execution" pattern from the
2026 Agent Architecture Improvement Plan.

Key Features:
1. Code syntax validation
2. Import availability checking
3. Dry-run execution with timeout
4. Early error detection
"""

from typing import Dict, Any, List, Optional
import json
import ast
import re

from .performance import track_performance


@track_performance("verify_plan")
async def verify_plan_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify Plan Node: Sandbox dry-runner for generated code

    Performs a dry-run of generated code to detect errors before
    actual execution in the Act node.

    Args:
        state: Current agent state

    Returns:
        Updated state with plan_verification
    """
    from .sandbox import create_sandbox
    import os

    try:
        generated_code = state.get("generated_code", "")

        if not generated_code:
            state["plan_verification"] = {
                "status": "failed",
                "error": "No code generated for verification",
                "can_proceed": False,
            }
            return state

        # Step 1: Syntax validation
        syntax_check = validate_syntax(generated_code)

        # Step 2: Import availability check
        import_check = validate_imports(generated_code)

        # Step 3: Structure validation
        structure_check = validate_code_structure(generated_code)

        # Step 4: Quick dry-run (modified code with early exit)
        dry_run_result = await perform_dry_run(generated_code, state)

        # Compile verification report
        verification_report = {
            "status": determine_status(syntax_check, import_check, structure_check, dry_run_result),
            "syntax_check": syntax_check,
            "import_check": import_check,
            "structure_check": structure_check,
            "dry_run": dry_run_result,
            "can_proceed": dry_run_result.get("success", False),
            "warnings": collect_warnings(syntax_check, import_check, structure_check),
            "recommendations": generate_verification_recommendations(
                syntax_check, import_check, structure_check, dry_run_result
            ),
        }

        state["plan_verification"] = verification_report

        # Store dry run results for reference
        state["dry_run_results"] = dry_run_result

    except Exception as e:
        state["plan_verification"] = {
            "status": "error",
            "error": str(e),
            "can_proceed": False,
        }
        state["dry_run_results"] = {"error": str(e)}

    return state


def validate_syntax(code: str) -> Dict[str, Any]:
    """
    Validate Python syntax of generated code

    Args:
        code: Python code string

    Returns:
        Syntax validation result
    """
    try:
        ast.parse(code)
        return {
            "valid": True,
            "error": None,
        }
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Syntax error at line {e.lineno}: {e.msg}",
            "line": e.lineno,
        }
    except Exception as e:
        return {
            "valid": False,
            "error": f"Parsing error: {str(e)}",
        }


def validate_imports(code: str) -> Dict[str, Any]:
    """
    Validate that required imports are present and available

    Args:
        code: Python code string

    Returns:
        Import validation result
    """
    # Extract imports from code
    imports = extract_imports(code)

    # Check for required imports
    required_imports = {
        "json": False,
    }

    # Check if playwright is used (should be imported)
    if "playwright" in code.lower() or "sync_playwright" in code or "page.goto" in code:
        required_imports["playwright"] = False

    for imp in imports:
        for req in required_imports:
            if req in imp:
                required_imports[req] = True

    missing = [k for k, v in required_imports.items() if not v]

    return {
        "valid": len(missing) == 0,
        "missing_imports": missing,
        "found_imports": imports,
    }


def validate_code_structure(code: str) -> Dict[str, Any]:
    """
    Validate the structure of generated code

    Args:
        code: Python code string

    Returns:
        Structure validation result
    """
    issues = []

    # Check for main function
    has_main = "def main()" in code or "def scrape(" in code
    if not has_main:
        issues.append("No main function found. Code should have a main() or scrape() function.")

    # Check for JSON output
    has_json_output = "print(json" in code or "json.dumps" in code
    if not has_json_output:
        issues.append("No JSON output found. Code should print results as JSON.")

    # Check for proper error handling
    has_try_except = "try:" in code and "except" in code
    if not has_try_except:
        issues.append("No error handling found. Consider adding try-except blocks.")

    # Check for browser initialization
    has_browser = "sync_playwright" in code or "chromium.launch" in code
    if not has_browser:
        issues.append("No browser initialization found. Web scraping typically requires Playwright.")

    # Check for proper browser closure
    has_browser_close = "browser.close()" in code
    if has_browser and not has_browser_close:
        issues.append("Browser not properly closed. Add browser.close() to prevent resource leaks.")

    # Check for sync API (not async)
    has_async_api = "async def" in code or "await page" in code
    if has_async_api:
        issues.append("Code uses async API. Use sync_playwright with sync API instead.")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "has_main_function": has_main,
        "has_json_output": has_json_output,
        "has_error_handling": has_try_except,
    }


async def perform_dry_run(code: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform a dry-run of the generated code with early exit

    Modifies the code to exit after initialization and basic checks.

    Args:
        code: Generated code
        state: Current agent state

    Returns:
        Dry run result
    """
    from .sandbox import create_sandbox

    # Modify code for dry run - add early exit after initialization
    dry_run_code = inject_dry_run_exit(code)

    try:
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(dry_run_code, timeout=30)

        return {
            "success": result["success"],
            "output": result.get("output"),
            "error": result.get("error"),
            "stderr": result.get("stderr", ""),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def inject_dry_run_exit(code: str) -> str:
    """
    Inject early exit code for dry run

    Adds exit after browser initialization and basic checks.

    Args:
        code: Original code

    Returns:
        Modified code with early exit
    """
    # Find the browser initialization and add early exit after it
    # This is a simple heuristic - we add exit after browser.new_page()

    lines = code.split("\n")
    modified_lines = []

    for i, line in enumerate(lines):
        modified_lines.append(line)

        # Add early exit after browser initialization
        if "browser.new_page()" in line or ("page = browser" in line and "new_page" in line):
            # Add a few lines to allow basic setup
            modified_lines.append("        # Dry-run: Early exit after initialization")
            modified_lines.append("        print(json.dumps({\"dry_run\": \"success\", \"browser_initialized\": True}))")
            modified_lines.append("        browser.close()")
            modified_lines.append("        return {\"results\": [], \"metadata\": {\"dry_run\": True}}")
            break

    return "\n".join(modified_lines)


def extract_imports(code: str) -> List[str]:
    """
    Extract import statements from code

    Args:
        code: Python code string

    Returns:
        List of import statements
    """
    imports = []

    for line in code.split("\n"):
        line = line.strip()
        if line.startswith("import ") or line.startswith("from "):
            imports.append(line)

    return imports


def determine_status(
    syntax_check: Dict[str, Any],
    import_check: Dict[str, Any],
    structure_check: Dict[str, Any],
    dry_run: Dict[str, Any],
) -> str:
    """
    Determine overall verification status

    Args:
        syntax_check: Syntax validation result
        import_check: Import validation result
        structure_check: Structure validation result
        dry_run: Dry run result

    Returns:
        Status string: "passed", "warning", or "failed"
    """
    if not syntax_check["valid"]:
        return "failed"

    if not dry_run.get("success", False):
        return "failed"

    if not import_check["valid"] or not structure_check["valid"]:
        return "warning"

    return "passed"


def collect_warnings(
    syntax_check: Dict[str, Any],
    import_check: Dict[str, Any],
    structure_check: Dict[str, Any],
) -> List[str]:
    """
    Collect all warnings from validation checks

    Args:
        syntax_check: Syntax validation result
        import_check: Import validation result
        structure_check: Structure validation result

    Returns:
        List of warning messages
    """
    warnings = []

    if not import_check["valid"]:
        warnings.append(f"Missing imports: {', '.join(import_check['missing_imports'])}")

    if structure_check.get("issues"):
        warnings.extend(structure_check["issues"])

    return warnings


def generate_verification_recommendations(
    syntax_check: Dict[str, Any],
    import_check: Dict[str, Any],
    structure_check: Dict[str, Any],
    dry_run: Dict[str, Any],
) -> List[str]:
    """
    Generate recommendations based on verification results

    Args:
        syntax_check: Syntax validation result
        import_check: Import validation result
        structure_check: Structure validation result
        dry_run: Dry run result

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if not syntax_check["valid"]:
        recommendations.append(f"Fix syntax error: {syntax_check['error']}")

    if not import_check["valid"]:
        recommendations.append("Add missing import statements")

    if not structure_check["valid"]:
        if not structure_check["has_main_function"]:
            recommendations.append("Add a main() or scrape() function")
        if not structure_check["has_json_output"]:
            recommendations.append("Ensure code prints results as JSON")
        if not structure_check["has_error_handling"]:
            recommendations.append("Consider adding try-except blocks for error handling")

    if not dry_run.get("success", False):
        error = dry_run.get("error", "Unknown error")
        recommendations.append(f"Fix execution error: {error[:100]}")

    return recommendations


def should_skip_plan_verification(state: Dict[str, Any]) -> bool:
    """
    Check if plan verification should be skipped

    Args:
        state: Current agent state

    Returns:
        True if verification should be skipped
    """
    import os

    # Skip if feature flag is disabled
    if os.getenv("ENABLE_PLAN_VERIFICATION", "true").lower() != "true":
        return True

    # Skip if no code was generated
    if not state.get("generated_code"):
        return True

    return False
