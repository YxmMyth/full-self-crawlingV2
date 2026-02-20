# Full-Self-Crawling 前端可视化面板设计文档

**文档版本**: v2.0.0  
**发布日期**: 2026-02-17  
**文档角色**: 前端可视化面板设计规范（面向 Coding Agent 的实现规范）  
**适用对象**: 前端开发者、Coding Agent、系统集成工程师

**v2.0.0 核心变更（新增用户展示面板）**:
1. **架构分拆**：将前端系统分为"开发者工作台（Developer Dashboard）"和"用户展示面板（User Viewer）"两个并列模块，明确不同用户的使用场景和功能边界。
2. **用户展示面板**：新增面向终端用户的展示面板（§11 User Viewer），包括需求输入面板、任务进度面板、结果展示面板（6 种渲染组件）和导出面板，完全由 `display_manifest.json` 驱动动态渲染。
3. **数据接口新增**：为 User Viewer 新增 5 个 API 端点（任务创建、确认、进度查询、展示清单获取、结果获取），与 Developer Dashboard 的数据接口完全隔离。
4. **实现分阶段扩展**：在原有 Phase A/B/C 基础上新增 Phase D/E/F，分别对应 User Viewer 静态布局、动态渲染和完整闭环的实现。
5. **映射关系更新**：在 §6 映射表中新增 User Viewer 与 AGENTS.md 中 §30（数据模型）、§31（用户交互）、§32（站点知识库）的对应关系。

---

## 0. 架构概述（v2.0.0 新增）

前端系统分为两个并列模块：

1. **开发者工作台（Developer Dashboard）**：面向系统开发者、运维工程师和调试人员，展示状态机、预算、事件流、LLM 路由、诊断链路等系统内部细节。**本文档 §1-§10 的原有内容全部属于 Developer Dashboard。**

2. **用户展示面板（User Viewer）**：面向终端用户，提供自然语言需求输入、简化的任务进度追踪和根据内容类型动态渲染的结果展示。**详见 §11 User Viewer。**

**访问路径**：
- Developer Dashboard: `/dashboard`
- User Viewer: `/viewer`

## 1. 文档定位（Developer Dashboard）

### 1.1 角色定义

本文档定义 Full-Self-Crawling 系统的两个前端模块：**开发者工作台（Developer Dashboard）** 和 **用户展示面板（User Viewer）**。§1-§10 定义 Developer Dashboard，§11 定义 User Viewer。

本文档定义：
- 前端架构与技术栈
- 页面布局与组件设计（Developer Dashboard + User Viewer）
- 数据接口契约
- 与 AGENTS.md 的映射关系
- 样式规范
- 实现分阶段计划

### 1.2 与 AGENTS.md 的关系

**Developer Dashboard** 消费 `AGENTS (1).md` 中定义的系统内部数据契约：
- §5 双层状态机（顶层状态机 + Crawl 子状态机）
- §27 LLM 路由契约（角色、模型、fallback）
- §16 工件与报告契约（必需工件、RunSummary）
- §18 监控与事件契约（指标、事件类型）
- §3 Runtime Truth（autonomy_budget、graph_limits）

**User Viewer** 消费 `AGENTS (1).md` 中定义的产品层数据契约：
- §30 数据模型契约（CrawlRecord、DisplayManifest）
- §31 用户交互模型（IntentContract、ClarificationCard、TaskCompletionNotification）
- §32 站点知识库契约（用于决策参考和风险提示）

前端面板通过 `serve` 命令（§15.4）提供的端点获取实时数据，并以可视化方式展示系统运行状态。

---

## 2. 设计目标（Developer Dashboard）

开发者工作台旨在提供以下能力：

1. **实时可视化系统运行状态**：展示当前状态机节点、执行进度、成功/失败率。
2. **状态机流程追踪**：可视化顶层状态机和 Crawl 子状态机的流转，支持节点状态着色（已完成/进行中/失败）。
3. **Strategy Agent 循环监控**：展示 Sense→Orient→Act→Verify→Learn 的当前阶段、已完成轮次、决策记录。
4. **预算消耗监控**：可视化 autonomy_budget（per_iteration 和 per_run）的各项额度进度条，实时展示剩余/已消耗。
5. **LLM 路由状态监控**：展示各角色当前使用的模型、fallback 事件、跨链使用情况。
6. **事件流实时追踪**：滚动展示系统事件（§18.2），支持按类型过滤。
7. **工件浏览与报告查看**：列出已生成工件（§16.1），支持点击查看内容。
8. **诊断与修复追踪**：展示 Diagnose→Plan→Apply→Verify→Commit/Rollback 的修复链路。

---

## 3. 技术栈

### 3.1 核心技术选型

```yaml
frontend_tech_stack:
  application_type: 单页应用 (SPA)
  runtime: 纯前端（无服务端渲染）
  
  core_stack:
    html: HTML5
    css: CSS3 + CSS Variables（用于主题管理）
    javascript: ES6+ (Vanilla JS，不依赖 React/Vue/Angular)
  
  visualization_library:
    name: D3.js
    version: ">=7.8.0"
    rationale: 与 runtime_truth.report_contract.visualization_style (d3_high_density) 一致
  
  data_loading:
    static_mode: JSON 文件加载（通过 fetch API）
    realtime_mode: WebSocket 或 Server-Sent Events (SSE)
    rationale: 支持静态报告查看和实时监控两种模式
  
  theme:
    style: 深色科技感主题
    color_scheme: 高对比度、易读性优先
  
  dependencies:
    - d3.js (可视化)
    - 无其他外部依赖（避免引入庞大框架）
```

### 3.2 无后端依赖说明

前端面板完全独立运行，数据获取方式：
1. **静态模式**：从 `./output/{run_id}/` 目录加载 JSON 工件（通过文件服务器）
2. **实时模式**：连接 `serve` 命令提供的 WebSocket/SSE 端点
3. **混合模式**：先加载历史数据（JSON），再订阅实时更新（WebSocket/SSE）

