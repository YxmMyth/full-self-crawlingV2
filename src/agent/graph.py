"""
Graph - LangGraph 鐘舵€佹満

瀹氫箟渚﹀療浠诲姟鐨?LangGraph 鐘舵€佹満銆?
CodeAct 鏋舵瀯锛氭瘡涓妭鐐硅 LLM 鐢熸垚 Python 浠ｇ爜锛岀劧鍚庡湪娌欑涓墽琛屻€?
2026 鏋舵瀯鏀硅繘锛?- Phase 1: Verification-Before-Execution (validate_node, verify_plan_node)
- Phase 2: Stealth-First Default (anti-bot detection in sense_node)
- 鐭湡浼樺寲: 澧炲己鐨凱rompt銆侀€夋嫨鍣ㄥ簱
- Agent Skills: 鍙鐢ㄧ殑鎶€鑳芥ā鍧?- 澧為噺鐢熸垚: 鍙慨澶嶉敊璇儴鍒?- Vision闆嗘垚: 瑙嗚妯″瀷杈呭姪椤甸潰鐞嗚В
"""

from typing import Literal
from langgraph.graph import StateGraph, END, START
import json
import os

from .state import (
    ReconState,
    create_initial_state,
    should_run_sool,
    should_retry,
    should_reflect,
    should_retry_from_reflection,
    should_interact,
    should_proceed_after_plan_verification,
    compute_data_success,
    get_stealth_config,
    get_verification_confidence_threshold,
)
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
    """鍒涘缓渚﹀療浠诲姟鐘舵€佹満

    Reflexion 澧炲己鐗堬細寮曞叆鍙嶆€濊妭鐐癸紝浠庡け璐ヤ腑瀛︿範

    2026 鏋舵瀯鏀硅繘锛?    - Phase 1: 娣诲姞 validate_node 鍜?verify_plan_node
    - 鏂版祦绋? START 鈫?sense 鈫?validate 鈫?plan 鈫?verify_plan 鈫?act 鈫?verify 鈫?...

    Returns:
        StateGraph: 缂栬瘧濂界殑鐘舵€佹満
    """
    graph = StateGraph(ReconState)

    # 娣诲姞鑺傜偣
    graph.add_node("sense", sense_node)
    graph.add_node("interact", interact_node)  # 鏂板锛氫氦浜掕妭鐐?
    graph.add_node("validate", validate_node)  # Phase 1: 閫夋嫨鍣ㄩ獙璇佽妭鐐?
    graph.add_node("plan", plan_node)
    graph.add_node("verify_plan", verify_plan_node)  # Phase 1: 浠ｇ爜璁″垝楠岃瘉鑺傜偣
    graph.add_node("act", act_node)
    graph.add_node("verify", verify_node)
    graph.add_node("reflect", reflect_node)  # 鏂板锛氬弽鎬濊妭鐐?
    graph.add_node("report", report_node)
    graph.add_node("soal", soal_node)

    # 娣诲姞杈癸細START 鈫?sense锛堝叆鍙ｇ偣锛?
    graph.add_edge(START, "sense")

    # 鏉′欢杈癸細sense 鈫?interact 鎴?sense 鈫?validate
    # 浣跨敤 should_interact 鍒ゆ柇鏄惁闇€瑕佷氦浜?
    graph.add_conditional_edges(
        "sense",
        should_interact,
        {
            "interact": "interact",
            "validate": "validate",  # Phase 1: 璧伴獙璇佽妭鐐?
        }
    )

    # 娣诲姞杈癸紙姝ｅ父娴佺▼锛?
    graph.add_edge("interact", "validate")  # 浜や簰鍚庝篃闇€瑕侀獙璇?
    # Phase 1: validate 鈫?plan (楠岃瘉鍚庤繘鍏ヨ鍒掗樁娈?
    graph.add_edge("validate", "plan")

    # Phase 1: plan 鈫?verify_plan (璁″垝鍚庤繘琛屼唬鐮侀獙璇?
    graph.add_edge("plan", "verify_plan")

    # Phase 1: verify_plan 鈫?act (楠岃瘉鍚庢墽琛?
    graph.add_conditional_edges(
        "verify_plan",
        should_proceed_after_plan_verification,
        {
            "act": "act",
            "soal": "soal",
            "report": "report",
        }
    )

    # 鏉′欢杈癸細act 鈫?verify 鎴?act 鈫?soal
    graph.add_conditional_edges(
        "act",
        should_run_sool,
        {
            "soal": "soal",
            "verify": "verify"
        }
    )

    # 鏉′欢杈癸細verify 鈫?reflect 鎴?verify 鈫?report
    # 浣跨敤 should_reflect 鍒ゆ柇鏄惁闇€瑕佸弽鎬濓紙鏁版嵁涓虹┖鎴栬川閲忎綆锛?
    graph.add_conditional_edges(
        "verify",
        should_reflect,
        {
            "reflect": "reflect",
            "report": "report"
        }
    )

    # 鍙嶆€濆悗鍒ゆ柇鏄噸璇曡繕鏄姤鍛?
    graph.add_conditional_edges(
        "reflect",
        should_retry_from_reflection,
        {
            "retry": "plan",  # 閲嶈瘯鏃跺洖鍒?plan 鑺傜偣
            "report": "report"
        }
    )

    # SOOAL 寰幆
    graph.add_edge("soal", "verify_plan")  # Phase 1: SOOAL 鍚庨噸鏂伴獙璇佷唬鐮?
    # 缁撴潫
    graph.add_edge("report", END)

    return graph.compile()


# ===== 鑺傜偣瀹炵幇锛圕odeAct 妯″紡锛?====

