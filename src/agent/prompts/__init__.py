"""
Prompts - Prompt 模板

LLM 代码生成和修复使用的 Prompt 模板。
适配 LangGraph 状态机的各节点。

CodeAct 架构：所有处理逻辑由 LLM 生成 Python 代码，然后在沙箱中执行。
"""

import re
from typing import Optional, Dict


# ============================================================================
# 工具函数：提取 Python 代码
# ============================================================================

def extract_python_code(llm_response: str) -> str:
    """
    从 LLM 响应中提取 Python 代码

    支持以下格式：
    1. ```python ... ```
    2. ``` ... ```
    3. 直接代码（无代码块）

    Args:
        llm_response: LLM 返回的文本

    Returns:
        提取的 Python 代码
    """
    # 尝试提取 ```python 代码块
    pattern = r'```python\n(.*?)\n```'
    match = re.search(pattern, llm_response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 尝试提取 ``` 代码块（无语言标记）
    pattern = r'```\n(.*?)\n```'
    match = re.search(pattern, llm_response, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 没有代码块，直接返回原文本
    return llm_response.strip()


# ============================================================================
# Sense 节点 Prompts - DOM 分析代码生成
# ============================================================================

def get_sense_dom_analysis_prompt(url: str, user_goal: str, html: str) -> str:
    """
    生成 Sense 阶段的 DOM 分析 Prompt
    """
    return f"""你是一个网页结构分析专家。请生成 Python 代码分析以下网页的 DOM 结构。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}

【HTML 内容（前 10000 字符）】
{html[:10000]}

【代码要求】
1. 使用 BeautifulSoup 解析 HTML
2. 生成一个完整的、可直接运行的 Python 脚本
3. 输出 JSON 格式的分析结果

【输出格式】
```json
{{
  "article_selector": "文章/条目容器的 CSS 选择器",
  "title_selector": "标题的选择器",
  "link_selector": "链接的选择器",
  "pagination": {{"type": "next_page|infinite_scroll|load_more|none", "selector": "..."}},
  "sample_entries": [
    {{"title": "...", "link": "...", "extra": "..."}}
  ],
  "recommendations": ["建议1", "建议2"]
}}
```

【代码模板】
```python
from bs4 import BeautifulSoup
import json
import sys

html = '''{html[:5000]}'''

soup = BeautifulSoup(html, 'lxml')

# 分析 DOM 结构
analysis = {{
    "article_selector": "请根据 HTML 分析",
    "title_selector": "请根据 HTML 分析",
    "link_selector": "请根据 HTML 分析",
    "pagination": {{"type": "none", "selector": ""}},
    "sample_entries": [],
    "recommendations": []
}}

# 提取样例数据（前 3 条）
# TODO: 根据 HTML 结构实现

print(json.dumps(analysis, ensure_ascii=False, indent=2))
```

请只输出 Python 代码，不要有其他说明。
"""


# ============================================================================
# Plan 节点 Prompts - 爬虫代码生成
# ============================================================================

def get_code_generation_prompt(url: str, user_goal: str, dom_analysis: str) -> str:
    """
    生成 Plan 阶段的爬虫代码生成 Prompt
    """
    return f"""你是一个爬虫代码生成专家。请生成完整的爬虫代码。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}

【DOM 分析结果】
{dom_analysis}

【代码要求】
1. 使用 **playwright.sync_api**（同步模式，不是 async！）
2. 正确的 API 调用：
   - `browser = p.chromium.launch(headless=True)`
   - `page = browser.new_page()`  ← 正确！
   - 不要使用 `browser.new_context()` ← 错误！
3. 提取的数据以 JSON 格式输出到 stdout

【常见错误避免】
| 错误写法 | 正确写法 |
|---------|---------|
| `browser.new_context()` | `browser.new_page()` |
| `await page.goto()` | `page.goto()` (同步模式) |
| `async def scrape()` | `def scrape()` (同步函数) |
| 忘记 `import json` | 必须在顶部导入 |

【输出格式】
```json
{{
  "results": [{{"field1": "value1", ...}}],
  "metadata": {{"total_pages": 1, "sample_size": N}}
}}
```

【代码模板】
```python
from playwright.sync_api import sync_playwright
import json

def scrape(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()  # 正确的 API

        page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待内容加载
        try:
            page.wait_for_selector('body', timeout=10000)
        except:
            pass

        results = []

        # TODO: 根据 DOM 分析结果实现数据提取
        # 参考: {dom_analysis[:500]}

        browser.close()

        return {{
            "results": results,
            "metadata": {{"total_pages": 1, "sample_size": len(results)}}
        }}

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "{url}"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))
```

请只输出完整可执行的 Python 代码，不要有其他说明。
"""


# ============================================================================
# SOOAL 节点 Prompts - 诊断和修复代码生成
# ============================================================================

def get_code_diagnose_prompt(error: str, code: str) -> str:
    """
    生成 SOOAL 阶段的诊断 Prompt
    """
    return f"""你是一个代码诊断专家。请生成 Python 代码分析以下爬虫代码执行错误。

【错误信息】
{error}

【失败的代码】
```python
{code[:3000]}
```

【代码要求】
1. 生成一个 Python 脚本分析错误类型
2. 输出 JSON 格式的诊断结果

【输出格式】
```json
{{
  "error_type": "selector_error|syntax_error|timeout_error|api_error|rate_limit|other",
  "root_cause": "错误的根本原因描述",
  "fix_suggestion": "具体的修复建议",
  "confidence": 0.9
}}
```

【错误类型参考】
- selector_error: CSS 选择器找不到元素
- syntax_error: Python 语法错误
- timeout_error: 页面加载超时
- api_error: Playwright API 使用错误
- rate_limit: 触发反爬限制
- other: 其他错误

【诊断代码模板】
```python
import json
import re

