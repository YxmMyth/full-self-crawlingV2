"""
State - LangGraph 状态定义

定义侦察任务的状态结构，用于 LangGraph 状态机。
"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
import os


# ============================================================================
# 配置函数 - 从环境变量获取阈值
# ============================================================================

def get_quality_threshold() -> float:
    """获取质量阈值，默认 0.6

    可以通过环境变量 QUALITY_THRESHOLD 配置。
    低于此值的质量分数将触发代码重新生成。
    """
    return float(os.getenv("QUALITY_THRESHOLD", "0.6"))


def get_max_sool_iterations() -> int:
    """获取最大 SOOAL 迭代次数，默认 6

    可以通过环境变量 MAX_SOOL_ITERATIONS 配置。
    达到此次数后将停止代码修复，直接生成报告。
    """
    return int(os.getenv("MAX_SOOL_ITERATIONS", "6"))


def get_validation_config() -> Dict[str, bool]:
    """获取验证配置选项

    返回从环境变量读取的验证开关配置。
    """
    return {
        "validate_images": os.getenv("VALIDATE_IMAGES", "true").lower() == "true",
        "check_image_accessibility": os.getenv("CHECK_IMAGE_ACCESSIBILITY", "false").lower() == "true",
        "check_duplicates": os.getenv("CHECK_DUPLICATES", "true").lower() == "true",
        "validate_urls": os.getenv("VALIDATE_URLS", "true").lower() == "true",
        "validate_dates": os.getenv("VALIDATE_DATES", "true").lower() == "true",
    }


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
    sense_analysis: Optional[Dict[str, Any]]  # DOM 分析结果

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
    quality_stats: Optional[Dict[str, Any]]  # 详细的质量统计信息

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
        sense_analysis=None,

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
        quality_stats=None,

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
    """判断是否需要 SOOAL 修复

    Returns:
        "soal" - 执行失败，需要修复
        "verify" - 执行成功，继续验证
    """
    execution_result = state.get("execution_result")
    max_iter = get_max_sool_iterations()

    # 如果没有执行结果，需要 SOOAL
    if not execution_result:
        return "soal"

    # 执行成功，跳过 SOOAL
    if execution_result.get("success"):
        return "verify"

    # 执行失败，检查迭代次数
    error = execution_result.get("error")
    if error and state.get("sool_iteration", 0) < max_iter:
        return "soal"

    # 超过最大迭代次数，直接验证
    return "verify"


def should_retry(state: ReconState) -> str:
    """判断是否需要重试

    使用可配置的质量阈值和最大迭代次数。

    Returns:
        "report" - 质量合格或达到最大迭代，生成报告
        "retry" - 质量不合格且未达到最大迭代，重新生成代码
    """
    quality = state.get("quality_score", 0)
    threshold = get_quality_threshold()
    max_iter = get_max_sool_iterations()

    # 质量合格，生成报告
    if quality >= threshold:
        return "report"

    # 达到最大迭代次数，生成报告
    if state.get("sool_iteration", 0) >= max_iter:
        return "report"

    # 质量不合格且未达到最大迭代，重试
    return "retry"
