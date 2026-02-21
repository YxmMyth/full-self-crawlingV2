"""
Graph - LangGraph 状态机

定义侦察任务的 LangGraph 状态机。
"""

from typing import Literal
from langgraph.graph import StateGraph, END, START

from .state import ReconState, create_initial_state, should_run_sool, should_retry


def create_recon_graph() -> StateGraph:
    """创建侦察任务状态机

    Returns:
        StateGraph: 编译好的状态机
    """
    graph = StateGraph(ReconState)

    # 添加节点
    graph.add_node("sense", sense_node)
    graph.add_node("plan", plan_node)
    graph.add_node("act", act_node)
    graph.add_node("verify", verify_node)
    graph.add_node("report", report_node)
    graph.add_node("soal", soal_node)

    # 添加边：START → sense（入口点）
    graph.add_edge(START, "sense")

    # 添加边（正常流程）
    graph.add_edge("sense", "plan")
    graph.add_edge("plan", "act")

    # 条件边：act → verify 或 act → soal
    graph.add_conditional_edges(
        "act",
        should_run_sool,
        {
            "soal": "soal",
            "verify": "verify"
        }
    )

    # 条件边：verify → report 或 verify → plan（重试）
    graph.add_conditional_edges(
        "verify",
        lambda state: "retry" if should_retry(state) == "retry" else "report",
        {
            "retry": "plan",
            "report": "report"
        }
    )

    # SOOAL 循环
    graph.add_edge("soal", "act")

    # 结束
    graph.add_edge("report", END)

    return graph.compile()


# ===== 节点实现（简化版）=====

async def sense_node(state: ReconState) -> ReconState:
    """Sense 节点：快速探测站点"""
    from .tools import BrowserTool

    state["stage"] = "sense"

    browser = BrowserTool()
    try:
        result = await browser.browse(
            state["site_url"],
            wait_for="body",
            screenshot=True,
        )
        state["site_context"] = result
        state["detected_features"] = result.get("features", [])
        state["html_snapshot"] = result.get("html", "")[:5000]  # 限制大小
    except Exception as e:
        state["error"] = f"Sense failed: {str(e)}"
        state["stage"] = "failed"
    finally:
        await browser.close()

    return state


async def plan_node(state: ReconState) -> ReconState:
    """Plan 节点：LLM 生成爬虫代码"""
    from .prompts import CODE_GENERATION_PROMPT
    from .llm import generate_code

    state["stage"] = "plan"

    # 构建 prompt
    prompt = CODE_GENERATION_PROMPT.format(
        site_url=state["site_url"],
        user_goal=state["user_goal"],
        detected_features=", ".join(state.get("detected_features", [])),
        html_size=len(state.get("html_snapshot", "")),
    )

    # 调用 LLM 生成代码
    try:
        code = await generate_code(prompt)
        state["generated_code"] = code
        state["plan_reasoning"] = f"LLM 根据 {len(state.get('detected_features', []))} 个特征生成代码"
    except Exception as e:
        state["error"] = f"Plan failed: {str(e)}"
        state["generated_code"] = ""

    return state


async def act_node(state: ReconState) -> ReconState:
    """Act 节点：沙箱执行代码"""
    from .sandbox import create_sandbox

    state["stage"] = "act"

    # 创建沙箱（可配置使用 Docker 或 Simple）
    executor = create_sandbox(use_docker=False)  # 开发阶段用 Simple

    result = await executor.execute(
        code=state["generated_code"],
        timeout=300,
    )

    state["execution_result"] = result
    state["execution_logs"] = [result.get("stderr", "")]
    state["sool_iteration"] = state.get("sool_iteration", 0)

    # 提取 sample_data 供 verify 节点使用
    if result.get("parsed_data"):
        if isinstance(result["parsed_data"], dict) and "results" in result["parsed_data"]:
            state["sample_data"] = result["parsed_data"]["results"]
        elif isinstance(result["parsed_data"], list):
            state["sample_data"] = result["parsed_data"]
        else:
            state["sample_data"] = []
    else:
        state["sample_data"] = []

    return state


async def verify_node(state: ReconState) -> ReconState:
    """Verify 节点：质量评估"""
    from .llm import ZhipuClient
    import os

    state["stage"] = "verify"

    # 使用 LLM 评估质量
    try:
        client = ZhipuClient(api_key=os.environ.get("ZHIPU_API_KEY"))
        quality_result = await client.evaluate_quality(
            user_goal=state["user_goal"],
            extracted_data=state.get("sample_data", []),
        )
        state["quality_score"] = quality_result.get("overall_score", 0.0)
        state["quality_issues"] = quality_result.get("issues", [])
    except Exception as e:
        # 降级：基于执行结果简单打分
        if state["execution_result"].get("success"):
            state["quality_score"] = 0.8
        else:
            state["quality_score"] = 0.0

    return state


async def report_node(state: ReconState) -> ReconState:
    """Report 节点：生成最终报告"""
    from .llm import ZhipuClient
    import os

    state["stage"] = "report"

    # 使用 LLM 生成报告
    try:
        client = ZhipuClient(api_key=os.environ.get("ZHIPU_API_KEY"))
        markdown = await client.generate_report(
            site_url=state["site_url"],
            user_goal=state["user_goal"],
            site_info=state.get("site_context", {}),
            sample_data=state.get("sample_data", []),
        )
        state["markdown_report"] = markdown
    except Exception as e:
        # 降级：生成简单报告
        markdown = f"""# 网站数据侦察报告

## 站点信息
- URL: {state['site_url']}
- 用户需求: {state['user_goal']}

## 侦察总结
- SOOAL 迭代: {state['sool_iteration']}
- 质量分数: {state.get('quality_score', 0)}
- 样本数量: {len(state.get('sample_data', []))}
"""
        state["markdown_report"] = markdown

    state["final_report"] = {
        "site_url": state["site_url"],
        "user_goal": state["user_goal"],
        "quality_score": state.get("quality_score", 0),
        "sample_data": state.get("sample_data", []),
        "generated_code": state.get("generated_code", ""),
    }
    state["stage"] = "done"

    return state


async def soal_node(state: ReconState) -> ReconState:
    """SOOAL 节点：代码修复"""
    from .llm import ZhipuClient
    import os

    state["sool_iteration"] += 1

    # 使用 LLM 修复代码
    try:
        client = ZhipuClient(api_key=os.environ.get("ZHIPU_API_KEY"))
        repaired_code = await client.repair_code(
            original_code=state["generated_code"],
            error_logs="\n".join(state.get("execution_logs", [])),
            iteration=state["sool_iteration"],
        )
        state["generated_code"] = repaired_code
        state["last_error"] = "Code repaired by LLM"
    except Exception as e:
        state["last_error"] = f"SOOAL failed: {str(e)}"

    # 记录错误历史
    if state.get("error_history") is None:
        state["error_history"] = []
    state["error_history"].append(state.get("last_error", "unknown"))

    return state


# ===== 沙箱执行器导入 =====

from .sandbox import create_sandbox