error_text = '''{error[:1000]}'''

# 分析错误
error_type = "other"
root_cause = "待分析"
fix_suggestion = "待分析"

# TODO: 根据 error_text 判断错误类型

diagnosis = {{
    "error_type": error_type,
    "root_cause": root_cause,
    "fix_suggestion": fix_suggestion,
    "confidence": 0.8
}}

print(json.dumps(diagnosis, ensure_ascii=False, indent=2))
```

请只输出 Python 代码，不要有其他说明。
"""


def get_code_repair_prompt(diagnosis: str, code: str) -> str:
    """
    生成 SOOAL 阶段的修复 Prompt
    """
    return f"""你是一个代码修复专家。请根据诊断结果修复爬虫代码。

【诊断结果】
{diagnosis}

【原代码】
```python
{code[:5000]}
```

【修复要求】
1. 根据诊断结果修复代码
2. 使用 **playwright.sync_api**（同步模式）
3. 确保 API 调用正确：
   - `browser = p.chromium.launch(headless=True)`
   - `page = browser.new_page()` ← 正确！
   - 不要使用 `browser.new_context()` ← 错误！
4. 确保输出 JSON 格式包含 results 和 metadata
5. 只输出修复后的完整代码

请生成修复后的代码。
"""


# ============================================================================
# Verify 节点 Prompts
# ============================================================================

def get_quality_evaluation_prompt(user_goal: str, extracted_data: str) -> str:
    """
    生成 Verify 阶段的质量评估 Prompt

    保留原有接口以保持向后兼容。
    内部调用增强版评估函数。
    """
    return get_enhanced_quality_evaluation_prompt(
        user_goal=user_goal,
        extracted_data=extracted_data,
        validation_rules=None,
    )


def get_enhanced_quality_evaluation_prompt(
    user_goal: str,
    extracted_data: str,
    validation_rules: Optional[dict] = None,
) -> str:
    """
    生成增强的质量评估 Prompt

    新增验证维度：
    - 图片质量: URL 有效性、占位图检测
    - 格式验证: 日期、价格、URL 格式
    - 内容质量: 非空检查、重复检测
    - 细粒度需求: 用户自定义规则

    Args:
        user_goal: 用户需求描述
        extracted_data: 提取的采样数据（JSON 字符串）
        validation_rules: 验证规则字典（可选）

    Returns:
        完整的质量评估 Prompt
    """
    rules = validation_rules or {}

    return f"""请生成 Python 代码评估以下采样数据的质量。

【用户需求】
{user_goal}

【提取的数据】
{extracted_data}

【验证规则】
{{"check_duplicates": {rules.get("check_duplicates", True)},
 "validate_urls": {rules.get("validate_urls", True)},
 "validate_images": {rules.get("validate_images", False)},
 "validate_price": {rules.get("validate_price", False)},
 "validate_date": {rules.get("validate_date", False)}}}

【代码要求】
生成一个完整的 Python 脚本，包含以下验证函数：

1. **validate_images(items)**: 图片质量验证
   - 检查图片 URL 格式有效性
   - 检测占位图（包含 "placeholder", "default", "no-image" 等）
   - 返回: {{"total": N, "valid": M, "placeholder": K, "invalid": L}}

2. **validate_formats(items)**: 格式验证
   - 日期格式: YYYY-MM-DD, ISO 8601 等
   - 价格格式: 数字 + 货币符号
   - URL 格式: 有效的 http(s) URL
   - 返回: {{"date_valid": N, "price_valid": M, "url_valid": K}}

3. **validate_content(items)**: 内容质量验证
   - 检查必填字段是否为空
   - 检测重复记录（基于标题/链接去重）
   - 检测无意义内容（"N/A", "null", "待补充"）
   - 返回: {{"empty_fields": N, "duplicates": M, "invalid_content": K}}

4. **calculate_quality_score(items)**: 综合评分
   - relevance (0.4): 与用户需求的相关性（根据字段匹配度判断）
   - completeness (0.3): 必填字段完整度
   - accuracy (0.2): 格式正确性
   - content_quality (0.1): 内容质量（非空、无重复）

【输出格式】
请输出 JSON 格式的评估结果：

```json
{{
  "relevance": 0.9,
  "completeness": 0.8,
  "accuracy": 0.95,
  "content_quality": 0.7,
  "overall_score": 0.85,
  "image_stats": {{"total": 50, "valid": 45, "placeholder": 5, "invalid": 0}},
  "format_stats": {{"date_valid": 48, "date_total": 50, "price_valid": 50, "price_total": 50, "url_valid": 49, "url_total": 50}},
  "content_stats": {{"empty_fields": 2, "duplicates": 0, "invalid_content": 1, "total_items": 50}},
  "issues": ["具体问题描述..."],
  "suggestions": ["改进建议..."]
}}
```

【数据定义】
请使用以下数据定义：

```python
import json
from urllib.parse import urlparse
from datetime import datetime
import re

