# -*- coding: utf-8 -*-
"""
HTML测试报告生成器

读取测试结果，生成美观的HTML报告。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List


def load_results(results_dir: Path) -> List[Dict[str, Any]]:
    """加载测试结果"""
    results = []

    # 查找 summary.json
    summary_file = results_dir / 'summary.json'
    if summary_file.exists():
        with open(summary_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('results', [])

    # 如果没有 summary.json，扫描各测试目录
    for test_dir in results_dir.iterdir():
        if not test_dir.is_dir() or not test_dir.name.startswith('test_'):
            continue

        state_file = test_dir / 'state.json'
        if state_file.exists():
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
                results.append({
                    'id': test_dir.name.split('_')[1],
                    'output_dir': str(test_dir),
                    **state
                })

    return results


def generate_html_report(results: List[Dict[str, Any]], output_path: Path):
    """生成HTML报告"""

    # 统计数据
    total = len(results)
    success = sum(1 for r in results if r.get('status') in ['done', 'report'])
    failed = total - success
    total_samples = sum(r.get('sample_count', 0) for r in results)
    avg_quality = sum(r.get('quality_score', 0) for r in results) / max(total, 1)

    # 按质量分数分类
    high_quality = sum(1 for r in results if r.get('quality_score', 0) >= 0.8)
    medium_quality = sum(1 for r in results if 0.5 <= r.get('quality_score', 0) < 0.8)
    low_quality = sum(1 for r in results if r.get('quality_count', 0) < 0.5)

    # 生成HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>测试报告 - {datetime.now().strftime("%Y-%m-%d %H:%M")}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}

        .header .time {{
            opacity: 0.9;
            font-size: 0.9rem;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}

        .stat-card .value {{
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}

        .stat-card.success .value {{ color: #10b981; }}
        .stat-card.failed .value {{ color: #ef4444; }}
        .stat-card.info .value {{ color: #3b82f6; }}
        .stat-card.warning .value {{ color: #f59e0b; }}

        .stat-card .label {{
            color: #6b7280;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .quality-bar {{
            height: 10px;
            background: #e5e7eb;
            border-radius: 5px;
            overflow: hidden;
            display: flex;
            margin-top: 20px;
        }}

        .quality-segment {{
            height: 100%;
            transition: width 0.3s;
        }}

        .quality-segment.high {{ background: #10b981; }}
        .quality-segment.medium {{ background: #f59e0b; }}
        .quality-segment.low {{ background: #ef4444; }}

        .quality-legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 10px;
            font-size: 0.85rem;
            color: #6b7280;
        }}

        .test-results {{
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .test-item {{
            border-bottom: 1px solid #e5e7eb;
            padding: 20px;
            transition: background 0.2s;
        }}

        .test-item:last-child {{
            border-bottom: none;
        }}

        .test-item:hover {{
            background: #f9fafb;
        }}

        .test-header {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
        }}

        .test-id {{
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            flex-shrink: 0;
        }}

        .test-id.success {{ background: #10b981; }}
        .test-id.failed {{ background: #ef4444; }}
        .test-id.error {{ background: #6b7280; }}

        .test-info {{
            flex: 1;
        }}

        .test-url {{
            color: #3b82f6;
            text-decoration: none;
            font-size: 0.85rem;
        }}

        .test-url:hover {{
            text-decoration: underline;
        }}

        .test-stats {{
            display: flex;
            gap: 20px;
            margin-top: 10px;
        }}

        .test-stat {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 0.9rem;
            color: #6b7280;
        }}

        .test-stat .icon {{
            font-size: 1.1rem;
        }}

        .quality-badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 500;
        }}

        .quality-badge.high {{
            background: #d1fae5;
            color: #065f46;
        }}

        .quality-badge.medium {{
            background: #fef3c7;
            color: #92400e;
        }}

        .quality-badge.low {{
            background: #fee2e2;
            color: #991b1b;
        }}

        .samples-preview {{
            margin-top: 10px;
            padding: 10px;
            background: #f3f4f6;
            border-radius: 5px;
            font-size: 0.85rem;
        }}

        .sample-item {{
            padding: 5px 0;
            border-bottom: 1px dashed #d1d5db;
        }}

        .sample-item:last-child {{
            border-bottom: none;
        }}

        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #6b7280;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 网站爬虫测试报告</h1>
            <div class="time">生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card success">
                <div class="value">{success}</div>
                <div class="label">成功</div>
            </div>
            <div class="stat-card failed">
                <div class="value">{failed}</div>
                <div class="label">失败</div>
            </div>
            <div class="stat-card info">
                <div class="value">{total_samples}</div>
                <div class="label">总样本数</div>
            </div>
            <div class="stat-card warning">
                <div class="value">{avg_quality:.1%}</div>
                <div class="label">平均质量</div>
            </div>
        </div>

        <div class="test-results">
"""

    # 添加每个测试的结果
    for result in results:
        status = result.get('status', 'unknown')
        quality_score = result.get('quality_score', 0)
        sample_count = result.get('sample_count', 0)

        # 确定状态样式
        if status in ['done', 'report']:
            status_class = 'success'
            status_icon = '✓'
        elif status == 'error':
            status_class = 'error'
            status_icon = '✗'
        else:
            status_class = 'failed'
            status_icon = '⚠'

        # 确定质量等级
        if quality_score >= 0.8:
            quality_class = 'high'
            quality_text = '高'
        elif quality_score >= 0.5:
            quality_class = 'medium'
            quality_text = '中'
        else:
            quality_class = 'low'
            quality_text = '低'

        # 获取样本预览
        samples_preview = ''
        sample_data = result.get('sample_data', [])
        if sample_data:
            samples_preview = '<div class="samples-preview">样本预览:'
            for i, sample in enumerate(sample_data[:3]):
                sample_str = json.dumps(sample, ensure_ascii=False)
                samples_preview += f'<div class="sample-item">{i+1}. {sample_str[:80]}...</div>'
            samples_preview += '</div>'

        html += f"""
            <div class="test-item">
                <div class="test-header">
                    <div class="test-id {status_class}">{status_icon}</div>
                    <div class="test-info">
                        <div><strong>#{result.get('id', '?')}</strong> {result.get('description', '')[:80]}</div>
                        <a href="{result.get('url', '')}" class="test-url" target="_blank">{result.get('url', '')}</a>
                    </div>
                    <span class="quality-badge {quality_class}">{quality_text}质量 {quality_score:.0%}</span>
                </div>
                <div class="test-stats">
                    <div class="test-stat">
                        <span class="icon">📦</span>
                        <span>{sample_count} 个样本</span>
                    </div>
                    <div class="test-stat">
                        <span class="icon">🎯</span>
                        <span>质量分数: {quality_score:.2f}</span>
                    </div>
                </div>
                {samples_preview}
            </div>
"""

    html += f"""
        </div>

        <div class="quality-bar">
            <div class="quality-segment high" style="width: {high_quality/total*100:.1f}%"></div>
            <div class="quality-segment medium" style="width: {medium_quality/total*100:.1f}%"></div>
            <div class="quality-segment low" style="width: {low_quality/total*100:.1f}%"></div>
        </div>
        <div class="quality-legend">
            <span>🟢 高质量 (≥80%): {high_quality}</span>
            <span>🟡 中等质量 (50-80%): {medium_quality}</span>
            <span>🔴 低质量 (<50%): {low_quality}</span>
        </div>

        <div class="footer">
            <p>报告生成于 {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</p>
            <p>共测试 {total} 个场景 | 成功率 {success/total*100:.1f}%</p>
        </div>
    </div>
</body>
</html>
"""

    # 保存HTML
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] HTML报告已生成: {output_path}")
    return output_path


def main():
    import argparse

    parser = argparse.ArgumentParser(description='生成HTML测试报告')
    parser.add_argument(
        'input',
        type=str,
        help='测试结果目录路径',
    )
    parser.add_argument(
        '-o',
        '--output',
        type=str,
        default=None,
        help='输出HTML文件路径（默认: input/report.html）',
    )

    args = parser.parse_args()

    input_dir = Path(args.input)

    # 默认输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_dir / 'report.html'

    print("="*70)
    print("  HTML测试报告生成器")
    print("="*70)
    print(f"  输入目录: {input_dir}")
    print(f"  输出文件: {output_path}")

    # 加载结果
    results = load_results(input_dir)
    print(f"  加载了 {len(results)} 个测试结果")

    if not results:
        print("  [ERROR] 未找到测试结果")
        return 1

    # 生成HTML报告
    generate_html_report(results, output_path)

    print("\n[OK] 报告生成完成！")
    print(f"  在浏览器中打开: file://{output_path.absolute()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
