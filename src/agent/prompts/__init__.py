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
    # 检测是否需要代码片段提取
    needs_code_extraction = _detect_code_snippet_need(user_goal)

    code_extraction_guide = ""
    if needs_code_extraction:
        code_extraction_guide = """

【代码片段提取（SVG/HTML）】
如果用户需求包含"SVG代码"、"HTML代码片段"、"富文本"、"图标"等关键词：
- 使用 `page.inner_html()` 或 `element.inner_html()` 提取 HTML/SVG 代码
- 使用 `page.evaluate("el => el.outerHTML")` 获取包含元素自身的完整代码
- 等待 JS 动态内容加载完成: `page.wait_for_selector('svg', timeout=15000)`

提取示例：
```python
# 提取 SVG 代码
svgs = page.locator("svg").all()
for svg in svgs[:5]:  # 限量采样
    svg_code = svg.evaluate("el => el.outerHTML")
    results.append({{"svg_code": svg_code, "type": "svg"}})

# 提取 HTML 片段
html_blocks = page.locator(".rich-text, .description, [data-html]").all()
for block in html_blocks[:5]:
    html_snippet = block.inner_html()
    results.append({{"html_snippet": html_snippet, "type": "html"}})
```
"""

    return f"""你是一个爬虫代码生成专家。请生成完整的爬虫代码。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}

【DOM 分析结果】
{dom_analysis}
{code_extraction_guide}

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


def _detect_code_snippet_need(user_goal: str) -> bool:
    """检测用户需求是否包含代码片段提取关键词"""
    keywords = [
        "svg", "html代码", "html片段", "html snippet",
        "代码片段", "code snippet", "图标", "icon",
        "富文本", "rich text", "组件", "component",
        "元素", "element", "标签", "tag"
    ]
    goal_lower = user_goal.lower()
    return any(keyword in goal_lower for keyword in keywords)


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

def get_deep_validation_prompt(
    data_type: str,
    sample_items: list,
    user_goal: str,
    validation_rules: dict = None,
) -> str:
    """
    生成深度验证代码的 Prompt

    Args:
        data_type: "image" | "pdf" | "video"
        sample_items: 需要验证的样本数据（JSON 字符串或列表）
        user_goal: 用户需求描述
        validation_rules: 验证规则（如最小分辨率要求）

    Returns:
        完整的 Python 验证代码 Prompt
    """
    import json

    if isinstance(sample_items, list):
        sample_data_str = json.dumps(sample_items, ensure_ascii=False)
    else:
        sample_data_str = sample_items

    rules = validation_rules or {}

    if data_type == "image":
        min_resolution = rules.get("min_image_resolution", "1920x1080")
        min_width, min_height = map(int, min_resolution.split("x"))

        return f"""请生成 Python 代码深度验证以下图片数据。

【用户需求】
{user_goal}

【验证规则】
- 最小分辨率要求: {min_width}x{min_height}
- 检测占位图: 是
- 检测缩略图: 是

【数据样本】
{sample_data_str[:2000]}

【代码要求】
生成一个完整的 Python 脚本，使用 PIL (Pillow) 进行深度图片验证：

1. **下载图片**: 使用 requests 下载图片（timeout=10s）
2. **基础验证**:
   - 分辨率检查: width >= {min_width}, height >= {min_height}
   - 格式检查: JPEG, PNG, WebP 等常见格式
   - 大小检查: 记录文件大小

3. **占位图检测**:
   - URL 包含: placeholder, default, no-image, generic, sample, example
   - 中文: 占位, 默认
   - 尺寸过小: width < 300 or height < 300

4. **输出格式**:
```json
{{
  "images": [
    {{
      "url": "...",
      "valid": true,
      "width": 1920,
      "height": 1080,
      "format": "JPEG",
      "file_size_bytes": 123456,
      "is_high_res": true,
      "is_placeholder": false,
      "is_thumbnail": false
    }}
  ],
  "summary": {{
    "total": N,
    "valid": M,
    "placeholder": K,
    "low_res": L
  }}
}}
```

