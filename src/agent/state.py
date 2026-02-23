"""
State - LangGraph 鐘舵€佸畾涔?
瀹氫箟渚﹀療浠诲姟鐨勭姸鎬佺粨鏋勶紝鐢ㄤ簬 LangGraph 鐘舵€佹満銆?"""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime
import os


# ============================================================================
# 閰嶇疆鍑芥暟 - 浠庣幆澧冨彉閲忚幏鍙栭槇鍊?# ============================================================================

def get_quality_threshold() -> float:
    """鑾峰彇璐ㄩ噺闃堝€硷紝榛樿 0.6

    鍙互閫氳繃鐜鍙橀噺 QUALITY_THRESHOLD 閰嶇疆銆?    浣庝簬姝ゅ€肩殑璐ㄩ噺鍒嗘暟灏嗚Е鍙戜唬鐮侀噸鏂扮敓鎴愩€?    """
    return float(os.getenv("QUALITY_THRESHOLD", "0.6"))


def get_max_sool_iterations() -> int:
    """鑾峰彇鏈€澶?SOOAL 杩唬娆℃暟锛岄粯璁?6

    鍙互閫氳繃鐜鍙橀噺 MAX_SOOL_ITERATIONS 閰嶇疆銆?    杈惧埌姝ゆ鏁板悗灏嗗仠姝唬鐮佷慨澶嶏紝鐩存帴鐢熸垚鎶ュ憡銆?    """
    return int(os.getenv("MAX_SOOL_ITERATIONS", "3"))


def get_validation_config() -> Dict[str, bool]:
    """鑾峰彇楠岃瘉閰嶇疆閫夐」

    杩斿洖浠庣幆澧冨彉閲忚鍙栫殑楠岃瘉寮€鍏抽厤缃€?    """
    return {
        "validate_images": os.getenv("VALIDATE_IMAGES", "true").lower() == "true",
        "check_image_accessibility": os.getenv("CHECK_IMAGE_ACCESSIBILITY", "false").lower() == "true",
        "check_duplicates": os.getenv("CHECK_DUPLICATES", "true").lower() == "true",
        "validate_urls": os.getenv("VALIDATE_URLS", "true").lower() == "true",
        "validate_dates": os.getenv("VALIDATE_DATES", "true").lower() == "true",
    }


def get_deep_validation_config() -> Dict[str, Any]:
    """
    鑾峰彇娣卞害楠岃瘉閰嶇疆

    杩斿洖浠庣幆澧冨彉閲忚鍙栫殑娣卞害楠岃瘉閰嶇疆銆?    娣卞害楠岃瘉浼氬湪娌欑涓笅杞藉拰楠岃瘉瀹為檯鍐呭锛堝浘鐗囥€丳DF銆佽棰戯級銆?
    Returns:
        閰嶇疆瀛楀吀锛屽寘鍚細
        - enabled: 鏄惁鍚敤娣卞害楠岃瘉
        - max_images: 鏈€澶氶獙璇佺殑鍥剧墖鏁伴噺
        - min_image_resolution: 鏈€灏忓浘鐗囧垎杈ㄧ巼瑕佹眰
        - pdf_validation_enabled: 鏄惁楠岃瘉 PDF
        - clip_relevance_threshold: CLIP 鐩稿叧鎬ч槇鍊?    """
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
    鑾峰彇 Vision API 閰嶇疆

    鏀寔澶氫釜 Vision API 鎻愪緵鍟嗭細
    - openai: OpenAI GPT-4V
    - aliyun: 闃块噷浜戠櫨鐐煎妯℃€佸ぇ妯″瀷
    - tencent: 鑵捐浜戯紙棰勭暀锛?    - none: 绂佺敤

    Returns:
        閰嶇疆瀛楀吀锛屽寘鍚細
        - provider: 鎻愪緵鍟嗗悕绉?        - enabled: 鏄惁鍚敤
        - api_key: API 瀵嗛挜
        - model: 妯″瀷鍚嶇О
    """
    provider = os.getenv("VISION_API_PROVIDER", "none").lower()
    enabled = os.getenv("ENABLE_VISION_API", "false").lower() == "true"

    # 榛樿妯″瀷閰嶇疆
    default_models = {
        "openai": "gpt-4o",
        "aliyun": "qwen3-omni-flash",  # 澶氭ā鎬佽兘鍔涙ā鍨?
        "tencent": "",
    }

    # 榛樿 base_url 閰嶇疆
    default_base_urls = {
        "openai": "",
        "aliyun": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",  # 榛樿鏂板姞鍧?
        "tencent": "",
    }

    # 鑾峰彇 API Key锛堟牴鎹?provider锛?
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
    elif provider == "aliyun":
        api_key = os.getenv("ALIYUN_API_KEY", "")
    elif provider == "tencent":
        api_key = os.getenv("TENCENT_API_KEY", "")
    else:
        api_key = ""
        enabled = False

    # 鑾峰彇 base_url锛堟牴鎹?provider锛?
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
    鑾峰彇闅愯韩閰嶇疆

    Returns:
        閰嶇疆瀛楀吀锛屽寘鍚細
        - auto_detect: 鏄惁鑷姩妫€娴嬪弽鐖櫕绛夌骇
        - default_level: 榛樿闅愯韩绛夌骇
        - levels: 鍚勭瓑绾х殑閰嶇疆
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
    鑾峰彇楠岃瘉缃俊搴﹂槇鍊?
    Returns:
        缃俊搴﹂槇鍊?(榛樿 0.7)
    """
    return float(os.getenv("VERIFICATION_CONFIDENCE_THRESHOLD", "0.7"))


