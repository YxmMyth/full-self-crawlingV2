# -*- coding: utf-8 -*-
"""
完整测试脚本 - 基于 new-need.csv 的10个场景

运行端到端测试，收集结果和截图，生成测试报告。
"""

import asyncio
import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agent.agent import SiteAgent
from src.agent.performance import format_performance_report


def print_performance_summary(performance_data: dict) -> None:
    """打印性能摘要

    Args:
        performance_data: 性能数据字典
    """
    from src.agent.performance import get_performance_summary

    summary = get_performance_summary(performance_data)

    # 按耗时排序
    nodes_sorted = sorted(
        summary["nodes"].items(),
        key=lambda x: x[1]["duration"],
        reverse=True
    )

    for node, data in nodes_sorted:
        duration = data["duration"]
        percentage = (duration / summary["total_time"] * 100) if summary["total_time"] > 0 else 0
        status_icon = "[OK]" if data["status"] == "success" else "[ERR]"
        print(f"    {status_icon} {node:15s}: {duration:6.2f}s ({percentage:5.1f}%)")

    print(f"    总计: {summary['total_time']:.2f}s")


def load_test_scenarios(csv_path: str) -> List[Dict[str, Any]]:
    """从CSV文件加载测试场景"""
    scenarios = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 解析CSV行
            scenarios.append({
                'id': row.get('#', '').strip(),
                'description': row.get('数据需求（简述）', '').strip(),
                'url': row.get('真实匹配站点URL（点击即用）', '').strip(),
                'notes': row.get('为什么完美匹配（关键元素）', '').strip(),
            })

    return scenarios


async def run_single_test(
    scenario: Dict[str, Any],
    output_dir: Path,
    test_config: Dict[str, Any],
) -> Dict[str, Any]:
    """运行单个测试场景"""
    test_id = scenario['id']
    url = scenario['url']
    description = scenario['description']

    print(f"\n{'='*70}")
    print(f"  测试 #{test_id}: {description[:50]}...")
    print(f"{'='*70}")
    print(f"  URL: {url}")
    print(f"  备注: {scenario['notes'][:80]}...")

    # 创建场景输出目录
    scenario_dir = output_dir / f"test_{test_id}_{description[:20].strip()}"
    scenario_dir.mkdir(parents=True, exist_ok=True)

    result = {
        'id': test_id,
        'description': description,
        'url': url,
        'status': 'unknown',
        'flow_success': False,
        'data_success': False,
        'completion_status': 'unknown',
        'failure_reason': None,
        'quality_score': 0.0,
        'sample_count': 0,
        'error': None,
        'output_dir': str(scenario_dir),
        'started_at': datetime.now().isoformat(),
        'performance_data': None,  # 新增：性能数据
    }

    try:
        # 创建 Agent
        agent = SiteAgent()

        # 准备任务参数
        task_params = {
            "site_url": url,
            "user_goal": description,
            "task_id": f"test_{test_id}",
        }

        # 运行 Agent
        print(f"  [INFO] 启动 Agent...")
        agent_result = await agent.run(task_params)

        # 从结果中提取数据
        final_state = agent_result.get('final_state', {})
        result['status'] = final_state.get('stage', agent_result.get('stage', 'unknown'))
        result['flow_success'] = bool(agent_result.get('success', False))
        result['data_success'] = bool(agent_result.get('data_success', False))
        result['completion_status'] = agent_result.get('completion_status', result['status'])
        result['failure_reason'] = agent_result.get('failure_reason') or final_state.get('failure_reason')
        result['quality_score'] = final_state.get('quality_score', 0.0)
        result['sample_count'] = len(final_state.get('sample_data', []))
        result['completed_at'] = datetime.now().isoformat()

        # 保存性能数据
        result['performance_data'] = final_state.get('performance_data', {})

        # 保存样本数据
        sample_data = final_state.get('sample_data', [])
        if sample_data:
            samples_file = scenario_dir / 'samples.json'
            with open(samples_file, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, ensure_ascii=False, indent=2)
            print(f"  [SUCCESS] 保存样本: {samples_file}")

        # 保存生成的代码
        generated_code = agent_result.get('generated_code')
        if generated_code:
            code_file = scenario_dir / 'generated_code.py'
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(generated_code)
            print(f"  [INFO] 保存代码: {code_file}")

        # 保存完整状态
        state_file = scenario_dir / 'state.json'
        with open(state_file, 'w', encoding='utf-8') as f:
            # 移除不能序列化的字段
            state_copy = dict(final_state)
            state_copy['agent_result'] = agent_result
            json.dump(state_copy, f, ensure_ascii=False, indent=2, default=str)

        # 显示结果摘要
        print(f"\n  [结果] 状态: {result['status']}")
        print(f"  [结果] 流程成功: {result['flow_success']}")
        print(f"  [结果] 数据成功: {result['data_success']}")
        print(f"  [结果] 质量分数: {result['quality_score']:.2f}")
        print(f"  [结果] 样本数量: {result['sample_count']}")
        if result['failure_reason']:
            print(f"  [结果] 失败原因: {result['failure_reason']}")

        # 显示性能摘要（如果启用）
        if test_config.get('track_performance') and result.get('performance_data'):
            print(f"\n  [性能] 节点耗时:")
            print_performance_summary(result['performance_data'])

        if result['sample_count'] > 0:
            print(f"\n  [预览] 前3个样本:")
            for i, sample in enumerate(sample_data[:3]):
                print(f"    [{i+1}] {str(sample)[:100]}...")

    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        result['completed_at'] = datetime.now().isoformat()
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

    return result