【代码模板】
```python
import requests
from PIL import Image
from io import BytesIO
import json

def validate_image(url: str) -> dict:
    '''深度验证单张图片'''
    try:
        headers = {{"User-Agent": "Mozilla/5.0"}}
        response = requests.get(url, timeout=10, headers=headers)
        img = Image.open(BytesIO(response.content))

        return {{
            "url": url,
            "valid": True,
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "file_size_bytes": len(response.content),
            "is_high_res": img.width >= {min_width} and img.height >= {min_height},
            "is_placeholder": any(kw in url.lower() for kw in ['placeholder', 'default', 'no-image']),
            "is_thumbnail": img.width < 300 or img.height < 300
        }}
    except Exception as e:
        return {{"url": url, "valid": False, "error": str(e)}}

# 主程序
items = {sample_data_str[:500]}
results = []
for item in items:
    for key, value in item.items():
        if 'image' in key.lower() and isinstance(value, str):
            results.append(validate_image(value))

summary = {{
    "total": len(results),
    "valid": sum(1 for r in results if r.get("valid")),
    "placeholder": sum(1 for r in results if r.get("is_placeholder")),
    "low_res": sum(1 for r in results if not r.get("is_high_res", True))
}}

print(json.dumps({{"images": results, "summary": summary}}, ensure_ascii=False))
```

请只输出 Python 代码，不要有其他说明。
"""

    elif data_type == "pdf":
        return f"""请生成 Python 代码深度验证以下 PDF 数据。

【用户需求】
{user_goal}

【数据样本】
{sample_data_str[:2000]}

【代码要求】
生成一个完整的 Python 脚本，使用 PyPDF2 进行深度 PDF 验证：

1. **下载 PDF**: 使用 requests 下载 PDF（timeout=15s）
2. **基础验证**:
   - 页数检查: 记录总页数
   - 内容检查: 提取第一页文本，判断是否有实际内容
   - 加密检查: 判断是否加密

3. **输出格式**:
```json
{{
  "pdfs": [
    {{
      "url": "...",
      "valid": true,
      "pages": 10,
      "has_content": true,
      "is_encrypted": false,
      "file_size_bytes": 123456,
      "preview_text": "前200字符..."
    }}
  ],
  "summary": {{
    "total": N,
    "valid": M,
    "empty_content": K
  }}
}}
```

【代码模板】
```python
import requests
import PyPDF2
from io import BytesIO
import json

def validate_pdf(url: str) -> dict:
    '''深度验证单个 PDF'''
    try:
        headers = {{"User-Agent": "Mozilla/5.0"}}
        response = requests.get(url, timeout=15, headers=headers)
        pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))

        first_page_text = ""
        if len(pdf_reader.pages) > 0:
            first_page_text = pdf_reader.pages[0].extract_text() or ""

        return {{
            "url": url,
            "valid": True,
            "pages": len(pdf_reader.pages),
            "has_content": len(first_page_text.strip()) > 50,
            "is_encrypted": pdf_reader.is_encrypted,
            "file_size_bytes": len(response.content),
            "preview_text": first_page_text[:200]
        }}
    except Exception as e:
        return {{"url": url, "valid": False, "error": str(e)}}

# 主程序
items = {sample_data_str[:500]}
results = []
for item in items:
    for key, value in item.items():
        if 'pdf' in key.lower() and isinstance(value, str):
            results.append(validate_pdf(value))

summary = {{
    "total": len(results),
    "valid": sum(1 for r in results if r.get("valid")),
    "empty_content": sum(1 for r in results if not r.get("has_content", True))
}}

print(json.dumps({{"pdfs": results, "summary": summary}}, ensure_ascii=False))
```

请只输出 Python 代码，不要有其他说明。
"""

    elif data_type == "video":
        return f"""请生成 Python 代码验证以下视频数据。

【用户需求】
{user_goal}

【数据样本】
{sample_data_str[:2000]}

【代码要求】
生成一个完整的 Python 脚本，验证视频链接的可访问性：

1. **HEAD 请求**: 检查链接是否可访问
2. **内容类型**: 验证 Content-Type 是否为视频
3. **文件大小**: 记录文件大小（如果可用）

【代码模板】
```python
import requests
import json

def validate_video(url: str) -> dict:
    '''验证视频链接'''
    try:
        headers = {{"User-Agent": "Mozilla/5.0"}}
        response = requests.head(url, timeout=10, headers=headers, allow_redirects=True)

        content_type = response.headers.get("Content-Type", "")
        content_length = response.headers.get("Content-Length")

        is_video = "video/" in content_type

        return {{
            "url": url,
            "valid": is_video,
            "content_type": content_type,
            "file_size_bytes": int(content_length) if content_length else None,
            "accessible": response.status_code == 200
        }}
    except Exception as e:
        return {{"url": url, "valid": False, "error": str(e)}}

# 主程序
items = {sample_data_str[:500]}
results = []
for item in items:
    for key, value in item.items():
        if 'video' in key.lower() and isinstance(value, str):
            results.append(validate_video(value))

print(json.dumps({{"videos": results}}, ensure_ascii=False))
```