class ReconState(TypedDict):
    """渚﹀療浠诲姟鐘舵€?
    LangGraph 鐘舵€佹満浣跨敤鐨勬牳蹇冩暟鎹粨鏋?    """
    # ===== 杈撳叆 =====
    site_url: str
    user_goal: str
    task_id: str
    created_at: str

    # ===== Sense 鑺傜偣 =====
    site_context: Optional[Dict[str, Any]]
    detected_features: Optional[List[str]]
    html_snapshot: Optional[str]
    sense_analysis: Optional[Dict[str, Any]]  # DOM 鍒嗘瀽缁撴灉
    valid_selectors: Optional[List[str]]  # 楠岃瘉杩囩殑閫夋嫨鍣?
    dom_structure: Optional[Dict[str, Any]]  # DOM 缁撴瀯鍒嗘瀽
    stealth_enabled: Optional[bool]  # 鏄惁鍚敤鍙嶇埇铏粫杩?
    # ===== Phase 2: Stealth Configuration =====
    stealth_config: Optional[Dict[str, Any]]  # 闅愯韩閰嶇疆 (level, settings)
    anti_bot_level: Optional[str]  # 鍙嶇埇铏瓑绾ф娴?(none/low/medium/high)

    # ===== Interact 鑺傜偣锛堝姝ヤ氦浜掞級=====
    interaction_result: Optional[Dict[str, Any]]  # 浜や簰鎵ц缁撴灉
    interaction_detected: Optional[bool]  # 鏄惁妫€娴嬪埌闇€瑕佷氦浜?
    final_url_after_interaction: Optional[str]  # 浜や簰鍚庣殑鏈€缁?URL

    # ===== Plan 鑺傜偣 =====
    generated_code: Optional[str]
    plan_reasoning: Optional[str]

    # ===== Phase 1: Validation Report =====
    validation_report: Optional[Dict[str, Any]]  # 閫夋嫨鍣ㄩ獙璇佹姤鍛?
    validated_selectors: Optional[List[str]]  # 瀹為檯楠岃瘉閫氳繃鐨勯€夋嫨鍣?
    plan_verification: Optional[Dict[str, Any]]  # 浠ｇ爜璁″垝楠岃瘉缁撴灉
    dry_run_results: Optional[Dict[str, Any]]  # 骞茶繍琛岀粨鏋?
    # ===== Act 鑺傜偣 =====
    execution_result: Optional[Dict[str, Any]]
    execution_logs: Optional[List[str]]
    screenshots: Optional[List[str]]

    # ===== Verify 鑺傜偣 =====
    quality_score: Optional[float]
    sample_data: Optional[List[Dict[str, Any]]]
    quality_issues: Optional[List[str]]
    quality_stats: Optional[Dict[str, Any]]  # 璇︾粏鐨勮川閲忕粺璁′俊鎭?
    # ===== Report 鑺傜偣 =====
    final_report: Optional[Dict[str, Any]]
    markdown_report: Optional[str]

    # ===== SOOAL 寰幆 =====
    sool_iteration: int
    last_error: Optional[str]
    error_history: Optional[List[str]]

    # ===== Reflexion 鍙嶆€濊蹇?=====
    failure_history: Optional[List[Dict[str, Any]]]  # 缁撴瀯鍖栧け璐ヨ褰?
    reflection_memory: Optional[List[str]]           # 鍙嶆€濇枃鏈?
    successful_patterns: Optional[List[str]]         # 鎴愬姛妯″紡
    attempt_signatures: Optional[List[str]]          # 浠ｇ爜绛惧悕锛堥槻閲嶅锛?
    # ===== Phase 4: Deep Reflection Memory =====
    website_type: Optional[str]  # 缃戠珯绫诲瀷鍒嗙被 (ecommerce/news/social_media/etc.)
    website_features: Optional[List[str]]  # 缃戠珯鐗瑰緛妫€娴?
    domain_insights: Optional[Dict[str, Any]]  # 鍩熷悕绾у埆鐨勬礊瀵?
    attempted_strategies: Optional[List[str]]  # 灏濊瘯杩囩殑绛栫暐鍒楄〃
    partial_success_data: Optional[Dict[str, Any]]  # 閮ㄥ垎鎴愬姛鐨勮缁嗘暟鎹?
    classification_detail: Optional[Dict[str, Any]]
    navigation_trace: Optional[List[Dict[str, Any]]]

    # ===== Vision Integration =====
    screenshot_data: Optional[bytes]  # 椤甸潰鎴浘鏁版嵁
    visual_analysis: Optional[Dict[str, Any]]  # 瑙嗚鍒嗘瀽缁撴灉

    # ===== 鎬ц兘杩借釜 =====
    performance_data: Optional[Dict[str, Any]]  # 鍚勮妭鐐规€ц兘鏁版嵁锛堣€楁椂銆佺姸鎬佺瓑锛?
    data_success: Optional[bool]
    completion_status: Optional[str]
    failure_reason: Optional[str]

    # ===== 鎺у埗 =====
    stage: str  # sense/plan/act/verify/reflect/report/done/failed
    error: Optional[str]


