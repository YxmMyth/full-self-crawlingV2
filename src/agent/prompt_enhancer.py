"""
Prompt Enhancer - 改进的Prompt生成器

整合选择器库和最佳实践，生成更精准的代码生成Prompt。
"""

from typing import Dict, List, Optional
from .selector_library import suggest_selectors, get_selector_fix_suggestion, generate_selector_suggestion_prompt


def get_enhanced_code_generation_prompt(
    url: str,
    user_goal: str,
    dom_analysis: str,
    website_type: str = "unknown",
    stealth_level: str = "none",
    failure_history: Optional[List[Dict]] = None,
    reflection_memory: Optional[List[str]] = None,
    validated_selectors: Optional[List[str]] = None,
) -> str:
    """
    增强版代码生成Prompt

    整合了选择器库、失败历史、反思记忆和验证结果。
    """
    import json

    # 1. 选择器建议
    selector_suggestion = generate_selector_suggestion_prompt(url, user_goal, website_type)

    # 2. 失败历史提示
    failure_hint = ""
    if failure_history:
        recent_failures = failure_history[-2:]  # 最近2次
        failure_types = [f.get("failure_type", "") for f in recent_failures]
        failure_hint = f"""

【历史失败类型】
避免以下已知的失败类型：{", ".join(set(failure_types))}

上次失败的根因：{recent_failures[-1].get("root_cause", "N/A")[:150] if recent_failures else "N/A"}
"""

    # 3. 反思记忆提示
    reflection_hint = ""
    if reflection_memory:
        latest = reflection_memory[-1]
        reflection_hint = f"""

【上次的反思】
{latest[:300]}
"""

    # 4. 验证过的选择器
    validated_hint = ""
    if validated_selectors:
        validated_text = "\n".join(f"- {s}" for s in validated_selectors[:5])
        validated_hint = f"""

【✅ 已验证有效的选择器】
请优先使用以下已验证的选择器：
{validated_text}
"""

    # 5. 隐身配置
    stealth_config = _get_stealth_config_text(stealth_level)

    # 6. 代码片段提取检测
    code_extraction_guide = _get_code_extraction_guide(user_goal)

    return f"""你是一个Web爬虫代码生成专家。请生成完整、健壮的爬虫代码。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}
网站类型: {website_type}
{selector_suggestion}
{validated_hint}
【DOM 分析结果】
{dom_analysis[:1000]}
{failure_hint}
{reflection_hint}

【⚠️ 代码质量要求】
1. **健壮性优先**：代码必须能处理异常情况
2. **选择器容错**：使用try-except包裹选择器操作
3. **数据验证**：检查提取的数据是否为空
4. **资源释放**：确保browser.close()在finally块中

【代码结构要求】
```python
from playwright.sync_api import sync_playwright
import json
import time
import random

def scrape(url: str) -> dict:
    results = []
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                {stealth_config}
            )
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={{"width": 1920, "height": 1080}}
            )

            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素
            try:
                page.wait_for_selector('body', timeout=10000)
            except:
                pass

            # 人类行为延迟
            time.sleep(random.uniform(1, 2))

            # === 数据提取 ===
            # 使用已验证的选择器或建议的选择器

            # 方法1: 使用单个选择器
            items = page.locator("SELECTOR_HERE").all()
            for item in items:
                try:
                    result = {{}}
                    # 提取各个字段
                    result["field"] = item.locator("SUB_SELECTOR").text_content()
                    results.append(result)
                except Exception as e:
                    continue

            # 方法2: 如果没有单个容器，逐个提取
            if not results:
                # 分别提取标题、链接、图片等
                pass

    except Exception as e:
        # 记录错误但继续
        error = str(e)
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("title") or r.get("name")]

    return {{
        "results": valid_results,
        "metadata": {{
            "total_extracted": len(results),
            "valid_count": len(valid_results),
            "url": url
        }}
    }}

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "{url}"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

【选择器使用最佳实践】
1. **优先级**：已验证选择器 > 建议选择器 > DOM分析中的选择器
2. **容错处理**：每个选择器操作都要try-except
3. **备选方案**：如果主选择器失败，尝试备选选择器
4. **属性选择器**：使用 [class*='keyword'] 进行部分匹配
5. **文本提取**：使用 .text_content() 而不是 .inner_text() 更快

【常见错误及修复】
| 问题 | 修复方法 |
|------|---------|
| 选择器匹配0个 | 使用更通用的选择器或属性选择器 |
| 选择器匹配太多 | 添加父容器限定 |
| 文本为空 | 检查是否需要等待加载 |
| timeout | 增加wait_for_selector的timeout |
| 元素不可见 | 使用force=True或wait_for_load_state |

{code_extraction_guide}

【⚠️ 关键注意事项】
1. 必须使用 sync_playwright（同步模式）
2. browser.new_page() 不是 browser.new_context()
3. 必须在finally中close browser
4. 结果必须是JSON格式输出到stdout
5. 数据要验证非空后再添加到results

请只输出完整可执行的 Python 代码，不要有其他说明。
"""