# 输入数据
items = {extracted_data}

def validate_images(items: list) -> dict:
    '''验证图片质量'''
    stats = {{"total": 0, "valid": 0, "placeholder": 0, "invalid": 0}}
    placeholder_keywords = ['placeholder', 'default', 'no-image', 'no_image',
                           'generic', 'sample', 'example', 'empty', 'missing',
                           '占位', '默认']

    for item in items:
        for key, value in item.items():
            if 'image' in key.lower() or 'img' in key.lower() or 'picture' in key.lower() or 'photo' in key.lower():
                if isinstance(value, str) and value:
                    stats["total"] += 1
                    # 检查 URL 有效性
                    try:
                        result = urlparse(value)
                        if not all([result.scheme in ['http', 'https'], result.netloc]):
                            stats["invalid"] += 1
                            continue
                    except:
                        stats["invalid"] += 1
                        continue

                    # 检查占位图
                    if any(kw in value.lower() for kw in placeholder_keywords):
                        stats["placeholder"] += 1
                    else:
                        stats["valid"] += 1

    return stats

def validate_formats(items: list) -> dict:
    '''验证数据格式'''
    stats = {{"date_valid": 0, "date_total": 0,
              "price_valid": 0, "price_total": 0,
              "url_valid": 0, "url_total": 0}}

    # 日期格式模式
    date_patterns = [
        r'^\\d{{4}}-\\d{{2}}-\\d{{2}}$',           # YYYY-MM-DD
        r'^\\d{{4}}/\\d{{2}}/\\d{{2}}$',           # YYYY/MM/DD
        r'^\\d{{4}}年\\d{{1,2}}月\\d{{1,2}}日$',  # 中文日期
    ]

    # 价格格式模式
    price_pattern = r'^[¥$€£]?\s*\\d+(\\.\\d+)?\\s*[元美元EURGBPUSD]?$'

    for item in items:
        for key, value in item.items():
            if not isinstance(value, str):
                continue

            # 日期验证
            if 'date' in key.lower() or 'time' in key.lower() or '时间' in key or '日期' in key:
                stats["date_total"] += 1
                if any(re.match(p, value.strip()) for p in date_patterns):
                    stats["date_valid"] += 1

            # 价格验证
            elif 'price' in key.lower() or '成本' in key or '价格' in key or '费用' in key:
                stats["price_total"] += 1
                if re.match(price_pattern, value.strip()):
                    stats["price_valid"] += 1

            # URL 验证
            elif 'url' in key.lower() or 'link' in key.lower() or 'href' in key.lower() or '链接' in key:
                stats["url_total"] += 1
                try:
                    result = urlparse(value)
                    if all([result.scheme in ['http', 'https'], result.netloc]):
                        stats["url_valid"] += 1
                except:
                    pass

    return stats