def create_initial_state(
    site_url: str,
    user_goal: str,
    task_id: Optional[str] = None,
) -> ReconState:
    """Create initial agent state."""
    import uuid

    return ReconState(
        # 杈撳叆
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

        # Reflexion 鍙嶆€濊蹇?
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
        classification_detail=None,
        navigation_trace=[],

        # Vision Integration
        screenshot_data=None,
        visual_analysis=None,
        performance_data={},
        data_success=None,
        completion_status=None,
        failure_reason=None,

        # 鎺у埗
        stage="sense",
        error=None,
    )


# ===== 杈呭姪鍑芥暟 =====

def should_run_sool(state: ReconState) -> str:
    """Determine whether SOOAL repair should run after act."""
    execution_result = state.get("execution_result")
    max_iter = get_max_sool_iterations()
    generated_code = (state.get("generated_code") or "").strip()
    plan_verification = state.get("plan_verification") or {}

    # No execution result or empty code should always retry repair.
    if not execution_result or not generated_code:
        return "soal"

    # Respect verification-before-execution gate.
    if plan_verification and not plan_verification.get("can_proceed", True):
        return "soal"

    if execution_result.get("success"):
        parsed_data = execution_result.get("parsed_data")
        has_data = False

        if isinstance(parsed_data, dict):
            results = parsed_data.get("results")
            has_data = isinstance(results, list) and len(results) > 0
        elif isinstance(parsed_data, list):
            has_data = len(parsed_data) > 0

        # Treat "code ran but yielded no data" as a repair case unless retries exhausted.
        if not has_data and state.get("sool_iteration", 0) < max_iter:
            return "soal"

        return "verify"

    error = execution_result.get("error")
    if error and state.get("sool_iteration", 0) < max_iter:
        return "soal"

    return "verify"