async def run_all_tests(
    scenarios: List[Dict[str, Any]],
    output_dir: Path,
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """运行所有测试场景"""
    results = []

    for scenario in scenarios:
        try:
            result = await run_single_test(scenario, output_dir, config)
            results.append(result)
        except Exception as e:
            print(f"\n  [CRASH] 测试 #{scenario.get('id', '?')} 崩溃: {e}")
            results.append({
                'id': scenario.get('id', '?'),
                'description': scenario.get('description', '?'),
                'url': scenario.get('url', '?'),
                'status': 'crashed',
                'error': str(e),
            })

        # 短暂延迟，避免请求过快
        await asyncio.sleep(2)

    return results


def generate_summary_report(results: List[Dict[str, Any]], output_dir: Path):
    """生成测试摘要报告"""
    total = len(results)
    flow_success = sum(1 for r in results if r.get('flow_success'))
    data_success = sum(1 for r in results if r.get('data_success'))
    failed = total - data_success

    total_samples = sum(r.get('sample_count', 0) for r in results)
    avg_quality = sum(r.get('quality_score', 0) for r in results) / max(total, 1)

    print(f"\n{'='*70}")
    print(f"  测试摘要报告")
    print(f"{'='*70}")
    print(f"  总数: {total}")
    print(f"  流程成功: {flow_success} ({flow_success/total*100:.1f}%)")
    print(f"  数据成功: {data_success} ({data_success/total*100:.1f}%)")
    print(f"  数据失败: {failed} ({failed/total*100:.1f}%)")
    print(f"  总样本数: {total_samples}")
    print(f"  平均质量: {avg_quality:.2f}")

    print(f"\n  详细结果:")
    for r in results:
        status_icon = "[OK]" if r.get('data_success') else "[FAIL]"
        samples = r.get('sample_count', 0)
        quality = r.get('quality_score', 0)
        print(f"    {status_icon} #{r['id']} {r['description'][:40]}... | "
              f"样本: {samples} | 质量: {quality:.2f}")

    # 保存摘要到文件
    summary_file = output_dir / 'summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            'total': total,
            'flow_success': flow_success,
            'data_success': data_success,
            'failed': failed,
            'total_samples': total_samples,
            'avg_quality': avg_quality,
            'results': results,
            'generated_at': datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2)

    print(f"\n  摘要已保存到: {summary_file}")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='运行完整测试')
    parser.add_argument(
        '--data',
        type=str,
        default='data/requirements/new-need.csv',
        help='测试场景CSV文件路径',
    )
    parser.add_argument(
        '--output',
        type=str,
        default=f'resources/test_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        help='输出目录',
    )
    parser.add_argument(
        '--vision',
        action='store_true',
        help='启用 Vision API',
    )
    parser.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='单个测试超时时间（秒）',
    )
    parser.add_argument(
        '--track-performance',
        action='store_true',
        help='启用性能追踪，显示各节点耗时',
    )

    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("  完整测试 - 10个场景端到端测试")
    print("="*70)
    print(f"  数据文件: {args.data}")
    print(f"  输出目录: {output_dir}")
    print(f"  Vision API: {'启用' if args.vision else '禁用'}")

    # 加载测试场景
    scenarios = load_test_scenarios(args.data)
    print(f"\n  加载了 {len(scenarios)} 个测试场景")

    # 配置
    config = {
        'enable_vision_api': args.vision,
        'timeout': args.timeout,
        'track_performance': args.track_performance,
    }

    # 运行测试
    results = await run_all_tests(scenarios, output_dir, config)

    # 生成摘要报告
    generate_summary_report(results, output_dir)


if __name__ == "__main__":
    asyncio.run(main())
