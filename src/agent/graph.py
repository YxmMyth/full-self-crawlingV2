"""
Graph - LangGraph 状态机

定义侦察任务的 LangGraph 状态机。

CodeAct 架构：每个节点让 LLM 生成 Python 代码，然后在沙箱中执行。
"""

from typing import Literal
from langgraph.graph import StateGraph, END, START
import json
import os

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


# ===== 节点实现（CodeAct 模式）=====

async def sense_node(state: ReconState) -> ReconState:
    """
    Sense 节点：生成 DOM 分析代码并执行

    CodeAct 模式：
    1. LLM 生成 DOM 分析代码
    2. 沙箱执行生成的代码
    3. 解析分析结果
    """
    from .prompts import get_sense_dom_analysis_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox

    state["stage"] = "sense"

    try:
        # 获取 HTML（使用 BrowserTool 快速获取）
        from .tools import BrowserTool
        browser = BrowserTool()

        browse_result = await browser.browse(
            state["site_url"],
            wait_for="body",
        )
        html = browse_result.get("html", "")[:10000]  # 前 10k 字符
        await browser.close()

        # LLM 生成 DOM 分析代码
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))
        prompt = get_sense_dom_analysis_prompt(
            url=state["site_url"],
            user_goal=state["user_goal"],
            html=html,
        )

        llm_response = await client.generate_code(prompt)
        analysis_code = extract_python_code(llm_response)

        # 沙箱执行分析代码
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(analysis_code, timeout=60)

        if result["success"] and isinstance(result["output"], dict):
            state["sense_analysis"] = result["output"]
            state["detected_features"] = result["output"].get("recommendations", [])
            state["html_snapshot"] = html[:5000]
        else:
            # 分析失败，使用默认值
            state["sense_analysis"] = {}
            state["detected_features"] = []
            state["html_snapshot"] = html[:5000]
            state["error"] = result.get("error", "Unknown error")

    except Exception as e:
        state["error"] = f"Sense failed: {str(e)}"
        state["sense_analysis"] = {}
        state["detected_features"] = []
        state["html_snapshot"] = ""

    return state


async def plan_node(state: ReconState) -> ReconState:
    """
    Plan 节点：基于 Sense 分析生成爬虫代码

    CodeAct 模式：
    1. 使用 Sense 分析结果构建 prompt
    2. LLM 生成爬虫代码（sync_playwright）
    """
    from .prompts import get_code_generation_prompt, extract_python_code
    from .llm import ZhipuClient

    state["stage"] = "plan"

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 构建 prompt（包含 Sense 分析结果）
        dom_analysis = json.dumps(state.get("sense_analysis", {}), ensure_ascii=False)

        prompt = get_code_generation_prompt(
            url=state["site_url"],
            user_goal=state["user_goal"],
            dom_analysis=dom_analysis,
        )

        llm_response = await client.generate_code(prompt)
        code = extract_python_code(llm_response)

        state["generated_code"] = code
        state["plan_reasoning"] = f"LLM 基于 DOM 分析生成爬虫代码"

    except Exception as e:
        state["error"] = f"Plan failed: {str(e)}"
        state["generated_code"] = ""

    return state


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


async def soal_node(state: ReconState) -> ReconState:
    """
    SOOAL 节点：代码诊断和修复

    CodeAct 模式：
    1. LLM 生成诊断代码
    2. 沙箱执行诊断代码
    3. 基于诊断结果，LLM 生成修复代码
    """
    from .prompts import get_code_diagnose_prompt, get_code_repair_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox

    state["sool_iteration"] = state.get("sool_iteration", 0) + 1

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 获取错误信息
        execution_result = state.get("execution_result", {})
        error = execution_result.get("error") or execution_result.get("stderr", "Unknown error")
        code = state.get("generated_code", "")

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

        state["generated_code"] = repaired_code
        state["last_error"] = f"Code repaired: {diagnosis.get('error_type', 'unknown')}"

    except Exception as e:
        state["last_error"] = f"SOOAL failed: {str(e)}"

    # 记录错误历史
    if state.get("error_history") is None:
        state["error_history"] = []
    state["error_history"].append(state.get("last_error", "unknown"))

    return state


# ===== 沙箱执行器导入 =====

from .sandbox import create_sandbox