def should_retry(state: ReconState) -> str:
    """Return whether to continue retrying based on quality and retry budget."""
    quality = state.get("quality_score", 0)
    threshold = get_quality_threshold()
    max_iter = get_max_sool_iterations()

    # Quality passes threshold: finish.
    if quality >= threshold:
        return "report"

    # Retry budget exhausted: finish.
    if state.get("sool_iteration", 0) >= max_iter:
        return "report"

    # Otherwise keep retrying.
    return "retry"


def should_reflect(state: ReconState) -> str:
    """Choose reflect vs report based on data presence, quality, and retry budget."""
    sample_data = state.get("sample_data", [])
    quality = state.get("quality_score", 0)
    max_iter = get_max_sool_iterations()

    # Empty data must trigger reflection if retries remain.
    if len(sample_data) == 0:
        # Check retry budget.
        if state.get("sool_iteration", 0) < max_iter:
            return "reflect"
        return "report"

    # Low quality also triggers reflection if retries remain.
    if quality < 0.3:
        if state.get("sool_iteration", 0) < max_iter:
            return "reflect"
        return "report"

    # Good enough quality: finish.
    return "report"


def should_retry_from_reflection(state: ReconState) -> str:
    """After reflection, decide whether to retry or finalize."""
    max_iter = get_max_sool_iterations()
    current_iter = state.get("sool_iteration", 0)

    if current_iter >= max_iter:
        return "report"

    return "retry"


def should_interact(state: ReconState) -> str:
    """Determine whether an interaction/navigation step is needed."""
    sense_analysis = state.get("sense_analysis", {})
    detected_features = state.get("detected_features", []) or []
    user_goal = (state.get("user_goal") or "").lower()
    site_url = (state.get("site_url") or "").lower()

    if sense_analysis.get("requires_interaction"):
        return "interact"

    # If analysis says target data is not on current page, prefer interaction first.
    if sense_analysis.get("target_data_on_page") is False:
        return "interact"

    for feature in detected_features:
        lower = feature.lower()
        if (
            "search" in lower
            or "form" in lower
            or "pagination" in lower
            or "filter" in lower
            or "menu" in lower
            or "category" in lower
        ):
            return "interact"

    if state.get("interaction_detected"):
        return "interact"

    # Landing pages often require one extra step to reach list/detail pages.
    if site_url.endswith("/") and any(
        token in user_goal
        for token in ["列表", "list", "jobs", "职位", "产品", "商品", "论文", "公告", "chart", "图表", "news", "文章"]
    ):
        return "interact"

    return "validate"


def should_proceed_after_plan_verification(state: ReconState) -> str:
    """Route from verify_plan to act/soal/report based on gate and retry budget."""
    generated_code = (state.get("generated_code") or "").strip()
    verification = state.get("plan_verification") or {}
    max_iter = get_max_sool_iterations()
    current_iter = state.get("sool_iteration", 0)

    if not generated_code:
        if current_iter >= max_iter:
            return "report"
        return "soal"

    if not verification:
        if current_iter >= max_iter:
            return "report"
        return "soal"

    if verification.get("can_proceed", False):
        return "act"

    if current_iter >= max_iter:
        return "report"

    return "soal"


def compute_data_success(state: ReconState) -> bool:
    """Determine if extracted data is usable for downstream consumers."""
    sample_data = state.get("sample_data") or []
    quality_score = state.get("quality_score") or 0.0
    threshold = get_quality_threshold()

    if not isinstance(sample_data, list) or len(sample_data) == 0:
        return False

    return quality_score >= threshold

