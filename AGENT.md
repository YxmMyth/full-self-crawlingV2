# Full-Self-Crawling - Hybrid Recon Agent

**Version**: v3.0.0 (Hybrid Architecture)
**Date**: 2026-02-21
**Scope**: Single-site reconnaissance agent with code generation

---

## Table of Contents

1. [Agent Overview](#1-agent-overview)
2. [Hybrid Architecture](#2-hybrid-architecture)
3. [LangGraph State Machine](#3-langgraph-state-machine)
4. [Tool Chain](#4-tool-chain)
5. [Code Generation & Execution](#5-code-generation--execution)
6. [Interface Design](#6-interface-design)
7. [Long-term Memory](#7-long-term-memory)
8. [Deployment](#8-deployment)

---

## 1. Agent Overview

### 1.1 Positioning

**SiteAgent - 混合架构侦察智能体**

```
输入：url + user_goal
  ↓
LLM 分析 → 生成爬虫代码 → 沙箱执行 → 输出报告 + 样本
```

**核心特性**：

| 特性 | 说明 |
|------|------|
| **代码生成** | LLM 生成完整爬虫代码，而非调用预定义组件 |
| **状态机驱动** | LangGraph 状态机控制执行流程 |
| **工具预置** | Browser、Firecrawl、解析工具供 LLM 使用 |
| **沙箱执行** | 生成的代码在隔离环境中运行 |
| **自修复** | SOOAL 循环：失败 → 分析错误 → 修改代码 → 重跑 |
| **记忆积累** | RAG 记忆库存储历史 insights |

### 1.2 真实案例参考

| 产品 | 架构特点 |
|------|----------|
| **Kadoa** | AI Recon Mode + 置信度评分 + 代表性样本 |
| **Anthropic Computer Use** | 视觉 + 鼠标点击 + LangGraph 状态机 |
| **Bright Data** | 代理集成 + 反爬评估 |
| **OpenDevin** | CodeAct：生成代码 → 执行 → 看日志 → 修复 |

### 1.3 与传统架构对比

| | 传统（预定义组件） | Hybrid（新） |
|---|------------------|--------------|
| 爬取逻辑 | 开发者写组件 | **LLM 生成代码** |
| 适配新网站 | 等开发者更新 | **LLM 自己适配** |
| 失败处理 | 修改配置参数 | **修改代码重跑** |
| 扩展性 | 受限于组件数量 | **无限（LLM 写新逻辑）** |

---

## 2. Hybrid Architecture

### 2.1 五层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Hybrid Recon 架构                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 1: Orchestrator 调度                             │   │
│  │  - 任务路由                                              │   │
│  │  - Agent 管理                                           │   │
│  │  - 结果呈现                                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                │
│                              ▼                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 2: LangGraph 状态机                             │   │
│  │  Sense → Plan → Act → Verify → Report                   │   │
│  │  - 状态持久化                                           │   │
│  │  - 循环控制                                             │   │
│  │  - 条件边（失败→SOOAL）                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                │
│                              ▼                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 3: 工具链 (Tool-Use)                            │   │
│  │  - Browser（Playwright + Computer Use）                  │   │
│  │  - Firecrawl API                                        │   │
│  │  - 解析工具（BeautifulSoup、lxml）                      │   │
│  │  - MCP 标准工具                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                │
│                              ▼                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 4: 代码生成 + 沙箱执行                          │   │
│  │  - LLM 生成完整爬虫代码                                  │   │
│  │  - E2B/Browserbase 沙箱执行                             │   │
│  │  - 截图 + 日志收集                                       │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                │
│                              ▼                                │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Layer 5: 长期记忆 + 报告                               │   │
│  │  - RAG 记忆库                                           │   │
│  │  - JSON 报告输出                                         │   │
│  │  - 历史 insights                                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 执行流程

```
用户需求 → Orchestrator → SiteAgent
                              │
                              ▼
                    ┌─────────────────┐
                    │  Sense 节点     │
                    │  - 快速探测站点  │
                    │  - 收集上下文    │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Plan 节点      │
                    │  - LLM 分析需求  │
                    │  - 生成爬虫代码  │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Act 节点       │
                    │  - 沙箱执行代码  │
                    │  - 收集结果      │
                    └─────────────────┘
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
              成功                  失败
                    │                   │
                    ▼                   ▼
            ┌───────────┐      ┌─────────────┐
            │ Verify节点 │      │  SOOAL 循环 │
            │  质量打分  │      │  分析错误   │
            └───────────┘      │  修改代码   │
                    │         │  重跑      │
                    ▼         └─────────────┘
            ┌───────────┐            │
            │ Report节点│◄───────────┘
            │ 输出报告  │
            └───────────┘
```

---

## 3. LangGraph State Machine

### 3.1 状态定义

```python
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph

class ReconState(TypedDict):
    """侦察任务状态"""
    # 输入
    site_url: str
    user_goal: str

    # Sense
    site_context: Optional[Dict[str, Any]]     # 站点上下文
    detected_features: Optional[List[str]]     # 检测到的特征

    # Plan
    generated_code: Optional[str]              # LLM 生成的代码
    plan_reasoning: Optional[str]             # 规划推理

    # Act
    execution_result: Optional[Dict[str, Any]] # 执行结果
    execution_logs: Optional[List[str]]       # 执行日志
    screenshots: Optional[List[str]]          # 截图

    # Verify
    quality_score: Optional[float]            # 质量分数
    sample_data: Optional[List[Dict]]         # 样本数据

    # Report
    final_report: Optional[Dict[str, Any]]    # 最终报告

    # SOOAL
    sool_iteration: int                       # SOOAL 迭代次数
    last_error: Optional[str]                 # 最后的错误
```

### 3.2 状态机图

```python
from langgraph.graph import StateGraph, END

graph = StateGraph(ReconState)

# 添加节点
graph.add_node("sense", sense_node)
graph.add_node("plan", plan_node)
graph.add_node("act", act_node)
graph.add_node("verify", verify_node)
graph.add_node("report", report_node)
graph.add_node("sool", soal_node)  # SOOAL 修复节点

# 添加边（正常流程）
graph.add_edge("sense", "plan")
graph.add_edge("plan", "act")

# 条件边：act → verify 或 act → sool
graph.add_conditional_edges(
    "act",
    should_run_sool,
    {
        "sool": "sool",
        "verify": "verify"
    }
)

# 条件边：verify → report 或 verify → plan（重试）
graph.add_conditional_edges(
    "verify",
    should_retry,
    {
        "retry": "plan",
        "report": "report"
    }
)

# SOOAL 循环
graph.add_edge("sool", "act")

graph.add_edge("report", END)
```

### 3.3 节点实现示例

```python
async def sense_node(state: ReconState) -> ReconState:
    """Sense 节点：快速探测站点"""
    from tools import browser_tool

    # 访问首页，获取上下文
    context = await browser_tool.browse(state["site_url"])

    # 检测页面特征
    features = detect_page_features(context)

    state["site_context"] = context
    state["detected_features"] = features
    return state

async def plan_node(state: ReconState) -> ReconState:
    """Plan 节点：LLM 生成爬虫代码"""
    from prompts import CODE_GENERATION_PROMPT

    # 构建 prompt
    prompt = CODE_GENERATION_PROMPT.format(
        site_url=state["site_url"],
        user_goal=state["user_goal"],
        site_context=state["site_context"],
        detected_features=state["detected_features"]
    )

    # LLM 生成代码
    code = await llm_generate(prompt)

    state["generated_code"] = code
    state["plan_reasoning"] = "根据站点特征生成定制爬虫"
    return state

async def act_node(state: ReconState) -> ReconState:
    """Act 节点：沙箱执行代码"""
    from sandbox import execute_in_sandbox

    # 在沙箱中执行
    result = await execute_in_sandbox(
        code=state["generated_code"],
        timeout=300
    )

    state["execution_result"] = result
    state["execution_logs"] = result.get("logs", [])
    state["screenshots"] = result.get("screenshots", [])
    return state
```

---

## 4. Tool Chain

### 4.1 Browser 工具

```python
# src/agent/tools/browser.py

from playwright.async_api import async_playwright
from typing import Dict, Any, Optional

class BrowserTool:
    """Playwright 浏览器工具"""

    async def browse(
        self,
        url: str,
        wait_for: Optional[str] = None,
        screenshot: bool = False,
    ) -> Dict[str, Any]:
        """访问页面并返回信息"""
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.goto(url)

            if wait_for:
                await page.wait_for_selector(wait_for)

            # 获取内容
            html = await page.content()
            url = page.url

            # 截图
            screenshot_data = None
            if screenshot:
                screenshot_data = await page.screenshot()

            await browser.close()

            return {
                "html": html,
                "url": url,
                "screenshot": screenshot_data,
            }

    async def detect_features(self, html: str) -> List[str]:
        """检测页面特征"""
        features = []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        # 检测表格
        if soup.find('table'):
            features.append("table")

        # 检测 JSON-LD
        if soup.find('script', type='application/ld+json'):
            features.append("json-ld")

        # 检测图片
        if soup.find_all('img'):
            features.append("images")

        # 检测分页
        if soup.find('a', class_=re.compile(r'pag|next')):
            features.append("pagination")

        return features
```

### 4.2 Firecrawl 工具

```python
# src/agent/tools/firecrawl.py

import httpx

class FirecrawlTool:
    """Firecrawl API 工具"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.firecrawl.dev/v0"

    async def scrape(self, url: str) -> Dict[str, Any]:
        """快速获取页面内容（Markdown + 结构化）"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/scrape",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"url": url}
            )
            return response.json()

    async def map(self, url: str, limit: int = 100) -> List[str]:
        """映射站点结构"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/map",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"url": url, "limit": limit}
            )
            data = response.json()
            return data.get("links", [])
```

### 4.3 解析工具

```python
# src/agent/tools/parser.py

from bs4 import BeautifulSoup
import lxml
import json

class ParserTool:
    """HTML 解析工具"""

    def extract_text(self, html: str) -> str:
        """提取纯文本"""
        soup = BeautifulSoup(html, 'lxml')
        return soup.get_text(separator='\n', strip=True)

    def extract_table(self, html: str) -> List[Dict]:
        """提取表格数据"""
        soup = BeautifulSoup(html, 'lxml')
        tables = []

        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                rows.append(cells)
            tables.append(rows)

        return tables

    def extract_json_ld(self, html: str) -> List[Dict]:
        """提取 JSON-LD 数据"""
        soup = BeautifulSoup(html, 'lxml')
        scripts = soup.find_all('script', type='application/ld+json')

        data = []
        for script in scripts:
            try:
                data.append(json.loads(script.string))
            except:
                pass

        return data
```

---

## 5. Code Generation & Execution

### 5.1 Prompt 模板

```python
# src/agent/prompts.py

CODE_GENERATION_PROMPT = """
你是一个爬虫专家。请根据以下信息生成完整的 Playwright 爬虫代码。

站点 URL: {site_url}
用户需求: {user_goal}

站点上下文:
{site_context}

检测到的特征: {detected_features}

要求:
1. 生成完整的、可直接运行的 Python 代码
2. 使用 playwright 异步 API
3. 实现错误处理和重试逻辑
4. 提取的数据以 JSON 格式返回
5. 代码必须包含 main() 函数

代码格式:
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
        await page.goto(url)

        # 等待加载
        # TODO: 根据站点特征添加等待逻辑

        # 提取数据
        data = []

        # TODO: 实现数据提取逻辑

        await browser.close()
        return {{"results": data}

def main():
    url = "{site_url}"
    result = asyncio.run(scrape(url))
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
```

请生成完整代码:
"""
```

### 5.2 沙箱执行

```python
# src/agent/sandbox.py

import asyncio
import subprocess
import tempfile
import os
from typing import Dict, Any

class SandboxExecutor:
    """沙箱代码执行器"""

    async def execute(
        self,
        code: str,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """在沙箱中执行代码"""

        # 写入临时文件
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            code_path = f.name

        try:
            # 执行代码
            process = await asyncio.create_subprocess_exec(
                'python',
                code_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tempfile.gettempdir(),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return {
                "success": process.returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": process.returncode,
            }

        except asyncio.TimeoutError:
            process.kill()
            return {
                "success": False,
                "error": "Execution timeout",
            }

        finally:
            # 清理临时文件
            try:
                os.unlink(code_path)
            except:
                pass
```

### 5.3 SOOAL 代码修复

```python
# src/agent/sool/code_repair.py

from prompts import CODE_REPAIR_PROMPT

async def sool_code_repair(
    original_code: str,
    error_logs: str,
    iteration: int,
) -> str:
    """SOOAL 代码修复"""

    if iteration >= 6:
        raise Exception("Max SOOAL iterations reached")

    prompt = CODE_REPAIR_PROMPT.format(
        original_code=original_code,
        error_logs=error_logs,
        iteration=iteration,
    )

    # LLM 生成修复后的代码
    repaired_code = await llm_generate(prompt)

    return repaired_code
```

---

## 6. Interface Design

### 6.1 任务参数（简化）

```python
task_params = {
    # 必填
    "site_url": "https://example.com",
    "user_goal": "提取所有商品价格和库存",

    # 可选
    "max_samples": 50,           # 最大采样数量
    "timeout": 300,              # 超时时间（秒）
    "use_firecrawl": False,      # 是否使用 Firecrawl
}
```

### 6.2 回调机制

```python
# 进度回调
on_progress(data: {
    "stage": "sense" | "plan" | "act" | "verify" | "report",
    "message": str,
    "sool_iteration": int,       # SOOAL 迭代次数
})

# 完成回调
on_result(result: {
    "success": bool,
    "report": ReconnaissanceReport,
})

# 错误回调
on_error(error: {
    "stage": str,
    "error": str,
    "logs": List[str],
})
```

### 6.3 输出格式

```python
{
    "success": true,
    "agent_id": "agent_xxx",
    "site_url": "https://example.com",
    "report": {
        "site_info": {...},
        "scout_summary": {
            "total_estimated_pages": 5000,
            "high_value_ratio": 0.73,
            "avg_quality_score": 0.95,
        },
        "sample_data": {
            "modality": "tabular",
            "total_samples": 47,
            "high_quality_samples": 35,
            "samples_by_url": {
                "https://example.com/product/1": {
                    "data": {...},
                    "quality_score": 0.92,
                },
                ...
            },
            "preview": [...],
        },
        "generated_code": "...",  # 生成的爬虫代码
        "execution_logs": [...],
    },
}
```

---

## 7. Long-term Memory

### 7.1 RAG 记忆库

```python
# src/agent/memory.py

class ReconMemory:
    """侦察任务记忆库"""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    async def store_insight(
        self,
        site_url: str,
        insight_type: str,
        content: str,
    ):
        """存储洞察"""
        await self.vector_store.add(
            text=content,
            metadata={
                "site_url": site_url,
                "type": insight_type,
                "timestamp": datetime.now().isoformat(),
            }
        )

    async def retrieve_insights(
        self,
        site_url: str,
        insight_type: Optional[str] = None,
    ) -> List[str]:
        """检索相关洞察"""
        filters = {"site_url": site_url}
        if insight_type:
            filters["type"] = insight_type

        results = await self.vector_store.search(
            query=site_url,
            filters=filters,
            limit=5,
        )

        return [r.text for r in results]
```

### 7.2 记忆类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `code_pattern` | 有效代码模式 | "该站使用 XPath 而非 CSS 选择器" |
| `anti_bot` | 反爬信息 | "该站有 Cloudflare 保护" |
| `data_structure` | 数据结构 | "商品数据在 <script> 标签的 JSON 中" |
| `extraction_rule` | 提取规则 | "价格在 .price 类中，需要处理单位" |

---

## 8. Deployment

### 8.1 Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 安装 Playwright 浏览器
RUN playwright install --with-deps chromium

# 复制代码
COPY . .

# 暴露端口（如需 API 服务）
EXPOSE 8000

# 默认命令
CMD ["python", "-m", "agent.main"]
```

### 8.2 requirements.txt

```
# 核心框架
langgraph>=0.2.0
langchain>=0.3.0

# 浏览器自动化
playwright>=1.40.0

# HTTP 客户端
httpx>=0.27.0

# HTML 解析
beautifulsoup4>=4.12.0
lxml>=5.0.0

# 向量数据库（记忆库）
chromadb>=0.5.0
# 或 pinecone-client>=2.2.0

# LLM 客户端
anthropic>=0.40.0
# 或 openai>=1.0.0

# 工具
firecrawl-py>=0.1.0
```

---

## Appendix: 状态机完整示例

```python
# src/agent/graph.py

from langgraph.graph import StateGraph, END
from typing import Literal

def should_run_sool(state: ReconState) -> Literal["sool", "verify"]:
    """判断是否需要 SOOAL 修复"""
    if state["execution_result"].get("success"):
        return "verify"

    # 检查是否可以修复
    error = state["execution_result"].get("error")
    if error and state["sool_iteration"] < 6:
        return "sool"

    return "verify"

def should_retry(state: ReconState) -> Literal["retry", "report"]:
    """判断是否需要重试"""
    if state["quality_score"] and state["quality_score"] > 0.6:
        return "report"

    if state["sool_iteration"] >= 6:
        return "report"

    return "retry"

# 构建状态机
graph = StateGraph(ReconState)

# 添加节点
graph.add_node("sense", sense_node)
graph.add_node("plan", plan_node)
graph.add_node("act", act_node)
graph.add_node("verify", verify_node)
graph.add_node("report", report_node)
graph.add_node("sool", sool_node)

# 添加边
graph.add_edge("sense", "plan")
graph.add_edge("plan", "act")
graph.add_conditional_edges("act", should_run_sool)
graph.add_conditional_edges("verify", should_retry)
graph.add_edge("sool", "act")
graph.add_edge("report", END)

# 编译为可运行图
recon_graph = graph.compile()
```

---

**Document Version**: 3.0.0
**Last Updated**: 2026-02-21
**Key Changes**: Hybrid 架构，LangGraph 状态机，代码生成+沙箱执行