def _get_stealth_config_text(stealth_level: str) -> str:
    """获取隐身配置文本"""
    configs = {
        "none": "# 无隐身配置",
        "low": """args=["--disable-blink-features=AutomationControlled"]""",
        "medium": """args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]""",
        "high": """args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security"]""",
    }
    return configs.get(stealth_level, configs["none"])


def _get_code_extraction_guide(user_goal: str) -> str:
    """获取代码片段提取指南"""
    keywords = [
        "svg", "html代码", "html片段", "代码片段",
        "图标", "icon", "富文本", "组件"
    ]

    if not any(kw in user_goal.lower() for kw in keywords):
        return ""

    return """

【代码片段提取（SVG/HTML）】
如果需求包含代码片段提取：
- 使用 `page.evaluate("el => el.outerHTML")` 获取完整HTML
- 使用 `element.inner_html()` 获取内部HTML
- 等待动态内容: `page.wait_for_selector('svg', timeout=15000)`

示例：
```python
# 提取SVG
svgs = page.locator("svg").all()
for svg in svgs[:5]:
    svg_code = svg.evaluate("el => el.outerHTML")
    results.append({{"svg_code": svg_code, "type": "svg"}})

# 提取HTML片段
html_blocks = page.locator(".rich-text").all()
for block in html_blocks[:5]:
    html_snippet = block.inner_html()
    results.append({{"html_snippet": html_snippet, "type": "html"}})
```
"""


def get_error_diagnosis_prompt(
    error: str,
    code: str,
    execution_output: str = "",
    html_snapshot: str = "",
) -> str:
    """
    增强版错误诊断Prompt

    提供更详细的错误分析指导。
    """
    return f"""你是一个代码调试专家。请分析以下爬虫代码的执行错误。

【错误信息】
{error[:500]}

【执行输出】
{execution_output[:500] if execution_output else "无"}

【代码片段】
```python
{code[:1000]}
```

【HTML快照】
{html_snapshot[:500] if html_snapshot else "无"}

【请诊断】
请分析上述错误，并按以下JSON格式返回诊断结果：

```json
{{
  "error_type": "selector_error|timeout|api_error|syntax_error|other",
  "root_cause": "具体的根本原因...",
  "affected_code_part": "出错的代码片段...",
  "fix_strategy": "具体的修复策略...",
  "suggested_code_fix": "修复后的代码片段...",
  "alternative_selectors": ["备选选择器1", "备选选择器2"]
}}
```

【常见错误类型】
- **selector_error**: 选择器无匹配，需要更换选择器
- **timeout**: 页面加载超时，需要增加等待时间或检查元素是否存在
- **api_error**: Playwright API使用错误，如async/sync混用
- **syntax_error**: 代码语法错误
- **attribute_error**: 属性访问错误，通常是元素不存在

【诊断要点】
1. 识别错误的真正类型（不是表面的错误信息）
2. 找到导致错误的代码行
3. 分析为什么会出错（页面结构、选择器、时机等）
4. 提供具体的修复建议和代码
5. 给出备选方案

请输出JSON格式的诊断结果。
"""