请只输出 Python 代码，不要有其他说明。
"""

    else:
        return get_quality_evaluation_prompt(user_goal, sample_data_str)


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
    price_pattern = r'^[¥$€£]?\\s*\\d+(\\.\\d+)?\\s*[元美元EURGBPUSD]?$'

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
# Interact 节点 Prompts - 多步交互逻辑
# ============================================================================

def get_interact_prompt(
    url: str,
    user_goal: str,
    dom_analysis: str = "",
    detected_features: list = None,
) -> str:
    """
    生成交互阶段的 Prompt

    用于处理需要多步交互的场景，例如：
    1. 点击搜索按钮
    2. 填写表单
    3. 滚动加载
    4. 等待动态内容

    Args:
        url: 目标站点 URL
        user_goal: 用户需求
        dom_analysis: DOM 分析结果
        detected_features: 检测到的页面特征

    Returns:
        交互代码生成 Prompt
    """
    features = detected_features or []

    features_text = ""
    if features:
        features_text = f"\n【检测到的页面特征】\n{', '.join(features)}"

    return f"""你是一个浏览器交互专家。请生成处理多步交互的代码。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}
{features_text}

【DOM 分析结果】
{dom_analysis[:1000] if dom_analysis else "暂无"}

【常见交互类型】

1. **点击按钮触发内容加载**
   ```python
   # 查找并点击搜索/提交按钮
   search_btn = page.query_selector('button[type="submit"]')
   if not search_btn:
       search_btn = page.query_selector('button:has-text("Search")')
   if search_btn:
       search_btn.click()
       page.wait_for_timeout(2000)  # 等待内容加载
   ```

2. **填写表单并提交**
   ```python
   # 填写搜索框
   search_input = page.query_selector('input[name="search"], input[placeholder*="search" i]')
   if search_input:
       search_input.fill('keywords')
       search_input.press('Enter')
       page.wait_for_selector('.results, .items', timeout=5000)
   ```

3. **滚动加载更多内容**
   ```python
   # 多次滚动以加载所有内容
   for _ in range(3):
       page.evaluate('window.scrollBy(0, window.innerHeight)')
       page.wait_for_timeout(1000)
   ```

4. **添加 URL 参数（适用于搜索页）**
   ```python
   # 如果页面是搜索页但没有结果，尝试添加参数
   current_url = page.url
   if '?' not in current_url:
       page.goto(current_url + '?search=&page=1')
       page.wait_for_timeout(2000)
   ```

5. **点击"展开更多"链接**
   ```python
   # 查找并点击展开链接
   expand_links = page.query_selector_all('a:has-text("more"), a:has-text("展开"), button:has-text("show")')
   for link in expand_links[:3]:
       try:
           link.click()
           page.wait_for_timeout(500)
       except:
           pass
   ```

【代码要求】
1. 使用 **playwright.sync_api**（同步模式）
2. 定义 `interact(page)` 函数，执行交互后返回最终 URL
3. 添加适当的等待和错误处理
4. 输出 JSON 格式包含 final_url 和 interactions 记录

【输出格式】
```json
{{
  "final_url": "交互后的页面 URL",
  "interactions": ["点击了搜索按钮", "等待了2秒"],
  "success": true
}}
```

【代码模板】
```python
from playwright.sync_api import sync_playwright
import json

def interact(page) -> str:
    '''执行多步交互，返回最终 URL'''

    interactions = []

    # 示例：检查是否需要点击搜索按钮
    try:
        # 查找可能的搜索按钮
        search_selectors = [
            'button[type="submit"]',
            'button:has-text("Search")',
            'input[type="submit"]',
            'button:has-text("搜索")',
        ]

        search_btn = None
        for selector in search_selectors:
            search_btn = page.query_selector(selector)
            if search_btn:
                interactions.append(f"找到搜索按钮: {{selector}}")
                break

        if search_btn:
            search_btn.click()
            interactions.append("点击了搜索按钮")
            page.wait_for_timeout(2000)  # 等待结果加载
    except Exception as e:
        interactions.append(f"点击搜索按钮失败: {{str(e)}}")

    # 示例：检查是否需要添加 URL 参数
    current_url = page.url
    if '?' not in current_url and 'search' in current_url.lower():
        page.goto(current_url + '?keywords=')
        interactions.append("添加了 URL 参数")
        page.wait_for_timeout(2000)

    return page.url, interactions

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto("{url}", wait_until='domcontentloaded', timeout=30000)

        # 等待页面初始加载
        try:
            page.wait_for_selector('body', timeout=5000)
        except:
            pass

        # 执行交互
        final_url, interactions = interact(page)

        result = {{
            "final_url": final_url,
            "interactions": interactions,
            "success": final_url != page.url  # URL 变化说明可能发生了交互
        }}

        print(json.dumps(result, ensure_ascii=False))

        browser.close()

if __name__ == "__main__":
    main()
```

