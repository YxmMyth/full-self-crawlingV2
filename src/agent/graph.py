"""
Graph - LangGraph 状态机

定义侦察任务的 LangGraph 状态机。

CodeAct 架构：每个节点让 LLM 生成 Python 代码，然后在沙箱中执行。

2026 架构改进：
- Phase 1: Verification-Before-Execution (validate_node, verify_plan_node)
- Phase 2: Stealth-First Default (anti-bot detection in sense_node)
- 短期优化: 增强的Prompt、选择器库
- Agent Skills: 可复用的技能模块
- 增量生成: 只修复错误部分
- Vision集成: 视觉模型辅助页面理解
"""

from typing import Literal
from langgraph.graph import StateGraph, END, START
import json
import os

from .state import ReconState, create_initial_state, should_run_sool, should_retry, should_reflect, should_retry_from_reflection, should_interact, get_stealth_config, get_verification_confidence_threshold
from .performance import track_performance

# Phase 1: Import validation and verification nodes
from .validate_node import validate_node, should_skip_verification
from .verify_plan_node import verify_plan_node, should_skip_plan_verification

# Phase 2: Import stealth configuration
from .stealth_config import detect_anti_bot_level, get_stealth_template

# Short-term optimizations: Import enhanced prompts and selector library
from .prompt_enhancer import (
    get_enhanced_code_generation_prompt,
    get_error_diagnosis_prompt,
    get_reflection_enhancement_prompt,
)
from .selector_library import suggest_selectors, get_website_specific_selectors

# Agent Skills: Import skill manager
from .skills import SkillManager

# Incremental generation: Import incremental generator
from .incremental_generator import IncrementalCodeGenerator

# Vision integration
from .vision_integration import VisionIntegration, analyze_page_with_vision


def create_recon_graph() -> StateGraph:
    """创建侦察任务状态机

    Reflexion 增强版：引入反思节点，从失败中学习

    2026 架构改进：
    - Phase 1: 添加 validate_node 和 verify_plan_node
    - 新流程: START → sense → validate → plan → verify_plan → act → verify → ...

    Returns:
        StateGraph: 编译好的状态机
    """
    graph = StateGraph(ReconState)

    # 添加节点
    graph.add_node("sense", sense_node)
    graph.add_node("interact", interact_node)  # 新增：交互节点
    graph.add_node("validate", validate_node)  # Phase 1: 选择器验证节点
    graph.add_node("plan", plan_node)
    graph.add_node("verify_plan", verify_plan_node)  # Phase 1: 代码计划验证节点
    graph.add_node("act", act_node)
    graph.add_node("verify", verify_node)
    graph.add_node("reflect", reflect_node)  # 新增：反思节点
    graph.add_node("report", report_node)
    graph.add_node("soal", soal_node)

    # 添加边：START → sense（入口点）
    graph.add_edge(START, "sense")

    # 条件边：sense → interact 或 sense → validate
    # 使用 should_interact 判断是否需要交互
    graph.add_conditional_edges(
        "sense",
        should_interact,
        {
            "interact": "interact",
            "validate": "validate"  # Phase 1: 走验证节点
        }
    )

    # 添加边（正常流程）
    graph.add_edge("interact", "validate")  # 交互后也需要验证

    # Phase 1: validate → plan (验证后进入计划阶段)
    graph.add_edge("validate", "plan")

    # Phase 1: plan → verify_plan (计划后进行代码验证)
    graph.add_edge("plan", "verify_plan")

    # Phase 1: verify_plan → act (验证后执行)
    graph.add_edge("verify_plan", "act")

    # 条件边：act → verify 或 act → soal
    graph.add_conditional_edges(
        "act",
        should_run_sool,
        {
            "soal": "soal",
            "verify": "verify"
        }
    )

    # 条件边：verify → reflect 或 verify → report
    # 使用 should_reflect 判断是否需要反思（数据为空或质量低）
    graph.add_conditional_edges(
        "verify",
        should_reflect,
        {
            "reflect": "reflect",
            "report": "report"
        }
    )

    # 反思后判断是重试还是报告
    graph.add_conditional_edges(
        "reflect",
        should_retry_from_reflection,
        {
            "retry": "plan",  # 重试时回到 plan 节点
            "report": "report"
        }
    )

    # SOOAL 循环
    graph.add_edge("soal", "verify_plan")  # Phase 1: SOOAL 后重新验证代码

    # 结束
    graph.add_edge("report", END)

    return graph.compile()