def get_reflection_enhancement_prompt(
    url: str,
    execution_result: dict,
    sample_data: list,
    website_type: str,
    anti_bot_level: str,
    previous_reflections: list,
) -> str:
    """
    增强版反思Prompt

    提供更结构化的反思指导。
    """
    success = execution_result.get("success", False)
    error = execution_result.get("error", "") or execution_result.get("stderr", "")
    data_count = len(sample_data)

    # 分析数据质量
    data_quality = _analyze_data_quality(sample_data)

    return f"""你是一个Web爬虫专家，正在进行深度反思分析。

【任务信息】
- URL: {url}
- 网站类型: {website_type}
- 反爬虫等级: {anti_bot_level}

【执行结果】
- 执行成功: {success}
- 提取数据量: {data_count}条
- 错误信息: {error[:300] if error else "无"}
- 数据质量: {data_quality}

【提取的数据样本】
```json
{str(sample_data[:2])[:500]}
```

【历史反思】
{chr(10).join(f"{i+1}. {r[:200]}" for i, r in enumerate(previous_reflections[-3:]))}

【反思框架】
请按照以下框架进行反思：

### 1. 失败类型分类
从以下类型中选择最匹配的：
- **selector_error**: 选择器问题（无匹配/匹配过多）
- **js_rendering**: JS内容未正确渲染
- **timeout**: 页面加载超时
- **rate_limit**: 被速率限制
- **empty_result**: 执行成功但无数据
- **blocked**: 被反爬虫阻止
- **api_error**: Playwright API使用错误
- **code_bug**: 代码逻辑错误
- **anti_bot**: 反爬虫系统（CAPTCHA等）

### 2. 根本原因分析
结合网站类型({website_type})和反爬虫等级({anti_bot_level})：
- 为什么会出现这个错误？
- 是网站特殊结构导致的吗？
- 是反爬虫机制导致的吗？
- 是代码实现问题吗？

### 3. 数据质量评估
- 数据完整性如何？
- 有空字段吗？
- 有重复数据吗？
- 数据格式正确吗？

### 4. 修复建议
给出具体的、可操作的修复方案：
- 对于 {website_type} 类型的网站
- 对于 {anti_bot_level} 级别的反爬虫
- 避免重复历史错误

### 5. 下次策略
- 下次应该尝试什么不同的方法？
- 有没有备选方案？
- 需要调整什么参数？

请按以下JSON格式输出反思结果：

```json
{{
  "failure_type": "selector_error",
  "root_cause": "具体原因分析...",
  "data_quality_assessment": "数据质量评估...",
  "suggested_fix": "具体修复方案...",
  "next_strategy": "下次应该尝试的策略...",
  "alternative_approaches": ["备选方案1", "备选方案2"],
  "learnings": ["学到的东西1", "学到的东西2"]
}}
```

【⚠️ 重要】
- 如果是第2次及以上尝试，必须避免重复之前的错误
- 结合网站特征给出针对性的建议
- 修复建议必须具体可执行

请输出JSON格式的反思结果。
"""


def _analyze_data_quality(data: list) -> str:
    """分析数据质量"""
    if not data:
        return "无数据"

    # 检查空值
    total_fields = sum(len(item) for item in data[:10])
    empty_fields = sum(1 for item in data[:10] for v in item.values() if not v)

    if empty_fields > total_fields * 0.5:
        return "差（大量空值）"
    elif empty_fields > total_fields * 0.2:
        return "中等（部分空值）"
    else:
        return "良好"


# 导出函数
__all__ = [
    "get_enhanced_code_generation_prompt",
    "get_error_diagnosis_prompt",
    "get_reflection_enhancement_prompt",
]