请只输出完整可执行的 Python 代码，不要有其他说明。
"""


def get_enhanced_sense_prompt(
    url: str,
    user_goal: str,
    html: str,
    user_goal_requires_interaction: bool = False,
) -> str:
    """
    生成增强的 Sense 阶段 Prompt

    新增功能：
    1. 选择器验证
    2. 检测是否需要交互
    3. 分析 DOM 结构

    Args:
        url: 目标站点 URL
        user_goal: 用户需求
        html: HTML 内容
        user_goal_requires_interaction: 用户目标是否需要交互

    Returns:
        增强的 Sense Prompt
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
3. **测试多个选择器**并返回有效的
4. **检测是否需要交互**（如点击搜索按钮）
5. 输出 JSON 格式的分析结果

【输出格式】
```json
{{
  "article_selector": "文章/条目容器的 CSS 选择器",
  "title_selector": "标题的选择器",
  "link_selector": "链接的选择器",
  "valid_selectors": ["选择器1", "选择器2"],  // 实际测试有效的选择器
  "selector_test_results": [
    {{"selector": "a.link", "count": 10, "valid": true}},
    {{"selector": "div.item", "count": 0, "valid": false}}
  ],
  "pagination": {{"type": "next_page|infinite_scroll|load_more|none", "selector": "..."}},
  "requires_interaction": true/false,  // 是否需要交互（如点击搜索按钮）
  "interaction_hints": ["可能需要点击搜索按钮", "可能需要填写表单"],
  "sample_entries": [
    {{"title": "...", "link": "...", "extra": "..."}}
  ],
  "recommendations": ["建议1", "建议2"]
}}
```

【选择器测试要求】
在代码中测试以下常见选择器模式：
- 直接选择器: `a.card-link`, `article h2 a`
- 父子选择器: `div.card-list a`, `ul.items li a`
- 属性选择器: `[href*="/p/"]`, `[class*="title"]`
- 组合选择器: `article.post a[href]`

【交互检测要求】
检查页面是否包含：
- 搜索表单/搜索按钮
- "加载更多"按钮
- 分页链接
- 需要点击才能展开的内容

【代码模板】
```python
from bs4 import BeautifulSoup
import json
import sys

html = '''{html[:5000]}'''

soup = BeautifulSoup(html, 'lxml')

# 测试选择器
test_selectors = [
    # 根据实际页面调整
    'a[href]',
    'article a',
    '[class*="title"]',
    '[href*="/p/"]',
]

selector_results = []
for selector in test_selectors:
    elements = soup.select(selector)
    selector_results.append({{
        "selector": selector,
        "count": len(elements),
        "valid": len(elements) > 0
    }})

# 找出有效的选择器
valid_selectors = [r["selector"] for r in selector_results if r["valid"]]

# 检测是否需要交互
requires_interaction = False
interaction_hints = []

if soup.find('input', type='search') or soup.find('button', string=lambda s: s and 'search' in s.lower()):
    requires_interaction = True
    interaction_hints.append("检测到搜索框或搜索按钮")

if soup.find('a', string=lambda s: s and 'more' in s.lower()):
    requires_interaction = True
    interaction_hints.append("检测到'加载更多'链接")

analysis = {{
    "article_selector": "请根据 HTML 分析",
    "title_selector": "请根据 HTML 分析",
    "link_selector": "请根据 HTML 分析",
    "valid_selectors": valid_selectors,
    "selector_test_results": selector_results,
    "pagination": {{"type": "none", "selector": ""}},
    "requires_interaction": requires_interaction,
    "interaction_hints": interaction_hints,
    "sample_entries": [],
    "recommendations": []
}}

print(json.dumps(analysis, ensure_ascii=False, indent=2))
```

请只输出 Python 代码，不要有其他说明。
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
# 导出（新增深度验证函数）
# ============================================================================

__all__ = [
    # 基础函数
    "extract_python_code",
    # Sense 节点
    "get_sense_dom_analysis_prompt",
    "get_enhanced_sense_prompt",  # 新增：增强的 Sense Prompt（带选择器验证）
    # Plan 节点
    "get_code_generation_prompt",
    "get_code_generation_prompt_with_memory",  # 新增：带记忆的代码生成
    # Interact 节点（新增）
    "get_interact_prompt",
    # SOOAL 节点
    "get_code_diagnose_prompt",
    "get_code_repair_prompt",
    # Verify 节点
    "get_quality_evaluation_prompt",
    "get_enhanced_quality_evaluation_prompt",
    "get_deep_validation_prompt",
    "extract_validation_rules",
    # Reflexion 节点（新增）
    "get_reflection_prompt",
    # Report 节点
    "get_report_generation_prompt",
    # 常量（向后兼容）
    "AVAILABLE_TOOLS",
]


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


