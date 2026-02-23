"""
SiteAgent - 混合架构侦察智能体

基于 LangGraph 状态机 + LLM 代码生成 + 沙箱执行。
"""

import asyncio
import uuid
import os
from typing import Dict, Any, Optional, Callable, AsyncIterator
from pathlib import Path

# 加载 .env 文件
try:
    from dotenv import load_dotenv
    # 尝试加载项目根目录的 .env 文件
    env_path = Path(__file__).parent.parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass  # 如果没有 python-dotenv，就跳过

from .graph import create_recon_graph
from .state import ReconState, create_initial_state, compute_data_success


class SiteAgent:
    """
    混合架构侦察智能体

    特性:
    - LangGraph 状态机驱动
    - LLM 生成爬虫代码
    - 沙箱执行生成代码
    - SOOAL 自修复循环
    """

    def __init__(
        self,
        on_progress: Optional[Callable[[Dict], None]] = None,
        on_result: Optional[Callable[[Dict], None]] = None,
        on_error: Optional[Callable[[Dict], None]] = None,
    ):
        self.agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        self._callbacks = {
            "on_progress": on_progress,
            "on_result": on_result,
            "on_error": on_error,
        }

        # 创建状态机
        self.graph = create_recon_graph()

    async def run(self, task_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行侦察任务

        Args:
            task_params: {
                "site_url": str,      # 必填
                "user_goal": str,      # 必填
                "max_samples": int,    # 可选
                "timeout": int,        # 可选
            }

        Returns:
            侦察报告
        """
        # 创建初始状态
        initial_state = create_initial_state(
            site_url=task_params["site_url"],
            user_goal=task_params["user_goal"],
            task_id=task_params.get("task_id"),
        )

        # 运行状态机
        try:
            final_state = await self.graph.ainvoke(initial_state)

            data_success = final_state.get("data_success")
            if data_success is None:
                data_success = compute_data_success(final_state)

            # 构建结果（包含完整状态用于详细日志）
            result = {
                "success": final_state["stage"] == "done",
                "data_success": bool(data_success),
                "completion_status": final_state.get("completion_status", final_state.get("stage", "unknown")),
                "failure_reason": final_state.get("failure_reason"),
                "agent_id": self.agent_id,
                "site_url": task_params["site_url"],
                "user_goal": task_params["user_goal"],
                "report": final_state.get("final_report"),
                "markdown_report": final_state.get("markdown_report"),
                "generated_code": final_state.get("generated_code"),
                "stage": final_state["stage"],
                # 新增：完整状态，包含 failure_history, reflection_memory 等
                "final_state": {
                    "stage": final_state.get("stage"),
                    "quality_score": final_state.get("quality_score"),
                    "sample_data": final_state.get("sample_data"),
                    "generated_code": final_state.get("generated_code"),  # 修复：添加 generated_code 字段
                    "sool_iteration": final_state.get("sool_iteration", 0),
                    "failure_history": final_state.get("failure_history", []),
                    "reflection_memory": final_state.get("reflection_memory", []),
                    "attempt_signatures": final_state.get("attempt_signatures", []),
                    "quality_issues": final_state.get("quality_issues", []),
                    "performance_data": final_state.get("performance_data", {}),  # 新增：性能数据
                    "execution_result": final_state.get("execution_result", {}),
                    "plan_verification": final_state.get("plan_verification", {}),
                    "classification_detail": final_state.get("classification_detail", {}),
                    "navigation_trace": final_state.get("navigation_trace", []),
                    "website_type": final_state.get("website_type", "unknown"),
                    "data_success": bool(data_success),
                    "completion_status": final_state.get("completion_status", final_state.get("stage", "unknown")),
                    "failure_reason": final_state.get("failure_reason"),
                    "error": final_state.get("error"),
                }
            }

            # 成功回调
            if self._callbacks["on_result"]:
                self._callbacks["on_result"](result)

            return result

        except Exception as e:
            error_result = {
                "success": False,
                "data_success": False,
                "agent_id": self.agent_id,
                "site_url": task_params["site_url"],
                "error": str(e),
                "stage": "error",
                "completion_status": "error",
                "failure_reason": "AGENT_RUNTIME_ERROR",
            }

            # 错误回调
            if self._callbacks["on_error"]:
                self._callbacks["on_error"](error_result)

            return error_result

    def get_status(self) -> Dict[str, Any]:
        """获取 Agent 状态"""
        return {
            "agent_id": self.agent_id,
            "graph": "LangGraph ReconGraph",
            "nodes": ["sense", "plan", "act", "verify", "report", "soal"],
        }

    async def stream(self, task_params: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        """
        流式输出侦察进度

        实时输出每个节点的执行结果
        """
        initial_state = create_initial_state(
            site_url=task_params["site_url"],
            user_goal=task_params["user_goal"],
        )

        async for event in self.graph.astream(initial_state):
            # LangGraph 的 astream 返回的是 (node_name, state) 元组或字典
            if isinstance(event, dict):
                node_name = event.get("node", "")
                state = event.get("state", event)
            else:
                # 尝试解包元组
                try:
                    node_name, state = event
                except:
                    continue

            # 输出每个节点完成后的状态
            if node_name == "sense":
                yield {"stage": "sense", "state": state}
            elif node_name == "plan":
                yield {"stage": "plan", "state": state}
            elif node_name == "act":
                yield {"stage": "act", "state": state}
            elif node_name == "verify":
                yield {"stage": "verify", "state": state}
            elif node_name == "report":
                yield {"stage": "report", "state": state}

    async def close(self):
        """
        关闭 Agent 并释放资源

        关闭浏览器连接等资源。
        """
        # 如果有需要清理的资源，在这里处理
        # 当前实现中，浏览器由沙箱管理，会自动关闭
        pass


# ===== 兼容性导出 =====

# 旧的组件名兼容
from .tools import BrowserTool
from .tools import ParserTool
