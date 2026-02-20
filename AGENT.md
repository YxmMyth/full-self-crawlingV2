# Full-Self-Crawling - Single Site Agent

**Version**: v2.0.0 (Data Reconnaissance Architecture)
**Date**: 2026-02-20
**Scope**: Single-site data reconnaissance agent

---

## Table of Contents

1. [Agent Overview](#1-agent-overview)
2. [Reconnaissance Phase](#2-reconnaissance-phase)
3. [Interface Design](#3-interface-design)
4. [Core Components](#4-core-components)
5. [Data Models](#5-data-models)
6. [Configuration Specification](#6-configuration-specification)
7. [Deployment & Containerization](#7-deployment--containerization)

---

## 1. Agent Overview

### 1.1 Agent Positioning

**SiteAgent - 网站数据侦察智能体**

```
使命：针对任意用户需求，对网站进行广泛轻量侦察
    → 真实采样提取指定形态数据
    → 输出"带真实样本的决策报告"
    → 用户/Orchestrator 自己决定要不要继续爬
```

#### 核心特性

| 特性 | 说明 |
|------|------|
| **用完即弃** | 每次都是新实例，不跨实例学习 |
| **单一目标形态** | 用户只指定一种目标形态（text/tabular/pdf/json/image/api） |
| **真实采样** | 不是"猜HTML"，而是真实爬取提取样本数据 |
| **侦察报告** | Markdown + JSON，包含真实样本预览 |
| **智能终止** | 无目标形态或强反爬时提前终止 |
| **无用户交互** | Agent 不直接和用户交互，只接收 Orchestrator 指令 |

#### Agent 不是什么

| 不是 | 说明 |
|------|------|
| 不是爬虫生成器 | 不输出爬虫代码 |
| 不是全站爬虫 | 不追求爬完全站，只做侦察采样 |
| 不是决策者 | 不决定"要不要爬"，只输出报告供决策 |

### 1.2 Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    SiteAgent Execution Flow                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  输入：site_url + target_modality + user_goal                   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │           Phase 1: Wide Mapping（广泛侦察）              │   │
│  │  - BFS/DFS 遍历发现 URL                                   │   │
│  │  - 检测每个 URL 的可能形态标记                            │   │
│  │  - 构建 URL → 形态映射                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │      Phase 2: Intelligent Targeted Sampling（智能采样）  │   │
│  │  - 根据站点规模动态调整采样数量                           │   │
│  │  - 优先采样可能包含目标形态的 URL                         │   │
│  │  - 边探索边爬取，边探索边提取                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │        Phase 3: Multi-Modal Extraction（多模态提取）     │   │
│  │  - 真实爬取采样页面（Playwright/Firecrawl JS渲染）       │   │
│  │  - 根据目标形态动态提取数据                               │   │
│  │  - 质量评估 + 错误记录                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Phase 4: Report Generation（报告生成）       │   │
│  │  - Markdown 报告（人类可读）                               │   │
│  │  - JSON 数据（程序可用）                                  │   │
│  │  - 真实样本预览（按 URL 分组）                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│                      输出：ReconnaissanceReport                  │
│                  Orchestrator/用户决定下一步                    │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Target Modalities

**目标形态枚举**（Orchestrator 与用户对齐）：

| 形态 | 说明 | 提取方式 |
|------|------|----------|
| `text` | 纯文本/文章 | Markdown + 段落分割 |
| `tabular` | 表格/列表 | LLM 转结构化 JSON |
| `json` | JSON-LD/嵌入JSON | 直接解析 + schema 验证 |
| `pdf` | PDF/文档 | 内置 PDF parser + OCR |
| `image` | 图片/图表 | Vision LLM OCR + 描述 |
| `api` | API 端点 | 检测 XHR/fetch，模拟调用 |
| `mixed` | 混合页面 | 自动拆分多形态分别提取 |

---

## 2. Reconnaissance Phase

### 2.1 Wide Mapping（广泛侦察）

**目标**：发现 URL 结构，标记每个 URL 的可能形态

```python
class URLNode:
    url: str
    depth: int
    page_type: str              # article/listing/category/static
    possible_modalities: List[str]  # 检测到的可能形态
    visited: bool = False
```

**形态检测规则**：

| URL 模式 | 可能形态 |
|----------|----------|
| 包含 `.pdf` | `pdf` |
| 包含 `/api/` | `api` |
| 包含 `<table>` 或 `<ul class="list">` | `tabular` |
| 包含 `<script type="application/ld+json">` | `json` |
| 包含 `<img>` 大图 | `image` |
| 默认 | `text` |

**终止条件**：
- 无目标形态：提前终止，报告"未发现目标形态"
- 强反爬：连续失败率 > 50%，提前终止

### 2.2 Intelligent Targeted Sampling（智能采样）

**采样数量**：根据站点规模动态调整

| 站点规模 | 采样数量 |
|----------|----------|
| 小站 (< 1000 页) | 50-80 页 |
| 中站 (1000-10000 页) | 80-150 页 |
| 大站 (> 10000 页) | 150-200 页 |

**采样策略**：优先采样可能包含目标形态的 URL

```python
def prioritize_urls(
    url_nodes: List[URLNode],
    target_modality: str
) -> List[URLNode]:
    # 1. 目标形态匹配的 URL 最高优先级
    # 2. 同类型页面分散采样
    # 3. 深度优先（内容页通常更深）
```

### 2.3 Multi-Modal Extraction（多模态提取）

**真实爬取**：使用 Playwright/Firecrawl 进行 JS 全渲染

**动态提取**：根据目标形态选择提取器

| 目标形态 | 提取器 |
|----------|--------|
| `text` | ArticleExtractor → Markdown |
| `tabular` | TableExtractor → LLM → JSON |
| `json` | JSONExtractor → 验证 |
| `pdf` | PDFExtractor → OCR |
| `image` | VisionExtractor → OCR + 描述 |
| `api` | APIExtractor → 模拟调用 |

### 2.4 Report Generation（报告生成）

**Markdown 报告**：根据目标形态动态调整章节

```
【网站数据侦察报告】—— example.com

用户需求：{user_goal}
目标形态：{target_modality}

侦察总结：
- 总页面估算：≈{total_pages}
- 高价值比例：{high_value_ratio}%
- 平均数据质量：{avg_quality_score}
- 数据形态分布：{modality_distribution}

真实样本预览（{preview_count}条）：
1. URL: {url}
   提取数据：{extracted_data}
   质量分数：{quality_score}
...

Top 推荐路径：
1. {path} → {modality}, 质量 {score}
...

可爬性评估：
- 反爬等级：{anti_bot_level}
- 推荐策略：{recommended_strategy}
- 预估成本：{cost_estimate}
```

---

## 3. Interface Design

### 3.1 Task Parameters

```python
task_params = {
    # 必填
    "site_url": "https://example.com",
    "target_modality": "tabular",  # 用户指定的单一目标形态
    "user_goal": "提取商品价格和库存",

    # 可选
    "max_samples": 150,            # 最大采样数（覆盖动态调整）
    "max_depth": 3,                # 最大探索深度
    "cost_limit_usd": 5.0,         # 成本上限
}
```

### 3.2 Callback Events

```python
# 进度回调
on_progress(data: {
    "stage": "mapping" | "sampling" | "extracting" | "reporting",
    "urls_discovered": int,
    "urls_sampled": int,
    "samples_extracted": int,
    "current_url": str,
    "message": str,
})

# 完成回调
on_result(result: {
    "success": bool,
    "report": ReconnaissanceReport,
})

# 提前终止回调
on_terminated(reason: {
    "reason": "no_target_modality" | "strong_anti_bot",
    "message": str,
})
```

### 3.3 Output Format

```python
{
    "success": true,
    "agent_id": "agent_xxx",
    "site_url": "https://example.com",
    "report": {
        "site_info": {...},
        "scout_summary": {...},
        "target_modality": "tabular",
        "site_structure": {...},
        "feasibility": {...},
        "cost_estimate": {...},
        "sample_data": {
            "modality": "tabular",
            "total_samples": 47,
            "high_quality_samples": 35,
            "samples_by_url": {
                "https://example.com/product/1": {
                    "data": {...},
                    "quality_score": 0.92,
                    "extracted_at": "2026-02-20T10:00:00Z",
                },
                ...
            },
            "preview": [...]  # 精选展示
        },
        "extraction_errors": [...],
    },
    "markdown_report": "# 网站数据侦察报告...",
}
```

---

## 4. Core Components

### 4.1 Explorer（侦察器）

```python
class Explorer:
    """Wide Mapping + Intelligent Sampling"""

    async def map_site(
        site_url: str,
        target_modality: str,
        max_depth: int,
    ) -> Dict[str, URLNode]:
        """遍历站点，构建 URL → 形态映射"""

    async def sample_urls(
        url_nodes: List[URLNode],
        target_modality: str,
        max_samples: int,
    ) -> List[str]:
        """智能采样，优先目标形态"""
```

### 4.2 Extractor（提取器）

```python
class MultiModalExtractor:
    """根据目标形态动态提取"""

    def __init__(self, target_modality: str):
        self.extractor = self._get_extractor(target_modality)

    async def extract(
        self,
        url: str,
        html: str,
    ) -> ExtractedData:
        """真实爬取并提取"""

    def _get_extractor(self, modality: str) -> BaseExtractor:
        """获取对应形态的提取器"""
```

### 4.3 Evaluator（评估器）

```python
class DataEvaluator:
    """评估提取数据的质量"""

    async def evaluate(
        self,
        data: ExtractedData,
        target_modality: str,
    ) -> QualityScore:
        """根据形态评估质量"""

    async def batch_evaluate(
        self,
        samples: List[ExtractedData],
    ) -> QualityMetrics:
        """批量评估，生成统计"""
```

### 4.4 Reporter（报告生成器）

```python
class ReportGenerator:
    """生成 Markdown + JSON 报告"""

    async def generate(
        self,
        site_info: SiteInfo,
        samples: List[ExtractedData],
        metrics: QualityMetrics,
        target_modality: str,
    ) -> ReconnaissanceReport:
        """生成完整报告"""
```

---

## 5. Data Models

### 5.1 ReconnaissanceReport

```python
@dataclass
class ReconnaissanceReport:
    """侦察报告（JSON 输出）"""
    site_info: SiteInfo
    scout_summary: ScoutSummary
    target_modality: str
    site_structure: SiteStructure
    feasibility: Feasibility
    cost_estimate: CostEstimate
    sample_data: SampleData
    extraction_errors: List[ExtractionError]
```

### 5.2 SampleData

```python
@dataclass
class SampleData:
    """样本数据（按 URL 分组）"""
    modality: str
    total_samples: int
    high_quality_samples: int
    samples_by_url: Dict[str, SampleRecord]  # URL → 提取数据
    preview: List[SampleRecord]  # 精选展示
```

### 5.3 SampleRecord

```python
@dataclass
class SampleRecord:
    """单个样本记录"""
    url: str
    data: Dict[str, Any]  # 提取的数据（形态不同结构不同）
    quality_score: float
    extracted_at: str
    extraction_method: str
```

---

## 6. Configuration Specification

### 6.1 激进配置（初始版本）

```yaml
# SiteAgent 配置
agent:
  # 采样配置
  sampling:
    min_samples: 50
    max_samples: 200
    max_depth: 3
    timeout_per_page: 30

  # 终止条件
  termination:
    failure_rate_threshold: 0.5    # 失败率 > 50% 终止
    min_consecutive_failures: 10    # 连续失败 10 次终止
    no_target_modality_terminate: true  # 无目标形态终止

  # 成本控制
  cost_control:
    max_time_minutes: 30
    max_pages_total: 500
    max_tokens_per_extraction: 5000

  # 提取配置
  extraction:
    js_render: true                # 默认使用 JS 渲染
    wait_for_selector: 5000        # 等待选择器出现
    screenshot_on_error: true
```

### 6.2 形态特定配置

```yaml
# 各形态提取器配置
extractors:
  text:
    min_content_length: 100
    remove_boilerplate: true

  tabular:
    require_table_headers: true
    max_tables_per_page: 10

  json:
    validate_schema: true
    max_json_size_kb: 100

  pdf:
    ocr_enabled: true
    max_pages: 50

  image:
    ocr_enabled: true
    max_image_size_mb: 10

  api:
    follow_redirects: true
    max_response_size_mb: 5
```

---

## 7. Deployment & Containerization

### 7.1 Dockerfile

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/
COPY . .
RUN playwright install --with-deps chromium
EXPOSE 8000
CMD ["python", "-m", "agent.main"]
```

### 7.2 环境变量

```bash
# 必填
SITE_URL=https://example.com
TARGET_MODALITY=tabular
USER_GOAL=提取商品价格

# 可选
MAX_SAMPLES=150
COST_LIMIT_USD=5.0
```

---

## Appendix A: Agent State Machine

```
┌──────┐    run()    ┌────────────┐    no_target    ┌──────────┐
│ Idle │ ──────────> │  Mapping   │ ──────────────>│Terminated│
└──────┘             └────────────┘               └──────────┘
                         │
                         ▼
                  ┌────────────┐
                  │  Sampling  │◄────┐
                  └────────────┘     │
                         │           │
                         ▼           │
                  ┌────────────┐     │
                  │ Extracting │     │
                  └────────────┘     │
                         │           │ strong_anti_bot
                         ▼           │
                  ┌────────────┐     │
                  │ Reporting  │─────┘
                  └────────────┘
                         │
                         ▼
                  ┌────────────┐
                  │ Completed  │
                  └────────────┘
```

---

## Appendix B: Output Artifacts

| 文件 | 说明 |
|------|------|
| `reconnaissance_report.json` | 结构化报告数据 |
| `reconnaissance_report.md` | Markdown 人类可读报告 |
| `sample_data.json` | 真实提取的样本数据 |
| `extraction_errors.json` | 提取错误日志（如有） |

---

**Document Version**: 2.0.0
**Last Updated**: 2026-02-20
**Key Changes**: 数据侦察架构，单一目标形态，真实采样，侦察报告输出