def validate_content(items: list) -> dict:
    '''验证内容质量'''
    stats = {{
        "empty_fields": 0,
        "duplicates": 0,
        "invalid_content": 0,
        "total_items": len(items)
    }}

    seen = set()
    null_values = ["n/a", "null", "none", "待补充", "暂无", "tbd", "-", "—",
                   "undefined", "unknown", "?"]

    for item in items:
        # 检查重复（基于标题或链接）
        identifier = item.get("title") or item.get("url") or item.get("link") or str(item.get("id", ""))
        if identifier and identifier in seen:
            stats["duplicates"] += 1
        seen.add(identifier)

        # 检查空字段和无意义内容
        for value in item.values():
            if value is None or value == "":
                stats["empty_fields"] += 1
            elif isinstance(value, str):
                val_stripped = value.strip()
                if not val_stripped:
                    stats["empty_fields"] += 1
                elif val_stripped.lower() in null_values:
                    stats["invalid_content"] += 1

    return stats

def calculate_quality_score(items: list, image_stats: dict, format_stats: dict, content_stats: dict) -> dict:
    '''计算综合质量分数'''
    total_items = len(items)
    if total_items == 0:
        return {{"relevance": 0, "completeness": 0, "accuracy": 0, "content_quality": 0, "overall_score": 0}}

    # relevance: 基于数据丰富度（平均每条记录的字段数）
    avg_fields = sum(len([v for v in item.values() if v not in [None, ""]]) for item in items) / total_items
    relevance = min(1.0, avg_fields / 5)  # 假设 5 个字段为满分

    # completeness: 基于非空字段比例
    total_fields = sum(len(item) for item in items)
    filled_fields = total_fields - content_stats.get("empty_fields", 0)
    completeness = filled_fields / total_fields if total_fields > 0 else 0

    # accuracy: 基于格式验证通过率
    format_valid = 0
    format_total = 0
    for k in ["date_total", "price_total", "url_total"]:
        if format_stats.get(k, 0) > 0:
            format_total += format_stats[k]
            valid_key = k.replace("_total", "_valid")
            format_valid += format_stats.get(valid_key, 0)
    accuracy = format_valid / format_total if format_total > 0 else 0.8

    # content_quality: 基于内容质量（无重复、无无效内容）
    content_quality = 1.0
    if content_stats.get("total_items", 0) > 0:
        dup_ratio = content_stats.get("duplicates", 0) / content_stats["total_items"]
        invalid_ratio = content_stats.get("invalid_content", 0) / max(content_stats["total_items"] * 3, 1)
        content_quality = max(0, 1.0 - dup_ratio - invalid_ratio)

    # 综合得分
    overall_score = (relevance * 0.4 + completeness * 0.3 + accuracy * 0.2 + content_quality * 0.1)

    return {{
        "relevance": round(relevance, 2),
        "completeness": round(completeness, 2),
        "accuracy": round(accuracy, 2),
        "content_quality": round(content_quality, 2),
        "overall_score": round(overall_score, 2)
    }}

# 主程序
if __name__ == "__main__":
    image_stats = validate_images(items)
    format_stats = validate_formats(items)
    content_stats = validate_content(items)
    scores = calculate_quality_score(items, image_stats, format_stats, content_stats)

    # 收集问题
    issues = []
    if scores["completeness"] < 0.7:
        issues.append(f"数据完整性较低: {{scores['completeness']}}，部分必填字段可能缺失")
    if image_stats.get("placeholder", 0) > 0:
        issues.append(f"发现占位图: {{image_stats['placeholder']}} 个")
    if content_stats.get("duplicates", 0) > 0:
        issues.append(f"发现重复记录: {{content_stats['duplicates']}} 条")

    result = {{
        **scores,
        "image_stats": image_stats,
        "format_stats": format_stats,
        "content_stats": content_stats,
        "issues": issues,
        "suggestions": []
    }}

    print(json.dumps(result, ensure_ascii=False, indent=2))