# ============================================================================
# Reflexion 节点 Prompts - 反思和记忆增强
# ============================================================================

def get_reflection_prompt(
    url: str,
    user_goal: str,
    execution_result: dict,
    sample_data: list,
    generated_code: str,
    previous_reflections: list = None,
) -> str:
    """
    生成 Reflexion 阶段的反思 Prompt

    基于 Reflexion 论文 (arXiv:2303.11366) 的 Act-Reflect-Remember 循环，
    让 LLM 深度分析失败原因并生成结构化反思。

    Args:
        url: 目标站点 URL
        user_goal: 用户需求
        execution_result: 执行结果
        sample_data: 提取的数据样本
        generated_code: 生成的代码
        previous_reflections: 历史反思记录

    Returns:
        反思 Prompt
    """
    import json

    # 分析执行结果
    success = execution_result.get("success", False)
    error = execution_result.get("error", "")
    stderr = execution_result.get("stderr", "")
    data_count = len(sample_data)

    # 构建历史反思文本
    previous_reflections_text = ""
    if previous_reflections:
        previous_reflections_text = "\n## 历史反思（最近3次）\n"
        for i, refl in enumerate(previous_reflections[-3:], 1):
            previous_reflections_text += f"{i}. {refl}\n"
    else:
        previous_reflections_text = "\n## 历史反思\n（无）\n"

    # 样本数据预览
    sample_preview = json.dumps(sample_data[:3], ensure_ascii=False) if sample_data else "[]"

    return f"""你是一个Web爬虫专家，正在分析一次失败的爬虫尝试。

## 任务信息
- URL: {url}
- 目标: {user_goal}

## 执行结果
- 执行成功: {success}
- 提取数据量: {data_count}条
- 错误信息: {error[:500] if error else "无"}
- 标准错误输出: {stderr[:500] if stderr else "无"}

## 生成的代码（前2000字符）
```python
{generated_code[:2000]}
```

## 提取的数据样本
```json
{sample_preview}
```

{previous_reflections_text}

## 请进行深度反思

分析这次失败的原因，并按以下格式输出：

### 1. 失败类型
从以下类型中选择一个：
- **selector_error**: CSS选择器不匹配元素
- **js_rendering**: JavaScript内容未正确渲染
- **timeout**: 页面加载或操作超时
- **rate_limit**: 被速率限制或封禁
- **empty_result**: 执行成功但无数据提取
- **syntax_error**: 代码语法错误
- **api_error**: Playwright API使用错误
- **blocked**: 被反爬虫系统阻止
- **other**: 其他原因

### 2. 根本原因
具体分析为什么失败，不要泛泛而谈。

### 3. 下次应该尝试的方法
给出具体的、可操作的修复建议。

### 4. 避免重复
说明下次应该避免什么，确保不重复相同的错误。

请以JSON格式输出：
```json
{{
    "failure_type": "selector_error",
    "root_cause": "具体的根本原因分析...",
    "suggested_fix": "具体的修复建议...",
    "avoid_repeat": "下次应该避免..."
}}
```

**重要**: 如果这是第2次或更多次尝试，请确保你的分析与历史反思不同，找到新的角度！
"""


