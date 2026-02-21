"""
Prompts - Prompt 模板

LLM 代码生成和修复使用的 Prompt 模板。
"""

# 代码生成 Prompt
CODE_GENERATION_PROMPT = """
你是一个爬虫专家。请根据以下信息生成完整的 Playwright 爬虫代码。

站点 URL: {site_url}
用户需求: {user_goal}

站点上下文:
- 检测到的特征: {detected_features}
- 页面 HTML 大小: {html_size} bytes

要求:
1. 生成完整的、可直接运行的 Python 代码
2. 使用 playwright.async_api
3. 实现错误处理和重试逻辑
4. 提取的数据以 JSON 格式输出到 stdout
5. 代码必须包含 async def scrape() 函数和 main() 入口

代码模板:
```python
from playwright.async_api import async_playwright
import json
import asyncio

async def scrape(url: str) -> dict:
    '''爬取主函数'''
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 访问页面
        await page.goto(url, wait_until='domcontentloaded')

        # 等待内容加载
        # TODO: 根据页面特征添加适当的等待逻辑

        # 提取数据
        results = []

        # TODO: 根据用户需求实现数据提取逻辑
        # 用户需求: {user_goal}

        await browser.close()
        return {{"results": results}

def main():
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "{site_url}"
    result = asyncio.run(scrape(url))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

请生成完整代码，只输出代码，不要有其他说明:
"""

# 代码修复 Prompt
CODE_REPAIR_PROMPT = """
你是一个代码修复专家。请修复以下爬虫代码中的错误。

原始代码:
```python
{original_code}
```

错误信息:
```
{error_logs}
```

修复要求:
1. 分析错误原因
2. 修复代码中的问题
3. 添加更好的错误处理
4. 只输出修复后的完整代码

请生成修复后的代码:
"""

# 报告生成 Prompt
REPORT_GENERATION_PROMPT = """
请生成网站侦察报告的 Markdown 格式。

站点信息:
- URL: {site_url}
- 用户需求: {user_goal}

侦察结果:
- 估算总页数: {total_pages}
- 采样数量: {sample_count}
- 高质量样本: {high_quality_count}
- 平均质量分数: {quality_score}

样本数据:
{sample_data_preview}

请生成以下格式的 Markdown 报告:
```markdown
# 网站数据侦察报告

## 站点信息
- URL: ...
- 用户需求: ...

## 侦察总结
- 总页面估算: ...
- 高价值比例: ...
- 平均数据质量: ...

## 真实样本预览
1. ...
2. ...

## 推荐爬取路径
1. ...
2. ...

## 可爬性评估
- 反爬等级: ...
- 推荐策略: ...
```

请生成报告:
"""

# 质量评估 Prompt
QUALITY_EVALUATION_PROMPT = """
请评估以下提取数据的质量。

用户需求: {user_goal}

提取的数据:
{extracted_data}

请从以下维度评估 (0-1 分):
1. relevance - 与用户需求的相关性
2. completeness - 数据完整性
3. accuracy - 数据准确性

请以 JSON 格式输出:
```json
{{
  "relevance": 0.9,
  "completeness": 0.8,
  "accuracy": 0.95,
  "overall_score": 0.88,
  "issues": ["字段X缺失"],
  "suggestions": ["建议..."]
}}
```
"""
