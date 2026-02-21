"""
Agent 结构测试 - 不调用 LLM API

仅验证状态机结构和节点定义是否正确
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_graph_structure():
    """测试图结构"""
    print("测试 LangGraph 状态机结构...")

    from src.agent.graph import create_recon_graph

    graph = create_recon_graph()

    # 获取所有节点
    nodes = list(graph.nodes.keys())
    print(f"  节点: {nodes}")

    # 验证节点存在
    expected_nodes = ["sense", "plan", "act", "verify", "report", "soal"]
    for node in expected_nodes:
        if node not in nodes:
            print(f"  [FAIL] 缺少节点: {node}")
            return False
        print(f"  [OK] 节点存在: {node}")

    return True


def test_state_initialization():
    """测试状态初始化"""
    print("\n测试状态初始化...")

    from src.agent.state import create_initial_state

    state = create_initial_state(
        site_url="https://example.com",
        user_goal="测试目标"
    )

    # 验证初始值
    assert state["site_url"] == "https://example.com", "site_url 未设置"
    assert state["user_goal"] == "测试目标", "user_goal 未设置"
    assert state["stage"] == "sense", "初始阶段应该是 sense"
    assert state["sool_iteration"] == 0, "初始迭代次数应该是 0"

    print("  [OK] 状态初始化正确")
    print(f"    - task_id: {state['task_id']}")
    print(f"    - stage: {state['stage']}")
    print(f"    - sool_iteration: {state['sool_iteration']}")

    return True


def test_state_helper_functions():
    """测试辅助函数"""
    print("\n测试辅助函数...")

    from src.agent.state import should_run_sool, should_retry, create_initial_state

    # 测试 should_run_sool
    state = create_initial_state(
        site_url="https://example.com",
        user_goal="测试"
    )

    # 没有执行结果，应该返回 soal
    result = should_run_sool(state)
    assert result == "soal", f"无执行结果时应返回 'soal'，实际返回: {result}"
    print("  [OK] should_run_sool: 无执行结果 -> soal")

    # 模拟执行成功
    state["execution_result"] = {"success": True}
    result = should_run_sool(state)
    assert result == "verify", f"执行成功时应返回 'verify'，实际返回: {result}"
    print("  [OK] should_run_sool: 执行成功 -> verify")

    # 模拟执行失败
    state["execution_result"] = {"success": False, "error": "test error"}
    result = should_run_sool(state)
    assert result == "soal", f"执行失败时应返回 'soal'，实际返回: {result}"
    print("  [OK] should_run_sool: 执行失败 -> soal")

    # 测试 should_retry
    state["quality_score"] = 0.8
    result = should_retry(state)
    assert result == "report", f"质量合格时应返回 'report'，实际返回: {result}"
    print("  [OK] should_retry: 质量合格 -> report")

    state["quality_score"] = 0.4
    result = should_retry(state)
    assert result == "retry", f"质量不合格时应返回 'retry'，实际返回: {result}"
    print("  [OK] should_retry: 质量不合格 -> retry")

    return True


def test_agent_creation():
    """测试 Agent 创建"""
    print("\n测试 SiteAgent 创建...")

    from src.agent import SiteAgent

    agent = SiteAgent()
    status = agent.get_status()

    print(f"  [OK] Agent 创建成功")
    print(f"    - agent_id: {status['agent_id']}")
    print(f"    - graph: {status['graph']}")
    print(f"    - nodes: {status['nodes']}")

    return True


def test_llm_client():
    """测试 LLM 客户端（不调用 API）"""
    print("\n测试 ZhipuClient 创建...")

    from src.agent.llm import ZhipuClient

    # 创建客户端（使用假 key）
    client = ZhipuClient(api_key="test_key")

    print("  [OK] ZhipuClient 创建成功")
    print(f"    - model: {client.model}")
    print(f"    - base_url: {client.base_url}")

    return True


def test_browser_tool():
    """测试 BrowserTool 创建"""
    print("\n测试 BrowserTool 创建...")

    from src.agent.tools import BrowserTool

    tool = BrowserTool()

    print("  [OK] BrowserTool 创建成功")

    return True


def test_sandbox():
    """测试沙箱创建"""
    print("\n测试沙箱创建...")

    from src.agent.sandbox import create_sandbox

    # 测试简单沙箱
    sandbox = create_sandbox(use_docker=False)
    print("  [OK] SimpleSandbox 创建成功")

    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("  Agent 结构测试（无需 API Key）")
    print("=" * 60)

    tests = [
        test_graph_structure,
        test_state_initialization,
        test_state_helper_functions,
        test_agent_creation,
        test_llm_client,
        test_browser_tool,
        test_sandbox,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {test.__name__}: {e}")

    print("\n" + "=" * 60)
    print(f"  测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n所有测试通过! 状态机结构正确。")
        print("\n下一步：设置 ZHIPU_API_KEY 后运行完整测试:")
        print("  $env:ZHIPU_API_KEY='your_key'")
        print("  python tests/test_single_agent.py")
    else:
        print("\n部分测试失败，请检查错误信息。")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
