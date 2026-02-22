# Recon Agent 能力检测测试

检测 Recon Agent 当期能力边界，验证10个不同类型的数据采集需求。

## 测试概述

| # | 数据需求 | 站点 | 数据类型 | 难度 | 阶段 |
|---|---------|------|---------|------|------|
| 5 | 学术论文 (arXiv) | PDF链接+摘要 | text, url | ⭐ | Phase 1 |
| 9 | 博客 (Medium) | 嵌套HTML+图片 | text, image | ⭐⭐ | Phase 1 |
| 2 | 新闻 (TechCrunch) | 富文本+视频 | html, video | ⭐⭐ | Phase 2 |
| 7 | 菜谱 (AllRecipes) | 配料+步骤HTML | html, image | ⭐⭐ | Phase 2 |
| 10 | 政府公告 (UK) | PDF+HTML表格 | html, pdf | ⭐⭐ | Phase 2 |
| 4 | 招聘 (Indeed) | 职位+Logo | html, image | ⭐⭐⭐ | Phase 3 |
| 3 | 数据图表 (Datawrapper) | SVG代码 | svg | ⭐⭐⭐ | Phase 3 |
| 6 | 房产 (Zillow) | 户型图SVG/PDF | svg, pdf | ⭐⭐⭐⭐ | Phase 3 |
| 1 | 电商 (Amazon) | 产品+价格+PDF | all | ⭐⭐⭐⭐⭐ | Phase 4 |
| 8 | 股票 (Yahoo) | K线图SVG | svg, real-time | ⭐⭐⭐⭐⭐ | Phase 4 |

## 目录结构

```
tests/capability_test/
├── __init__.py           # 模块导出
├── test_cases.py         # 10个测试用例定义
├── runner.py             # 测试执行器
├── result_analyzer.py    # 结果分析器
└── results/              # 测试结果输出目录
    ├── summary_*.json    # 汇总报告 (JSON)
    ├── summary_*.md      # 汇总报告 (Markdown)
    └── test_*.json       # 单个测试结果
```

## 快速开始

### 运行所有测试

```bash
python run_capability_test.py
```

### 运行指定阶段

```bash
python run_capability_test.py --phase 1    # 基础验证
python run_capability_test.py --phase 2    # 扩展验证
python run_capability_test.py --phase 3    # 增强功能
python run_capability_test.py --phase 4    # 高级挑战
```

### 运行单个测试

```bash
python run_capability_test.py --id 5       # 测试 arXiv
```

### 列出所有测试

```bash
python run_capability_test.py --list
```

## 环境要求

- Python 3.8+
- ZHIPU_API_KEY 环境变量 (用于 LLM 调用)

```bash
# PowerShell
$env:ZHIPU_API_KEY='your_api_key_here'

# CMD
set ZHIPU_API_KEY=your_api_key_here

# Linux/Mac
export ZHIPU_API_KEY='your_api_key_here'
```

## 评估标准

| 阶段 | 目标通过率 | 说明 |
|------|-----------|------|
| Phase 1 | >= 80% | 基础能力验证 |
| Phase 2 | >= 80% | 中级能力验证 |
| Phase 3 | >= 50% | 增强功能验证 |
| Phase 4 | 识别边界 | 极限能力探索 |

### 单个测试通过标准

- **执行成功**: 无异常，返回结果
- **质量分数**: >= 0.6 (可配置)
- **数据完整度**: 预期字段 >= 50% 存在
- **数据量**: >= 最少数据条数

## 能力矩阵

| 能力域 | 支持度 | 自动化 | 稳定性 |
|-------|-------|--------|--------|
| 文本/HTML提取 | ✅ | 全自动 | 高 |
| 图片URL提取 | ✅ | 全自动 | 高 |
| 图片深度验证 | ✅ | 半自动 | 中高 |
| PDF验证 | ✅ | 半自动 | 中高 |
| SVG代码提取 | ✅ | 全自动 | 高 |
| SVG语法验证 | ✅ | 全自动 | 高 |
| 动态内容处理 | ✅ | LLM生成 | 中 |
| 懒加载检测 | ⚠️ | LLM生成 | 低 |
| 速率限制处理 | ❌ | 无 | - |
| 反爬绕过 | ❌ | 无 | - |
| WebSocket处理 | ❌ | 无 | - |
| Canvas提取 | ❌ | 无 | - |

## 输出报告

### JSON 报告

```json
{
  "test_run": {
    "started_at": "2026-02-22T...",
    "total_duration_seconds": 1234.5
  },
  "overall_stats": {
    "passed": 7,
    "failed": 3,
    "pass_rate": 0.7
  },
  "phase_stats": {...},
  "capability_analysis": {...}
}
```

### Markdown 报告

自动生成包含以下内容的 Markdown 报告：
- 总体结果
- 各阶段通过率
- 能力验证结果
- 失败原因分析
- 改进建议

## 代码示例

### 基本使用

```python
import asyncio
from tests.capability_test import CapabilityTestRunner

async def run_tests():
    runner = CapabilityTestRunner()

    # 运行所有测试
    results = await runner.run_all()

    # 运行指定阶段
    # results = await runner.run_all(phase_filter=1)

    return results

asyncio.run(run_tests())
```

### 单个测试

```python
from tests.capability_test import get_test_case_by_id, CapabilityTestRunner

async def run_single():
    test_case = get_test_case_by_id(5)  # arXiv
    runner = CapabilityTestRunner()
    result = await runner.run_single_test(test_case)
    return result

asyncio.run(run_single())
```

### 结果分析

```python
from tests.capability_test import ResultAnalyzer

analyzer = ResultAnalyzer()
report = analyzer.analyze(test_results)

# 生成 Markdown 报告
md_report = analyzer.generate_markdown_report()
print(md_report)
```

## 扩展测试

### 添加新测试用例

编辑 `test_cases.py`，添加新的 `TestCase`:

```python
TestCase(
    id=11,
    name="新站点",
    url="https://example.com",
    user_goal="提取XX数据",
    data_types=["text", "image"],
    expected_fields=["title", "content"],
    difficulty=2,
    phase=2,
    min_quality_score=0.6,
    min_data_count=1,
    capabilities=["basic_html_parsing"],
)
```

### 自定义能力

编辑 `test_cases.py` 中的 `CAPABILITY_MATRIX`:

```python
CAPABILITY_MATRIX = {
    "new_capability": {
        "supported": True,
        "stability": "high"
    },
}
```

## 故障排查

### 测试失败

1. 检查 `results/` 目录中的详细日志
2. 查看单个测试的 JSON 结果
3. 确认网络连接和 API 密钥

### 常见错误

| 错误 | 原因 | 解决方案 |
|------|------|----------|
| ZHIPU_API_KEY not set | 未设置 API 密钥 | 设置环境变量 |
| Timeout | 页面加载超时 | 增加 timeout 配置 |
| Selector error | CSS 选择器失效 | 等待 Sense 阶段重新分析 |

## 版本历史

- v3.3.0 - 初始版本，支持 10 个测试用例
- 基于 CodeAct + LangGraph 架构
- 支持深度验证（图片/PDF/视频）