---

## 4. 页面布局与组件设计

### 4.1 整体布局

```text
+------------------------------------------------------------------+
|                        顶部导航栏 (Header)                          |
|  Logo | Run ID | 当前状态 | 执行时间 | 预算剩余 | 刷新按钮           |
+------------------------------------------------------------------+
|                                                                  |
|  +-------------------------+  +-------------------------------+  |
|  |                         |  |                               |  |
|  |   顶层状态机面板         |  |   Strategy Agent 循环仪表盘   |  |
|  |   (State Machine)       |  |   (Agent Loop Dashboard)      |  |
|  |                         |  |                               |  |
|  +-------------------------+  +-------------------------------+  |
|                                                                  |
|  +-------------------------+  +-------------------------------+  |
|  |                         |  |                               |  |
|  |  Crawl 子状态机面板      |  |   Autonomy Budget 面板        |  |
|  |  (Crawl Subflow)        |  |   (Budget Monitor)            |  |
|  |                         |  |                               |  |
|  +-------------------------+  +-------------------------------+  |
|                                                                  |
|  +-------------------------+  +-------------------------------+  |
|  |                         |  |                               |  |
|  |  LLM 路由状态面板        |  |   诊断与修复追踪面板          |  |
|  |  (LLM Routing)          |  |   (Repair Tracker)            |  |
|  |                         |  |                               |  |
|  +-------------------------+  +-------------------------------+  |
|                                                                  |
|  +----------------------------------------------------------+   |
|  |                                                          |   |
|  |               事件流面板 (Event Stream)                   |   |
|  |                                                          |   |
|  +----------------------------------------------------------+   |
|                                                                  |
|  +----------------------------------------------------------+   |
|  |                                                          |   |
|  |             工件浏览器 (Artifacts Browser)                |   |
|  |                                                          |   |
|  +----------------------------------------------------------+   |
|                                                                  |
+------------------------------------------------------------------+
```

### 4.2 组件详细设计

#### 4.2.1 顶层状态机面板 (State Machine Panel)

**功能**：可视化顶层状态机流程图，展示 Decide1→Scan→Decide2→Crawl→...→Finalize 的流转。

**数据源**：`/api/state-machine/current`（实时）或 `summary.json`（静态）