@track_performance("sense")
async def sense_node(state: ReconState) -> ReconState:
    """
    Sense 鑺傜偣锛氱敓鎴?DOM 鍒嗘瀽浠ｇ爜骞舵墽琛?
    澧炲己鐗堬細娣诲姞閫夋嫨鍣ㄩ獙璇佽兘鍔?
    Phase 2 澧炲己锛氭坊鍔犲弽鐖櫕绛夌骇妫€娴?
    Vision API 闆嗘垚锛氫娇鐢ㄨ瑙夋ā鍨嬭緟鍔╅〉闈㈢悊瑙?
    CodeAct 妯″紡锛?    1. LLM 鐢熸垚 DOM 鍒嗘瀽浠ｇ爜
    2. 娌欑鎵ц鐢熸垚鐨勪唬鐮?    3. 瑙ｆ瀽鍒嗘瀽缁撴灉
    4. 楠岃瘉閫夋嫨鍣ㄦ湁鏁堟€?    5. 妫€娴嬪弽鐖櫕绛夌骇
    6. Vision API 瑙嗚鍒嗘瀽锛堝彲閫夛級
    """
    from .prompts import get_enhanced_sense_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox
    from .state import get_vision_api_config

    state["stage"] = "sense"

    try:
        # 鑾峰彇 HTML锛堜娇鐢?BrowserTool 蹇€熻幏鍙栵級
        from urllib.parse import urlparse
        from .tools import BrowserTool, SelectorValidator
        from .site_classifier import SiteClassifier, get_website_features

        browser = BrowserTool()

        # ========== Vision API: 鎹曡幏鎴浘 ==========
        vision_config = get_vision_api_config()
        screenshot_enabled = vision_config.get("enabled", False)

        browse_result = await browser.browse(
            state["site_url"],
            wait_for="body",
            screenshot=screenshot_enabled,  # 鏍规嵁 Vision 閰嶇疆鍐冲畾鏄惁鎴浘
        )
        html = browse_result.get("html", "")

        # 淇濆瓨鎴浘鏁版嵁
        if screenshot_enabled and browse_result.get("screenshot"):
            state["screenshot_data"] = browse_result.get("screenshot")

        await browser.close()

        # ========== Phase 2: 鍙嶇埇铏瓑绾ф娴?==========
        # 鑷姩妫€娴嬪弽鐖櫕绛夌骇
        stealth_config = get_stealth_config()
        anti_bot_level = "none"  # 榛樿

        if stealth_config.get("auto_detect", True):
            # 浠?HTML 鍜?features 妫€娴嬪弽鐖櫕绛夌骇
            features = browse_result.get("features", [])
            anti_bot_level = detect_anti_bot_level(html)

            # 濡傛灉 features 涓寘鍚?anti-bot 鏍囪锛屽崌绾х瓑绾?
            if any("anti-bot" in f.lower() for f in features):
                level_ranks = {"none": 0, "low": 1, "medium": 2, "high": 3}
                current_rank = level_ranks.get(anti_bot_level, 0)
                anti_bot_level = [k for k, v in level_ranks.items() if v > current_rank][0] if current_rank < 3 else "high"

        # ========== 淇: 宸茬煡楂樺弽鐖櫕鍩熷悕纭紪鐮?==========
        # 瀵逛簬宸茬煡鐨勯珮鍙嶇埇铏煙鍚嶏紝寮哄埗璁剧疆涓?high
        known_high_domains = ["amazon.com", "amazon.co", "amazon.cn", "zillow.com", "indeed.com", "linkedin.com"]
        site_url_lower = state["site_url"].lower()
        if any(domain in site_url_lower for domain in known_high_domains):
            anti_bot_level = "high"

        state["anti_bot_level"] = anti_bot_level
        state["stealth_config"] = {
            "level": anti_bot_level,
            "auto_detected": True,
        }

        # LLM 鐢熸垚 DOM 鍒嗘瀽浠ｇ爜锛堜娇鐢ㄥ寮虹増 prompt锛?
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 鏅鸿兘鎻愬彇 HTML锛氱‘淇濆寘鍚富瑕佸唴瀹?
        # 瀵逛簬澶у瀷 HTML锛屽皾璇曟壘鍒颁富瑕佸唴瀹瑰尯鍩?
        html_for_analysis = html
        if len(html) > 50000:
            # HTML 寰堝ぇ锛屽皾璇曟櫤鑳芥彁鍙?
            # 绛栫暐锛氬彇鍓?20K + 涓棿 50K + 鍚?20K
            html_for_analysis = html[:20000] + html[len(html)//2:len(html)//2+50000] + html[-20000:]
        elif len(html) > 15000:
            # 涓瓑澶у皬锛屽彇鏇村鍐呭
            html_for_analysis = html[:50000] + html[-10000:]
        else:
            # 灏忓瀷 HTML锛屽叏閮ㄤ娇鐢?
            html_for_analysis = html

        prompt = get_enhanced_sense_prompt(
            url=state["site_url"],
            user_goal=state["user_goal"],
            html=html_for_analysis,
            user_goal_requires_interaction=False,  # 灏嗗湪鍒嗘瀽鍚庡垽鏂?
        )

        llm_response = await client.generate_code(prompt)
        analysis_code = extract_python_code(llm_response)

        # 娌欑鎵ц鍒嗘瀽浠ｇ爜
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(analysis_code, timeout=60)

        if result.get("success", False) and isinstance(result.get("output"), dict):
            output = result["output"]
            state["sense_analysis"] = output
            state["html_snapshot"] = html[:5000]

            # Merge feature sources for interaction and strategy selection.
            recommendation_features = output.get("recommendations", [])
            browser_features = browse_result.get("features", [])
            extracted_features = get_website_features(state["site_url"], state["html_snapshot"])
            merged_features = []
            for feature in recommendation_features + browser_features + extracted_features:
                if feature and feature not in merged_features:
                    merged_features.append(feature)
            state["detected_features"] = merged_features

            # Classify early so plan can consume website_type directly.
            classification = SiteClassifier.classify(state["site_url"], state["html_snapshot"])
            classification_conf = classification.get("confidence", 0.0)
            website_type = classification.get("type", "unknown")
            if classification_conf < 0.5:
                website_type = "unknown"

            state["classification_detail"] = classification
            state["website_type"] = website_type
            state["website_features"] = extracted_features
            state["domain_insights"] = {
                "domain": urlparse(state["site_url"]).netloc,
                "website_type": website_type,
                "features": extracted_features,
                "confidence": classification_conf,
                "method": classification.get("method", "unknown"),
            }
            if state.get("navigation_trace") is None:
                state["navigation_trace"] = []
            if not state.get("navigation_trace"):
                state["navigation_trace"] = [{
                    "step": "sense",
                    "from_url": state["site_url"],
                    "to_url": state["site_url"],
                    "reason": "initial_url",
                }]

            # ========== 鏂板锛氶€夋嫨鍣ㄩ獙璇?==========
            # 濡傛灉鍒嗘瀽缁撴灉鍖呭惈 valid_selectors锛岀洿鎺ヤ娇鐢?
            # 鍚﹀垯锛屾墜鍔ㄩ獙璇侀€夋嫨鍣?
            if output.get("valid_selectors"):
                state["valid_selectors"] = output.get("valid_selectors", [])
            elif output.get("selector_test_results"):
                # 浠庢祴璇曠粨鏋滀腑鎻愬彇鏈夋晥鐨勯€夋嫨鍣?
                valid = [
                    r["selector"] for r in output["selector_test_results"]
                    if r.get("valid", False)
                ]
                state["valid_selectors"] = valid
            else:
                # 浣跨敤 SelectorValidator 鎵嬪姩楠岃瘉
                validator = SelectorValidator(html)
                suggested = validator.suggest_selectors(state["user_goal"])
                test_results = validator.test_selectors(suggested[:5])
                valid = [r["selector"] for r in test_results if r["valid"]]
                state["valid_selectors"] = valid

            # 鍒嗘瀽 DOM 缁撴瀯
            validator = SelectorValidator(html)
            state["dom_structure"] = validator.analyze_dom_structure()

            # 妫€娴嬫槸鍚﹂渶瑕佷氦浜?
            state["interaction_detected"] = output.get("requires_interaction", False)

            # 妫€娴嬫槸鍚﹂渶瑕佸惎鐢ㄥ弽鐖櫕缁曡繃
            features = browse_result.get("features", [])
            state["stealth_enabled"] = any(
                "anti-bot" in f.lower() or "cloudflare" in f.lower()
                for f in features
            )

        else:
            # 鍒嗘瀽澶辫触锛屼娇鐢ㄩ粯璁ゅ€?
            state["sense_analysis"] = {}
            state["detected_features"] = []
            state["html_snapshot"] = html[:5000]
            state["valid_selectors"] = []
            state["dom_structure"] = {}
            state["error"] = result.get("error", "Unknown error")
            state["classification_detail"] = {"type": "unknown", "confidence": 0.0, "method": "sense_failed"}
            state["website_type"] = "unknown"
            state["website_features"] = []
            state["domain_insights"] = {}

        # ========== Vision API: 瑙嗚鍒嗘瀽 ==========
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

                # 淇濆瓨瑙嗚鍒嗘瀽缁撴灉
                state["visual_analysis"] = {
                    "page_type": visual_result.page_type,
                    "layout_description": visual_result.layout_description,
                    "key_elements": visual_result.key_elements,
                    "suggested_selectors": visual_result.suggested_selectors,
                    "confidence": visual_result.confidence,
                }

                # 鍚堝苟瑙嗚寤鸿鐨勯€夋嫨鍣ㄥ埌 valid_selectors
                if visual_result.suggested_selectors:
                    current_selectors = set(state.get("valid_selectors", []))
                    current_selectors.update(visual_result.suggested_selectors)
                    state["valid_selectors"] = list(current_selectors)

            except Exception as vision_error:
                # Vision API 澶辫触涓嶅奖鍝嶄富娴佺▼
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
        state["classification_detail"] = {"type": "unknown", "confidence": 0.0, "method": "sense_exception"}
        state["website_type"] = "unknown"
        state["website_features"] = []
        state["domain_insights"] = {}
        if state.get("navigation_trace") is None:
            state["navigation_trace"] = []

    return state


@track_performance("interact")
async def interact_node(state: ReconState) -> ReconState:
    """
    Interact 鑺傜偣锛氬鐞嗗姝ヤ氦浜?
    鐢ㄤ簬澶勭悊闇€瑕佷氦浜掔殑鍦烘櫙锛?    1. 鐐瑰嚮鎼滅储鎸夐挳
    2. 濉啓琛ㄥ崟
    3. 婊氬姩鍔犺浇
    4. 绛夊緟鍔ㄦ€佸唴瀹?
    CodeAct 妯″紡锛?    1. LLM 鐢熸垚浜や簰浠ｇ爜
    2. 娌欑鎵ц浜や簰浠ｇ爜
    3. 杩斿洖浜や簰鍚庣殑 URL
    """
    from .prompts import get_interact_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox

    state["stage"] = "interact"

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 鏋勫缓浜や簰 prompt
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

        # 娌欑鎵ц浜や簰浠ｇ爜
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(interact_code, timeout=120)

        if result.get("success", False) and isinstance(result.get("output"), dict):
            output = result["output"]
            state["interaction_result"] = output
            from_url = state["site_url"]
            final_url = output.get("final_url", state["site_url"])
            state["final_url_after_interaction"] = final_url
            state["interaction_detected"] = False  # 宸插畬鎴愪氦浜?
            # 濡傛灉 URL 鍙樺寲浜嗭紝鏇存柊绔欑偣 URL 鐢ㄤ簬鍚庣画鐖彇
            if state.get("navigation_trace") is None:
                state["navigation_trace"] = []
            state["navigation_trace"].append({
                "step": "interact",
                "from_url": from_url,
                "to_url": final_url,
                "reason": output.get("reason", "llm_interaction"),
            })

            if final_url and final_url != state["site_url"]:
                state["site_url"] = final_url
        else:
            # 浜や簰澶辫触锛岀户缁娇鐢ㄥ師 URL
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
    Plan 鑺傜偣锛氬熀浜?Sense 鍒嗘瀽 + 鍘嗗彶鍙嶆€濈敓鎴愮埇铏唬鐮?
    Reflexion 澧炲己鐗堬細
    1. 浣跨敤 Sense 鍒嗘瀽缁撴灉鏋勫缓 prompt
    2. 浼犲叆澶辫触鍘嗗彶鍜屽弽鎬濊蹇?    3. LLM 鐢熸垚鐖櫕浠ｇ爜锛坰ync_playwright锛?
    Phase 2 澧炲己锛氭牴鎹弽鐖櫕绛夌骇鑷姩浣跨敤闅愯韩閰嶇疆
    鐭湡浼樺寲锛氫娇鐢ㄥ寮虹殑Prompt鍜岄€夋嫨鍣ㄥ簱
    """
    from .prompts import extract_python_code
    from .llm import ZhipuClient
    from .memory import generate_code_signature

    state["stage"] = "plan"

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 鏋勫缓 prompt锛堝寘鍚?Sense 鍒嗘瀽缁撴灉锛?
        dom_analysis = json.dumps(state.get("sense_analysis", {}), ensure_ascii=False)
        target_url = state.get("final_url_after_interaction") or state["site_url"]

        # ========== 淇: 瀹夊叏鑾峰彇鍘嗗彶鍙嶆€濆拰澶辫触璁板綍 ==========
        # 纭繚 state 涓彲鑳藉瓨鍦ㄧ殑 None 鍊艰杞崲涓虹┖鍒楄〃
        failure_history_raw = state.get("failure_history") or []
        reflection_memory_raw = state.get("reflection_memory") or []
        failure_history = failure_history_raw[-3:] if failure_history_raw else []
        reflection_memory = reflection_memory_raw[-3:] if reflection_memory_raw else []
        successful_patterns = state.get("successful_patterns", [])
        iteration = state.get("sool_iteration", 0)

        # 鑾峰彇缃戠珯绫诲瀷鍜屽弽鐖櫕绛夌骇
        website_type = state.get("website_type", "unknown")
        classification_detail = state.get("classification_detail") or {}
        if classification_detail.get("confidence", 0.0) < 0.5:
            website_type = "unknown"
        anti_bot_level = state.get("anti_bot_level", "none")
        stealth_enabled = state.get("stealth_enabled", False)

        # Pull selectors validated earlier in the pipeline.
        validated_selectors = state.get("validated_selectors", [])

        # ========== 淇: 鍚敤閫夋嫨鍣ㄥ簱闆嗘垚 ==========
        # 鑾峰彇缃戠珯鐗瑰畾閫夋嫨鍣ㄥ苟娣诲姞鍒?validated_selectors
        from .selector_library import get_website_specific_selectors

        domain_selectors = get_website_specific_selectors(target_url)
        if domain_selectors:
            # 灏嗙壒瀹氶€夋嫨鍣ㄦ坊鍔犲埌 validated_selectors
            if not validated_selectors:
                validated_selectors = []
            validated_selectors.extend(domain_selectors.values())

            # 鍘婚噸
            validated_selectors = list(set(validated_selectors))
            state["validated_selectors"] = validated_selectors

        # ========== 鐭湡浼樺寲锛氫娇鐢ㄥ寮虹殑Prompt ==========
        # Build an enhanced code-generation prompt.
        prompt = get_enhanced_code_generation_prompt(
            url=target_url,
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

        if not code or not code.strip():
            state["generated_code"] = ""
            state["error"] = "Plan failed: empty code block"
            state["failure_reason"] = "PLAN_PROMPT_ERROR"
            return state

        # Track code signatures to avoid repeated attempts.
        code_signature = generate_code_signature(code)
        if state.get("attempt_signatures") is None:
            state["attempt_signatures"] = []
        state["attempt_signatures"].append(code_signature)

        # 鐢熸垚鎺ㄧ悊璇存槑
        parts = []
        if validated_selectors:
            parts.append(f"using {len(validated_selectors)} validated selectors")
        if anti_bot_level != "none":
            parts.append(f"stealth level={anti_bot_level}")
        if failure_history:
            parts.append(f"based on {len(failure_history)} prior failures")
        if website_type != "unknown":
            parts.append(f"site-specific optimization for {website_type}")

        reasoning = f"{' + '.join(parts) if parts else 'llm code generation'}"

        state["generated_code"] = code
        state["plan_reasoning"] = reasoning

    except Exception as e:
        state["error"] = f"Plan failed: {str(e)}"
        state["generated_code"] = ""
        state["failure_reason"] = "PLAN_PROMPT_ERROR"

    return state


@track_performance("act")
async def act_node(state: ReconState) -> ReconState:
    """
    Act 鑺傜偣锛氭矙绠辨墽琛岀埇铏唬鐮?
    CodeAct 妯″紡锛?    1. 浣跨敤 Docker/Local 娌欑鎵ц浠ｇ爜
    2. 瑙ｆ瀽鎵ц缁撴灉锛圝SON锛?    """
    from .sandbox import create_sandbox

    state["stage"] = "act"
    generated_code = (state.get("generated_code") or "").strip()
    plan_verification = state.get("plan_verification") or {}

    if not generated_code:
        state["execution_result"] = {
            "success": False,
            "error": "Empty generated code blocked before execution",
            "stderr": "EMPTY_CODE_BLOCKED",
            "parsed_data": None,
        }
        state["execution_logs"] = ["EMPTY_CODE_BLOCKED"]
        state["sample_data"] = []
        state["failure_reason"] = "EMPTY_CODE_BLOCKED"
        return state

    if plan_verification and not plan_verification.get("can_proceed", True):
        state["execution_result"] = {
            "success": False,
            "error": "Plan verification blocked execution",
            "stderr": "PLAN_VERIFY_BLOCKED",
            "parsed_data": None,
        }
        state["execution_logs"] = ["PLAN_VERIFY_BLOCKED"]
        state["sample_data"] = []
        state["failure_reason"] = "PLAN_VERIFY_BLOCKED"
        return state

    # 鍒涘缓娌欑锛堝紑鍙戦樁娈电敤 Simple锛岀敓浜х敤 Docker锛?
    use_docker = os.getenv("USE_DOCKER", "false").lower() == "true"
    executor = create_sandbox(use_docker=use_docker)

    result = await executor.execute(
        code=generated_code,
        timeout=300,
    )

    state["execution_result"] = result
    state["execution_logs"] = [result.get("stderr", ""), result.get("stdout", "")]
    state["sool_iteration"] = state.get("sool_iteration", 0)

    # 鎻愬彇 sample_data 渚?verify 鑺傜偣浣跨敤
    if result.get("parsed_data"):
        if isinstance(result["parsed_data"], dict) and "results" in result["parsed_data"]:
            state["sample_data"] = result["parsed_data"]["results"]
        elif isinstance(result["parsed_data"], list):
            state["sample_data"] = result["parsed_data"]
        else:
            state["sample_data"] = []
    else:
        state["sample_data"] = []
        if result.get("success"):
            state["failure_reason"] = state.get("failure_reason") or "NO_DATA_EXTRACTED"

    return state


@track_performance("verify")
async def verify_node(state: ReconState) -> ReconState:
    """
    Verify 鑺傜偣锛氳瘎浼版暟鎹川閲?
    CodeAct 妯″紡锛?    1. LLM 鐢熸垚璐ㄩ噺璇勪及浠ｇ爜锛堝寮虹増锛氬浘鐗囥€佹牸寮忋€佸唴瀹归獙璇侊級
    2. 娌欑鎵ц璇勪及浠ｇ爜
    3. 瑙ｆ瀽璐ㄩ噺鍒嗘暟鍜岃缁嗙粺璁?    4. 鏀硅繘鐨勯檷绾х瓥鐣ワ細涓嶅彧妫€鏌ユ暟閲忥紝瀹為檯妫€鏌ユ暟鎹唴瀹?    5. 鏂板锛氭繁搴﹂獙璇侊紙鍙€夛紝妫€鏌ュ浘鐗?PDF/瑙嗛瀹為檯鍐呭锛?    """
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

        # 鑾峰彇楠岃瘉瑙勫垯锛堜粠 user_goal 涓彁鍙栵級
        validation_rules = extract_validation_rules(state.get("user_goal", ""))

        # 鍩虹楠岃瘉
        prompt = get_enhanced_quality_evaluation_prompt(
            user_goal=state["user_goal"],
            extracted_data=sample_data_json,
            validation_rules=validation_rules,
        )

        llm_response = await client.generate_code(prompt)
        eval_code = extract_python_code(llm_response)

        # 娌欑鎵ц璇勪及浠ｇ爜
        sandbox = create_sandbox(use_docker=False)
        result = await sandbox.run_python_code(eval_code, timeout=30)

        if result.get("success", False) and isinstance(result.get("output"), dict):
            output = result["output"]
            state["quality_score"] = output.get("overall_score", 0.5)
            state["quality_issues"] = output.get("issues", [])
            # 鏂板锛氬瓨鍌ㄨ缁嗙殑楠岃瘉缁熻
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
            # 鉁?鏀硅繘鐨勯檷绾х瓥鐣ワ細瀹為檯妫€鏌ユ暟鎹唴瀹?
            state["quality_score"] = fallback_quality_check(sample_data)
            state["quality_issues"] = ["LLM 璇勪及澶辫触锛屼娇鐢ㄥ熀纭€楠岃瘉"]
            state["quality_stats"] = {"fallback": True}

        # ========== 鏂板锛氭繁搴﹂獙璇侊紙鍙€夛級 ==========
        deep_validation_config = get_deep_validation_config()
        if deep_validation_config["enabled"]:
            deep_result = await run_deep_validation(
                sample_data=sample_data[:deep_validation_config["max_images"]],
                user_goal=state["user_goal"],
                validation_rules=validation_rules,
                sandbox=sandbox,
                client=client,
            )

            # 鍚堝苟娣卞害楠岃瘉缁撴灉鍒?quality_stats
            if state.get("quality_stats") is None:
                state["quality_stats"] = {}
            state["quality_stats"]["deep_validation"] = deep_result

            # 鏍规嵁娣卞害楠岃瘉缁撴灉璋冩暣璐ㄩ噺鍒嗘暟
            critical_issues = deep_result.get("critical_issues", 0)
            if critical_issues > 0:
                # 姣忎釜涓ラ噸闂鎵?10%
                penalty = min(0.5, critical_issues * 0.1)
                state["quality_score"] = max(0, state["quality_score"] * (1 - penalty))
                state["quality_issues"] = state.get("quality_issues", [])
                state["quality_issues"].append(
                    f"deep validation found {critical_issues} critical issues"
                )

    except Exception as e:
        state["quality_score"] = fallback_quality_check(state.get("sample_data", []))
        state["quality_issues"] = [f"璇勪及寮傚父: {str(e)}"]
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
    杩愯娣卞害楠岃瘉

    妫€娴嬫暟鎹腑鏄惁鍖呭惈鍥剧墖/PDF/瑙嗛锛屽苟杩涜娣卞害楠岃瘉銆?
    Args:
        sample_data: 閲囨牱鏁版嵁
        user_goal: 鐢ㄦ埛闇€姹?        validation_rules: 楠岃瘉瑙勫垯
        sandbox: 娌欑瀹炰緥
        client: LLM 瀹㈡埛绔?
    Returns:
        娣卞害楠岃瘉缁撴灉
    """
    from .prompts import get_deep_validation_prompt, extract_python_code

    result = {
        "enabled_types": [],
        "results": {},
        "critical_issues": 0,
    }

    # 妫€娴嬫暟鎹被鍨?
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

    # 鍥剧墖娣卞害楠岃瘉
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

            # 娌欑鎵ц锛堥渶瑕?PIL锛?
            deep_result = await sandbox.run_python_code(eval_code, timeout=60)

            if deep_result.get("success", False):
                result["results"]["images"] = deep_result.get("output")

                # 缁熻涓ラ噸闂
                output = deep_result.get("output", {})
                if isinstance(output, dict):
                    images = output.get("images", [])
                    # 缁熻鏃犳晥鍥剧墖鏁伴噺
                    invalid_count = sum(1 for img in images if isinstance(img, dict) and not img.get("valid", True))
                    result["critical_issues"] += invalid_count
            else:
                result["results"]["images"] = {"error": deep_result.get("error", "Unknown error")}

        except Exception as e:
            result["results"]["images"] = {"error": str(e)}

    # PDF 娣卞害楠岃瘉
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

            if deep_result.get("success", False):
                result["results"]["pdfs"] = deep_result.get("output")

                # 缁熻涓ラ噸闂
                output = deep_result.get("output", {})
                if isinstance(output, dict):
                    pdfs = output.get("pdfs", [])
                    invalid_count = sum(1 for pdf in pdfs if isinstance(pdf, dict) and not pdf.get("valid", True))
                    result["critical_issues"] += invalid_count
            else:
                result["results"]["pdfs"] = {"error": deep_result.get("error", "Unknown error")}

        except Exception as e:
            result["results"]["pdfs"] = {"error": str(e)}

    # 瑙嗛楠岃瘉
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

            if deep_result.get("success", False):
                result["results"]["videos"] = deep_result.get("output")
            else:
                result["results"]["videos"] = {"error": deep_result.get("error", "Unknown error")}

        except Exception as e:
            result["results"]["videos"] = {"error": str(e)}

    return result


def fallback_quality_check(sample_data: list) -> float:
    """
    鏀硅繘鐨勯檷绾ц川閲忔鏌?
    涓嶅啀鍙绠楁暟閲忥紝鑰屾槸瀹為檯妫€鏌ユ暟鎹唴瀹广€?
    妫€鏌ラ」鐩細
    1. 绌鸿褰曟娴嬶細璁板綍鏄惁涓虹┖鎴栨墍鏈夊€奸兘涓虹┖
    2. 鍏抽敭瀛楁妫€娴嬶細title/name/url/link 鏄惁涓虹┖
    3. 鏃犳剰涔夊唴瀹规娴嬶細N/A, null, 寰呰ˉ鍏呯瓑

    Args:
        sample_data: 閲囨牱鏁版嵁鍒楄〃

    Returns:
        璐ㄩ噺鍒嗘暟 (0.0 - 1.0)
    """
    if not sample_data:
        return 0.0

    total = len(sample_data)
    issues = 0
    null_values = ["n/a", "null", "none", "todo", "pending", "tbd", "-", "undefined"]

    for item in sample_data:
        if not isinstance(item, dict):
            issues += 1
            continue

        # 妫€鏌ユ槸鍚︽湁鍊?
        if not item or all(v is None or v == "" for v in item.values()):
            issues += 1
            continue

        # 妫€鏌ュ叧閿瓧娈?
        for key in ["title", "name", "url", "link", "href"]:
            if key in item:
                val = str(item.get(key, "")).strip()
                if not val:
                    issues += 1
                elif val.lower() in null_values:
                    issues += 1

    # 璐ㄩ噺 = (鏈夋晥璁板綍鏁? / 鎬绘暟
    valid_ratio = (total - min(issues, total)) / total
    return round(valid_ratio, 2)


@track_performance("report")
async def report_node(state: ReconState) -> ReconState:
    """
    Report 鑺傜偣锛氱敓鎴愪睛瀵熸姤鍛?
    CodeAct 妯″紡锛?    1. 浣跨敤 LLM 鐢熸垚 Markdown 鎶ュ憡
    """
    from .prompts import get_report_generation_prompt
    from .llm import ZhipuClient

    state["stage"] = "report"
    sample_items = state.get("sample_data") or []
    site_context = state.get("site_context") or {}

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        site_info = json.dumps(site_context, ensure_ascii=False)
        sample_data = json.dumps(sample_items[:5], ensure_ascii=False)

        markdown = await client.generate_code(
            get_report_generation_prompt(
                site_url=state["site_url"],
                user_goal=state["user_goal"],
                site_info=site_info,
                sample_data=sample_data,
                sool_iteration=state.get("sool_iteration", 0),
                quality_score=state.get("quality_score", 0),
                sample_count=len(sample_items),
            )
        )

        state["markdown_report"] = markdown

    except Exception as e:
        # 闄嶇骇锛氱敓鎴愮畝鍗曟姤鍛?
        markdown = f"""# 缃戠珯鏁版嵁渚﹀療鎶ュ憡

## 绔欑偣淇℃伅
- URL: {state['site_url']}
- 鐢ㄦ埛闇€姹? {state['user_goal']}

## 渚﹀療鎬荤粨
- SOOAL 杩唬: {state.get('sool_iteration', 0)}
- 璐ㄩ噺鍒嗘暟: {state.get('quality_score', 0)}
- 鏍锋湰鏁伴噺: {len(sample_items)}
"""
        state["markdown_report"] = markdown

    sample_count = len(sample_items)
    data_success = compute_data_success(state)
    state["data_success"] = data_success
    state["completion_status"] = "done"

    if not data_success and not state.get("failure_reason"):
        if sample_count == 0:
            state["failure_reason"] = "NO_DATA_EXTRACTED"
        else:
            state["failure_reason"] = "LOW_QUALITY"

    state["final_report"] = {
        "site_url": state["site_url"],
        "user_goal": state["user_goal"],
        "quality_score": state.get("quality_score", 0),
        "sample_data": sample_items,
        "sample_count": sample_count,
        "data_success": data_success,
        "completion_status": state.get("completion_status"),
        "failure_reason": state.get("failure_reason"),
        "generated_code": state.get("generated_code", ""),
        "website_type": state.get("website_type", "unknown"),
        "classification_detail": state.get("classification_detail", {}),
        "navigation_trace": state.get("navigation_trace", []),
    }
    state["stage"] = "done"

    return state


@track_performance("soal")
async def soal_node(state: ReconState) -> ReconState:
    """
    SOOAL 鑺傜偣锛氫唬鐮佽瘖鏂拰淇

    Phase 5 澧炲己锛氭敮鎸佸閲忎唬鐮佺敓鎴愶紝鍙慨澶嶉敊璇儴鍒?
    CodeAct 妯″紡锛?    1. LLM 鐢熸垚璇婃柇浠ｇ爜
    2. 娌欑鎵ц璇婃柇浠ｇ爜
    3. 鍩轰簬璇婃柇缁撴灉锛孡LM 鐢熸垚淇浠ｇ爜锛堟敮鎸佸閲忎慨澶嶏級
    """
    from .prompts import get_code_diagnose_prompt, get_code_repair_prompt, extract_python_code
    from .llm import ZhipuClient
    from .sandbox import create_sandbox
    # Phase 5: Import incremental generator
    from .incremental_generator import IncrementalCodeGenerator

    state["sool_iteration"] = state.get("sool_iteration", 0) + 1

    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 鑾峰彇閿欒淇℃伅
        execution_result = state.get("execution_result") or {}
        error = execution_result.get("error") or execution_result.get("stderr", "Unknown error")
        code = state.get("generated_code", "")

        # ========== Phase 5: 澧為噺浠ｇ爜鐢熸垚 ==========
        # 鏆傛椂绂佺敤澧為噺淇锛屼娇鐢ㄥ叏閲忛噸鍐欙紙鏇寸ǔ瀹氾級
        incremental_generator = IncrementalCodeGenerator()

        # 鍒ゆ柇鏄惁搴旇浣跨敤澧為噺淇
        # use_incremental = incremental_generator.should_use_incremental_fix(state)
        use_incremental = False  # 寮哄埗浣跨敤鍏ㄩ噺閲嶅啓

        if use_incremental:
            # 浣跨敤澧為噺淇锛氬彧淇閿欒閮ㄥ垎
            error_analysis = incremental_generator.analyze_error(code, execution_result)

            # 鐢熸垚閽堝鎬х殑淇Prompt
            fix_prompt = incremental_generator.generate_targeted_prompt(
                code=code,
                error_analysis=error_analysis,
                validated_selectors=state.get("validated_selectors"),
            )

            llm_response = await client.generate_code(fix_prompt)
            repaired_code = extract_python_code(llm_response)

            # 濡傛灉澧為噺淇澶辫触锛屽洖閫€鍒板叏閲忎慨澶?
            if not repaired_code or len(repaired_code) < 100:
                # 鍥為€€鍒板叏閲忎慨澶?
                use_incremental = False

        if not use_incremental:
            # 鍘熸湁鐨勫叏閲忎慨澶嶆祦绋?            # 鐢熸垚璇婃柇浠ｇ爜
            diagnose_prompt = get_code_diagnose_prompt(
                error=error,
                code=code[:3000],  # 闄愬埗浠ｇ爜澶у皬
            )

            llm_response = await client.generate_code(diagnose_prompt)
            diagnose_code = extract_python_code(llm_response)

            # 娌欑鎵ц璇婃柇浠ｇ爜
            sandbox = create_sandbox(use_docker=False)
            diagnosis_result = await sandbox.run_python_code(diagnose_code, timeout=30)

            if diagnosis_result.get("success", False) and isinstance(diagnosis_result.get("output"), dict):
                diagnosis = diagnosis_result["output"]
            else:
                diagnosis = {
                    "error_type": "unknown",
                    "root_cause": error[:200],
                    "fix_suggestion": "妫€鏌ヤ唬鐮佽娉曞拰 API 浣跨敤",
                }

            # 鐢熸垚淇浠ｇ爜
            repair_prompt = get_code_repair_prompt(
                diagnosis=json.dumps(diagnosis, ensure_ascii=False),
                code=code[:5000],
            )

            llm_response = await client.generate_code(repair_prompt)
            repaired_code = extract_python_code(llm_response)

        # 璁板綍淇鏂瑰紡
        fix_method = "incremental" if use_incremental else "full_regeneration"
        state["last_error"] = f"Code repaired ({fix_method}): {error[:50]}"

        state["generated_code"] = repaired_code

    except Exception as e:
        state["last_error"] = f"SOOAL failed: {str(e)}"

    # 璁板綍閿欒鍘嗗彶
    if state.get("error_history") is None:
        state["error_history"] = []
    state["error_history"].append(state.get("last_error", "unknown"))

    return state


@track_performance("reflect")
async def reflect_node(state: ReconState) -> ReconState:
    """
    Reflect 鑺傜偣锛氭繁搴﹀垎鏋愬け璐ュ師鍥狅紙Reflexion 妯″紡锛?
    Phase 4 澧炲己锛欴eep Reflection Memory
    - 缃戠珯绫诲瀷鍒嗙被
    - 鍩熷悕娲炲療瀛樺偍
    - 灏濊瘯绛栫暐璁板綍
    - 閮ㄥ垎鎴愬姛鏁版嵁鍒嗘瀽

    鍩轰簬 Reflexion 璁烘枃 (arXiv:2303.11366) 鐨?Act-Reflect-Remember 寰幆锛?    1. 鍒嗘瀽鎵ц缁撴灉鍜屾暟鎹?    2. 鐢熸垚缁撴瀯鍖栫殑澶辫触鍒嗘瀽
    3. 瀛樺偍鍙嶆€濆埌 deep reflection memory 涓緵涓嬫浣跨敤
    """
    from .prompts import get_reflection_prompt, get_deep_reflection_prompt
    from .llm import ZhipuClient
    from .memory import parse_reflection, FailureMemory
    # Phase 4: Import deep reflection memory and site classifier
    from .reflection_memory import DeepReflectionMemory, analyze_partial_success
    from .site_classifier import SiteClassifier, get_website_features

    state["stage"] = "reflect"


    try:
        client = ZhipuClient(api_key=os.getenv("ZHIPU_API_KEY"))

        # 鏀堕泦涓婁笅鏂?
        execution_result = state.get("execution_result") or {}
        sample_data = state.get("sample_data", [])
        generated_code = state.get("generated_code", "")

        # ========== 淇: 瀹夊叏鑾峰彇 previous_reflections ==========
        reflection_memory_raw = state.get("reflection_memory") or []
        previous_reflections = reflection_memory_raw[-3:] if reflection_memory_raw else []

        # ========== Phase 4: 缃戠珯鍒嗙被鍜岀壒寰佹彁鍙?==========
        url = state["site_url"]
        html = state.get("html_snapshot", "")

        # 鍒嗙被缃戠珯绫诲瀷锛堜紭鍏堜娇鐢?sense 闃舵缁撴灉锛?
        classification = state.get("classification_detail")
        if not classification:
            classification = SiteClassifier.classify(url, html)
            state["classification_detail"] = classification
        website_type = classification.get("type", "unknown")
        state["website_type"] = website_type

        # 鎻愬彇缃戠珯鐗瑰緛
        website_features = state.get("website_features") or get_website_features(url, html)
        state["website_features"] = website_features

        # 鑾峰彇鍩熷悕娲炲療
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        state["domain_insights"] = {
            "domain": domain,
            "website_type": website_type,
            "features": website_features,
            "confidence": classification.get("confidence", 0.0),
            "method": classification.get("method", "unknown"),
        }

        # 鑾峰彇鍙嶇埇铏瓑绾?
        anti_bot_level = state.get("anti_bot_level", "none")

        # ========== Phase 4: 鍒嗘瀽閮ㄥ垎鎴愬姛鏁版嵁 ==========
        partial_success = analyze_partial_success(execution_result, sample_data)
        state["partial_success_data"] = partial_success

        # 纭畾灏濊瘯杩囩殑绛栫暐
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

        # 浣跨敤娣卞害鍙嶆€?prompt锛圥hase 4锛?
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

        # 瑙ｆ瀽鍙嶆€濈粨鏋?
        reflection = parse_reflection(llm_response)

        # 瀛樺偍鍙嶆€濇枃鏈?
        if state.get("reflection_memory") is None:
            state["reflection_memory"] = []
        state["reflection_memory"].append(reflection["text"])

        # 瀛樺偍缁撴瀯鍖栧け璐ヨ褰?
        if state.get("failure_history") is None:
            state["failure_history"] = []

        failure_record = {
            "iteration": state.get("sool_iteration", 0),
            "failure_type": reflection["failure_type"],
            "root_cause": reflection["root_cause"],
            "suggested_fix": reflection["suggested_fix"],
            "avoid_repeat": reflection["avoid_repeat"],
            "data_count": len(sample_data),
            # Phase 4: 鏂板瀛楁
            "website_type": website_type,
            "anti_bot_level": anti_bot_level,
            "attempted_strategies": attempted_strategies,
            "partial_success": partial_success,
        }
        state["failure_history"].append(failure_record)

        # ========== Phase 4: 瀛樺偍鍒版繁搴﹀弽鎬濊蹇?==========
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
        # 闄嶇骇锛氱畝鍗曞弽鎬?
        error_msg = str(e)
        if state.get("reflection_memory") is None:
            state["reflection_memory"] = []

        simple_reflection = f"鎵ц澶辫触: {error_msg}锛屾暟鎹噺: {len(state.get('sample_data', []))}"
        state["reflection_memory"].append(simple_reflection)
        state["last_error"] = f"Reflection failed: {error_msg}"

        # 鍚屾椂璁板綍鍒?failure_history
        if state.get("failure_history") is None:
            state["failure_history"] = []
        state["failure_history"].append({
            "iteration": state.get("sool_iteration", 0),
            "failure_type": "unknown",
            "root_cause": error_msg[:200],
            "suggested_fix": "check error details",
            "data_count": len(state.get("sample_data", [])),
        })

    return state


# ===== 娌欑鎵ц鍣ㄥ鍏?=====

from .sandbox import create_sandbox

