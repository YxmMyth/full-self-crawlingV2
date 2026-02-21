"""
Graph - LangGraph 状态机

定义侦察任务的 LangGraph 状态机。
"""

from typing import Literal
from langgraph.graph import StateGraph, END

from .state import ReconState, create_initial_state, should_run_sool, should_retry
from .nodes import (
    sense_node,
    plan_node,
    act_node,
    verify_node,
    report_node,
    soal_node,
)


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

    # 添加边（正常流程）
    graph.add_edge("sense", "plan")
    graph.add_edge("plan", "act")

    # 条件边：act → verify 或 act → sool
    graph.add_conditional_edges(
        "act",
        lambda state: "sool" if should_run_sool(state) == "sool" else "verify",
        {
            "sool": "sool",
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
    graph.add_edge("sool", "act")

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

    state["stage"] = "plan"

    # 构建 prompt
    prompt = CODE_GENERATION_PROMPT.format(
        site_url=state["site_url"],
        user_goal=state["user_goal"],
        detected_features=", ".join(state.get("detected_features", [])),
        html_size=len(state.get("html_snapshot", "")),
    )

    # TODO: 调用 LLM 生成代码
    # code = await llm_generate(prompt)
    # state["generated_code"] = code

    # 临时：使用占位符
    state["generated_code"] = "# TODO: LLM generated code\n" + prompt
    state["plan_reasoning"] = "根据站点特征生成定制爬虫"

    return state


async def act_node(state: ReconState) -> ReconState:
    """Act 节点：沙箱执行代码"""
    from .sandbox import SandboxExecutor

    state["stage"] = "act"

    executor = SandboxExecutor()

    result = await executor.execute(
        code=state["generated_code"],
        timeout=300,
    )

    state["execution_result"] = result
    state["execution_logs"] = result.get("logs", [])
    state["sool_iteration"] = state.get("sool_iteration", 0)

    return state


async def verify_node(state: ReconState) -> ReconState:
    """Verify 节点：质量评估"""
    state["stage"] = "verify"

    # TODO: 实际的质量评估逻辑
    # 临时：基于执行结果打分
    if state["execution_result"].get("success"):
        state["quality_score"] = 0.8
        state["sample_data"] = state["execution_result"].get("data", [])
    else:
        state["quality_score"] = 0.0
        state["sample_data"] = []

    return state


async def report_node(state: ReconState) -> ReconState:
    """Report 节点：生成最终报告"""
    from .prompts import REPORT_GENERATION_PROMPT

    state["stage"] = "report"

    # 生成报告
    # TODO: 使用 LLM 生成 Markdown 报告
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
    from .prompts import CODE_REPAIR_PROMPT

    state["sool_iteration"] += 1

    # TODO: 使用 LLM 修复代码
    prompt = CODE_REPAIR_PROMPT.format(
        original_code=state["generated_code"],
        error_logs="\n".join(state.get("execution_logs", [])),
        sool_iteration=state["sool_iteration"],
    )

    # repaired_code = await llm_generate(prompt)
    # state["generated_code"] = repaired_code

    # 临时：记录错误历史
    if state.get("error_history") is None:
        state["error_history"] = []
    state["error_history"].append(state.get("last_error", "unknown"))

    return state


# ===== 沙箱执行器 =====

class SandboxExecutor:
    """沙箱代码执行器（简化版）"""

    async def execute(
        self,
        code: str,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """在沙箱中执行代码"""
        import asyncio
        import tempfile
        import os

        # 写入临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8'
        ) as f:
            f.write(code)
            code_path = f.name

        try:
            # 执行代码
            process = await asyncio.create_subprocess_exec(
                'python',
                code_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            success = process.returncode == 0

            return {
                "success": success,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode,
                "error": stderr if not success else None,
            }

        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": "Execution timeout",
            }

        finally:
            # 清理临时文件
            try:
                os.unlink(code_path)
            except:
                pass
