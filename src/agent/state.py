"""
State - LangGraph 状态定义

定义侦察任务的状态结构，用于 LangGraph 状态机。
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class ReconState(TypedDict):
    """侦察任务状态

    LangGraph 状态机使用的核心数据结构
    """
    # ===== 输入 =====
    site_url: str
    user_goal: str
    task_id: str
    created_at: str

    # ===== Sense 节点 =====
    site_context: Optional[Dict[str, Any]]
    detected_features: Optional[List[str]]
    html_snapshot: Optional[str]

    # ===== Plan 节点 =====
    generated_code: Optional[str]
    plan_reasoning: Optional[str]

    # ===== Act 节点 =====
    execution_result: Optional[Dict[str, Any]]
    execution_logs: Optional[List[str]]
    screenshots: Optional[List[str]]

    # ===== Verify 节点 =====
    quality_score: Optional[float]
    sample_data: Optional[List[Dict[str, Any]]]
    quality_issues: Optional[List[str]]

    # ===== Report 节点 =====
    final_report: Optional[Dict[str, Any]]
    markdown_report: Optional[str]

    # ===== SOOAL 循环 =====
    sool_iteration: int
    last_error: Optional[str]
    error_history: Optional[List[str]]

    # ===== 控制 =====
    stage: str  # sense/plan/act/verify/report/done/failed
    error: Optional[str]


def create_initial_state(
    site_url: str,
    user_goal: str,
    task_id: Optional[str] = None,
) -> ReconState:
    """创建初始状态"""
    import uuid

    return ReconState(
        # 输入
        site_url=site_url,
        user_goal=user_goal,
        task_id=task_id or f"recon_{uuid.uuid4().hex[:8]}",
        created_at=datetime.now().isoformat(),

        # Sense
        site_context=None,
        detected_features=None,
        html_snapshot=None,

        # Plan
        generated_code=None,
        plan_reasoning=None,

        # Act
        execution_result=None,
        execution_logs=None,
        screenshots=None,

        # Verify
        quality_score=None,
        sample_data=None,
        quality_issues=None,

        # Report
        final_report=None,
        markdown_report=None,

        # SOOAL
        sool_iteration=0,
        last_error=None,
        error_history=None,

        # 控制
        stage="sense",
        error=None,
    )


# ===== 辅助函数 =====

def should_run_sool(state: ReconState) -> str:
    """判断是否需要 SOOAL 修复"""
    if not state.get("execution_result"):
        return "sool"

    if state["execution_result"].get("success"):
        return "verify"

    # 检查错误是否可修复
    error = state["execution_result"].get("error")
    if error and state["sool_iteration"] < 6:
        return "sool"

    return "verify"


def should_retry(state: ReconState) -> str:
    """判断是否需要重试"""
    quality = state.get("quality_score", 0)

    if quality >= 0.6:
        return "report"

    if state["sool_iteration"] >= 6:
        return "report"  # 放弃重试，直接报告

    return "retry"