def get_code_generation_prompt_with_memory(
    url: str,
    user_goal: str,
    dom_analysis: str,
    failure_history: list = None,
    reflection_memory: list = None,
    successful_patterns: list = None,
    iteration: int = 0,
) -> str:
    """
    生成带历史记忆的代码生成 Prompt

    在原有代码生成 Prompt 基础上，加入：
    1. 失败历史 - 避免重复错误
    2. 反思总结 - 利用经验改进
    3. 成功模式 - 参考有效方法
    4. 迭代次数 - 明确当前进度

    Args:
        url: 目标站点 URL
        user_goal: 用户需求
        dom_analysis: DOM 分析结果
        failure_history: 失败历史记录
        reflection_memory: 反思记忆
        successful_patterns: 成功模式
        iteration: 当前迭代次数

    Returns:
        代码生成 Prompt
    """
    import json

    # 检测是否需要代码片段提取
    needs_code_extraction = _detect_code_snippet_need(user_goal)

    code_extraction_guide = ""
    if needs_code_extraction:
        code_extraction_guide = """

【代码片段提取（SVG/HTML）】
如果用户需求包含"SVG代码"、"HTML代码片段"、"富文本"、"图标"等关键词：
- 使用 `page.inner_html()` 或 `element.inner_html()` 提取 HTML/SVG 代码
- 使用 `page.evaluate("el => el.outerHTML")` 获取包含元素自身的完整代码
- 等待 JS 动态内容加载完成: `page.wait_for_selector('svg', timeout=15000)`

提取示例：
```python
# 提取 SVG 代码
svgs = page.locator("svg").all()
for svg in svgs[:5]:  # 限量采样
    svg_code = svg.evaluate("el => el.outerHTML")
    results.append({{"svg_code": svg_code, "type": "svg"}})

# 提取 HTML 片段
html_blocks = page.locator(".rich-text, .description, [data-html]").all()
for block in html_blocks[:5]:
    html_snippet = block.inner_html()
    results.append({{"html_snippet": html_snippet, "type": "html"}})
```
"""

    # 构建历史经验部分
    memory_section = ""

    if failure_history:
        memory_section += "\n## ⚠️ 失败历史（请避免重复）\n"
        for i, fail in enumerate(failure_history[-3:], 1):
            memory_section += f"""
### 尝试 #{i}
- 失败类型: {fail.get('failure_type', 'unknown')}
- 原因: {fail.get('root_cause', 'unknown')[:200]}
- 数据量: {fail.get('data_count', 0)}条
- 建议: {fail.get('suggested_fix', '无')[:200]}
"""

    if reflection_memory:
        memory_section += "\n## 📝 反思总结\n"
        for i, refl in enumerate(reflection_memory[-3:], 1):
            memory_section += f"{i}. {refl[:300]}\n"

    if successful_patterns:
        memory_section += f"\n## ✅ 成功模式（可以参考）\n"
        for pattern in successful_patterns:
            memory_section += f"- {pattern}\n"

    if iteration > 0:
        memory_section += f"\n---\n\n**⚠️ 这是第 {iteration + 1} 次尝试。请确保不重复之前的错误！**\n"

    return f"""你是一个爬虫代码生成专家。请生成完整的爬虫代码。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}

{memory_section}

【DOM 分析结果】
{dom_analysis}
{code_extraction_guide}

【代码要求】
1. 使用 **playwright.sync_api**（同步模式，不是 async！）
2. 正确的 API 调用：
   - `browser = p.chromium.launch(headless=True)`
   - `page = browser.new_page()`  ← 正确！
   - 不要使用 `browser.new_context()` ← 错误！
3. 提取的数据以 JSON 格式输出到 stdout
4. **确保不重复之前的错误**：如果失败历史提到选择器问题，请使用不同的选择器策略

【常见错误避免】
| 错误写法 | 正确写法 |
|---------|---------|
| `browser.new_context()` | `browser.new_page()` |
| `await page.goto()` | `page.goto()` (同步模式) |
| `async def scrape()` | `def scrape()` (同步函数) |
| 忘记 `import json` | 必须在顶部导入 |
| 硬编码单一选择器 | 准备备选选择器 |

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

        # 等待内容加载 - 使用多种策略确保成功
        try:
            page.wait_for_selector('body', timeout=10000)
        except:
            pass

        results = []

        # TODO: 根据 DOM 分析结果实现数据提取
        # 参考: {dom_analysis[:500]}

        # 如果第一次尝试没获取到数据，尝试备选方法
        if not results:
            # TODO: 实现备选提取策略
            pass

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
# Phase 1: Validation Node Prompts
# ============================================================================

def get_validation_prompt(
    url: str,
    user_goal: str,
    failed_selectors: list,
    html: str,
) -> str:
    """
    生成选择器验证 Prompt

    当初始选择器验证失败时，生成替代选择器建议。
    """
    failed_text = "\n".join(f"- {s}" for s in failed_selectors) if failed_selectors else "无"

    return f"""你是一个网页结构分析专家。请生成 Python 代码寻找替代的 CSS 选择器。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}

【验证失败的选择器】
{failed_text}

【HTML 内容（前 10000 字符）】
{html[:10000]}

【代码要求】
生成一个完整的 Python 脚本，用于：
1. 分析 HTML 结构
2. 生成备选选择器
3. 测试这些选择器
4. 返回有效的选择器列表

【输出格式】
```json
{{
  "alternative_selectors": ["选择器1", "选择器2", "选择器3"],
  "test_results": [
    {{"selector": "...", "count": 10, "valid": true}},
    {{"selector": "...", "count": 0, "valid": false}}
  ],
  "recommendations": ["建议1", "建议2"]
}}
```

