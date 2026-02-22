# Full-Self-Crawling - Hybrid Recon Agent

**Version**: v3.2.0 (Enhanced Quality Validation)
**Date**: 2026-02-22
**Scope**: Single-site reconnaissance agent with code generation

---

## Reader Guide

本文档面向两类读者：

| 读者类型 | 阅读重点 |
|---------|---------|
| **开发者** | 关注架构设计、状态机实现、接口协议、错误处理 |
| **Coding Agent** | 关注数据格式、接口规范、Prompt 模板、代码示例 |

**快速导航**：
- 想了解 Agent 如何工作 → 阅读 [1. Agent Overview](#1-agent-overview) 和 [2. Hybrid Architecture](#2-hybrid-architecture)
- 想调用 Agent → 阅读 [6. Interface Design](#6-interface-design) 和 [9. Orchestrator 交互协议](#9-orchestrator-交互协议)
- 想扩展功能 → 阅读 [3. LangGraph State Machine](#3-langgraph-state-machine) 和 [4. Tool Chain](#4-tool-chain)
- 出现问题 → 阅读 [8. SOOAL 自修复循环](#8-sooal-自修复循环) 和 [10. 错误处理策略](#10-错误处理策略)

---

## Table of Contents

1. [Agent Overview](#1-agent-overview)
2. [Hybrid Architecture](#2-hybrid-architecture)
3. [LangGraph State Machine](#3-langgraph-state-machine)
4. [Tool Chain](#4-tool-chain)
5. [Code Generation & Execution](#5-code-generation--execution)
6. [Interface Design](#6-interface-design)
7. [SOOAL 自修复循环](#7-sooal-自修复循环)
8. [Long-term Memory](#8-long-term-memory)
9. [Orchestrator 交互协议](#9-orchestrator-交互协议)
10. [错误处理策略](#10-错误处理策略)
11. [完整案例演示](#11-完整案例演示)
12. [Deployment](#12-deployment)

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

## 2. Agent 在系统中的位置

```
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator（编排层）                   │
│  - 和用户交互                                                │
│  - 精确化需求                                              │
│  - 分配任务给 Agent                                         │
│  - 收集报告呈现给用户                                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                    分发任务
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SiteAgent（侦察 Agent）                    │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           LangGraph 状态机（每个 Agent 独立）             │  │
│  │  Sense → Plan → Act → Verify → Report                   │  │
│  │  - 分阶段生成代码                                       │  │
│  │  - 沙箱执行                                             │  │
│  │  - SOOAL 自修复                                          │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                              │
│  输入：site_url + data_requirement                             │
│  输出：Reconnaissance Report                                  │
│        - site_info: 网站信息                                 │
│        - data_info: 数据信息（数量、质量）                     │
│        - sample_data: 真实样本数据                            │
└─────────────────────────────────────────────────────────────────┘
```

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

### 2.2 分阶段代码生成策略

**策略**：分阶段生成，而非一次性生成大段代码

```
Sense 节点 → 生成"探测代码"
    ├─ 访问首页
    ├─ 检测页面特征
    └─ 快速分析

Plan 节点 → 生成"采样+提取代码"
    ├─ 根据需求设计采样逻辑
    ├─ 定义数据提取规则
    └─ 实现 JSON 输出

Act 节点 → 执行代码
    ├─ Docker 沙箱运行
    ├─ 收集执行结果
    └─ 捕获错误日志

SOOAL 节点 → 生成"修复代码"
    ├─ 分析错误原因
    ├─ 修改代码逻辑
    └─ 重新执行
```

**优势**：
- 每个阶段代码更小、更易调试
- LLM 可以根据上一阶段结果调整下一阶段代码
- 失败时只修复相关阶段，不用重新生成全部

---

### 2.3 执行流程

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
    quality_issues: Optional[List[str]]       # 质量问题列表
    quality_stats: Optional[Dict[str, Any]]   # 详细质量统计（新增）

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

## 7. SOOAL 自修复循环

SOOAL（Sense → Orient → Act → Verify → Learn）是 Recon Agent 的核心自适应机制，用于处理采样/执行失败（如反爬封禁、代码崩溃、选择器失效）。最多 5 轮循环，失败后返回带错误信息的报告。

### 7.1 设计理念

| 阶段 | 英文 | 说明 | 输入 → 输出 |
|------|------|------|------------|
| 感知 | Sense | 收集失败证据 | 错误日志 → 证据包 |
| 判断 | Orient | 分析根因和对策 | 证据包 → 修复方案 |
| 行动 | Act | 执行修复 | 修复方案 → 新代码 |
| 验证 | Verify | 检查修复效果 | 执行结果 → 通过/失败 |
| 学习 | Learn | 记录有效策略 | 成功方案 → 记忆库 |

### 7.2 循环流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    SOOAL 循环流程                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Act 节点执行失败                                                │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐                                               │
│  │  Sense      │  收集：错误日志、页面截图、HTML结构、robots.txt │
│  └─────────────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐                                               │
│  │  Orient     │  LLM 分析：根因是什么？能修复吗？              │
│  └─────────────┘   → 选择器失效？反爬封禁？超时？               │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐                                               │
│  │  Act        │  LLM 修改代码：                                │
│  └─────────────┘   - 加等待时间、换选择器、加 proxy、改 UA      │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────┐                                               │
│  │  Verify     │  检查：执行成功？数据质量？                    │
│  └─────────────┘                                               │
│         │                                                       │
│    ┌────┴────┐                                                │
│    ▼         ▼                                                │
│  通过      失败                                                 │
│    │         │                                                 │
│    ▼         ▼                                                 │
│ Learn    回 Act（最多5轮）                                      │
│    │         │                                                 │
│    ▼         ▼                                                 │
│ 记忆    放弃（返回失败报告）                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 在 LangGraph 中的实现

```python
# src/agent/graph.py

def should_run_sool(state: ReconState) -> Literal["sool", "verify"]:
    """判断是否需要 SOOAL 修复"""
    if not state.get("execution_result"):
        return "sool"

    # 执行成功，直接验证
    if state["execution_result"].get("success"):
        return "verify"

    # 检查错误是否可修复
    error = state["execution_result"].get("error")
    if error and state["sool_iteration"] < 5:
        return "sool"

    # 超过迭代次数，放弃修复
    return "verify"

# 条件边：Act → Sool 或 Act → Verify
graph.add_conditional_edges(
    "act",
    should_run_sool,
    {
        "sool": "sool",
        "verify": "verify"
    }
)

# SOOAL 循环：Sool → Act
graph.add_edge("sool", "act")
```

### 7.4 SOOAL 节点实现

```python
async def soal_node(state: ReconState) -> ReconState:
    """SOOAL 节点：分析错误 → 修改代码 → 重跑"""
    from llm import ZhipuClient
    from prompts import CODE_REPAIR_PROMPT

    state["sool_iteration"] += 1

    # 1. Sense：收集错误信息
    error_logs = "\n".join(state.get("execution_logs", []))
    last_error = state.get("execution_result", {}).get("error", "")

    # 2. Orient：LLM 分析根因（通过 CODE_REPAIR_PROMPT）
    # 3. Act：LLM 生成修复后的代码
    client = ZhipuClient(api_key=os.environ.get("ZHIPU_API_KEY"))

    repaired_code = await client.repair_code(
        original_code=state["generated_code"],
        error_logs=f"迭代 {state['sool_iteration']}: {last_error}\n{error_logs}",
        iteration=state["sool_iteration"],
    )

    state["generated_code"] = repaired_code
    state["last_error"] = last_error

    # 4. Learn：记录错误历史
    if state.get("error_history") is None:
        state["error_history"] = []
    state["error_history"].append({
        "iteration": state["sool_iteration"],
        "error": last_error,
        "action": "code_repair"
    })

    return state
```

### 7.5 常见场景处理

| 场景 | 根因 | Orient 判断 | Act 行动 | Learn 记录 |
|------|------|------------|---------|-----------|
| 元素未找到 | 选择器失效 | "选择器变化，需更新" | 修改 selector，加 wait_for_selector | "该站用 data-id 而非 class" |
| 执行超时 | 页面加载慢 | "加载时间长，需增加等待" | 增加超时时间，加显式等待 | "该站首屏加载需 5s+" |
| 空数据 | 结构变化 | "DOM 结构已变化" | 重新分析 HTML，换提取逻辑 | "数据现在在 JSON-LD 中" |
| 被封禁 | 反爬检测 | "触发反爬，需伪装" | 加随机 UA、延迟、代理 | "该站有 Cloudflare 保护" |
| JSON 解析失败 | 输出格式错误 | "输出非有效 JSON" | 修复输出代码，加 try-except | "需确保输出是纯 JSON" |

### 7.6 降级策略

当 SOOAL 循环无法修复时（达到 5 轮上限）：

```python
# 降级到失败报告
if state["sool_iteration"] >= 5:
    state["stage"] = "failed"
    state["final_report"] = {
        "success": False,
        "reason": "SOOAL_MAX_ITERATIONS",
        "error_history": state["error_history"],
        "last_error": state["last_error"],
        "recommendation": "建议人工介入或尝试其他策略"
    }
    return state  # 直接结束，不再继续
```

---

## 8. Long-term Memory

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

## 9. Orchestrator 交互协议

Agent 与 Orchestrator 之间的通信协议，定义任务下发、进度回调、结果返回的格式。

### 9.1 任务下发格式

Orchestrator → Agent：

```python
{
    # 必填字段
    "task_id": "recon_20250221_abc123",
    "site_url": "https://example.com/products",
    "user_goal": "提取所有商品的标题、价格、库存、图片链接",

    # 可选字段
    "max_samples": 50,           # 最大采样数量
    "timeout": 300,              # 单次执行超时（秒）
    "priority": "normal",        # 任务优先级：low/normal/high
    "callback_url": None,        # 回调地址（异步模式）
    "metadata": {                # 额外元信息
        "domain": "example.com",
        "category": "ecommerce"
    }
}
```

### 9.2 进度回调事件

Agent → Orchestrator（实时推送）：

```python
# 阶段开始
{
    "event_type": "stage_start",
    "task_id": "recon_20250221_abc123",
    "agent_id": "agent_xyz",
    "stage": "sense",            # sense/plan/act/verify/report
    "timestamp": "2025-02-21T10:30:00Z"
}

# 阶段完成
{
    "event_type": "stage_complete",
    "task_id": "recon_20250221_abc123",
    "agent_id": "agent_xyz",
    "stage": "plan",
    "duration_ms": 3500,
    "output": {
        "code_generated": true,
        "code_length": 1247
    },
    "timestamp": "2025-02-21T10:30:05Z"
}

# SOOAL 触发
{
    "event_type": "soal_started",
    "task_id": "recon_20250221_abc123",
    "agent_id": "agent_xyz",
    "iteration": 1,
    "error": "SelectorTimeoutError: .product-list not found",
    "timestamp": "2025-02-21T10:30:15Z"
}

# 进度更新
{
    "event_type": "progress",
    "task_id": "recon_20250221_abc123",
    "agent_id": "agent_xyz",
    "message": "正在提取第 2 页数据...",
    "progress_percent": 40,
    "timestamp": "2025-02-21T10:30:20Z"
}
```

### 9.3 最终结果返回

Agent → Orchestrator（任务完成）：

```python
# 成功
{
    "event_type": "task_complete",
    "task_id": "recon_20250221_abc123",
    "agent_id": "agent_xyz",
    "success": true,
    "duration_seconds": 127,
    "stage": "done",

    "result": {
        "site_info": {
            "url": "https://example.com/products",
            "title": "Products - Example Store",
            "detected_features": ["pagination", "grid-layout", "lazy-load"],
            "anti_crawl_level": "low"
        },
        "data_info": {
            "estimated_total": 5000,
            "sample_count": 47,
            "quality_score": 0.92
        },
        "sample_data": [
            {
                "title": "Product A",
                "price": 199.99,
                "stock": "In Stock",
                "image_url": "https://example.com/img/a.jpg"
            },
            # ... more samples
        ],
        "generated_code": "async def scrape...",
        "execution_summary": {
            "sool_iterations": 1,
            "pages_visited": 2,
            "extraction_success_rate": 0.95
        }
    },
    "timestamp": "2025-02-21T10:32:00Z"
}

# 失败
{
    "event_type": "task_failed",
    "task_id": "recon_20250221_abc123",
    "agent_id": "agent_xyz",
    "success": false,
    "stage": "failed",
    "error": {
        "type": "SOOAL_MAX_ITERATIONS",
        "message": "无法修复选择器错误，达到最大迭代次数",
        "last_error": "SelectorTimeoutError: .product-list not found",
        "error_history": [
            {"iteration": 1, "error": "..."},
            {"iteration": 2, "error": "..."}
        ]
    },
    "partial_result": {
        "site_info": {...},
        "sample_data": []  # 部分成功的数据
    },
    "timestamp": "2025-02-21T10:32:00Z"
}
```

### 9.4 通信模式

| 模式 | 说明 | 适用场景 |
|------|------|---------|
| **同步调用** | Orchestrator 等待 Agent 返回结果 | 单站侦察、批量任务 |
| **异步回调** | Agent 通过 webhook 推送事件 | 长时间任务、实时监控 |
| **流式输出** | Agent 实时推送各节点结果 | 调试模式、演示场景 |

### 9.5 状态同步

```python
# Agent 内部状态（LangGraph State）
ReconState = {
    "stage": "act",              # 当前阶段
    "sool_iteration": 2,         # SOOAL 迭代次数
    "last_error": None,          # 最后的错误
}

# 暴露给 Orchestrator 的状态摘要
def get_status_summary(state: ReconState) -> dict:
    return {
        "task_id": state["task_id"],
        "agent_id": state.get("agent_id"),
        "stage": state["stage"],
        "progress": calculate_progress(state),
        "sool_active": state["sool_iteration"] > 0,
        "can_continue": state["stage"] not in ["done", "failed"]
    }
```

---

## 10. 质量评估与验证机制

### 10.1 验证架构

Verify 节点采用 **CodeAct 风格验证**：LLM 生成验证代码 → 沙箱执行 → 返回详细质量报告。

```
┌─────────────────────────────────────────────────────────────────┐
│                    Verify 节点验证流程                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  采样数据                                                       │
│    │                                                           │
│    ▼                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │    LLM 生成验证代码（包含具体规则）                      │   │
│  │  - 图片验证、格式验证、重复检测                           │   │
│  └─────────────────────────────────────────────────────────┘   │
│    │                                                           │
│    ▼                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           沙箱执行验证代码                                │   │
│  │  返回详细的质量报告和问题列表                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│    │                                                           │
│    ▼                                                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           可配置阈值决策 + 反馈到 Plan 节点              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 10.2 验证维度

| 维度 | 权重 | 验证内容 | 可审查性 |
|------|------|----------|----------|
| **relevance** | 0.4 | 与用户需求的相关性（字段匹配度） | ✅ 完全可审查 |
| **completeness** | 0.3 | 必填字段完整度（非空比例） | ✅ 完全可审查 |
| **accuracy** | 0.2 | 格式正确性（日期、价格、URL） | ✅ 完全可审查 |
| **content_quality** | 0.1 | 内容质量（无重复、无无效内容） | ✅ 完全可审查 |

### 10.3 可审查性分类

#### 完全可审查的数据（文本/结构化）

| 数据类型 | 审查方式 | 可验证内容 |
|---------|---------|-----------|
| 纯文本 | 字符串匹配、正则、LLM | 长度、格式、语义 |
| URL | urlparse、正则、HEAD请求 | 格式、可达性 |
| 日期/时间 | datetime.strptime、正则 | 格式、范围 |
| 价格/数字 | 正则、类型转换 | 格式、货币符号 |
| 邮箱/电话 | 正则 | 格式有效性 |
| JSON/XML | 解析器、Schema验证 | 结构完整性 |
| HTML片段 | BeautifulSoup | 标签闭合、选择器 |

#### 不可完整审查的数据（需要外部工具）

| 数据类型 | 局限性 | 需要的工具 |
|---------|-------|-----------|
| 图片URL | 只能验证URL格式 | 下载+Vision API |
| 图片Base64 | 只能验证编码有效性 | 解码+Vision模型 |
| 视频URL | 只能验证URL | 视频处理库 |
| PDF链接 | 只能验证URL | PDF解析库 |

### 10.4 验证规则自动提取

```python
# src/agent/prompts.py

def extract_validation_rules(user_goal: str) -> dict:
    """
    从用户需求中自动提取验证规则

    示例:
    - "提取高清图片" → {"validate_images": True, "image_quality": "high"}
    - "价格格式要正确" → {"validate_price": True}
    - "不能有重复" → {"check_duplicates": True}
    """
    rules = {
        "check_duplicates": True,
        "validate_urls": True,
    }

    goal_lower = user_goal.lower()

    if "图片" in goal_lower or "image" in goal_lower:
        rules["validate_images"] = True
        if "高清" in goal_lower or "high" in goal_lower:
            rules["image_quality"] = "high"

    if "价格" in goal_lower or "price" in goal_lower:
        rules["validate_price"] = True

    if "日期" in goal_lower or "date" in goal_lower:
        rules["validate_date"] = True

    return rules
```

### 10.5 降级策略改进

**旧版问题**：只检查数据量 `min(0.9, sample_count/50)`，导致 30 条空记录能得 0.6 分

**新版降级**：实际检查数据内容

```python
# src/agent/graph.py

def fallback_quality_check(sample_data: list) -> float:
    """
    改进的降级质量检查 - 实际检查数据内容

    检查项目：
    1. 空记录检测：记录是否为空或所有值都为空
    2. 关键字段检测：title/name/url/link 是否为空
    3. 无意义内容检测：N/A, null, 待补充等
    """
    if not sample_data:
        return 0.0

    total = len(sample_data)
    issues = 0
    null_values = ["n/a", "null", "none", "待补充", "暂无", "tbd", "-", "—"]

    for item in sample_data:
        # 检查是否有值
        if not item or all(v is None or v == "" for v in item.values()):
            issues += 1
            continue

        # 检查关键字段
        for key in ["title", "name", "url", "link"]:
            if key in item:
                val = str(item.get(key, "")).strip()
                if not val or val.lower() in null_values:
                    issues += 1

    # 质量 = (有效记录数) / 总数
    valid_ratio = (total - min(issues, total)) / total
    return round(valid_ratio, 2)
```

### 10.6 配置选项

```bash
# .env 配置

# 质量阈值 (0.0-1.0)
QUALITY_THRESHOLD=0.6

# 最大 SOOAL 迭代次数
MAX_SOOL_ITERATIONS=6

# 验证开关
VALIDATE_IMAGES=true
CHECK_DUPLICATES=true
VALIDATE_URLS=true
VALIDATE_DATES=true
```

### 10.7 质量统计输出格式

```python
{
    "quality_score": 0.85,
    "quality_stats": {
        "scores": {
            "relevance": 0.90,
            "completeness": 0.80,
            "accuracy": 0.95,
            "content_quality": 0.70
        },
        "image_stats": {
            "total": 50,
            "valid": 45,
            "placeholder": 5,
            "invalid": 0
        },
        "format_stats": {
            "date_valid": 48,
            "date_total": 50,
            "price_valid": 50,
            "price_total": 50,
            "url_valid": 49,
            "url_total": 50
        },
        "content_stats": {
            "empty_fields": 2,
            "duplicates": 0,
            "invalid_content": 1,
            "total_items": 50
        }
    },
    "quality_issues": [
        "数据完整性较低: 0.8",
        "发现占位图: 5 个"
    ],
    "suggestions": []
}
```

---

## 11. 错误处理策略

### 10.1 各节点错误处理

| 节点 | 错误类型 | 处理策略 | 是否重试 |
|------|---------|---------|---------|
| **Sense** | 网络超时 | 换用 Firecrawl API | ✅ 1 次 |
| **Sense** | 页面 404 | 标记失败，返回报告 | ❌ |
| **Plan** | LLM 调用失败 | 重试 LLM 调用 | ✅ 3 次 |
| **Plan** | 代码为空 | 用模板代码 | ✅ 1 次 |
| **Act** | 执行超时 | 进入 SOOAL 增加超时 | ✅ |
| **Act** | 选择器失效 | 进入 SOOAL 修复代码 | ✅ |
| **Act** | 沙箱崩溃 | 重启沙箱，重新执行 | ✅ 1 次 |
| **Verify** | 质量分数 < 0.6 | 返回 Plan 重新生成 | ✅ |
| **Report** | LLM 生成失败 | 用模板报告 | ✅ 1 次 |

### 10.2 超时策略

```python
TIMEOUT_CONFIG = {
    "sense": 30,       # 快速探测，30 秒
    "plan": 60,        # LLM 生成代码，60 秒
    "act": 300,        # 沙箱执行，5 分钟
    "verify": 30,      # 质量评估，30 秒
    "report": 60,      # 报告生成，60 秒
    "total": 1800,     # 整体任务，30 分钟
}

# 超时后的处理
async def handle_timeout(stage: str, state: ReconState):
    if stage == "act":
        # Act 超时，SOOAL 尝试增加超时时间
        state["generated_code"] = inject_timeout_increase(
            state["generated_code"],
            new_timeout=600
        )
        return state
    else:
        # 其他阶段超时，记录并返回
        return await generate_failure_report(
            state, reason="TIMEOUT", stage=stage
        )
```

### 10.3 降级方案

当主要策略失败时的降级方案：

| 场景 | 主策略 | 降级策略 |
|------|-------|---------|
| Playwright 失败 | BrowserTool（Playwright） | Firecrawl API |
| LLM 代码生成失败 | GLM-4.7 生成 | 用预置模板 |
| 沙箱执行失败 | Docker 沙箱 | SimpleSandbox（本地） |
| 质量评估失败 | LLM 评估 | 基于规则打分 |
| 报告生成失败 | LLM 生成 | JSON 格式报告 |

### 10.4 错误分类与处理

```python
class ErrorType(Enum):
    """错误类型分类"""
    RECOVERABLE = "recoverable"      # 可恢复：SOOAL 处理
    RETRYABLE = "retryable"          # 可重试：直接重试
    FATAL = "fatal"                  # 致命：直接失败

def classify_error(error: Exception) -> ErrorType:
    """错误分类"""
    if isinstance(error, (SelectorError, TimeoutError)):
        return ErrorType.RECOVERABLE
    elif isinstance(error, (NetworkError, LLMRateLimitError)):
        return ErrorType.RETRYABLE
    else:
        return ErrorType.FATAL
```

### 10.5 错误上报格式

```python
{
    "error_event": {
        "task_id": "recon_abc",
        "agent_id": "agent_xyz",
        "stage": "act",
        "error_type": "SelectorTimeoutError",
        "error_message": ".product-list not found after 30s",
        "stack_trace": "...",            # 开发模式下包含
        "context": {
            "url": "https://example.com",
            "selector": ".product-list",
            "page_source_snippet": "..."
        },
        "handling_action": "sool_triggered",
        "timestamp": "2025-02-21T10:30:00Z"
    }
}
```

---

## 12. 完整案例演示

### 11.1 任务输入

```python
task = {
    "site_url": "https://books.toscrape.com/",
    "user_goal": "提取所有图书的标题、价格、库存状态、星级评分"
}
```

### 11.2 Sense 阶段输出

```python
{
    "stage": "sense",
    "site_context": {
        "title": "Books to Scrape - We love being scraped!",
        "url": "https://books.toscrape.com/",
        "status_code": 200
    },
    "detected_features": [
        "product-grid",      # 网格布局
        "pagination",        # 分页导航
        "rating-stars",      # 星级评分
        "price-display"      # 价格显示
    ],
    "html_snapshot": "<html>...</html>"  # 前 5000 字符
}
```

### 11.3 Plan 阶段输出

```python
{
    "stage": "plan",
    "plan_reasoning": "检测到产品网格布局，使用 CSS 选择器 .product_pod 提取",
    "generated_code": '''
async def scrape(url: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        # 等待产品加载
        await page.wait_for_selector(".product_pod")

        results = []
        products = await page.query_selector_all(".product_pod")

        for product in products:
            title = await product.query_selector(".product_title")
            price = await product.query_selector(".price_color")
            stock = await product.query_selector(".instockavailability")
            rating = await product.query_selector("[class*='star-rating']")

            results.append({
                "title": await title.inner_text() if title else "",
                "price": await price.inner_text() if price else "",
                "stock": await stock.inner_text() if stock else "",
                "rating": await rating.get_attribute("class") if rating else ""
            })

        await browser.close()
        return {"results": results, "metadata": {"total": len(results)}}
'''
}
```

### 11.4 Act 阶段输出

```python
{
    "stage": "act",
    "execution_result": {
        "success": true,
        "stdout": '{"results": [...], "metadata": {"total": 20}}',
        "stderr": "",
        "returncode": 0
    },
    "parsed_data": {
        "results": [
            {
                "title": "A Light in the Attic",
                "price": "£51.77",
                "stock": "In stock",
                "rating": "star-rating Three"
            },
            # ... 19 more items
        ],
        "metadata": {"total": 20}
    },
    "sool_iteration": 0
}
```

### 11.5 Verify 阶段输出

```python
{
    "stage": "verify",
    "quality_score": 0.95,
    "quality_issues": [],
    "sample_data": [  # 提取的样本
        {
            "title": "A Light in the Attic",
            "price": "£51.77",
            "stock": "In stock",
            "rating": "Three"
        }
    ]
}
```

### 11.6 Report 阶段输出

```python
{
    "stage": "done",
    "final_report": {
        "site_info": {
            "url": "https://books.toscrape.com/",
            "title": "Books to Scrape",
            "type": "电商/图书",
            "features": ["产品网格", "分页", "星级评分"]
        },
        "data_info": {
            "estimated_total": 1000,      # 基于 50 页 × 20 本/页
            "sample_count": 20,
            "quality_score": 0.95,
            "fields": ["title", "price", "stock", "rating"]
        },
        "sample_data": [...],  # 20 本书的完整数据
        "crawling_strategy": {
            "recommended_method": "playwright",
            "pagination": "?page=1,2,3...",
            "anti_crawl": "none"
        }
    },
    "markdown_report": """
# 网站数据侦察报告

## 站点信息
- URL: https://books.toscrape.com/
- 类型: 电商/图书

## 侦察总结
- 估算总量: ~1000 条
- 样本质量: 0.95/1.0
- 数据结构: 高度结构化

## 真实样本预览
1. A Light in the Attic - £51.77 - In stock - Three
2. Tipping the Velvet - £53.74 - In stock - One
...
"""
}
```

### 11.7 SOOAL 场景示例

假设 Act 阶段选择器 `.product_pod` 失效：

```
第 1 次 Act 失败 → SelectorTimeoutError
    ↓
SOOAL Sense: 收集错误 "SelectorTimeoutError: .product_pod not found"
    ↓
SOOAL Orient: LLM 分析 → "选择器可能已变化，尝试 article.product_pod"
    ↓
SOOAL Act: 修改代码为 `article.product_pod`
    ↓
第 2 次 Act → 成功！
    ↓
继续 Verify → Report
```

---

## 13. Deployment

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

**Document Version**: 3.2.0
**Last Updated**: 2026-02-22
**Key Changes**:
- 新增质量评估与验证机制独立章节
- 可配置的质量阈值（QUALITY_THRESHOLD）
- 改进的降级策略：实际检查数据内容而非仅计数
- 图片/格式/内容多维度验证
- 自动从用户需求提取验证规则
- 新增 quality_stats 详细统计输出

**Changelog**:
- v3.2.0: 增强质量验证机制，修复降级策略缺陷
- v3.1.0: 完善文档结构，添加协议和案例
- v3.0.0: Hybrid 架构，LangGraph 状态机，代码生成+沙箱执行