# ===== 节点实现（CodeAct 模式）=====

@track_performance("sense")
async def sense_node(state: ReconState) -> ReconState:
    """
    Sense 节点：生成 DOM 分析代码并执行

    增强版：添加选择器验证能力

    Phase 2 增强：添加反爬虫等级检测

    Vision API 集成：使用视觉模型辅助页面理解

    CodeAct 模式：
    1. LLM 生成 DOM 分析代码
    2. 沙箱执行生成的代码
    3. 解析分析结果
    4. 验证选择器有效性
    5. 检测反爬虫等级
    6. Vision API 视觉分析（可选）
    """
    from .prompts import get_enhanced_sense_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox
    from .state import get_vision_api_config

    state["stage"] = "sense"

    try:
        # 获取 HTML（使用 BrowserTool 快速获取）
        from .tools import BrowserTool, SelectorValidator

        browser = BrowserTool()

        # ========== Vision API: 捕获截图 ==========
        vision_config = get_vision_api_config()
        screenshot_enabled = vision_config.get("enabled", False)

        browse_result = await browser.browse(
            state["site_url"],
            wait_for="body",
            screenshot=screenshot_enabled,  # 根据 Vision 配置决定是否截图
        )
        html = browse_result.get("html", "")

        # 保存截图数据
        if screenshot_enabled and browse_result.get("screenshot"):
            state["screenshot_data"] = browse_result.get("screenshot")

        await browser.close()

        # ========== Phase 2: 反爬虫等级检测 ==========
        # 自动检测反爬虫等级
        stealth_config = get_stealth_config()
        anti_bot_level = "none"  # 默认

        if stealth_config.get("auto_detect", True):
            # 从 HTML 和 features 检测反爬虫等级
            features = browse_result.get("features", [])
            anti_bot_level = detect_anti_bot_level(html)

            # 如果 features 中包含 anti-bot 标记，升级等级
            if any("anti-bot" in f.lower() for f in features):
                level_ranks = {"none": 0, "low": 1, "medium": 2, "high": 3}
                current_rank = level_ranks.get(anti_bot_level, 0)
                anti_bot_level = [k for k, v in level_ranks.items() if v > current_rank][0] if current_rank < 3 else "high"

        state["anti_bot_level"] = anti_bot_level
        state["stealth_config"] = {
            "level": anti_bot_level,
            "auto_detected": True,
        }

        # LLM 生成 DOM 分析代码（使用增强版 prompt）
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 智能提取 HTML：确保包含主要内容
        # 对于大型 HTML，尝试找到主要内容区域
        html_for_analysis = html
        if len(html) > 50000:
            # HTML 很大，尝试智能提取
            # 策略：取前 20K + 中间 50K + 后 20K
            html_for_analysis = html[:20000] + html[len(html)//2:len(html)//2+50000] + html[-20000:]
        elif len(html) > 15000:
            # 中等大小，取更多内容
            html_for_analysis = html[:50000] + html[-10000:]
        else:
            # 小型 HTML，全部使用
            html_for_analysis = html

        prompt = get_enhanced_sense_prompt(
            url=state["site_url"],
            user_goal=state["user_goal"],
            html=html_for_analysis,
            user_goal_requires_interaction=False,  # 将在分析后判断
        )

        llm_response = await client.generate_code(prompt)
        analysis_code = extract_python_code(llm_response)

        # 沙箱执行分析代码
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(analysis_code, timeout=60)

        if result["success"] and isinstance(result["output"], dict):
            output = result["output"]
            state["sense_analysis"] = output
            state["detected_features"] = output.get("recommendations", [])
            state["html_snapshot"] = html[:5000]

            # ========== 新增：选择器验证 ==========
            # 如果分析结果包含 valid_selectors，直接使用
            # 否则，手动验证选择器
            if output.get("valid_selectors"):
                state["valid_selectors"] = output.get("valid_selectors", [])
            elif output.get("selector_test_results"):
                # 从测试结果中提取有效的选择器
                valid = [
                    r["selector"] for r in output["selector_test_results"]
                    if r.get("valid", False)
                ]
                state["valid_selectors"] = valid
            else:
                # 使用 SelectorValidator 手动验证
                validator = SelectorValidator(html)
                suggested = validator.suggest_selectors(state["user_goal"])
                test_results = validator.test_selectors(suggested[:5])
                valid = [r["selector"] for r in test_results if r["valid"]]
                state["valid_selectors"] = valid

            # 分析 DOM 结构
            validator = SelectorValidator(html)
            state["dom_structure"] = validator.analyze_dom_structure()

            # 检测是否需要交互
            state["interaction_detected"] = output.get("requires_interaction", False)

            # 检测是否需要启用反爬虫绕过
            features = browse_result.get("features", [])
            state["stealth_enabled"] = any(
                "anti-bot" in f.lower() or "cloudflare" in f.lower()
                for f in features
            )

        else:
            # 分析失败，使用默认值
            state["sense_analysis"] = {}
            state["detected_features"] = []
            state["html_snapshot"] = html[:5000]
            state["valid_selectors"] = []
            state["dom_structure"] = {}
            state["error"] = result.get("error", "Unknown error")

        # ========== Vision API: 视觉分析 ==========
        if screenshot_enabled and state.get("screenshot_data"):
            try:
                vision_integration = VisionIntegration(
                    api_key=vision_config.get("api_key"),
                    provider=vision_config.get("provider", "openai")
                )

                visual_result = await vision_integration.analyze_screenshot(
                    screenshot_data=state["screenshot_data"],
                    user_goal=state["user_goal"],
                    url=state["site_url"],
                )

                # 保存视觉分析结果
                state["visual_analysis"] = {
                    "page_type": visual_result.page_type,
                    "layout_description": visual_result.layout_description,
                    "key_elements": visual_result.key_elements,
                    "suggested_selectors": visual_result.suggested_selectors,
                    "confidence": visual_result.confidence,
                }

                # 合并视觉建议的选择器到 valid_selectors
                if visual_result.suggested_selectors:
                    current_selectors = set(state.get("valid_selectors", []))
                    current_selectors.update(visual_result.suggested_selectors)
                    state["valid_selectors"] = list(current_selectors)

            except Exception as vision_error:
                # Vision API 失败不影响主流程
                state["visual_analysis"] = {
                    "error": f"Vision API failed: {str(vision_error)}",
                    "page_type": "unknown",
                    "confidence": 0.0,
                }

    except Exception as e:
        state["error"] = f"Sense failed: {str(e)}"
        state["sense_analysis"] = {}
        state["detected_features"] = []
        state["html_snapshot"] = ""
        state["valid_selectors"] = []
        state["dom_structure"] = {}

    return state


@track_performance("interact")
async def interact_node(state: ReconState) -> ReconState:
    """
    Interact 节点：处理多步交互

    用于处理需要交互的场景：
    1. 点击搜索按钮
    2. 填写表单
    3. 滚动加载
    4. 等待动态内容

    CodeAct 模式：
    1. LLM 生成交互代码
    2. 沙箱执行交互代码
    3. 返回交互后的 URL
    """
    from .prompts import get_interact_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox

    state["stage"] = "interact"

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 构建交互 prompt
        dom_analysis = json.dumps(state.get("sense_analysis", {}), ensure_ascii=False)
        detected_features = state.get("detected_features", [])

        prompt = get_interact_prompt(
            url=state["site_url"],
            user_goal=state["user_goal"],
            dom_analysis=dom_analysis,
            detected_features=detected_features,
        )

        llm_response = await client.generate_code(prompt)
        interact_code = extract_python_code(llm_response)

        # 沙箱执行交互代码
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(interact_code, timeout=120)

        if result["success"] and isinstance(result["output"], dict):
            output = result["output"]
            state["interaction_result"] = output
            state["final_url_after_interaction"] = output.get("final_url", state["site_url"])
            state["interaction_detected"] = False  # 已完成交互

            # 如果 URL 变化了，更新站点 URL 用于后续爬取
            if output.get("final_url") and output["final_url"] != state["site_url"]:
                state["site_url"] = output["final_url"]
        else:
            # 交互失败，继续使用原 URL
            state["interaction_result"] = {"error": result.get("error", "Unknown error")}
            state["final_url_after_interaction"] = state["site_url"]

    except Exception as e:
        state["error"] = f"Interact failed: {str(e)}"
        state["interaction_result"] = {"error": str(e)}
        state["final_url_after_interaction"] = state["site_url"]

    return state


@track_performance("plan")
async def plan_node(state: ReconState) -> ReconState:
    """
    Plan 节点：基于 Sense 分析 + 历史反思生成爬虫代码

    Reflexion 增强版：
    1. 使用 Sense 分析结果构建 prompt
    2. 传入失败历史和反思记忆
    3. LLM 生成爬虫代码（sync_playwright）

    Phase 2 增强：根据反爬虫等级自动使用隐身配置
    短期优化：使用增强的Prompt和选择器库
    """
    from .prompts import extract_python_code
    from .llm import ZhipuClient
    from .memory import generate_code_signature

    state["stage"] = "plan"

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 构建 prompt（包含 Sense 分析结果）
        dom_analysis = json.dumps(state.get("sense_analysis", {}), ensure_ascii=False)

        # 获取历史反思和失败记录
        failure_history = state.get("failure_history", [])[-3:]  # 最近3次
        reflection_memory = state.get("reflection_memory", [])[-3:]
        successful_patterns = state.get("successful_patterns", [])
        iteration = state.get("sool_iteration", 0)

        # 获取网站类型和反爬虫等级
        website_type = state.get("website_type", "unknown")
        anti_bot_level = state.get("anti_bot_level", "none")
        stealth_enabled = state.get("stealth_enabled", False)

        # 获取验证过的选择器（从validate_node）
        validated_selectors = state.get("validated_selectors", [])

        # ========== 短期优化：使用增强的Prompt ==========
        # 使用增强的代码生成Prompt，整合选择器库和失败历史
        prompt = get_enhanced_code_generation_prompt(
            url=state["site_url"],
            user_goal=state["user_goal"],
            dom_analysis=dom_analysis,
            website_type=website_type,
            stealth_level=anti_bot_level if anti_bot_level != "none" else "medium",
            failure_history=failure_history,
            reflection_memory=reflection_memory,
            validated_selectors=validated_selectors,
        )

        llm_response = await client.generate_code(prompt)
        code = extract_python_code(llm_response)

        # 记录代码签名（防重复）
        code_signature = generate_code_signature(code)
        if state.get("attempt_signatures") is None:
            state["attempt_signatures"] = []
        state["attempt_signatures"].append(code_signature)

        # 生成推理说明
        parts = []
        if validated_selectors:
            parts.append(f"使用{len(validated_selectors)}个已验证选择器")
        if anti_bot_level != "none":
            parts.append(f"应用隐身配置({anti_bot_level})")
        if failure_history:
            parts.append(f"基于{len(failure_history)}次失败历史")
        if website_type != "unknown":
            parts.append(f"针对{website_type}网站优化")

        reasoning = f"{' + '.join(parts) if parts else 'LLM代码生成'}"

        state["generated_code"] = code
        state["plan_reasoning"] = reasoning

    except Exception as e:
        state["error"] = f"Plan failed: {str(e)}"
        state["generated_code"] = ""

    return state


@track_performance("act")
async def act_node(state: ReconState) -> ReconState:
    """
    Act 节点：沙箱执行爬虫代码

    CodeAct 模式：
    1. 使用 Docker/Local 沙箱执行代码
    2. 解析执行结果（JSON）
    """
    from .sandbox import create_sandbox

    state["stage"] = "act"

    # 创建沙箱（开发阶段用 Simple，生产用 Docker）
    use_docker = os.getenv("USE_DOCKER", "false").lower() == "true"
    executor = create_sandbox(use_docker=use_docker)

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


@track_performance("verify")
async def verify_node(state: ReconState) -> ReconState:
    """
    Verify 节点：评估数据质量

    CodeAct 模式：
    1. LLM 生成质量评估代码（增强版：图片、格式、内容验证）
    2. 沙箱执行评估代码
    3. 解析质量分数和详细统计
    4. 改进的降级策略：不只检查数量，实际检查数据内容
    5. 新增：深度验证（可选，检查图片/PDF/视频实际内容）
    """
    from .prompts import (
        get_enhanced_quality_evaluation_prompt,
        get_deep_validation_prompt,
        extract_python_code,
        extract_validation_rules,
    )
    from .llm import ZhipuClient
    from .sandbox import create_sandbox
    from .state import get_deep_validation_config

    state["stage"] = "verify"

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        sample_data = state.get("sample_data", [])
        sample_data_json = json.dumps(sample_data[:20], ensure_ascii=False)

        # 获取验证规则（从 user_goal 中提取）
        validation_rules = extract_validation_rules(state.get("user_goal", ""))

        # 基础验证
        prompt = get_enhanced_quality_evaluation_prompt(
            user_goal=state["user_goal"],
            extracted_data=sample_data_json,
            validation_rules=validation_rules,
        )

        llm_response = await client.generate_code(prompt)
        eval_code = extract_python_code(llm_response)

        # 沙箱执行评估代码
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(eval_code, timeout=30)

        if result["success"] and isinstance(result["output"], dict):
            output = result["output"]
            state["quality_score"] = output.get("overall_score", 0.5)
            state["quality_issues"] = output.get("issues", [])
            # 新增：存储详细的验证统计
            state["quality_stats"] = {
                "image_stats": output.get("image_stats", {}),
                "format_stats": output.get("format_stats", {}),
                "content_stats": output.get("content_stats", {}),
                "scores": {
                    "relevance": output.get("relevance", 0),
                    "completeness": output.get("completeness", 0),
                    "accuracy": output.get("accuracy", 0),
                    "content_quality": output.get("content_quality", 0),
                },
            }
        else:
            # ✅ 改进的降级策略：实际检查数据内容
            state["quality_score"] = fallback_quality_check(sample_data)
            state["quality_issues"] = ["LLM 评估失败，使用基础验证"]
            state["quality_stats"] = {"fallback": True}

        # ========== 新增：深度验证（可选） ==========
        deep_validation_config = get_deep_validation_config()
        if deep_validation_config["enabled"]:
            deep_result = await run_deep_validation(
                sample_data=sample_data[:deep_validation_config["max_images"]],
                user_goal=state["user_goal"],
                validation_rules=validation_rules,
                sandbox=sandbox,
                client=client,
            )

            # 合并深度验证结果到 quality_stats
            if state.get("quality_stats") is None:
                state["quality_stats"] = {}
            state["quality_stats"]["deep_validation"] = deep_result

            # 根据深度验证结果调整质量分数
            critical_issues = deep_result.get("critical_issues", 0)
            if critical_issues > 0:
                # 每个严重问题扣 10%
                penalty = min(0.5, critical_issues * 0.1)
                state["quality_score"] = max(0, state["quality_score"] * (1 - penalty))
                state["quality_issues"] = state.get("quality_issues", [])
                state["quality_issues"].append(f"深度验证发现 {critical_issues} 个严重问题")

    except Exception as e:
        state["quality_score"] = fallback_quality_check(state.get("sample_data", []))
        state["quality_issues"] = [f"评估异常: {str(e)}"]
        state["quality_stats"] = {"fallback": True, "error": str(e)}

    return state


async def run_deep_validation(
    sample_data: list,
    user_goal: str,
    validation_rules: dict,
    sandbox,
    client,
) -> dict:
    """
    运行深度验证

    检测数据中是否包含图片/PDF/视频，并进行深度验证。

    Args:
        sample_data: 采样数据
        user_goal: 用户需求
        validation_rules: 验证规则
        sandbox: 沙箱实例
        client: LLM 客户端

    Returns:
        深度验证结果
    """
    from .prompts import get_deep_validation_prompt, extract_python_code

    result = {
        "enabled_types": [],
        "results": {},
        "critical_issues": 0,
    }

    # 检测数据类型
    has_images = False
    has_pdfs = False
    has_videos = False

    for item in sample_data:
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if not isinstance(value, str):
                continue
            if 'image' in key.lower() or 'img' in key.lower():
                has_images = True
            elif 'pdf' in key.lower():
                has_pdfs = True
            elif 'video' in key.lower() or 'movie' in key.lower():
                has_videos = True

    # 图片深度验证
    if has_images and validation_rules.get("validate_images"):
        try:
            result["enabled_types"].append("image")

            prompt = get_deep_validation_prompt(
                data_type="image",
                sample_items=sample_data,
                user_goal=user_goal,
                validation_rules=validation_rules,
            )

            llm_response = await client.generate_code(prompt)
            eval_code = extract_python_code(llm_response)

            # 沙箱执行（需要 PIL）
            deep_result = await sandbox.run_python_code(eval_code, timeout=60)

            if deep_result["success"]:
                result["results"]["images"] = deep_result["output"]

                # 统计严重问题
                output = deep_result.get("output", {})
                if isinstance(output, dict):
                    images = output.get("images", [])
                    # 统计无效图片数量
                    invalid_count = sum(1 for img in images if isinstance(img, dict) and not img.get("valid", True))
                    result["critical_issues"] += invalid_count
            else:
                result["results"]["images"] = {"error": deep_result.get("error", "Unknown error")}

        except Exception as e:
            result["results"]["images"] = {"error": str(e)}

    # PDF 深度验证
    if has_pdfs:
        try:
            result["enabled_types"].append("pdf")

            prompt = get_deep_validation_prompt(
                data_type="pdf",
                sample_items=sample_data,
                user_goal=user_goal,
                validation_rules=validation_rules,
            )

            llm_response = await client.generate_code(prompt)
            eval_code = extract_python_code(llm_response)

            deep_result = await sandbox.run_python_code(eval_code, timeout=60)

            if deep_result["success"]:
                result["results"]["pdfs"] = deep_result["output"]

                # 统计严重问题
                output = deep_result.get("output", {})
                if isinstance(output, dict):
                    pdfs = output.get("pdfs", [])
                    invalid_count = sum(1 for pdf in pdfs if isinstance(pdf, dict) and not pdf.get("valid", True))
                    result["critical_issues"] += invalid_count
            else:
                result["results"]["pdfs"] = {"error": deep_result.get("error", "Unknown error")}

        except Exception as e:
            result["results"]["pdfs"] = {"error": str(e)}

    # 视频验证
    if has_videos:
        try:
            result["enabled_types"].append("video")

            prompt = get_deep_validation_prompt(
                data_type="video",
                sample_items=sample_data,
                user_goal=user_goal,
                validation_rules=validation_rules,
            )

            llm_response = await client.generate_code(prompt)
            eval_code = extract_python_code(llm_response)

            deep_result = await sandbox.run_python_code(eval_code, timeout=30)

            if deep_result["success"]:
                result["results"]["videos"] = deep_result["output"]
            else:
                result["results"]["videos"] = {"error": deep_result.get("error", "Unknown error")}

        except Exception as e:
            result["results"]["videos"] = {"error": str(e)}

    return result


def fallback_quality_check(sample_data: list) -> float:
    """
    改进的降级质量检查

    不再只计算数量，而是实际检查数据内容。

    检查项目：
    1. 空记录检测：记录是否为空或所有值都为空
    2. 关键字段检测：title/name/url/link 是否为空
    3. 无意义内容检测：N/A, null, 待补充等

    Args:
        sample_data: 采样数据列表

    Returns:
        质量分数 (0.0 - 1.0)
    """
    if not sample_data:
        return 0.0

    total = len(sample_data)
    issues = 0
    null_values = ["n/a", "null", "none", "待补充", "暂无", "tbd", "-", "—", "undefined"]

    for item in sample_data:
        if not isinstance(item, dict):
            issues += 1
            continue

        # 检查是否有值
        if not item or all(v is None or v == "" for v in item.values()):
            issues += 1
            continue

        # 检查关键字段
        for key in ["title", "name", "url", "link", "href"]:
            if key in item:
                val = str(item.get(key, "")).strip()
                if not val:
                    issues += 1
                elif val.lower() in null_values:
                    issues += 1

    # 质量 = (有效记录数) / 总数
    valid_ratio = (total - min(issues, total)) / total
    return round(valid_ratio, 2)


@track_performance("report")
async def report_node(state: ReconState) -> ReconState:
    """
    Report 节点：生成侦察报告

    CodeAct 模式：
    1. 使用 LLM 生成 Markdown 报告
    """
    from .prompts import get_report_generation_prompt
    from .llm import ZhipuClient

    state["stage"] = "report"

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        site_info = json.dumps(state.get("site_context", {}), ensure_ascii=False)
        sample_data = json.dumps(state.get("sample_data", [])[:5], ensure_ascii=False)

        markdown = await client.generate_code(
            get_report_generation_prompt(
                site_url=state["site_url"],
                user_goal=state["user_goal"],
                site_info=site_info,
                sample_data=sample_data,
                sool_iteration=state.get("sool_iteration", 0),
                quality_score=state.get("quality_score", 0),
                sample_count=len(state.get("sample_data", [])),
            )
        )

        state["markdown_report"] = markdown

    except Exception as e:
        # 降级：生成简单报告
        markdown = f"""# 网站数据侦察报告

## 站点信息
- URL: {state['site_url']}
- 用户需求: {state['user_goal']}

## 侦察总结
- SOOAL 迭代: {state.get('sool_iteration', 0)}
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


@track_performance("soal")
async def soal_node(state: ReconState) -> ReconState:
    """
    SOOAL 节点：代码诊断和修复

    Phase 5 增强：支持增量代码生成，只修复错误部分

    CodeAct 模式：
    1. LLM 生成诊断代码
    2. 沙箱执行诊断代码
    3. 基于诊断结果，LLM 生成修复代码（支持增量修复）
    """
    from .prompts import get_code_diagnose_prompt, get_code_repair_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox
    # Phase 5: Import incremental generator
    from .incremental_generator import IncrementalCodeGenerator

    state["sool_iteration"] = state.get("sool_iteration", 0) + 1

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 获取错误信息
        execution_result = state.get("execution_result", {})
        error = execution_result.get("error") or execution_result.get("stderr", "Unknown error")
        code = state.get("generated_code", "")

        # ========== Phase 5: 增量代码生成 ==========
        # 暂时禁用增量修复，使用全量重写（更稳定）
        incremental_generator = IncrementalCodeGenerator()

        # 判断是否应该使用增量修复
        # use_incremental = incremental_generator.should_use_incremental_fix(state)
        use_incremental = False  # 强制使用全量重写

        if use_incremental:
            # 使用增量修复：只修复错误部分
            error_analysis = incremental_generator.analyze_error(code, execution_result)

            # 生成针对性的修复Prompt
            fix_prompt = incremental_generator.generate_targeted_prompt(
                code=code,
                error_analysis=error_analysis,
                validated_selectors=state.get("validated_selectors"),
            )

            llm_response = await client.generate_code(fix_prompt)
            repaired_code = extract_python_code(llm_response)

            # 如果增量修复失败，回退到全量修复
            if not repaired_code or len(repaired_code) < 100:
                # 回退到全量修复
                use_incremental = False

        if not use_incremental:
            # 原有的全量修复流程
            # 生成诊断代码
            diagnose_prompt = get_code_diagnose_prompt(
                error=error,
                code=code[:3000],  # 限制代码大小
            )

            llm_response = await client.generate_code(diagnose_prompt)
            diagnose_code = extract_python_code(llm_response)

            # 沙箱执行诊断代码
            sandbox = create_sandbox(use_docker=False)
            diagnosis_result = await sandbox.run_python_code(diagnose_code, timeout=30)

            if diagnosis_result["success"] and isinstance(diagnosis_result["output"], dict):
                diagnosis = diagnosis_result["output"]
            else:
                diagnosis = {
                    "error_type": "unknown",
                    "root_cause": error[:200],
                    "fix_suggestion": "检查代码语法和 API 使用",
                }

            # 生成修复代码
            repair_prompt = get_code_repair_prompt(
                diagnosis=json.dumps(diagnosis, ensure_ascii=False),
                code=code[:5000],
            )

            llm_response = await client.generate_code(repair_prompt)
            repaired_code = extract_python_code(llm_response)

        # 记录修复方式
        fix_method = "incremental" if use_incremental else "full_regeneration"
        state["last_error"] = f"Code repaired ({fix_method}): {error[:50]}"

        state["generated_code"] = repaired_code

    except Exception as e:
        state["last_error"] = f"SOOAL failed: {str(e)}"

    # 记录错误历史
    if state.get("error_history") is None:
        state["error_history"] = []
    state["error_history"].append(state.get("last_error", "unknown"))

    return state


@track_performance("reflect")
async def reflect_node(state: ReconState) -> ReconState:
    """
    Reflect 节点：深度分析失败原因（Reflexion 模式）

    Phase 4 增强：Deep Reflection Memory
    - 网站类型分类
    - 域名洞察存储
    - 尝试策略记录
    - 部分成功数据分析

    基于 Reflexion 论文 (arXiv:2303.11366) 的 Act-Reflect-Remember 循环：
    1. 分析执行结果和数据
    2. 生成结构化的失败分析
    3. 存储反思到 deep reflection memory 中供下次使用
    """
    from .prompts import get_reflection_prompt, get_deep_reflection_prompt
    from .llm import ZhipuClient
    from .memory import parse_reflection, FailureMemory
    # Phase 4: Import deep reflection memory and site classifier
    from .reflection_memory import DeepReflectionMemory, analyze_partial_success
    from .site_classifier import SiteClassifier, get_website_features

    state["stage"] = "reflect"

    # 增加 SOOAL 迭代计数
    state["sool_iteration"] = state.get("sool_iteration", 0) + 1

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 收集上下文
        execution_result = state.get("execution_result", {})
        sample_data = state.get("sample_data", [])
        generated_code = state.get("generated_code", "")
        previous_reflections = state.get("reflection_memory", [])[-3:]  # 最近3次反思

        # ========== Phase 4: 网站分类和特征提取 ==========
        url = state["site_url"]
        html = state.get("html_snapshot", "")

        # 分类网站类型
        classification = SiteClassifier.classify(url, html)
        website_type = classification["type"]
        state["website_type"] = website_type

        # 提取网站特征
        website_features = get_website_features(url, html)
        state["website_features"] = website_features

        # 获取域名洞察
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        state["domain_insights"] = {
            "domain": domain,
            "website_type": website_type,
            "features": website_features,
        }

        # 获取反爬虫等级
        anti_bot_level = state.get("anti_bot_level", "none")

        # ========== Phase 4: 分析部分成功数据 ==========
        partial_success = analyze_partial_success(execution_result, sample_data)
        state["partial_success_data"] = partial_success

        # 确定尝试过的策略
        attempted_strategies = []
        if state.get("stealth_enabled"):
            attempted_strategies.append(f"stealth_browser_{anti_bot_level}")
        if state.get("validated_selectors"):
            attempted_strategies.append("validated_selectors")
        if "page.wait_for_timeout" in generated_code:
            attempted_strategies.append("human_delays")
        if "playwright-stealth" in generated_code or "add_init_script" in generated_code:
            attempted_strategies.append("anti_detection_script")

        state["attempted_strategies"] = attempted_strategies

        # 使用深度反思 prompt（Phase 4）
        reflection_prompt = get_deep_reflection_prompt(
            url=url,
            user_goal=state["user_goal"],
            execution_result=execution_result,
            sample_data=sample_data,
            generated_code=generated_code[:2000],
            previous_reflections=previous_reflections,
            website_type=website_type,
            anti_bot_level=anti_bot_level,
            website_features=website_features,
            partial_success=partial_success,
        )

        llm_response = await client.generate_code(reflection_prompt)

        # 解析反思结果
        reflection = parse_reflection(llm_response)

        # 存储反思文本
        if state.get("reflection_memory") is None:
            state["reflection_memory"] = []
        state["reflection_memory"].append(reflection["text"])

        # 存储结构化失败记录
        if state.get("failure_history") is None:
            state["failure_history"] = []

        failure_record = {
            "iteration": state.get("sool_iteration", 0),
            "failure_type": reflection["failure_type"],
            "root_cause": reflection["root_cause"],
            "suggested_fix": reflection["suggested_fix"],
            "avoid_repeat": reflection["avoid_repeat"],
            "data_count": len(sample_data),
            # Phase 4: 新增字段
            "website_type": website_type,
            "anti_bot_level": anti_bot_level,
            "attempted_strategies": attempted_strategies,
            "partial_success": partial_success,
        }
        state["failure_history"].append(failure_record)

        # ========== Phase 4: 存储到深度反思记忆 ==========
        deep_memory = DeepReflectionMemory()
        deep_memory.add_reflection(
            url=url,
            website_type=website_type,
            anti_bot_level=anti_bot_level,
            failure_type=reflection["failure_type"],
            root_cause=reflection["root_cause"],
            suggested_fix=reflection["suggested_fix"],
            attempted_strategies=attempted_strategies,
            partial_success_data=partial_success,
            execution_result=execution_result,
        )

        state["last_error"] = f"Reflection: {reflection['failure_type']} - {reflection['suggested_fix'][:100]}"

    except Exception as e:
        # 降级：简单反思
        error_msg = str(e)
        if state.get("reflection_memory") is None:
            state["reflection_memory"] = []

        simple_reflection = f"执行失败: {error_msg}，数据量: {len(state.get('sample_data', []))}"
        state["reflection_memory"].append(simple_reflection)
        state["last_error"] = f"Reflection failed: {error_msg}"

        # 同时记录到 failure_history
        if state.get("failure_history") is None:
            state["failure_history"] = []
        state["failure_history"].append({
            "iteration": state.get("sool_iteration", 0),
            "failure_type": "unknown",
            "root_cause": error_msg[:200],
            "suggested_fix": "检查错误信息",
            "data_count": len(state.get("sample_data", [])),
        })

    return state


# ===== 沙箱执行器导入 =====

from .sandbox import create_sandbox