请只输出 Python 代码，不要有其他说明。
"""


def get_verify_plan_prompt(
    url: str,
    user_goal: str,
    code: str,
    validation_report: dict,
) -> str:
    """
    生成代码计划验证 Prompt

    在实际执行前验证代码的正确性。
    """
    import json
    validation_text = json.dumps(validation_report, ensure_ascii=False) if validation_report else "{}"

    return f"""请验证以下爬虫代码的正确性。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}

【验证报告】
{validation_text}

【生成的代码】
```python
{code[:5000]}
```

【请检查】
1. 语法错误
2. 缺失的导入
3. API 使用正确性
4. 错误处理
5. 资源释放（browser.close()）

请输出 JSON 格式的验证结果。
"""


# ============================================================================
# Phase 2: Stealth-First Default Prompts
# ============================================================================

def get_stealth_code_generation_prompt(
    url: str,
    user_goal: str,
    dom_analysis: str,
    stealth_level: str = "medium",
) -> str:
    """
    生成带隐身配置的代码生成 Prompt

    在代码生成时自动包含隐身浏览器配置。
    """
    # 检测是否需要代码片段提取
    needs_code_extraction = _detect_code_snippet_need(user_goal)

    code_extraction_guide = ""
    if needs_code_extraction:
        code_extraction_guide = """

【代码片段提取（SVG/HTML）】
如果用户需求包含"SVG代码"、"HTML代码片段"、"富文本"、"图标"等关键词：
- 使用 `page.inner_html()` 或 `element.inner_html()` 提取 HTML/SVG 代码
- 使用 `page.evaluate("el => el.outerHTML")` 获取包含元素自身的完整代码
- 等待 JS 动态内容加载完成: `page.wait_for_selector('svg', timeout=15000)`
"""

    # 根据隐身等级获取配置
    stealth_configs = {
        "none": {
            "launch_args": "[]",
            "delay": "0",
            "stealth_script": "# 无隐身脚本",
        },
        "low": {
            "launch_args": '["--disable-blink-features=AutomationControlled"]',
            "delay": "random.uniform(1, 2)",
            "stealth_script": """
        # 基础隐身脚本
        page.add_init_script('''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        ''')""",
        },
        "medium": {
            "launch_args": '["--disable-blink-features=AutomationControlled", "--no-sandbox"]',
            "delay": "random.uniform(2, 4)",
            "stealth_script": """
        # 隐身脚本
        page.add_init_script('''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}, loadTimes: function() {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]};
        ''')""",
        },
        "high": {
            "launch_args": '["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security"]',
            "delay": "random.uniform(3, 6)",
            "stealth_script": """
        # 高级隐身脚本
        page.add_init_script('''
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}};
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]};
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']};
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({{state: Notification.permission}}) :
                    originalQuery(parameters)
            );
        ''')""",
        },
    }

    config = stealth_configs.get(stealth_level, stealth_configs["medium"])

    return f"""你是一个爬虫代码生成专家。请生成完整的爬虫代码。

【任务目标】
站点 URL: {url}
用户需求: {user_goal}

【⚠️ 隐身配置】
隐身等级: {stealth_level}
此网站检测到反爬虫措施，必须使用隐身浏览器配置！

【DOM 分析结果】
{dom_analysis}
{code_extraction_guide}

【代码要求】
1. 使用 **playwright.sync_api**（同步模式）
2. **必须使用以下隐身配置**：
   - launch_args: [{config["launch_args"]}]
   - 随机延迟: {config["delay"]} 秒
{config["stealth_script"]}
3. 正确的 API 调用：`page = browser.new_page()`
4. 提取的数据以 JSON 格式输出到 stdout

【常见错误避免】
| 错误写法 | 正确写法 |
|---------|---------|
| `browser.new_context()` | `browser.new_page()` |
| `await page.goto()` | `page.goto()` (同步模式) |
| 忘记 `browser.close()` | 必须关闭浏览器释放资源 |

【输出格式】
```json
{{
  "results": [{{"field1": "value1", ...}}],
  "metadata": {{"total_pages": 1, "sample_size": N}}
}}
```

