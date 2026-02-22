"""
Test CodeAct-style Agent

测试基于 CodeAct 架构的 Agent：
- Sense: LLM 生成 DOM 分析代码 → 沙箱执行
- Plan: LLM 生成爬虫代码
- Act: 沙箱执行爬虫代码
- Verify: LLM 生成质量评估代码 → 沙箱执行
- SOOAL: LLM 生成诊断/修复代码
"""

import asyncio
import os
import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent import SiteAgent


async def test_arxiv():
    """测试 Arxiv（AI 论文）"""

    print("\n" + "=" * 60)
    print("  CodeAct Agent 测试 - Arxiv AI 论文")
    print("=" * 60)

    # 检查 API Key
    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("错误: 未设置 ZHIPU_API_KEY 环境变量")
        return False

    # 创建 Agent
    print("\n创建 SiteAgent...")
    agent = SiteAgent()

    # 测试参数
    task_params = {
        "site_url": "https://arxiv.org/list/cs.AI/recent",
        "user_goal": "提取 AI 论文列表，包括标题、作者、摘要链接",
    }

    print(f"站点 URL: {task_params['site_url']}")
    print(f"用户需求: {task_params['user_goal']}")

    # 执行侦察
    print("\n开始侦察...")
    print("流程: Sense → Plan → Act → Verify → Report\n")

    try:
        result = await agent.run(task_params)

        # 打印结果
        print("\n" + "=" * 60)
        print("  执行结果")
        print("=" * 60)
        print(f"状态: {'成功' if result.get('success') else '失败'}")
        print(f"阶段: {result.get('stage', 'unknown')}")
        print(f"Agent ID: {result.get('agent_id', 'unknown')}")

        if result.get("error"):
            print(f"\n错误信息:")
            print(f"  {result['error']}")

        # 打印样本数据
        if result.get("report") and result["report"].get("sample_data"):
            samples = result["report"]["sample_data"]
            print(f"\n样本数量: {len(samples)}")
            if samples:
                print("\n前 3 条样本:")
                for i, sample in enumerate(samples[:3], 1):
                    print(f"\n  [{i}]")
                    for k, v in sample.items():
                        print(f"      {k}: {str(v)[:100]}...")

        # 打印生成的代码片段
        if result.get("generated_code"):
            print(f"\n生成的爬虫代码 (前 500 字符):")
            print("-" * 60)
            code = result["generated_code"]
            preview = code[:500] + "..." if len(code) > 500 else code
            print(preview)
            print("-" * 60)

        # 打印报告片段
        if result.get("markdown_report"):
            print(f"\n侦察报告 (前 1000 字符):")
            print("-" * 60)
            report = result["markdown_report"]
            preview = report[:1000] + "..." if len(report) > 1000 else report
            print(preview)
            print("-" * 60)

        # 保存结果
        output_dir = project_root / "tests" / "output"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / "arxiv_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {output_file}")

        if result.get("markdown_report"):
            report_file = output_dir / "arxiv_report.md"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(result["markdown_report"])
            print(f"报告已保存到: {report_file}")

        return result.get("success", False)

    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    success = await test_arxiv()
    print("\n" + "=" * 60)
    print(f"测试结果: {'通过' if success else '失败'}")
    print("=" * 60)
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