**可视化设计**：
- 使用 D3.js 绘制流程图（节点 + 边）
- 节点形状：圆角矩形
- 节点状态着色：
  - 已完成：绿色 (#4CAF50)
  - 进行中：蓝色（闪烁动画，#2196F3）
  - 失败：红色 (#F44336)
  - 未执行：灰色 (#757575)
- 当前节点高亮（加粗边框 + 发光效果）
- 鼠标悬停显示节点详情（执行时间、输入输出）

**交互行为**：
- 点击节点：在右侧弹出详情面板，显示该节点的输入/输出数据
- 支持拖拽调整节点位置（可选）

**数据格式**：
```json
{
  "current_node": "Crawl",
  "nodes": [
    {"id": "Decide1", "status": "completed", "duration_sec": 2.5},
    {"id": "Scan", "status": "completed", "duration_sec": 15.3},
    {"id": "Decide2", "status": "completed", "duration_sec": 1.2},
    {"id": "Crawl", "status": "in_progress", "duration_sec": 45.0},
    {"id": "Finalize", "status": "pending", "duration_sec": null}
  ],
  "edges": [
    {"from": "Decide1", "to": "Scan"},
    {"from": "Scan", "to": "Decide2"},
    {"from": "Decide2", "to": "Crawl"},
    {"from": "Crawl", "to": "Finalize"}
  ]
}
```

---

#### 4.2.2 Crawl 子状态机面板 (Crawl Subflow Panel)

**功能**：嵌套展示 Crawl 节点的子状态机（PreCrawlMicroScan→StrategySelect→ExecuteBatch→VerifyBatch）。

**数据源**：`/api/crawl-subflow/current`（实时）或 `summary.json`（静态）

**可视化设计**：
- 类似顶层状态机，但布局更紧凑
- 使用虚线边框标识为子流程
- 状态着色规则与顶层状态机一致

**交互行为**：
- 点击节点：显示批次详情（成功/失败页面数、失败样本）

**数据格式**：
```json
{
  "current_node": "ExecuteBatch",
  "batch_no": 2,
  "nodes": [
    {"id": "PreCrawlMicroScan", "status": "completed", "duration_sec": 3.2},
    {"id": "StrategySelect", "status": "completed", "duration_sec": 0.5},
    {"id": "ExecuteBatch", "status": "in_progress", "duration_sec": 20.0, "success": 15, "failed": 5},
    {"id": "VerifyBatch", "status": "pending", "duration_sec": null}
  ]
}
```

---

#### 4.2.3 Strategy Agent 循环仪表盘 (Agent Loop Dashboard)

**功能**：展示 Strategy Agent 的 Sense→Orient→Act→Verify→Learn 循环状态。

**数据源**：`/api/strategy-agent/status`（实时）或 `summary.json`（静态）

**可视化设计**：
- 圆形仪表盘（类似时钟），5 个阶段均匀分布
- 当前阶段高亮（发光 + 指针指向）
- 中央显示已完成轮次数（如 "2/6"）
- 下方列表展示历史决策记录（最近 5 条）

**交互行为**：
- 点击阶段：展开该阶段的详细数据（如 Sense 阶段的证据、Orient 阶段的决策）

**数据格式**：
```json
{
  "current_phase": "Act",
  "completed_iterations": 2,
  "max_iterations": 6,
  "decisions": [
    {"iteration": 2, "phase": "Orient", "action": "plugin_update", "confidence": 0.95},
    {"iteration": 1, "phase": "Orient", "action": "strategy_switch", "confidence": 0.80}
  ]
}
```

---

#### 4.2.4 Autonomy Budget 面板 (Budget Monitor)

**功能**：可视化 autonomy_budget（per_iteration 和 per_run）的各项额度进度条。

**数据源**：`/api/budget/status`（实时）或 `summary.json`（静态）

**可视化设计**：
- 两组进度条：per_iteration 和 per_run
- 每组包含多个子项（如 max_change_plans, max_files_changed, max_lines_changed, ...）
- 进度条着色：
  - 安全：绿色（< 70%）
  - 警告：黄色（70%-90%）
  - 危险：红色（> 90%）
- 显示已消耗/总额度（如 "5 / 12"）

**交互行为**：
- 鼠标悬停显示详细消耗记录

**数据格式**：
```json
{
  "per_iteration": {
    "max_change_plans": {"consumed": 1, "limit": 2},
    "max_files_changed": {"consumed": 5, "limit": 12},
    "max_lines_changed": {"consumed": 350, "limit": 800},
    "max_tool_calls": {"consumed": 18, "limit": 40},
    "max_verify_fast_runs": {"consumed": 1, "limit": 2}
  },
  "per_run": {
    "max_iterations": {"consumed": 2, "limit": 6},
    "max_plugin_update_apply": {"consumed": 1, "limit": 3},
    "max_strategy_switch": {"consumed": 0, "limit": 3},
    "max_patch_apply": {"consumed": 0, "limit": 1},
    "max_replan": {"consumed": 0, "limit": 2}
  }
}
```

---

#### 4.2.5 LLM 路由状态面板 (LLM Routing Panel)

**功能**：展示各角色当前使用的模型、fallback 事件、跨链使用情况。

**数据源**：`/api/llm-routing/status`（实时）或 `summary.json`（静态）

**可视化设计**：
- 表格布局：角色 | 当前模型 | Fallback 次数 | 跨链次数
- 角色列表：orchestrator, coding, page_analysis
- 当前模型高亮（绿色），fallback 模型灰色
- Fallback 事件以时间轴展示（最近 10 条）

**交互行为**：
- 点击 Fallback 事件：查看详细原因（超时、错误码、错误信息）

**数据格式**：
```json
{
  "roles": [
    {
      "role": "orchestrator",
      "primary_model": "glm_general",
      "current_model": "glm_general",
      "fallback_count": 0,
      "cross_chain_count": 0
    },
    {
      "role": "coding",
      "primary_model": "glm_coding",
      "current_model": "glm_general",
      "fallback_count": 1,
      "cross_chain_count": 1
    }
  ],
  "fallback_events": [
    {
      "timestamp": "2026-02-16T16:10:30Z",
      "role": "coding",
      "from_model": "glm_coding",
      "to_model": "glm_general",
      "reason": "timeout"
    }
  ]
}
```

---

#### 4.2.6 事件流面板 (Event Stream Panel)

**功能**：实时滚动展示系统事件（§18.2 定义的事件类型）。

**数据源**：WebSocket/SSE 推送或轮询 `/api/events`

**可视化设计**：
- 滚动列表（类似控制台日志）
- 每条事件显示：时间戳 | 类型 | 节点 | 简要信息
- 事件类型着色：
  - state_transition：蓝色
  - llm_call：紫色
  - decision_made：绿色
  - failure_detected：红色
  - repair_started：黄色
  - repair_completed：绿色
  - budget_warning：橙色
- 支持按类型过滤（多选框）

**交互行为**：
- 点击事件：展开详细信息（完整 payload）
- 支持暂停/恢复滚动
- 支持搜索（按关键词）

**数据格式**：
```json
{
  "events": [
    {
      "timestamp": "2026-02-16T16:10:35Z",
      "type": "state_transition",
      "node": "Crawl",
      "message": "Entered Crawl node",
      "payload": {...}
    },
    {
      "timestamp": "2026-02-16T16:10:40Z",
      "type": "failure_detected",
      "node": "Crawl",
      "message": "10 pages failed with selector_drift",
      "payload": {...}
    }
  ]
}
```

---

#### 4.2.7 工件浏览器 (Artifacts Browser)

**功能**：列出 §16.1 定义的必需工件，支持点击查看内容。

**数据源**：`/api/artifacts/list`（实时）或静态文件索引

**可视化设计**：
- 文件列表（图标 + 文件名 + 大小 + 生成时间）
- 必需工件（§16.1）标记为"必需"徽章
- 已生成工件显示绿色勾选，未生成显示灰色占位

**交互行为**：
- 点击文件：在右侧面板或新标签页中打开
- JSON 文件：以格式化 JSON 展示
- HTML 文件：在 iframe 中预览
- 其他文件：提供下载链接

**数据格式**：
```json
{
  "artifacts": [
    {
      "name": "result.json",
      "required": true,
      "exists": true,
      "size_bytes": 1024000,
      "created_at": "2026-02-16T16:12:00Z",
      "url": "/artifacts/result.json"
    },
    {
      "name": "diagnosis.json",
      "required": true,
      "exists": true,
      "size_bytes": 5120,
      "created_at": "2026-02-16T16:11:30Z",
      "url": "/artifacts/diagnosis.json"
    },
    {
      "name": "report.html",
      "required": true,
      "exists": false,
      "size_bytes": null,
      "created_at": null,
      "url": null
    }
  ]
}
```

---

#### 4.2.8 诊断与修复追踪面板 (Repair Tracker)

**功能**：展示 Diagnose→Plan→Apply→Verify→Commit/Rollback 的修复链路。

**数据源**：`/api/repair/status`（实时）或 `summary.json`（静态）

**可视化设计**：
- 线性流程图（左到右）
- 节点：Diagnose → PluginUpdatePlan/PatchPlan → Apply → Verify → Commit/Rollback
- 节点状态着色（与状态机面板一致）
- 每个节点下方显示关键信息：
  - Diagnose：failure_type, confidence
  - Plan：action_type, risk_level
  - Verify：pass/fail, rollback_triggered

**交互行为**：
- 点击节点：查看详细数据（诊断报告、更新 diff、验证日志）

**数据格式**：
```json
{
  "repair_chain": [
    {"node": "Diagnose", "status": "completed", "failure_type": "selector_drift", "confidence": 0.95},
    {"node": "PluginUpdatePlan", "status": "completed", "action_type": "plugin_update", "risk_level": "low"},
    {"node": "PluginUpdateApply", "status": "completed", "files_changed": 1},
    {"node": "Verify", "status": "completed", "pass": true},
    {"node": "Commit", "status": "completed"}
  ]
}
```

---

## 5. 数据接口契约

本章节定义前端需要消费的数据接口，所有接口由 `serve` 命令提供。

### 5.1 REST API 端点

#### 5.1.1 健康检查

```
GET /healthz
Response: {"status": "ok"}
```

#### 5.1.2 当前运行状态

```
GET /api/status
Response:
{
  "run_id": "run_20260216_160633",
  "site": "example.com",
  "current_node": "Crawl",
  "execution_time_sec": 120,
  "exit_code": null
}
```

#### 5.1.3 状态机当前状态

```
GET /api/state-machine/current
Response: (参见 §4.2.1 数据格式)
```

#### 5.1.4 Crawl 子状态机状态

```
GET /api/crawl-subflow/current
Response: (参见 §4.2.2 数据格式)
```

#### 5.1.5 Strategy Agent 状态

```
GET /api/strategy-agent/status
Response: (参见 §4.2.3 数据格式)
```

#### 5.1.6 预算状态

```
GET /api/budget/status
Response: (参见 §4.2.4 数据格式)
```

#### 5.1.7 LLM 路由状态

```
GET /api/llm-routing/status
Response: (参见 §4.2.5 数据格式)
```

#### 5.1.8 事件列表

```
GET /api/events?since={timestamp}&limit={n}
Response: (参见 §4.2.6 数据格式)
```

#### 5.1.9 工件列表

```
GET /api/artifacts/list
Response: (参见 §4.2.7 数据格式)
```

#### 5.1.10 工件内容

```
GET /api/artifacts/{filename}
Response: 文件内容（JSON/HTML/Text）
```

#### 5.1.11 修复链路状态

```
GET /api/repair/status
Response: (参见 §4.2.8 数据格式)
```

---

### 5.2 实时数据推送

#### 5.2.1 WebSocket 端点

```
WebSocket: ws://localhost:8080/ws/events

消息格式：
{
  "type": "event",
  "data": {
    "timestamp": "2026-02-16T16:10:35Z",
    "type": "state_transition",
    "node": "Crawl",
    "message": "...",
    "payload": {...}
  }
}
```

#### 5.2.2 Server-Sent Events (SSE) 端点

```
GET /api/events/stream

事件格式：
data: {"timestamp": "...", "type": "state_transition", ...}

data: {"timestamp": "...", "type": "failure_detected", ...}
```

---

### 5.3 静态模式数据加载

当 `serve` 命令未运行时，前端可从静态工件目录加载数据：

```
/output/{run_id}/
├── summary.json          → /api/status, /api/state-machine/current
├── budget.json           → /api/budget/status
├── llm_routing.json      → /api/llm-routing/status
├── events.json           → /api/events
├── artifacts/
│   ├── result.json
│   ├── diagnosis.json
│   └── report.html
```

前端自动检测 `serve` 端点是否可用：
1. 尝试访问 `/healthz`
2. 若成功，使用实时模式（REST API + WebSocket/SSE）
3. 若失败，切换到静态模式（加载 JSON 文件）

---

## 6. 与 AGENTS.md 的映射关系

### 6.1 Developer Dashboard 映射

| 前端组件                  | AGENTS.md 章节                   | 数据契约                              |
|--------------------------|----------------------------------|--------------------------------------|
| 顶层状态机面板            | §5.1 顶层状态机                  | state_machine.top_level              |
| Crawl 子状态机面板        | §5.2 Crawl 子状态机              | state_machine.crawl_subflow          |
| Strategy Agent 循环仪表盘 | §4.4 策略智能体统一循环           | autonomy_budget (per_iteration/run)  |
| Autonomy Budget 面板      | §3 runtime_truth.autonomy_budget | autonomy_budget + graph_limits       |
| LLM 路由状态面板          | §27 LLM 调用规格                 | llm_routing                          |
| 事件流面板                | §18 监控与事件契约               | §18.2 事件类型                       |
| 工件浏览器                | §16 工件与报告契约               | §16.1 必需工件                       |
| 诊断与修复追踪面板        | §5.3 插件更新闭环 + §5.4 补丁闭环 | plugin_update_subflow + patch_subflow|

### 6.2 User Viewer 映射

| 前端组件                  | AGENTS.md 章节                   | 数据契约                              |
|--------------------------|----------------------------------|--------------------------------------|
| 需求输入面板              | §31.2 自然语言→IntentContract    | parse_user_intent (§27.4.1)          |
| 质询卡片                  | §31.3 质询卡片的数据格式         | ClarificationCard, ClarificationItem |
| 任务进度面板              | §31.5 结果通知契约               | TaskCompletionNotification           |
| 结果展示面板              | §30.2 展示清单（DisplayManifest）| DisplayManifest, CrawlRecord         |
| Article 渲染组件          | §30.1 CrawlRecord (content_type: article) | CrawlRecord + DisplayManifest        |
| Gallery 渲染组件          | §30.1 CrawlRecord (content_type: image)   | CrawlRecord.media_urls               |
| VideoGrid 渲染组件        | §30.1 CrawlRecord (content_type: video)   | CrawlRecord.media_urls               |
| CodeViewer 渲染组件       | §30.1 CrawlRecord (content_type: code)    | CrawlRecord.code_blocks              |
| DataTable 渲染组件        | §30.1 CrawlRecord (content_type: product/table) | CrawlRecord.structured_data  |
| CardList 渲染组件         | §30.1 CrawlRecord (content_type: mixed)   | CrawlRecord (通用 fallback)          |
| 导出面板                  | §16.1 必需工件                   | result.json, share_manifest.json     |

---

## 7. 样式规范

### 7.1 深色主题色板

```css
:root {
  /* 背景色 */
  --bg-primary: #0d1117;       /* 主背景 */
  --bg-secondary: #161b22;     /* 次级背景（面板） */
  --bg-tertiary: #21262d;      /* 三级背景（嵌套面板） */
  
  /* 主色 */
  --primary: #58a6ff;          /* 品牌蓝 */
  --secondary: #8b949e;        /* 次要灰 */
  
  /* 状态色 */
  --success: #4CAF50;          /* 成功/完成 */
  --warning: #FFC107;          /* 警告 */
  --error: #F44336;            /* 错误/失败 */
  --info: #2196F3;             /* 信息/进行中 */
  
  /* 文本色 */
  --text-primary: #c9d1d9;     /* 主文本 */
  --text-secondary: #8b949e;   /* 次要文本 */
  --text-tertiary: #6e7681;    /* 三级文本 */
  
  /* 边框色 */
  --border-primary: #30363d;   /* 主边框 */
  --border-secondary: #21262d; /* 次要边框 */
  
  /* 强调色 */
  --accent-purple: #bc8cff;    /* LLM 调用 */
  --accent-orange: #FF9800;    /* 预算警告 */
}
```

### 7.2 字体规范

```css
:root {
  /* 字体族 */
  --font-family-base: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-family-mono: "SF Mono", Monaco, "Cascadia Code", "Courier New", monospace;
  
  /* 字号 */
  --font-size-xs: 12px;
  --font-size-sm: 14px;
  --font-size-base: 16px;
  --font-size-lg: 18px;
  --font-size-xl: 24px;
  --font-size-2xl: 32px;
  
  /* 字重 */
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-bold: 700;
}
```

### 7.3 动画与过渡效果

```css
/* 通用过渡 */
.transition {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 闪烁动画（进行中状态） */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

.in-progress {
  animation: pulse 2s ease-in-out infinite;
}

/* 发光效果（高亮节点） */
.highlight {
  box-shadow: 0 0 10px var(--primary), 0 0 20px var(--primary);
}

/* 滑入动画（面板展开） */
@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.slide-in {
  animation: slideIn 0.3s ease-out;
}
```

### 7.4 响应式布局断点

```css
/* 断点定义 */
:root {
  --breakpoint-sm: 640px;   /* 小屏幕 */
  --breakpoint-md: 768px;   /* 中等屏幕 */
  --breakpoint-lg: 1024px;  /* 大屏幕 */
  --breakpoint-xl: 1280px;  /* 超大屏幕 */
}

/* 响应式布局 */
@media (max-width: 768px) {
  /* 小屏幕：单列布局 */
  .grid-2-cols { grid-template-columns: 1fr; }
}

@media (min-width: 769px) and (max-width: 1024px) {
  /* 中等屏幕：双列布局 */
  .grid-2-cols { grid-template-columns: repeat(2, 1fr); }
}

@media (min-width: 1025px) {
  /* 大屏幕：多列布局 */
  .grid-2-cols { grid-template-columns: repeat(2, 1fr); }
  .grid-3-cols { grid-template-columns: repeat(3, 1fr); }
}
```

---

## 8. 实现分阶段计划

### Phase A - 静态布局 + Mock 数据

**目标**：建立完整的页面布局和组件结构，使用 mock 数据展示。

**交付内容**：
1. HTML 页面结构（index.html）
2. CSS 样式表（styles.css）
3. JavaScript 主文件（app.js）
4. Mock 数据文件（mock-data.json）
5. 所有 8 个组件的静态渲染（使用 mock 数据）

**验收条件**：
- 在浏览器中打开 index.html，所有组件正确渲染
- 使用 mock 数据可正确展示状态机流程图
- 预算进度条可正确显示百分比
- 事件流可正确滚动展示
- 样式符合深色主题规范

---

### Phase B - 接入 serve 端点的实时数据

**目标**：替换 mock 数据为真实数据，实现与 `serve` 命令的集成。

**交付内容**：
1. 数据加载模块（data-loader.js）
2. WebSocket/SSE 客户端（realtime-client.js）
3. 自动切换静态/实时模式的逻辑
4. 数据更新时的组件刷新逻辑

**验收条件**：
- 启动 `serve` 命令后，前端可自动连接并显示实时数据
- 状态机节点状态变化时，前端可实时更新
- 事件流可实时接收新事件并滚动展示
- `serve` 命令停止后，前端可自动切换到静态模式

---

### Phase C - 交互增强（过滤、搜索、时间轴回放）

**目标**：增强用户交互体验，提供高级功能。

**交付内容**：
1. 事件流过滤功能（按类型多选）
2. 事件流搜索功能（按关键词）
3. 工件浏览器的文件预览功能
4. 状态机节点点击查看详情功能
5. 预算面板的详细消耗记录悬停提示
6. 时间轴回放功能（可选，用于调试历史运行）

**验收条件**：
- 事件流可按类型过滤（支持多选）
- 事件流搜索可正确匹配关键词
- 点击状态机节点可弹出详情面板
- 点击工件可在右侧面板或新标签页中查看
- 预算进度条悬停可显示详细消耗记录
- （可选）时间轴回放可重现历史运行过程

---

### Phase D - User Viewer 静态布局 + 6 种渲染组件（使用 mock 数据）

**目标**：实现 User Viewer 的所有页面布局和 6 种渲染组件，使用 mock 数据测试。

**交付内容**：
1. User Viewer 页面结构（viewer.html）
2. 需求输入面板组件（input-panel.js）
3. 质询卡片组件（clarification-card.js）
4. 任务进度面板组件（progress-panel.js）
5. 6 种渲染组件（ArticleViewer, ImageGallery, VideoGrid, CodeViewer, DataTable, CardList）
6. 导出面板组件（export-panel.js）
7. Mock DisplayManifest 和 CrawlRecord 数据

**验收条件**：
- 访问 `/viewer` 可看到需求输入面板
- 提交需求后（mock）可看到质询卡片，所有交互元素可正常渲染
- 确认后（mock）可看到进度面板
- 进度完成后（mock）可看到结果展示面板
- 6 种渲染组件均可使用 mock 数据正确渲染
- 样式符合深色主题规范

---

### Phase E - 接入后端 API + DisplayManifest 驱动的动态渲染

**目标**：实现 §11.6 定义的 5 个 API 端点（后端），前端接入真实 API。

**交付内容**：
1. 后端 API 实现（5 个端点）
2. 前端 API 客户端模块（api-client.js）
3. DisplayManifest 驱动的动态渲染逻辑
4. 结果数据分页加载逻辑

**验收条件**：
- 提交真实需求可获得真实的质询卡片
- 确认后可启动真实任务并获得 `run_id`
- 进度面板可实时显示真实任务进度
- 任务完成后可获取真实的 DisplayManifest
- 结果展示面板根据真实 DisplayManifest 正确选择渲染组件
- 分页加载结果数据可正常工作

---

### Phase F - 需求输入 + 质询交互 + 进度追踪完整闭环

**目标**：完善所有交互体验，实现完整的用户流程闭环。

**交付内容**：
1. 需求输入面板的示例提示、输入验证、错误处理
2. 质询卡片的多选、文本输入、必填项校验
3. 进度追踪的实时性优化（SSE 或 WebSocket）
4. 导出功能实现（JSON/CSV 下载、分享链接生成）
5. 用户反馈机制（加载动画、错误提示、成功提示）

**验收条件**：
- 用户可流畅完成"输入需求 → 确认质询 → 查看进度 → 浏览结果 → 导出数据"的完整流程
- 质询卡片的所有交互元素（下拉、输入、多选）均可正常工作
- 进度追踪可实时更新（延迟 < 3 秒）
- 导出功能可正常工作（JSON/CSV 下载成功，分享链接可访问）
- 错误处理完善（网络错误、API 错误、数据格式错误）

---

## 9. 验收标准

### 9.1 功能验收

1. **状态机可追踪**：所有 §5 定义的状态机节点（Decide1, Scan, Decide2, Crawl, ...）可在面板中追踪，且状态着色正确。
2. **预算可视化**：Budget 进度条与 runtime_truth 默认值一致（per_iteration: max_change_plans=2, max_files_changed=12, ...）。
3. **事件流可过滤**：事件流可按 §18.2 定义的事件类型过滤（state_transition, llm_call, decision_made, ...）。
4. **工件浏览完整**：工件浏览器可展示 §16.1 全部必需工件（result, diagnosis, plugin_update, patch, evidence, summary, decision_card, report_html, share_manifest）。
5. **serve 集成验证**：与 serve 命令的 /healthz 端点集成验证通过（返回 {"status": "ok"}）。

### 9.2 性能验收

1. **首屏加载时间**：< 2 秒（使用静态模式）
2. **事件流滚动流畅**：每秒接收 10+ 事件时，滚动无卡顿
3. **D3.js 渲染性能**：状态机流程图（30+ 节点）渲染时间 < 500ms

### 9.3 兼容性验收

1. **浏览器兼容**：支持 Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
2. **屏幕分辨率**：支持 1280x720 至 3840x2160 分辨率
3. **响应式布局**：在移动端（< 768px）可正确显示单列布局

---

## 10. 附录：参考资源

### 10.1 D3.js 学习资源

- [D3.js 官方文档](https://d3js.org/)
- [Observable D3 Gallery](https://observablehq.com/@d3/gallery)
- [D3 Graph Theory](https://d3-graph-gallery.com/)

### 10.2 WebSocket/SSE 资源

- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [MDN Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

### 10.3 深色主题参考

- [GitHub Dark Theme](https://github.com/settings/appearance)
- [VS Code Dark+ Theme](https://code.visualstudio.com/docs/getstarted/themes)

---

## 11. User Viewer（用户展示面板）

### 11.1 定位与目标

User Viewer 是面向终端用户的展示面板，设计理念为"极简交互 + 智能展示"。与 Developer Dashboard 不同，User Viewer 不暴露状态机、预算、LLM 路由等系统内部细节，仅提供：
1. 自然语言需求输入
2. 简化的任务进度追踪
3. 根据内容类型动态渲染的结果展示
4. 一键导出和分享功能

**核心原则**：
- **前置充分**：通过质询卡片穷尽歧义，用户确认后不再打扰。
- **执行静默**：任务执行过程中不弹窗、不打断。
- **结果智能**：根据 `display_manifest.json` 自动选择最佳渲染方式。

### 11.2 架构分拆

```text
前端系统
├── /dashboard         ← 开发者工作台（§1-§10 定义的内容）
│   └── 状态机、预算、事件流、LLM路由、诊断链路……
│
└── /viewer            ← 用户展示面板（本章节定义）
    ├── 需求输入面板   ← 自然语言输入框 + 质询卡片交互
    ├── 任务进度面板   ← 极简进度指示（"正在爬取… 已获取 42/100 条"）
    ├── 结果展示面板   ← 核心：根据 DisplayManifest 动态渲染
    │   ├── 图片类     → 瀑布流/网格画廊
    │   ├── 视频类     → 播放器卡片
    │   ├── 代码类     → 语法高亮代码块
    │   ├── 文章类     → 阅读视图（标题+正文+元数据）
    │   ├── 表格类     → 可排序/过滤的数据表格
    │   └── 混合类     → 自适应卡片布局
    └── 导出面板       ← 下载 JSON/CSV、生成分享链接
```

### 11.3 需求输入面板设计

#### 11.3.1 界面布局

- **居中大输入框**：类似搜索引擎风格，占据页面中央，placeholder 为"请用自然语言描述您的爬取需求"。
- **示例提示**：输入框下方显示 2-3 个示例需求，点击可填充到输入框（如"爬取这个电商网站的所有商品标题、价格和图片"）。
- **提交按钮**：输入框右侧的"开始分析"按钮。

#### 11.3.2 质询卡片交互

用户提交需求后，系统调用 `POST /api/task/create`（见 §11.6），返回质询卡片（`ClarificationCard`，定义见 AGENTS.md §31.2）。

**质询卡片渲染规则**：
- **标题**：明确告知用户"请确认以下爬取参数"。
- **确认项列表**：逐条渲染 `ClarificationItem`，每项包含问题描述、默认值和可选选项。
  - 如果 `options` 存在，渲染为下拉选择或多选框。
  - 如果 `options` 为空，渲染为文本输入框（填充默认值）。
  - 如果 `is_critical=true`，标记为必填项（红色星号）。
- **预估预算**：以卡片形式展示 `estimated_budget`（预估时间、请求数、成本）。
- **风险提示**：如果 `risk_warnings` 非空，以黄色警告框形式展示。
- **确认按钮**：卡片底部的"确认并开始"按钮，点击后调用 `POST /api/task/confirm`。

#### 11.3.3 确认后的状态变化

用户确认后，需求输入面板收缩到页面顶部（缩小为一行标题栏，显示任务名称和状态），任务进度面板展开。

### 11.4 任务进度面板设计

**极简设计**，不暴露状态机细节：

- **进度条**：水平进度条，显示"已完成 / 总数"（如"42 / 100"）。
- **当前阶段文字描述**：简化的文字说明，如：
  - "正在分析页面结构…"（Scan 阶段）
  - "正在抓取内容…"（Crawl 阶段）
  - "正在修复异常…"（Diagnose 或修复闭环）
  - "正在生成结果…"（Finalize 阶段）
- **预估剩余时间**：基于已完成数量和平均速度计算（如"预计剩余 3 分钟"）。
- **不暴露的内容**：状态机节点、预算消耗、LLM 路由信息、事件流细节。

**数据接口**：`GET /api/task/{run_id}/progress`（见 §11.6）。

**刷新策略**：每 2 秒轮询一次进度接口，或使用 SSE 实时推送。

### 11.5 结果展示面板设计

#### 11.5.1 核心机制

结果展示面板完全由 `display_manifest.json` 驱动：
1. 任务完成后，从 `GET /api/task/{run_id}/display-manifest` 获取 DisplayManifest。
2. 根据 `layout` 字段选择对应的渲染组件。
3. 从 `GET /api/task/{run_id}/results` 分页获取爬取结果。

**前端不做内容类型推断**，完全信任 DisplayManifest 的指示。

#### 11.5.2 预定义 6 种渲染组件

| layout | 渲染组件 | 适用场景 | 关键字段 |
|--------|---------|---------|----------|
| `article` | 文章阅读视图 | 文本内容为主（新闻、博客、文档） | `primary_field`（标题）、`content`（正文）、`metadata`（元数据侧栏） |
| `gallery` | 图片瀑布流/网格画廊 | 图片为主（图库、相册、电商商品图） | `media_urls`（图片 URL 列表）、`preview_field`（缩略图） |
| `video_grid` | 视频播放器卡片网格 | 视频为主（视频网站、课程平台） | `media_urls`（视频 URL 列表）、`primary_field`（标题）、`preview_field`（封面图） |
| `code_viewer` | 语法高亮代码块列表 | 代码片段为主（GitHub、技术博客） | `code_blocks`（代码块列表，包含 language、content）、`primary_field`（文件名或标题） |
| `data_table` | 可排序/过滤/分页的数据表格 | 结构化数据为主（产品列表、统计表格） | `structured_data`（表格数据）、`sort_field`（默认排序字段）、`group_by`（分组字段） |
| `card_list` | 通用卡片列表 | 混合内容类型的 fallback | `primary_field`（卡片标题）、`preview_field`（卡片缩略图）、`metadata`（卡片元数据） |

#### 11.5.3 各渲染组件详细设计

**1. Article（文章阅读视图）**
- **布局**：双栏布局，左侧为文章正文，右侧为元数据侧栏。
- **正文区域**：
  - 标题（`primary_field`，如 "title"）
  - 正文（`content` 字段）
  - 字数统计、阅读时间估算
- **元数据侧栏**：
  - 作者（`metadata.author`）
  - 发布时间（`metadata.publish_date`）
  - 标签（`metadata.tags`）
  - 原文链接（`url`）

**2. Gallery（图片瀑布流/网格画廊）**
- **布局**：响应式瀑布流布局或固定网格布局（可切换）。
- **图片卡片**：
  - 缩略图（`preview_field` 或 `media_urls[0]`）
  - 点击放大（lightbox 模式）
  - 悬停显示标题和元数据
- **功能**：
  - 图片懒加载
  - 批量下载
  - 分享单张或整个画廊

**3. VideoGrid（视频播放器卡片网格）**
- **布局**：固定网格布局（3-4 列）。
- **视频卡片**：
  - 封面图（`preview_field`）
  - 标题（`primary_field`）
  - 点击播放（内嵌播放器或跳转）
- **播放器**：使用 HTML5 `<video>` 或嵌入第三方播放器（如 YouTube、Vimeo）。

**4. CodeViewer（语法高亮代码块列表）**
- **布局**：单列布局，代码块依次排列。
- **代码块卡片**：
  - 文件名或标题（`primary_field`）
  - 语言标签（`code_blocks[].language`）
  - 语法高亮的代码内容（使用 Prism.js 或 Highlight.js）
  - 复制按钮
- **功能**：
  - 行号显示
  - 关键词搜索
  - 导出为 Markdown

**5. DataTable（可排序/过滤/分页的数据表格）**
- **布局**：表格布局，顶部为过滤器和排序控制。
- **表格功能**：
  - 列排序（点击表头）
  - 列过滤（顶部过滤器行）
  - 分页（每页 20-50 条）
  - 导出为 CSV/Excel
- **分组显示**：如果 `group_by` 非空，按该字段分组显示（如按类别分组）。

**6. CardList（通用卡片列表）**
- **布局**：响应式卡片网格（2-3 列）。
- **卡片内容**：
  - 缩略图（`preview_field`，如果存在）
  - 标题（`primary_field`）
  - 摘要（`metadata.summary` 或截取 `content` 前 100 字）
  - 元数据标签（`metadata.tags`）
- **功能**：
  - 点击卡片展开详情
  - 按字段排序（下拉选择）
  - 按字段过滤（侧边栏过滤器）

#### 11.5.4 组件选择逻辑

前端根据 `DisplayManifest.layout` 字段选择组件：

```javascript
const renderComponents = {
  article: ArticleViewer,
  gallery: ImageGallery,
  video_grid: VideoGrid,
  code_viewer: CodeViewer,
  data_table: DataTable,
  card_list: CardList,
};

const RendererComponent = renderComponents[displayManifest.layout];
```

**容错规则**：如果 `layout` 值不在预定义列表中，默认使用 `card_list`。

### 11.6 数据接口

User Viewer 需要消费以下 API 端点（与 Developer Dashboard 的端点隔离）：

| 端点 | 方法 | 用途 | 输入 | 输出 |
|-----|------|------|------|------|
| `/api/task/create` | POST | 提交自然语言需求，返回质询卡片 | `{"user_input": str, "site_url": str}` | `{"clarification_card": ClarificationCard}` |
| `/api/task/confirm` | POST | 确认质询，启动任务 | `{"clarification_card": ClarificationCard, "user_confirmed_values": dict}` | `{"run_id": str, "status": "started"}` |
| `/api/task/{run_id}/progress` | GET | 获取简化进度信息 | - | `{"status": str, "progress": float, "current_phase": str, "records_count": int, "estimated_remaining_seconds": int}` |
| `/api/task/{run_id}/display-manifest` | GET | 获取展示清单 | - | `DisplayManifest` |
| `/api/task/{run_id}/results` | GET | 获取爬取结果（分页） | `?page=1&per_page=20` | `{"records": list[CrawlRecord], "total": int, "page": int, "per_page": int}` |

**注意**：
- `/api/task/create` 调用 AGENTS.md §27.4.1 定义的 `parse_user_intent` LLM 能力。
- `/api/task/{run_id}/display-manifest` 返回由 AGENTS.md §27.4.2 定义的 `generate_display_manifest` LLM 能力生成的清单。
- 所有端点均需要认证（如 JWT token）。

### 11.7 导出面板设计

任务完成后，结果展示面板顶部显示导出按钮：

- **下载 JSON**：下载完整的 `result.json`。
- **下载 CSV**：将结果转换为 CSV 格式（仅适用于结构化数据）。
- **生成分享链接**：生成一个带有签名的静态 HTML 链接，供其他用户访问（使用 `share_manifest.json`）。
- **打印 / PDF 导出**：针对文章类型提供打印友好页面。

### 11.8 实现分阶段计划

在原有 Phase A/B/C 基础上新增：

#### Phase D - User Viewer 静态布局 + 6 种渲染组件实现（使用 mock 数据）

**交付目标**：
- 实现 User Viewer 的所有页面布局（需求输入、进度追踪、结果展示、导出）
- 实现 6 种渲染组件（Article、Gallery、VideoGrid、CodeViewer、DataTable、CardList）
- 使用 mock 数据测试各组件的渲染效果

**验收条件**：
1. 访问 `/viewer` 可看到需求输入面板
2. 提交需求后（mock）可看到质询卡片
3. 确认后（mock）可看到进度面板
4. 进度完成后（mock）可看到结果展示面板，并根据 mock DisplayManifest 正确选择渲染组件
5. 6 种渲染组件均可使用 mock 数据正确渲染

#### Phase E - 接入后端 API + DisplayManifest 驱动的动态渲染

**交付目标**：
- 实现 §11.6 定义的 5 个 API 端点（后端实现）
- 前端接入真实 API，替换 mock 数据
- 实现 DisplayManifest 驱动的动态渲染逻辑

**验收条件**：
1. 提交真实需求可获得真实的质询卡片
2. 确认后可启动真实任务并获得 `run_id`
3. 进度面板可实时显示真实任务进度
4. 任务完成后可获取真实的 DisplayManifest 和结果数据
5. 结果展示面板根据真实 DisplayManifest 正确选择渲染组件

#### Phase F - 需求输入 + 质询交互 + 进度追踪完整闭环

**交付目标**：
- 完善需求输入面板的交互体验（示例提示、输入验证、错误处理）
- 完善质询卡片的交互体验（多选、文本输入、必填项校验）
- 完善进度追踪的实时性（SSE 或 WebSocket）
- 完善导出功能（JSON/CSV 下载、分享链接生成）

**验收条件**：
1. 用户可流畅完成"输入需求 → 确认质询 → 查看进度 → 浏览结果 → 导出数据"的完整流程
2. 质询卡片的所有交互元素（下拉、输入、多选）均可正常工作
3. 进度追踪可实时更新（延迟 < 3 秒）
4. 导出功能可正常工作（JSON/CSV 下载成功，分享链接可访问）

---