请只输出完整可执行的 Python 代码，不要有其他说明。
"""


# ============================================================================
# Phase 4: Deep Reflection Prompts
# ============================================================================

def get_deep_reflection_prompt(
    url: str,
    user_goal: str,
    execution_result: dict,
    sample_data: list,
    generated_code: str,
    previous_reflections: list = None,
    website_type: str = "unknown",
    anti_bot_level: str = "none",
    website_features: list = None,
    partial_success: dict = None,
) -> str:
    """
    生成深度反思 Prompt

    Phase 4 增强：包含网站类型、反爬虫等级、特征、部分成功数据
    """
    import json

    # 分析执行结果
    success = execution_result.get("success", False)
    error = execution_result.get("error", "")
    stderr = execution_result.get("stderr", "")
    data_count = len(sample_data)

    # 构建历史反思文本
    previous_reflections_text = ""
    if previous_reflections:
        previous_reflections_text = "\n## 历史反思（最近3次）\n"
        for i, refl in enumerate(previous_reflections[-3:], 1):
            previous_reflections_text += f"{i}. {refl}\n"
    else:
        previous_reflections_text = "\n## 历史反思\n（无）\n"

    # 样本数据预览
    sample_preview = json.dumps(sample_data[:3], ensure_ascii=False) if sample_data else "[]"

    # 网站特征文本
    features_text = ", ".join(website_features) if website_features else "无"

    # 部分成功数据文本
    partial_text = ""
    if partial_success:
        partial_text = f"""
## 部分成功分析
- 是否部分成功: {partial_success.get('partial_success', False)}
- 成功率: {partial_success.get('success_rate', 0):.1%}
- 优势: {', '.join(partial_success.get('strengths', []))}
- 问题: {', '.join(partial_success.get('issues', []))}
"""

    return f"""你是一个Web爬虫专家，正在进行深度反思分析。

## 任务信息
- URL: {url}
- 目标: {user_goal}

## 网站分析（Phase 4 增强）
- 网站类型: {website_type}
- 反爬虫等级: {anti_bot_level}
- 检测到的特征: {features_text}
{partial_text}

## 执行结果
- 执行成功: {success}
- 提取数据量: {data_count}条
- 错误信息: {error[:500] if error else "无"}
- 标准错误输出: {stderr[:500] if stderr else "无"}

## 生成的代码（前2000字符）
```python
{generated_code[:2000]}
```

## 提取的数据样本
```json
{sample_preview}
```

{previous_reflections_text}

## 请进行深度反思

基于网站类型（{website_type}）和反爬虫等级（{anti_bot_level}），分析这次失败的原因。

### 1. 失败类型
从以下类型中选择一个：
- **selector_error**: CSS选择器不匹配元素
- **js_rendering**: JavaScript内容未正确渲染
- **timeout**: 页面加载或操作超时
- **rate_limit**: 被速率限制或封禁
- **empty_result**: 执行成功但无数据提取
- **syntax_error**: 代码语法错误
- **api_error**: Playwright API使用错误
- **blocked**: 被反爬虫系统阻止
- **anti_bot**: 反爬虫系统（CAPTCHA、Cloudflare等）
- **other**: 其他原因

### 2. 根本原因
结合网站类型和反爬虫等级，分析具体的根本原因。

### 3. 下次应该尝试的方法
给出具体的、可操作的修复建议，考虑：
- 对于 {website_type} 类型的网站
- 对于 {anti_bot_level} 级别的反爬虫
- 基于部分成功数据中的优势/问题

### 4. 避免重复
说明下次应该避免什么，确保不重复相同的错误。

请以JSON格式输出：
```json
{{
    "failure_type": "selector_error",
    "root_cause": "具体的根本原因分析...",
    "suggested_fix": "具体的修复建议...",
    "avoid_repeat": "下次应该避免..."
}}
```

**重要**: 如果这是第2次或更多次尝试，请确保你的分析与历史反思不同，找到新的角度！
"""


# ============================================================================
# Update __all__ exports
# ============================================================================

__all__ = [
    # 基础函数
    "extract_python_code",
    # Sense 节点
    "get_sense_dom_analysis_prompt",
    "get_enhanced_sense_prompt",
    # Plan 节点
    "get_code_generation_prompt",
    "get_code_generation_prompt_with_memory",
    # Interact 节点
    "get_interact_prompt",
    # SOOAL 节点
    "get_code_diagnose_prompt",
    "get_code_repair_prompt",
    # Verify 节点
    "get_quality_evaluation_prompt",
    "get_enhanced_quality_evaluation_prompt",
    "get_deep_validation_prompt",
    "extract_validation_rules",
    # Reflexion 节点
    "get_reflection_prompt",
    "get_deep_reflection_prompt",  # Phase 4
    # Report 节点
    "get_report_generation_prompt",
    # Phase 1: Validation
    "get_validation_prompt",
    "get_verify_plan_prompt",
    # Phase 2: Stealth
    "get_stealth_code_generation_prompt",
    # 常量（向后兼容）
    "AVAILABLE_TOOLS",
]
