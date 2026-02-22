# -*- coding: utf-8 -*-
"""
Performance Report Generator

生成性能分析报告，可视化各节点的执行时间和资源使用情况。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict


def load_test_results(results_dir: Path) -> List[Dict[str, Any]]:
    """加载测试结果

    Args:
        results_dir: 测试结果目录

    Returns:
        测试结果列表
    """
    results = []

    # 查找所有 state.json 文件
    for state_file in results_dir.glob("*/state.json"):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                results.append({
                    "state": state,
                    "path": state_file.parent,
                })
        except Exception as e:
            print(f"[Warning] Failed to load {state_file}: {e}")

    return results


def extract_performance_data(state: Dict[str, Any]) -> Dict[str, Any]:
    """从 state 中提取性能数据

    Args:
        state: Agent 状态

    Returns:
        性能数据
    """
    performance_data = state.get("performance_data", {})

    # 提取各节点的耗时
    nodes = {}
    total_time = 0

    for key, value in performance_data.items():
        if key.endswith("_duration"):
            node_name = key.replace("_duration", "")
            nodes[node_name] = {
                "duration": value,
                "status": performance_data.get(f"{node_name}_status", "unknown"),
                "calls": performance_data.get(f"{node_name}_calls", 1),
                "error": performance_data.get(f"{node_name}_error", ""),
            }
            total_time += value

    return {
        "nodes": nodes,
        "total_time": total_time,
        "raw_data": performance_data,
    }


def aggregate_performance_data(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """汇总所有测试的性能数据

    Args:
        results: 测试结果列表

    Returns:
        汇总后的性能数据
    """
    # 节点统计
    node_stats = defaultdict(lambda: {
        "durations": [],
        "success_count": 0,
        "error_count": 0,
        "errors": [],
    })

    total_tests = len(results)
    total_time = 0
    success_tests = 0

    for result in results:
        state = result["state"]
        perf = extract_performance_data(state)

        # 统计总时间
        total_time += perf["total_time"]

        # 统计成功/失败
        if state.get("quality_score", 0) > 0.5:
            success_tests += 1

        # 统计各节点
        for node_name, node_data in perf["nodes"].items():
            stats = node_stats[node_name]
            stats["durations"].append(node_data["duration"])

            if node_data["status"] == "success":
                stats["success_count"] += 1
            else:
                stats["error_count"] += 1
                if node_data.get("error"):
                    stats["errors"].append(node_data["error"])

    # 计算平均值和百分比
    summary = {
        "total_tests": total_tests,
        "success_tests": success_tests,
        "success_rate": success_tests / total_tests if total_tests > 0 else 0,
        "total_time": total_time,
        "avg_time_per_test": total_time / total_tests if total_tests > 0 else 0,
        "nodes": {},
    }

    for node_name, stats in node_stats.items():
        durations = stats["durations"]
        summary["nodes"][node_name] = {
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "total_duration": sum(durations),
            "success_count": stats["success_count"],
            "error_count": stats["error_count"],
            "errors": stats["errors"][:5],  # 最多保留5个错误
        }

    return summary


def generate_text_report(summary: Dict[str, Any]) -> str:
    """生成文本格式的性能报告

    Args:
        summary: 汇总后的性能数据

    Returns:
        报告文本
    """
    lines = []
    lines.append("=" * 70)
    lines.append("Performance Analysis Report")
    lines.append("=" * 70)
    lines.append("")

    # 总体统计
    lines.append("Overall Statistics:")
    lines.append(f"  Total tests: {summary['total_tests']}")
    lines.append(f"  Successful tests: {summary['success_tests']} ({summary['success_rate']*100:.1f}%)")
    lines.append(f"  Total time: {summary['total_time']:.2f}s")
    lines.append(f"  Average time per test: {summary['avg_time_per_test']:.2f}s")
    lines.append("")

    # 节点统计（按平均耗时排序）
    lines.append("Node Performance (sorted by average duration):")
    lines.append("")

    nodes_sorted = sorted(
        summary["nodes"].items(),
        key=lambda x: x[1]["avg_duration"],
        reverse=True
    )

    total_node_time = sum(n["total_duration"] for n in summary["nodes"].values())

    for node_name, stats in nodes_sorted:
        avg = stats["avg_duration"]
        percentage = (stats["total_duration"] / total_node_time * 100) if total_node_time > 0 else 0

        lines.append(f"  {node_name:20s}:")
        lines.append(f"    Average: {avg:7.2f}s ({percentage:5.1f}%)")
        lines.append(f"    Min/Max: {stats['min_duration']:7.2f}s / {stats['max_duration']:7.2f}s")
        lines.append(f"    Success/Errors: {stats['success_count']}/{stats['error_count']}")

        if stats["errors"]:
            lines.append(f"    Recent errors:")
            for error in stats["errors"][:3]:
                lines.append(f"      - {error[:80]}...")
        lines.append("")

    # 识别最慢的节点
    if nodes_sorted:
        slowest_node = nodes_sorted[0]
        lines.append(f"Bottleneck Analysis:")
        lines.append(f"  Slowest node: {slowest_node[0]} ({slowest_node[1]['avg_duration']:.2f}s avg)")
        lines.append(f"  Optimization recommendation:")
        if slowest_node[0] == "act":
            lines.append(f"    - Consider reducing sandbox timeout (current: 300s)")
            lines.append(f"    - Use 'domcontentloaded' instead of 'networkidle' for faster page loads")
        elif slowest_node[0] == "sense":
            lines.append(f"    - Reduce HTML size passed to LLM")
            lines.append(f"    - Cache DOM analysis results")
        elif slowest_node[0] == "plan":
            lines.append(f"    - Use shorter, more focused prompts")
            lines.append(f"    - Enable prompt caching")
        else:
            lines.append(f"    - Review {slowest_node[0]} implementation for optimization opportunities")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def generate_html_report(summary: Dict[str, Any], output_path: Path) -> None:
    """生成 HTML 格式的性能报告

    Args:
        summary: 汇总后的性能数据
        output_path: 输出文件路径
    """
    html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Analysis Report</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }
        .summary {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .card-value {
            font-size: 32px;
            font-weight: bold;
            color: #007bff;
        }
        .card-label {
            color: #666;
            margin-top: 5px;
        }
        .node-chart {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }
        .bar-container {
            margin: 10px 0;
        }
        .bar-label {
            display: flex;
            justify-content: space-between;
            margin-bottom: 5px;
        }
        .bar {
            height: 30px;
            background: #007bff;
            border-radius: 4px;
            transition: width 0.3s;
        }
        .bar:hover {
            background: #0056b3;
        }
        .error-list {
            background: #fff3cd;
            padding: 15px;
            border-radius: 4px;
            margin-top: 10px;
            border-left: 4px solid #ffc107;
        }
        .error-item {
            font-family: monospace;
            font-size: 12px;
            margin: 5px 0;
            color: #856404;
        }
        .timestamp {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <h1>Performance Analysis Report</h1>
    <p class="timestamp">Generated: {timestamp}</p>

    <div class="summary">
        <div class="card">
            <div class="card-value">{total_tests}</div>
            <div class="card-label">Total Tests</div>
        </div>
        <div class="card">
            <div class="card-value">{success_rate:.1f}%</div>
            <div class="card-label">Success Rate</div>
        </div>
        <div class="card">
            <div class="card-value">{total_time:.1f}s</div>
            <div class="card-label">Total Time</div>
        </div>
        <div class="card">
            <div class="card-value">{avg_time:.1f}s</div>
            <div class="card-label">Avg Time per Test</div>
        </div>
    </div>

    <div class="node-chart">
        <h2>Node Performance Breakdown</h2>
        {node_chart}
    </div>

    <div class="node-chart">
        <h2>Bottleneck Analysis</h2>
        <p><strong>Slowest node:</strong> {slowest_node} ({slowest_time:.2f}s avg)</p>
        <p><strong>Recommendation:</strong> {recommendation}</p>
    </div>
</body>
</html>"""

    # 生成节点图表
    nodes_sorted = sorted(
        summary["nodes"].items(),
        key=lambda x: x[1]["avg_duration"],
        reverse=True
    )

    total_node_time = sum(n["total_duration"] for n in summary["nodes"].values())

    node_chart_html = ""
    for node_name, stats in nodes_sorted:
        avg = stats["avg_duration"]
        percentage = (stats["total_duration"] / total_node_time * 100) if total_node_time > 0 else 0
        bar_width = min(percentage, 100)

        node_chart_html += f"""
        <div class="bar-container">
            <div class="bar-label">
                <strong>{node_name}</strong>
                <span>{avg:.2f}s ({percentage:.1f}%)</span>
            </div>
            <div class="bar" style="width: {bar_width}%"></div>
        </div>"""

        if stats["errors"]:
            node_chart_html += f'<div class="error-list"><strong>Recent errors:</strong>'
            for error in stats["errors"][:3]:
                node_chart_html += f'<div class="error-item">{error}</div>'
            node_chart_html += '</div>'

    # 生成建议
    slowest_node_name = nodes_sorted[0][0] if nodes_sorted else "unknown"
    slowest_time = nodes_sorted[0][1]["avg_duration"] if nodes_sorted else 0

    recommendations = {
        "act": "Consider reducing sandbox timeout (current: 300s), use 'domcontentloaded' instead of 'networkidle' for faster page loads",
        "sense": "Reduce HTML size passed to LLM, cache DOM analysis results",
        "plan": "Use shorter, more focused prompts, enable prompt caching",
        "validate": "Optimize selector validation logic",
        "verify": "Simplify quality evaluation criteria",
        "soal": "Use incremental code generation to reduce LLM calls",
    }
    recommendation = recommendations.get(slowest_node_name, f"Review {slowest_node_name} implementation for optimization opportunities")

    # 填充模板
    html_content = html.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_tests=summary["total_tests"],
        success_rate=summary["success_rate"] * 100,
        total_time=summary["total_time"],
        avg_time=summary["avg_time_per_test"],
        node_chart=node_chart_html,
        slowest_node=slowest_node_name,
        slowest_time=slowest_time,
        recommendation=recommendation,
    )

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate performance analysis report")
    parser.add_argument("results_dir", type=Path, help="Test results directory")
    parser.add_argument("--output", "-o", type=Path, help="Output file path")
    parser.add_argument("--format", "-f", choices=["text", "html", "both"], default="both",
                        help="Output format")

    args = parser.parse_args()

    # 加载测试结果
    print(f"[Loading] Test results from: {args.results_dir}")
    results = load_test_results(args.results_dir)
    print(f"[Loaded] {len(results)} test results")

    if not results:
        print("[Error] No test results found!")
        return

    # 汇总性能数据
    print("[Processing] Aggregating performance data...")
    summary = aggregate_performance_data(results)

    # 生成报告
    if args.format in ["text", "both"]:
        text_report = generate_text_report(summary)
        if args.output:
            text_path = args.output.with_suffix(".txt") if args.format == "text" else args.output.parent / "performance_report.txt"
        else:
            text_path = args.results_dir / "performance_report.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_report)
        print(f"[Output] Text report: {text_path}")

        # 也打印到控制台
        print("\n" + text_report)

    if args.format in ["html", "both"]:
        if args.output:
            html_path = args.output.with_suffix(".html") if args.format == "html" else args.output.parent / "performance_report.html"
        else:
            html_path = args.results_dir / "performance_report.html"
        generate_html_report(summary, html_path)
        print(f"[Output] HTML report: {html_path}")

    print("\n[Done] Performance report generated successfully!")


if __name__ == "__main__":
    main()
