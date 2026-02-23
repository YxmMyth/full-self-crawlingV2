"""
Agent structure smoke tests.

These tests validate graph wiring and core helper semantics without calling
external LLM APIs.
"""

import sys
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_graph_structure() -> bool:
    """Graph contains expected nodes."""
    from src.agent.graph import create_recon_graph

    graph = create_recon_graph()
    nodes = set(graph.nodes.keys())
    expected = {
        "sense",
        "interact",
        "validate",
        "plan",
        "verify_plan",
        "act",
        "verify",
        "reflect",
        "report",
        "soal",
    }
    missing = expected - nodes
    assert not missing, f"missing nodes: {sorted(missing)}"
    return True


def test_state_initialization() -> bool:
    """Initial state contains required defaults."""
    from src.agent.state import create_initial_state

    state = create_initial_state(site_url="https://example.com", user_goal="collect records")
    assert state["site_url"] == "https://example.com"
    assert state["user_goal"] == "collect records"
    assert state["stage"] == "sense"
    assert state["sool_iteration"] == 0
    return True


def test_state_helper_functions() -> bool:
    """Core routing helpers behave as expected."""
    from src.agent.state import (
        compute_data_success,
        create_initial_state,
        should_proceed_after_plan_verification,
        should_retry,
        should_run_sool,
    )

    state = create_initial_state(site_url="https://example.com", user_goal="collect records")

    # No execution output -> repair loop.
    assert should_run_sool(state) == "soal"

    # Successful execution with data -> verify.
    state["generated_code"] = "print('ok')"
    state["execution_result"] = {"success": True, "parsed_data": {"results": [{"title": "x"}]}}
    assert should_run_sool(state) == "verify"

    # Failed execution -> repair loop (if under budget).
    state["execution_result"] = {"success": False, "error": "runtime error"}
    assert should_run_sool(state) == "soal"

    # Quality retry routing.
    state["quality_score"] = 0.9
    assert should_retry(state) == "report"
    state["quality_score"] = 0.1
    assert should_retry(state) == "retry"

    # Plan verification gate.
    state["generated_code"] = ""
    state["plan_verification"] = {"can_proceed": True}
    assert should_proceed_after_plan_verification(state) == "soal"

    state["generated_code"] = "print('ok')"
    state["plan_verification"] = {"can_proceed": False}
    assert should_proceed_after_plan_verification(state) == "soal"

    state["plan_verification"] = {"can_proceed": True}
    assert should_proceed_after_plan_verification(state) == "act"

    # Data success semantics.
    state["sample_data"] = []
    state["quality_score"] = 0.9
    assert compute_data_success(state) is False

    state["sample_data"] = [{"title": "demo"}]
    state["quality_score"] = 0.9
    assert compute_data_success(state) is True
    return True


def test_agent_creation() -> bool:
    """Agent can be constructed."""
    from src.agent import SiteAgent

    agent = SiteAgent()
    status = agent.get_status()
    assert "agent_id" in status
    assert "graph" in status
    assert "nodes" in status
    return True


def test_llm_client_creation() -> bool:
    """LLM client can be created with a dummy key."""
    from src.agent.llm import ZhipuClient

    client = ZhipuClient(api_key="test_key")
    assert client.model
    return True


def test_browser_tool_creation() -> bool:
    """Browser tool can be created."""
    from src.agent.tools import BrowserTool

    _ = BrowserTool()
    return True


def test_sandbox_creation() -> bool:
    """Simple sandbox can be created."""
    from src.agent.sandbox import create_sandbox

    _ = create_sandbox(use_docker=False)
    return True


def main() -> bool:
    tests = [
        test_graph_structure,
        test_state_initialization,
        test_state_helper_functions,
        test_agent_creation,
        test_llm_client_creation,
        test_browser_tool_creation,
        test_sandbox_creation,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"[PASS] {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"[FAIL] {test.__name__}: {exc}")

    print(f"summary: passed={passed}, failed={failed}")
    return failed == 0


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
