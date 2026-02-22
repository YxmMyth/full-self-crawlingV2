"""
Result Analyzer - 测试结果分析器

分析测试结果，生成能力边界报告和改进建议。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CapabilityReport:
    """能力报告"""
    name: str
    theoretical_support: bool
    verified_support: bool
    success_rate: float
    tests_requiring: int
    tests_passed: int
    issues: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "theoretical_support": self.theoretical_support,
            "verified_support": self.verified_support,
            "success_rate": self.success_rate,
            "tests_requiring": self.tests_requiring,
            "tests_passed": self.tests_passed,
            "issues": self.issues,
        }


@dataclass
class PhaseReport:
    """阶段报告"""
    phase: int
    total: int
    passed: int
    pass_rate: float
    target_rate: float
    met_target: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase": self.phase,
            "total": self.total,
            "passed": self.passed,
            "pass_rate": self.pass_rate,
            "target_rate": self.target_rate,
            "met_target": self.met_target,
        }


@dataclass
class IssueAnalysis:
    """问题分析"""
    test_id: int
    test_name: str
    phase: int
    difficulty: int
    failure_reason: str
    missing_capabilities: List[str] = field(default_factory=list)
    suggested_fixes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "phase": self.phase,
            "difficulty": self.difficulty,
            "failure_reason": self.failure_reason,
            "missing_capabilities": self.missing_capabilities,
            "suggested_fixes": self.suggested_fixes,
        }


class ResultAnalyzer:
    """测试结果分析器"""

    def __init__(self):
        self.capability_reports: List[CapabilityReport] = []
        self.phase_reports: List[PhaseReport] = []
        self.issue_analyses: List[IssueAnalysis] = []
        self.recommendations: List[str] = []

    def analyze(self, test_results: List[Any]) -> Dict[str, Any]:
        """
        分析测试结果

        Args:
            test_results: TestResult 对象列表

        Returns:
            完整的分析报告
        """
        # 清空之前的结果
        self.capability_reports = []
        self.phase_reports = []
        self.issue_analyses = []
        self.recommendations = []

        # 分析各阶段结果
        self._analyze_phases(test_results)

        # 分析能力覆盖
        self._analyze_capabilities(test_results)

        # 分析失败原因
        self._analyze_failures(test_results)

        # 生成建议
        self._generate_recommendations()

        return {
            "capability_reports": [r.to_dict() for r in self.capability_reports],
            "phase_reports": [r.to_dict() for r in self.phase_reports],
            "issue_analyses": [i.to_dict() for i in self.issue_analyses],
            "recommendations": self.recommendations,
            "summary": self._generate_summary(),
        }

    def _analyze_phases(self, test_results: List[Any]):
        """分析各阶段测试结果"""
        phase_tests = {1: [], 2: [], 3: [], 4: []}
        for r in test_results:
            phase_tests[r.test_case.phase].append(r)

        # Phase 1 目标: >= 80% 通过率
        # Phase 2 目标: >= 80% 通过率
        # Phase 3 目标: >= 50% 通过率
        # Phase 4 目标: 识别能力边界
        targets = {1: 0.8, 2: 0.8, 3: 0.5, 4: 0.0}

        for phase, results in phase_tests.items():
            if not results:
                continue

            passed = sum(1 for r in results if r.is_passed())
            total = len(results)
            rate = passed / total if total > 0 else 0

            self.phase_reports.append(PhaseReport(
                phase=phase,
                total=total,
                passed=passed,
                pass_rate=rate,
                target_rate=targets[phase],
                met_target=rate >= targets[phase],
            ))

    def _analyze_capabilities(self, test_results: List[Any]):
        """分析能力覆盖情况"""
        from .test_cases import CAPABILITY_MATRIX

        for capability, info in CAPABILITY_MATRIX.items():
            # 找到需要这个能力的测试
            relevant_tests = [
                r for r in test_results
                if capability in r.test_case.capabilities
            ]

            if not relevant_tests:
                continue

            passed = sum(1 for r in relevant_tests if r.is_passed())
            success_rate = passed / len(relevant_tests) if relevant_tests else 0

            # 收集问题
            issues = []
            for r in relevant_tests:
                if not r.is_passed():
                    issues.append(f"#{r.test_case.id} {r.test_case.name}: {r.error_message or ', '.join(r.issues)}")

            self.capability_reports.append(CapabilityReport(
                name=capability,
                theoretical_support=info["supported"],
                verified_support=success_rate >= 0.5,
                success_rate=success_rate,
                tests_requiring=len(relevant_tests),
                tests_passed=passed,
                issues=issues,
            ))

    def _analyze_failures(self, test_results: List[Any]):
        """分析失败原因"""
        for r in test_results:
            if r.is_passed():
                continue

            # 确定失败原因
            failure_reason = r.error_message or ", ".join(r.issues) if r.issues else "未知原因"

            # 找出缺失的能力
            missing_caps = []
            for cap in r.test_case.capabilities:
                cap_report = next((c for c in self.capability_reports if c.name == cap), None)
                if cap_report and not cap_report.verified_support:
                    missing_caps.append(cap)

            # 生成修复建议
            suggested_fixes = self._get_fix_suggestions(r, missing_caps)

            self.issue_analyses.append(IssueAnalysis(
                test_id=r.test_case.id,
                test_name=r.test_case.name,
                phase=r.test_case.phase,
                difficulty=r.test_case.difficulty,
                failure_reason=failure_reason,
                missing_capabilities=missing_caps,
                suggested_fixes=suggested_fixes,
            ))

    def _get_fix_suggestions(self, result: Any, missing_caps: List[str]) -> List[str]:
        """获取修复建议"""
        suggestions = []

        # 根据缺失的能力给出建议
        for cap in missing_caps:
            if "rate_limit" in cap:
                suggestions.append("添加请求间延迟和速率限制检测")
                suggestions.append("实现退避重试策略")
            elif "anti_bot" in cap or "cloudflare" in cap:
                suggestions.append("模拟真实浏览器行为（User-Agent、指纹）")
                suggestions.append("考虑使用住宅代理或浏览器自动化服务")
            elif "websocket" in cap:
                suggestions.append("添加 WebSocket 监听能力")
                suggestions.append("拦截并解析 WebSocket 消息")
            elif "canvas" in cap:
                suggestions.append("实现 Canvas 截图和 OCR 识别")
                suggestions.append("或寻找数据 API 替代方案")
            elif "lazy_loading" in cap:
                suggestions.append("实现滚动加载检测和处理")
                suggestions.append("等待懒加载元素完全加载")

        # 根据错误信息给出建议
        if result.error_message:
            error_lower = result.error_message.lower()
            if "timeout" in error_lower:
                suggestions.append("增加页面加载等待时间")
                suggestions.append("优化选择器等待策略")
            elif "selector" in error_lower or "not found" in error_lower:
                suggestions.append("更新 CSS 选择器以适应页面结构变化")
                suggestions.append("增加更灵活的备选选择器")

        return suggestions

    def _generate_recommendations(self) -> List[str]:
        """生成总体建议"""
        recommendations = []

        # 分析通过率
        if self.phase_reports:
            phase_1 = next((p for p in self.phase_reports if p.phase == 1), None)
            phase_2 = next((p for p in self.phase_reports if p.phase == 2), None)

            if phase_1 and phase_1.pass_rate >= 0.8:
                recommendations.append("✅ 基础能力验证通过，核心采集功能稳定")
            else:
                recommendations.append("⚠️ 基础能力需要加强，请检查基础解析和提取逻辑")

            if phase_2 and phase_2.pass_rate >= 0.8:
                recommendations.append("✅ 中级能力验证通过，富文本和混合内容处理良好")
            else:
                recommendations.append("⚠️ 中级能力需要改进")

        # 分析能力覆盖
        failed_capabilities = [c for c in self.capability_reports if not c.verified_support]
        if failed_capabilities:
            recommendations.append("\n📋 需要增强的能力:")
            for cap in failed_capabilities:
                recommendations.append(f"  - {cap.name}: 当前通过率 {cap.success_rate:.0%}")

        # 分析失败测试
        if self.issue_analyses:
            recommendations.append("\n🔧 高优先级改进项:")

            # 按难度分组
            by_difficulty = {1: [], 2: [], 3: [], 4: [], 5: []}
            for issue in self.issue_analyses:
                by_difficulty[issue.difficulty].append(issue)

            # 优先处理低难度失败的测试
            for diff in range(1, 4):
                if by_difficulty[diff]:
                    for issue in by_difficulty[diff][:2]:  # 每个难度最多2个
                        recommendations.append(f"  - #{issue.test_id} {issue.test_name}: {issue.failure_reason[:50]}")

        return recommendations

    def _generate_summary(self) -> Dict[str, Any]:
        """生成汇总信息"""
        if not self.phase_reports:
            return {"status": "no_data"}

        # 计算总体统计
        total_tests = sum(p.total for p in self.phase_reports)
        total_passed = sum(p.passed for p in self.phase_reports)
        overall_rate = total_passed / total_tests if total_tests > 0 else 0

        # 确定能力等级
        if overall_rate >= 0.8:
            level = "高"
            description = "Agent 核心能力完善，可处理大多数常见网站"
        elif overall_rate >= 0.6:
            level = "中高"
            description = "Agent 具备基本能力，部分复杂场景需要优化"
        elif overall_rate >= 0.4:
            level = "中等"
            description = "Agent 能力有限，需要针对多种场景进行增强"
        else:
            level = "待提升"
            description = "Agent 需要重大改进才能满足生产需求"

        return {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "overall_pass_rate": round(overall_rate, 2),
            "capability_level": level,
            "description": description,
            "verified_capabilities": len([c for c in self.capability_reports if c.verified_support]),
            "total_capabilities_tested": len(self.capability_reports),
        }

    def generate_markdown_report(self) -> str:
        """生成 Markdown 格式的报告"""
        lines = [
            "# Recon Agent 能力边界分析报告",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 执行摘要",
            "",
        ]

        summary = self._generate_summary()
        if summary.get("status") != "no_data":
            lines.extend([
                f"- **能力等级**: {summary['capability_level']}",
                f"- **总通过率**: {summary['overall_pass_rate']:.1%}",
                f"- **验证能力**: {summary['verified_capabilities']}/{summary['total_capabilities_tested']}",
                "",
                summary["description"],
                "",
            ])

        # 阶段报告
        lines.extend([
            "## 各阶段测试结果",
            "",
            "| 阶段 | 通过率 | 目标 | 达标 |",
            "|------|--------|------|------|",
        ])

        for pr in self.phase_reports:
            status = "✅" if pr.met_target else "❌"
            lines.append(f"| Phase {pr.phase} | {pr.pass_rate:.1%} | {pr.target_rate:.0%} | {status} |")

        # 能力分析
        lines.extend([
            "",
            "## 能力验证结果",
            "",
            "| 能力 | 理论支持 | 实际支持 | 通过率 |",
            "|------|----------|----------|--------|",
        ])

        for cr in self.capability_reports:
            theoretical = "✅" if cr.theoretical_support else "❌"
            verified = "✅" if cr.verified_support else "❌"
            lines.append(f"| {cr.name} | {theoretical} | {verified} | {cr.success_rate:.0%} |")

        # 失败分析
        if self.issue_analyses:
            lines.extend([
                "",
                "## 失败原因分析",
                "",
            ])

            for issue in self.issue_analyses:
                lines.extend([
                    f"### #{issue.test_id} {issue.test_name}",
                    f"- **难度**: {'⭐' * issue.difficulty}",
                    f"- **失败原因**: {issue.failure_reason}",
                ])

                if issue.missing_capabilities:
                    lines.append(f"- **缺失能力**: {', '.join(issue.missing_capabilities)}")

                if issue.suggested_fixes:
                    lines.extend([
                        "- **修复建议**:",
                        *[f"  - {s}" for s in issue.suggested_fixes],
                    ])

                lines.append("")

        # 建议
        if self.recommendations:
            lines.extend([
                "## 改进建议",
                "",
            ])
            lines.extend([f"{rec}" for rec in self.recommendations])
            lines.append("")

        return "\n".join(lines)


def analyze_results(test_results: List[Any]) -> Dict[str, Any]:
    """
    便捷函数：分析测试结果

    Args:
        test_results: TestResult 对象列表

    Returns:
        分析报告字典
    """
    analyzer = ResultAnalyzer()
    return analyzer.analyze(test_results)
