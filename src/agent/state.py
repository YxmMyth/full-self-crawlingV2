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


def get_deep_validation_config() -> Dict[str, Any]:
    """
    获取深度验证配置

    返回从环境变量读取的深度验证配置。
    深度验证会在沙箱中下载和验证实际内容（图片、PDF、视频）。

    Returns:
        配置字典，包含：
        - enabled: 是否启用深度验证
        - max_images: 最多验证的图片数量
        - min_image_resolution: 最小图片分辨率要求
        - pdf_validation_enabled: 是否验证 PDF
        - clip_relevance_threshold: CLIP 相关性阈值
    """
    min_resolution = os.getenv("MIN_IMAGE_RESOLUTION", "1920x1080")

    return {
        "enabled": os.getenv("ENABLE_DEEP_VALIDATION", "false").lower() == "true",
        "max_images": int(os.getenv("MAX_IMAGES_TO_VALIDATE", "3")),
        "min_image_resolution": min_resolution,
        "min_image_width": int(min_resolution.split("x")[0]) if "x" in min_resolution else 1920,
        "min_image_height": int(min_resolution.split("x")[1]) if "x" in min_resolution else 1080,
        "pdf_validation_enabled": os.getenv("PDF_VALIDATION_ENABLED", "true").lower() == "true",
        "clip_relevance_threshold": float(os.getenv("CLIP_RELEVANCE_THRESHOLD", "0.3")),
        "video_validation_enabled": os.getenv("VIDEO_VALIDATION_ENABLED", "false").lower() == "true",
    }


def get_vision_api_config() -> Dict[str, Any]:
    """
    获取 Vision API 配置

    支持多个 Vision API 提供商：
    - openai: OpenAI GPT-4V
    - aliyun: 阿里云百炼多模态大模型
    - tencent: 腾讯云（预留）
    - none: 禁用

    Returns:
        配置字典，包含：
        - provider: 提供商名称
        - enabled: 是否启用
        - api_key: API 密钥
        - model: 模型名称
    """
    provider = os.getenv("VISION_API_PROVIDER", "none").lower()
    enabled = os.getenv("ENABLE_VISION_API", "false").lower() == "true"

    # 默认模型配置
    default_models = {
        "openai": "gpt-4o",
        "aliyun": "qwen3-omni-flash",  # 多模态能力模型
        "tencent": "",
    }

    # 默认 base_url 配置
    default_base_urls = {
        "openai": "",
        "aliyun": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",  # 默认新加坡
        "tencent": "",
    }

    # 获取 API Key（根据 provider）
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
    elif provider == "aliyun":
        api_key = os.getenv("ALIYUN_API_KEY", "")
    elif provider == "tencent":
        api_key = os.getenv("TENCENT_API_KEY", "")
    else:
        api_key = ""
        enabled = False

    # 获取 base_url（根据 provider）
    if provider == "aliyun":
        base_url = os.getenv("ALIYUN_BASE_URL", default_base_urls.get("aliyun", ""))
    elif provider == "openai":
        base_url = ""
    else:
        base_url = ""

    return {
        "provider": provider,
        "enabled": enabled and provider != "none",
        "api_key": api_key,
        "model": os.getenv("VISION_MODEL", default_models.get(provider, "")),
        "base_url": base_url,
    }


def get_stealth_config() -> Dict[str, Any]:
    """
    获取隐身配置

    Returns:
        配置字典，包含：
        - auto_detect: 是否自动检测反爬虫等级
        - default_level: 默认隐身等级
        - levels: 各等级的配置
    """
    return {
        "auto_detect": os.getenv("STEALTH_AUTO_DETECT", "true").lower() == "true",
        "default_level": os.getenv("STEALTH_DEFAULT_LEVEL", "medium"),
        "levels": {
            "none": {
                "use_stealth": False,
                "random_ua": False,
                "delay_range": (0, 0),
            },
            "low": {
                "use_stealth": True,
                "random_ua": True,
                "delay_range": (1, 2),
            },
            "medium": {
                "use_stealth": True,
                "random_ua": True,
                "delay_range": (2, 4),
            },
            "high": {
                "use_stealth": True,
                "random_ua": True,
                "delay_range": (3, 6),
            },
        },
    }