```

请只输出 Python 代码，不要有其他说明。
"""


def extract_validation_rules(user_goal: str) -> dict:
    """
    从用户需求中提取验证规则

    Args:
        user_goal: 用户需求描述

    Returns:
        验证规则字典

    示例:
        - "提取高清图片" → {{"image_quality": "high"}}
        - "价格格式要正确" → {{"validate_price": True}}
        - "不能有重复" → {{"check_duplicates": True}}
    """
    rules = {
        "check_duplicates": True,
        "validate_urls": True,
    }

    goal_lower = user_goal.lower()

    # 图片相关
    if "图片" in goal_lower or "image" in goal_lower or "img" in goal_lower:
        rules["validate_images"] = True
        if "高清" in goal_lower or "high" in goal_lower or "hd" in goal_lower:
            rules["image_quality"] = "high"

    # 价格相关
    if "价格" in goal_lower or "price" in goal_lower or "成本" in goal_lower or "费用" in goal_lower:
        rules["validate_price"] = True

    # 日期相关
    if "日期" in goal_lower or "date" in goal_lower or "时间" in goal_lower or "time" in goal_lower:
        rules["validate_date"] = True

    # 去重相关
    if "不重复" in goal_lower or "unique" in goal_lower or "去重" in goal_lower:
        rules["check_duplicates"] = True

    # 链接相关
    if "链接" in goal_lower or "url" in goal_lower or "link" in goal_lower:
        rules["validate_urls"] = True

    return rules


# ============================================================================
# Report 节点 Prompts
# ============================================================================

def get_report_generation_prompt(
    site_url: str,
    user_goal: str,
    site_info: str,
    sample_data: str,
    sool_iteration: int,
    quality_score: float,
    sample_count: int,
) -> str:
    """
    生成 Report 阶段的报告生成 Prompt
    """
    return f"""请生成网站侦察报告的 Markdown 格式。

【站点信息】
- URL: {site_url}
- 用户需求: {user_goal}

【站点上下文】
{site_info[:1000]}

【样本数据】（前 5 条）
{sample_data[:1000]}

【侦察统计】
- SOOAL 迭代次数: {sool_iteration}
- 质量分数: {quality_score}
- 样本数量: {sample_count}

【报告要求】
生成结构化的侦察报告，包含：
1. 站点基本信息
2. 数据侦察结果（估算总量、样本质量）
3. 真实样本预览
4. 可爬性评估
5. 推荐爬取策略

【输出格式示例】
```markdown
# 网站数据侦察报告

## 站点信息
- URL: {site_url}
- 用户需求: {user_goal}
- 侦察时间: 2026-XX-XX

## 侦察总结
- 估算数据总量: ~1000 条
- 样本质量分数: {quality_score}/1.0
- 数据结构化程度: 高

## 站点特征分析
- 页面类型: 列表页
- 分页方式: 传统分页
- 反爬等级: 低

## 真实样本预览
{{样本数据}}

## 可爬性评估
- 反爬等级: 低/中/高
- 技术难度: 简单/中等/复杂
- 推荐策略: [具体策略建议]
```

请生成报告。
"""


# ============================================================================
# 兼容性：保留旧名称（用于向后兼容）
# ============================================================================

# 旧的常量名，现在用函数替代
SENSE_DOM_ANALYSIS_PROMPT = ""  # 使用 get_sense_dom_analysis_prompt()
CODE_GENERATION_PROMPT = ""     # 使用 get_code_generation_prompt()
CODE_DIAGNOSE_PROMPT = ""       # 使用 get_code_diagnose_prompt()
CODE_REPAIR_PROMPT = ""         # 使用 get_code_repair_prompt()
QUALITY_EVALUATION_PROMPT = ""  # 使用 get_quality_evaluation_prompt()
REPORT_GENERATION_PROMPT = ""   # 使用 get_report_generation_prompt()


# ============================================================================
# 可用工具说明（给 LLM 参考）
# ============================================================================

AVAILABLE_TOOLS = """
## 可用的工具和库

### Browser (Playwright Sync)
```python
from playwright.sync_api import sync_playwright

def scrape(url: str) -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()  # 正确的 API
        page.goto(url)
        page.wait_for_selector('body', timeout=10000)
        content = page.inner_text(selector)
        browser.close()
```

### Parser (BeautifulSoup)
```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'lxml')
items = soup.select('.item-class')
```

### 数据输出
```python
import json
output = {{
    "results": data_list,
    "metadata": {{"total": len(data_list)}}
}}
print(json.dumps(output, ensure_ascii=False))
```
"""
