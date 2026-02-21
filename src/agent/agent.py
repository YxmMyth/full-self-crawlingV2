"""
SiteAgent - 混合架构侦察智能体

基于 LangGraph 状态机 + LLM 代码生成 + 沙箱执行。
"""

import asyncio
import uuid
from typing import Dict, Any, Optional, Callable

from .graph import create_recon_graph
from .state import ReconState, create_initial_state


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

            # 构建结果
            result = {
                "success": final_state["stage"] == "done",
                "agent_id": self.agent_id,
                "site_url": task_params["site_url"],
                "user_goal": task_params["user_goal"],
                "report": final_state.get("final_report"),
                "markdown_report": final_state.get("markdown_report"),
                "generated_code": final_state.get("generated_code"),
                "stage": final_state["stage"],
            }

            # 成功回调
            if self._callbacks["on_result"]:
                self._callbacks["on_result"](result)

            return result

        except Exception as e:
            error_result = {
                "success": False,
                "agent_id": self.agent_id,
                "site_url": task_params["site_url"],
                "error": str(e),
                "stage": "error",
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

    async def stream(self, task_params: Dict[str, Any]):
        """
        流式输出侦察进度

        实时输出每个节点的执行结果
        """
        initial_state = create_initial_state(
            site_url=task_params["site_url"],
            user_goal=task_params["user_goal"],
        )

        async for event in self.graph.astream(initial_state):
            # 输出每个节点完成后的状态
            if event.name == "sense":
                yield {"stage": "sense", "data": event}
            elif event.name == "plan":
                yield {"stage": "plan", "code_generated": True}
            elif event.name == "act":
                yield {"stage": "act", "executed": True}
            elif event.name == "verify":
                yield {"stage": "verify", "quality": event.get("quality_score")}
            elif event.name == "report":
                yield {"stage": "report", "done": True}


# ===== 兼容性导出 =====

# 旧的组件名兼容
from .tools import BrowserTool
from .tools import ParserTool
