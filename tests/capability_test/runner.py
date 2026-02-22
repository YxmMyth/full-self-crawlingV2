"""
Test Runner - 能力测试执行器

执行10个测试用例，收集结果并生成报告。
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent import SiteAgent
from .test_cases import TestCase, TEST_CASES, get_all_test_cases_sorted, TEST_CONFIG
from .result_analyzer import ResultAnalyzer


class TestResult:
    """单个测试用例的执行结果"""

    def __init__(self, test_case: TestCase):
        self.test_case = test_case
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.duration_seconds: float = 0
        self.success: bool = False
        self.error_message: str = ""
        self.quality_score: float = 0
        self.data_count: int = 0
        self.extracted_fields: List[str] = []
        self.sample_data: List[Dict] = []
        self.generated_code: str = ""
        self.issues: List[str] = []
        self.capabilities_used: List[str] = []
        self.raw_result: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "test_id": self.test_case.id,
            "test_name": self.test_case.name,
            "url": self.test_case.url,
            "user_goal": self.test_case.user_goal,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "success": self.success,
            "error_message": self.error_message,
            "quality_score": self.quality_score,
            "data_count": self.data_count,
            "expected_fields": self.test_case.expected_fields,
            "extracted_fields": self.extracted_fields,
            "field_coverage": len(self.extracted_fields) / len(self.test_case.expected_fields) if self.test_case.expected_fields else 0,
            "sample_data": self.sample_data[:3],  # 只保存前3条样本
            "generated_code_length": len(self.generated_code),
            "issues": self.issues,
            "capabilities_used": self.capabilities_used,
        }

    def is_passed(self) -> bool:
        """判断测试是否通过"""
        if not self.success:
            return False

        # 检查质量分数
        if self.quality_score < self.test_case.min_quality_score:
            return False

        # 检查数据量
        if self.data_count < self.test_case.min_data_count:
            return False

        # 检查字段覆盖（可选）
        if self.test_case.expected_fields:
            coverage = len(self.extracted_fields) / len(self.test_case.expected_fields)
            if coverage < 0.5:  # 至少50%字段
                return False

        return True


class CapabilityTestRunner:
    """能力测试执行器"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = {**TEST_CONFIG, **(config or {})}
        self.results: List[TestResult] = []
        self.agent: Optional[SiteAgent] = None

        # 创建结果目录
        self.results_dir = Path(project_root) / self.config["results_dir"]
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def _print_header(self, text: str):
        """打印标题"""
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)

    def _print_test_start(self, test_case: TestCase):
        """打印测试开始"""
        print(f"\n{'=' * 60}")
        print(f"  测试 #{test_case.id}: {test_case.name}")
        print(f"  阶段: Phase {test_case.phase} | 难度: {'⭐' * test_case.difficulty}")
        print(f"  URL: {test_case.url}")
        print(f"  目标: {test_case.user_goal}")
        print(f"{'=' * 60}\n")

    def _print_test_result(self, result: TestResult):
        """打印测试结果"""
        status = "✅ 通过" if result.is_passed() else "❌ 失败"
        print(f"\n{status}")
        print(f"  质量分数: {result.quality_score:.2f} / {result.test_case.min_quality_score}")
        print(f"  数据数量: {result.data_count} 条")
        print(f"  字段覆盖: {result.extracted_fields} / {result.test_case.expected_fields}")
        print(f"  执行时间: {result.duration_seconds:.1f} 秒")

        if result.issues:
            print(f"  问题: {', '.join(result.issues)}")

        if result.error_message:
            print(f"  错误: {result.error_message}")

    def _analyze_extracted_data(self, data: List[Dict]) -> List[str]:
        """分析提取的数据，返回实际提取的字段名"""
        if not data:
            return []

        # 收集所有可能的字段名
        all_fields = set()
        for item in data[:20]:  # 分析前20条
            if isinstance(item, dict):
                all_fields.update(item.keys())

        return sorted(list(all_fields))

    async def run_single_test(self, test_case: TestCase) -> TestResult:
        """运行单个测试用例"""
        result = TestResult(test_case)
        result.started_at = datetime.now().isoformat()

        self._print_test_start(test_case)

        # 创建新的Agent实例
        self.agent = SiteAgent()

        try:
            start_time = time.time()

            # 执行Agent
            agent_result = await self.agent.run({
                "site_url": test_case.url,
                "user_goal": test_case.user_goal,
            })

            result.duration_seconds = time.time() - start_time
            result.raw_result = agent_result

            # 分析结果
            if agent_result.get("success"):
                result.success = True
                result.generated_code = agent_result.get("generated_code", "")

                # 提取质量分数
                report = agent_result.get("report", {})
                result.quality_score = report.get("quality_score", 0.5)

                # 提取样本数据
                final_state = agent_result.get("_final_state", {})
                result.sample_data = report.get("sample_data", [])

                # 确保sample_data是列表
                if not isinstance(result.sample_data, list):
                    result.sample_data = []

                result.data_count = len(result.sample_data)

                # 分析提取的字段
                result.extracted_fields = self._analyze_extracted_data(result.sample_data)

                # 分析问题和能力
                result.issues = self._analyze_issues(result)

            else:
                result.error_message = agent_result.get("error", "Unknown error")

        except Exception as e:
            result.duration_seconds = time.time() - start_time
            result.error_message = str(e)
            result.success = False

        finally:
            result.completed_at = datetime.now().isoformat()
            # 关闭浏览器
            try:
                await self.agent.close()
            except:
                pass

        self._print_test_result(result)

        return result

    def _analyze_issues(self, result: TestResult) -> List[str]:
        """分析测试中的问题"""
        issues = []

        # 质量分数低
        if result.quality_score < result.test_case.min_quality_score:
            issues.append(f"质量分数低于阈值 ({result.quality_score:.2f} < {result.test_case.min_quality_score})")

        # 数据量不足
        if result.data_count < result.test_case.min_data_count:
            issues.append(f"数据量不足 ({result.data_count} < {result.test_case.min_data_count})")

        # 字段覆盖低
        if result.test_case.expected_fields and result.extracted_fields:
            coverage = len(result.extracted_fields) / len(result.test_case.expected_fields)
            if coverage < 0.5:
                issues.append(f"字段覆盖低 ({coverage:.1%})")

        # 空数据
        if result.data_count == 0:
            issues.append("未提取到任何数据")

        return issues

    async def run_phase(self, phase: int) -> List[TestResult]:
        """运行指定阶段的所有测试"""
        from .test_cases import get_test_cases_by_phase

        test_cases = get_test_cases_by_phase(phase)
        phase_results = []

        self._print_header(f"Phase {phase} 测试开始 ({len(test_cases)} 个用例)")

        for test_case in test_cases:
            result = await self.run_single_test(test_case)
            phase_results.append(result)
            self.results.append(result)

            # 保存单个测试结果
            self._save_single_result(result)

            # 短暂延迟，避免过于频繁的请求
            await asyncio.sleep(2)

        return phase_results

    async def run_all(self, phase_filter: int = None) -> List[TestResult]:
        """运行所有测试（或指定阶段）"""
        self._print_header("Recon Agent 能力检测测试")

        print(f"\n配置:")
        print(f"  总测试用例: {len(TEST_CASES)}")
        print(f"  结果保存路径: {self.results_dir}")
        if phase_filter:
            print(f"  仅运行 Phase {phase_filter}")

        start_time = time.time()
        total_duration = 0

        if phase_filter:
            # 运行指定阶段
            await self.run_phase(phase_filter)
        else:
            # 运行所有阶段
            for phase in range(1, 5):
                phase_cases = [tc for tc in TEST_CASES if tc.phase == phase]
                if phase_cases:
                    await self.run_phase(phase)

        total_duration = time.time() - start_time

        # 生成汇总报告
        summary = self._generate_summary(total_duration)
        self._save_summary(summary)

        self._print_header("测试完成")
        self._print_summary(summary)

        return self.results

    def _save_single_result(self, result: TestResult):
        """保存单个测试结果"""
        if not self.config.get("save_results"):
            return

        filename = f"test_{result.test_case.id:02d}_{result.test_case.name.replace(' ', '_')}.json"
        filepath = self.results_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)

        print(f"  结果已保存: {filepath}")

    def _generate_summary(self, total_duration: float) -> Dict[str, Any]:
        """生成汇总报告"""
        passed = [r for r in self.results if r.is_passed()]
        failed = [r for r in self.results if not r.is_passed()]

        # 按阶段统计
        phase_stats = {}
        for phase in range(1, 5):
            phase_results = [r for r in self.results if r.test_case.phase == phase]
            if phase_results:
                phase_passed = sum(1 for r in phase_results if r.is_passed())
                phase_stats[f"phase_{phase}"] = {
                    "total": len(phase_results),
                    "passed": phase_passed,
                    "rate": phase_passed / len(phase_results) if phase_results else 0,
                }

        # 按难度统计
        difficulty_stats = {}
        for difficulty in range(1, 6):
            diff_results = [r for r in self.results if r.test_case.difficulty == difficulty]
            if diff_results:
                diff_passed = sum(1 for r in diff_results if r.is_passed())
                difficulty_stats[f"difficulty_{difficulty}"] = {
                    "total": len(diff_results),
                    "passed": diff_passed,
                    "rate": diff_passed / len(diff_results) if diff_results else 0,
                }

        # 能力分析
        capability_analysis = self._analyze_capabilities()

        return {
            "test_run": {
                "started_at": self.results[0].started_at if self.results else None,
                "completed_at": datetime.now().isoformat(),
                "total_duration_seconds": round(total_duration, 2),
                "total_tests": len(self.results),
            },
            "overall_stats": {
                "passed": len(passed),
                "failed": len(failed),
                "pass_rate": len(passed) / len(self.results) if self.results else 0,
                "avg_quality_score": sum(r.quality_score for r in self.results) / len(self.results) if self.results else 0,
                "avg_duration": sum(r.duration_seconds for r in self.results) / len(self.results) if self.results else 0,
            },
            "phase_stats": phase_stats,
            "difficulty_stats": difficulty_stats,
            "capability_analysis": capability_analysis,
            "failed_tests": [
                {
                    "id": r.test_case.id,
                    "name": r.test_case.name,
                    "reason": r.issues[0] if r.issues else r.error_message,
                }
                for r in failed
            ],
        }

    def _analyze_capabilities(self) -> Dict[str, Any]:
        """分析能力覆盖情况（使用 ResultAnalyzer）"""
        analyzer = ResultAnalyzer()
        capability_reports = analyzer._analyze_capabilities(self.results)
        return {cr.name: cr.to_dict() for cr in capability_reports}

    def _print_summary(self, summary: Dict):
        """打印汇总信息"""
        stats = summary["overall_stats"]
        phase_stats = summary["phase_stats"]

        print(f"\n总体结果:")
        print(f"  通过: {stats['passed']} / {stats['total_tests']}")
        print(f"  通过率: {stats['pass_rate']:.1%}")
        print(f"  平均质量分数: {stats['avg_quality_score']:.2f}")
        print(f"  总耗时: {summary['test_run']['total_duration_seconds']:.1f} 秒")

        print(f"\n各阶段通过率:")
        for phase, data in phase_stats.items():
            print(f"  {phase}: {data['passed']}/{data['total']} ({data['rate']:.1%})")

        if summary["failed_tests"]:
            print(f"\n失败的测试:")
            for test in summary["failed_tests"]:
                print(f"  #{test['id']} {test['name']}: {test['reason']}")

    def _save_summary(self, summary: Dict):
        """保存汇总报告"""
        # JSON格式
        json_path = self.results_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        # Markdown格式
        md_path = self.results_dir / f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(self._generate_markdown_report(summary))

        print(f"\n汇总报告已保存:")
        print(f"  JSON: {json_path}")
        print(f"  Markdown: {md_path}")

    def _generate_markdown_report(self, summary: Dict) -> str:
        """生成Markdown格式的报告"""
        stats = summary["overall_stats"]
        phase_stats = summary["phase_stats"]
        capability_analysis = summary["capability_analysis"]

        lines = [
            "# Recon Agent 能力检测报告",
            "",
            f"**生成时间**: {summary['test_run']['completed_at']}",
            f"**执行时长**: {summary['test_run']['total_duration_seconds']:.1f} 秒",
            "",
            "## 总体结果",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 总测试数 | {stats['total_tests']} |",
            f"| 通过 | {stats['passed']} |",
            f"| 失败 | {stats['failed']} |",
            f"| **通过率** | **{stats['pass_rate']:.1%}** |",
            f"| 平均质量分数 | {stats['avg_quality_score']:.2f} |",
            f"| 平均执行时间 | {stats['avg_duration']:.1f}秒 |",
            "",
            "## 各阶段结果",
            "",
            "| 阶段 | 通过率 | 详情 |",
            "|------|--------|------|",
        ]

        for phase, data in phase_stats.items():
            phase_name = phase.replace("_", " ").title()
            lines.append(f"| {phase_name} | {data['rate']:.1%} | {data['passed']}/{data['total']} |")

        lines.extend([
            "",
            "## 能力分析",
            "",
            "| 能力 | 理论支持 | 验证通过率 | 实际支持 |",
            "|------|----------|------------|----------|",
        ])

        for capability, data in capability_analysis.items():
            theoretical = "✅" if data["theoretical_support"] else "❌"
            rate = f"{data['success_rate']:.0%}" if data['success_rate'] is not None else "N/A"
            verified = "✅" if data.get("verified_support") else "❌"
            lines.append(f"| {capability} | {theoretical} | {rate} | {verified} |")

        lines.extend([
            "",
            "## 测试详情",
            "",
            "| # | 名称 | 难度 | 状态 | 质量分数 | 数据量 |",
            "|---|------|------|------|----------|--------|",
        ])

        for r in self.results:
            status = "✅" if r.is_passed() else "❌"
            stars = "⭐" * r.test_case.difficulty
            lines.append(f"| {r.test_case.id} | {r.test_case.name} | {stars} | {status} | {r.quality_score:.2f} | {r.data_count} |")

        if summary["failed_tests"]:
            lines.extend([
                "",
                "## 失败原因分析",
                "",
            ])
            for test in summary["failed_tests"]:
                lines.append(f"- **#{test['id']} {test['name']}**: {test['reason']}")

        lines.extend([
            "",
            "## 结论",
            "",
        ])

        # 根据通过率给出结论
        if stats["pass_rate"] >= 0.8:
            lines.extend([
                "- ✅ **Phase 1-2 基础能力**：已验证，表现良好",
                "- 当前Agent在基础数据采集方面表现稳定",
            ])
        elif stats["pass_rate"] >= 0.5:
            lines.extend([
                "- ⚠️ **基础能力**：部分可用",
                "- 存在一些需要改进的地方",
            ])
        else:
            lines.extend([
                "- ❌ **基础能力不足**：需要重点改进",
            ])

        lines.extend([
            "",
            "## 改进建议",
            "",
        ])

        # 根据失败情况给出建议
        failed_capabilities = set()
        for r in self.results:
            if not r.is_passed():
                failed_capabilities.update(r.test_case.capabilities)

        if "rate_limit_handling" in failed_capabilities:
            lines.append("- 添加速率限制处理能力")
        if "anti_bot_handling" in failed_capabilities:
            lines.append("- 研究反爬虫绕过方案（如浏览器指纹模拟）")
        if "websocket_handling" in failed_capabilities:
            lines.append("- 添加 WebSocket 监听和数据提取功能")
        if "canvas_extraction" in failed_capabilities:
            lines.append("- 研究 Canvas 图表数据提取方案")

        lines.append("")

        return "\n".join(lines)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Recon Agent 能力检测测试")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4], help="只运行指定阶段")
    parser.add_argument("--id", type=int, help="只运行指定ID的测试")
    parser.add_argument("--verbose", action="store_true", help="详细输出")

    args = parser.parse_args()

    runner = CapabilityTestRunner()

    if args.id:
        # 运行单个测试
        from .test_cases import get_test_case_by_id
        test_case = get_test_case_by_id(args.id)
        if test_case:
            result = await runner.run_single_test(test_case)
            runner.results.append(result)
            runner._save_single_result(result)
        else:
            print(f"未找到 ID 为 {args.id} 的测试用例")
    else:
        # 运行所有测试或指定阶段
        await runner.run_all(phase_filter=args.phase)


if __name__ == "__main__":
    asyncio.run(main())