def get_verification_confidence_threshold() -> float:
    """
    获取验证置信度阈值

    Returns:
        置信度阈值 (默认 0.7)
    """
    return float(os.getenv("VERIFICATION_CONFIDENCE_THRESHOLD", "0.7"))


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
    valid_selectors: Optional[List[str]]  # 验证过的选择器
    dom_structure: Optional[Dict[str, Any]]  # DOM 结构分析
    stealth_enabled: Optional[bool]  # 是否启用反爬虫绕过

    # ===== Phase 2: Stealth Configuration =====
    stealth_config: Optional[Dict[str, Any]]  # 隐身配置 (level, settings)
    anti_bot_level: Optional[str]  # 反爬虫等级检测 (none/low/medium/high)

    # ===== Interact 节点（多步交互）=====
    interaction_result: Optional[Dict[str, Any]]  # 交互执行结果
    interaction_detected: Optional[bool]  # 是否检测到需要交互
    final_url_after_interaction: Optional[str]  # 交互后的最终 URL

    # ===== Plan 节点 =====
    generated_code: Optional[str]
    plan_reasoning: Optional[str]

    # ===== Phase 1: Validation Report =====
    validation_report: Optional[Dict[str, Any]]  # 选择器验证报告
    validated_selectors: Optional[List[str]]  # 实际验证通过的选择器
    plan_verification: Optional[Dict[str, Any]]  # 代码计划验证结果
    dry_run_results: Optional[Dict[str, Any]]  # 干运行结果

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

    # ===== Reflexion 反思记忆 =====
    failure_history: Optional[List[Dict[str, Any]]]  # 结构化失败记录
    reflection_memory: Optional[List[str]]           # 反思文本
    successful_patterns: Optional[List[str]]         # 成功模式
    attempt_signatures: Optional[List[str]]          # 代码签名（防重复）

    # ===== Phase 4: Deep Reflection Memory =====
    website_type: Optional[str]  # 网站类型分类 (ecommerce/news/social_media/etc.)
    website_features: Optional[List[str]]  # 网站特征检测
    domain_insights: Optional[Dict[str, Any]]  # 域名级别的洞察
    attempted_strategies: Optional[List[str]]  # 尝试过的策略列表
    partial_success_data: Optional[Dict[str, Any]]  # 部分成功的详细数据

    # ===== Vision Integration =====
    screenshot_data: Optional[bytes]  # 页面截图数据
    visual_analysis: Optional[Dict[str, Any]]  # 视觉分析结果

    # ===== 性能追踪 =====
    performance_data: Optional[Dict[str, Any]]  # 各节点性能数据（耗时、状态等）

    # ===== 控制 =====
    stage: str  # sense/plan/act/verify/reflect/report/done/failed
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
        valid_selectors=None,
        dom_structure=None,
        stealth_enabled=None,

        # Phase 2: Stealth Configuration
        stealth_config=None,
        anti_bot_level=None,

        # Interact
        interaction_result=None,
        interaction_detected=None,
        final_url_after_interaction=None,

        # Plan
        generated_code=None,
        plan_reasoning=None,

        # Phase 1: Validation Report
        validation_report=None,
        validated_selectors=None,
        plan_verification=None,
        dry_run_results=None,

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

        # Reflexion 反思记忆
        failure_history=None,
        reflection_memory=None,
        successful_patterns=None,
        attempt_signatures=None,

        # Phase 4: Deep Reflection Memory
        website_type=None,
        website_features=None,
        domain_insights=None,
        attempted_strategies=None,
        partial_success_data=None,

        # Vision Integration
        screenshot_data=None,
        visual_analysis=None,

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


def should_reflect(state: ReconState) -> str:
    """判断是否需要反思（Reflexion模式）

    基于Reflexion论文的Act-Reflect-Remember循环，
    当数据为空或质量过低时，触发深度反思。

    Returns:
        "reflect" - 数据为空或质量低，需要反思
        "report" - 任务完成或达到最大迭代
    """
    sample_data = state.get("sample_data", [])
    quality = state.get("quality_score", 0)
    max_iter = get_max_sool_iterations()

    # 数据为空，必须反思
    if len(sample_data) == 0:
        # 检查是否达到最大迭代次数
        if state.get("sool_iteration", 0) < max_iter:
            return "reflect"
        return "report"

    # 质量过低，反思
    if quality < 0.3:
        if state.get("sool_iteration", 0) < max_iter:
            return "reflect"
        return "report"

    # 质量合格，生成报告
    return "report"


def should_retry_from_reflection(state: ReconState) -> str:
    """反思后判断是否重试

    Returns:
        "retry" - 需要重新生成代码
        "report" - 放弃重试，生成报告
    """
    max_iter = get_max_sool_iterations()
    current_iter = state.get("sool_iteration", 0)

    if current_iter >= max_iter:
        return "report"

    return "retry"


def should_interact(state: ReconState) -> str:
    """判断是否需要交互

    基于 Sense 阶段的分析，判断页面是否需要多步交互。

    Returns:
        "interact" - 需要交互（如点击搜索按钮）
        "validate" - 不需要交互，直接进入验证阶段
    """
    sense_analysis = state.get("sense_analysis", {})
    detected_features = state.get("detected_features", [])

    # 如果 Sense 分析明确指出需要交互
    if sense_analysis.get("requires_interaction"):
        return "interact"

    # 如果检测到搜索框或提交按钮
    for feature in detected_features:
        if "search" in feature.lower() or "form" in feature.lower():
            return "interact"

    # 检查 interaction_detected 标志
    if state.get("interaction_detected"):
        return "interact"

    # 默认不需要交互，直接进入验证阶段
    return "validate"
