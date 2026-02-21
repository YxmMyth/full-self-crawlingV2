"""
Prompts - Prompt 模板

LLM 代码生成和修复使用的 Prompt 模板。
适配 LangGraph 状态机的各节点。
"""

# ============================================================================
# Sense 节点 Prompts
# ============================================================================

# Sense 节点主要使用 BrowserTool 直接探测，不需要专门的 LLM prompt
# 但可以添加分析 prompt 用于特征深度分析

SENSE_ANALYSIS_PROMPT = """
请分析以下站点信息，提取关键特征。

站点 URL: {site_url}
用户需求: {user_goal}

站点上下文:
{site_context}

HTML 快照 (前 2000 字符):
{html_snapshot}

请分析并输出 JSON:
```json
{{
  "detected_features": ["列表页", "分页", "图片预览"],
  "estimated_data_type": "产品列表",
  "anti_crawl_level": "low",
  "recommendations": ["使用 selector 等待", "注意反爬限制"]
}}
```
"""

# ============================================================================
# Plan 节点 Prompts
# ============================================================================

CODE_GENERATION_PROMPT = """
你是一个爬虫代码生成专家。请根据以下信息生成完整的采样代码。

【任务目标】
站点 URL: {site_url}
用户需求: {user_goal}

【站点上下文】
- 检测到的特征: {detected_features}
- 页面 HTML 大小: {html_size} bytes

【代码要求】
1. 生成完整的、可直接运行的 Python 代码
2. 使用 playwright.async_api 进行浏览器自动化
3. 实现健壮的错误处理和重试逻辑
4. 提取的数据以 JSON 格式输出到 stdout
5. 代码必须包含 async def scrape() 函数和 main() 入口

【输出格式】
输出的 JSON 必须包含:
- results: 提取的数据列表
- metadata: 元信息（如总页数、下一页链接等）

```json
{{
  "results": [{{"field1": "value1", ...}}],
  "metadata": {{"total_pages": 10, "has_next": true}}
}}
```

【代码模板参考】
```python
from playwright.async_api import async_playwright
import json
import asyncio
from typing import Dict, Any

async def scrape(url: str) -> Dict[str, Any]:
    '''爬取主函数 - 采样目标数据'''
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 访问页面
        await page.goto(url, wait_until='domcontentloaded', timeout=30000)

        # 等待内容加载 - 根据站点特征调整
        try:
            await page.wait_for_selector('body', timeout=10000)
        except:
            pass

        # 提取数据 - 根据用户需求实现
        results = []

        # TODO: 根据 "{user_goal}" 实现数据提取逻辑
        # 提示: 检测到 {detected_features}

        # 示例：提取列表项
        items = await page.query_selector_all('.item-selector')
        for item in items:
            results.append({{
                "title": await item.query_selector('.title')?.inner_text() or "",
                # 提取更多字段...
            }})

        await browser.close()

        return {{
            "results": results,
            "metadata": {{
                "total_pages": 1,
                "sample_size": len(results)
            }}
        }}

def main():
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "{site_url}"
    result = asyncio.run(scrape(url))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

请只输出代码，不要有其他说明。
"""

# ============================================================================
# Verify 节点 Prompts
# ============================================================================

QUALITY_EVALUATION_PROMPT = """
请评估以下采样数据的质量，判断是否满足用户需求。

【用户需求】
{user_goal}

【提取的数据】
{extracted_data}

【评估维度】
请从以下维度评估 (0-1 分):
1. relevance - 与用户需求的相关性
2. completeness - 数据完整性（必需字段是否齐全）
3. accuracy - 数据准确性（格式是否正确、是否有异常值）
4. overall_score - 综合得分 (relevance * 0.4 + completeness * 0.3 + accuracy * 0.3)

【输出格式】
```json
{{
  "relevance": 0.9,
  "completeness": 0.8,
  "accuracy": 0.95,
  "overall_score": 0.88,
  "issues": ["字段X缺失", "部分记录缺少标题"],
  "suggestions": ["建议增加字段提取逻辑", "建议添加数据验证"]
}}
```
"""

# ============================================================================
# Report 节点 Prompts
# ============================================================================

REPORT_GENERATION_PROMPT = """
请生成网站侦察报告的 Markdown 格式。

【站点信息】
- URL: {site_url}
- 用户需求: {user_goal}

【站点上下文】
{site_info}

【样本数据】（前 5 条）
{sample_data}

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
- 样本质量分数: 0.85/1.0
- 数据结构化程度: 高

## 站点特征分析
- 页面类型: 列表页
- 分页方式: 传统分页
- 反爬等级: 低
- 主要特征: [特征列表]

## 真实样本预览
1. {{样本1}}
2. {{样本2}}
...

## 可爬性评估
- 反爬等级: 低/中/高
- 技术难度: 简单/中等/复杂
- 推荐策略: [具体策略建议]

## 风险提示
- [潜在风险列表]
```

请生成报告：
"""

# ============================================================================
# SOOAL 节点 Prompts
# ============================================================================

CODE_REPAIR_PROMPT = """
你是一个代码修复专家。请分析并修复以下爬虫代码。

【原始代码】
```python
{original_code}
```

【执行错误】
```
{error_logs}
```

【迭代信息】
- 当前迭代次数: {iteration}
- 最大迭代次数: 5

【修复要求】
1. 分析错误的根本原因
2. 修复代码中的问题
3. 添加或改进错误处理逻辑
4. 确保输出格式符合规范（JSON 格式，包含 results 和 metadata）
5. 只输出修复后的完整代码

【常见问题排查】
- 元素未找到: 检查 selector 是否正确，增加等待时间
- 超时: 增加显式等待，使用 wait_for_selector
- 数据为空: 检查提取逻辑是否匹配页面结构
- JSON 格式错误: 确保输出的是有效的 JSON

请生成修复后的代码：
"""

# ============================================================================
# 工具使用 Prompts（给 LLM 生成代码时的工具说明）
# ============================================================================

AVAILABLE_TOOLS = """
## 可用的工具和库

### Browser (Playwright)
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url)
    await page.wait_for_selector(selector)
    content = await page.inner_text(selector)
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
output = {
    "results": data_list,
    "metadata": {"total": len(data_list)}
}
print(json.dumps(output, ensure_ascii=False))
```
"""
