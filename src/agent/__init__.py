"""
Agent Layer - Hybrid Reconnaissance Agent

基于 LangGraph 状态机 + LLM 代码生成 + 沙箱执行的混合架构。

Architecture:
    - LangGraph 状态机 (graph.py)
    - LLM 客户端 (llm/client.py - 智谱 GLM)
    - 沙箱执行器 (sandbox.py - Docker/Simple)
    - 工具链 (tools/ - Browser, Parser)
    - Prompt 模板 (prompts/)

Usage:
    agent = SiteAgent()
    result = await agent.run({
        "site_url": "https://example.com",
        "user_goal": "提取所有产品标题和价格"
    })
"""

from .agent import SiteAgent
from .callbacks import ProgressCallback, StuckCallback, ResultCallback
from .graph import create_recon_graph
from .state import ReconState, create_initial_state

__all__ = [
    "SiteAgent",
    "ProgressCallback",
    "StuckCallback",
    "ResultCallback",
    "create_recon_graph",
    "ReconState",
    "create_initial_state",
]
