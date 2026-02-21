"""
Single Agent End-to-End Test

测试 SiteAgent 完整流程：Sense → Plan → Act → Verify → Report

测试目标：Wikipedia (Albert Einstein)
理由：结构化好、无反爬、适合首次测试

数据需求：提取历史名人传记信息，包括生平、成就和时间线
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


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_result(result: dict):
    """打印结果摘要"""
    print_section("执行结果")

    print(f"状态: {'成功' if result.get('success') else '失败'}")
    print(f"阶段: {result.get('stage', 'unknown')}")
    print(f"Agent ID: {result.get('agent_id', 'unknown')}")

    if result.get("error"):
        print(f"\n错误信息:")
        print(f"  {result['error']}")

    if result.get("markdown_report"):
        print(f"\n侦察报告:")
        print("-" * 60)
        print(result["markdown_report"])
        print("-" * 60)

    if result.get("generated_code"):
        print(f"\n生成的代码:")
        print("-" * 60)
        code = result["generated_code"]
        # 只显示前 500 个字符
        preview = code[:500] + "..." if len(code) > 500 else code
        print(preview)
        print("-" * 60)


async def test_wikipedia_einstein():
    """测试 Wikipedia Albert Einstein 页面"""

    print_section("单 Agent 端到端测试")

    # 检查 API Key
    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("警告: 未设置 ZHIPU_API_KEY 环境变量")
        print("请设置后再运行测试:")
        print("  PowerShell: $env:ZHIPU_API_KEY='your_api_key_here'")
        print("  CMD: set ZHIPU_API_KEY=your_api_key_here")
        print("\n将使用模拟模式继续...")
        return

    # 创建 Agent
    print("\n创建 SiteAgent...")
    agent = SiteAgent()

    # 测试参数
    task_params = {
        "site_url": "https://en.wikipedia.org/wiki/Albert_Einstein",
        "user_goal": "提取历史名人传记信息，包括生平、成就和时间线",
    }

    print(f"站点 URL: {task_params['site_url']}")
    print(f"用户需求: {task_params['user_goal']}")

    # 执行侦察
    print_section("开始侦察")
    print("\n流程: Sense → Plan → Act → Verify → Report\n")

    try:
        result = await agent.run(task_params)

        # 打印结果
        print_result(result)

        # 保存结果到文件
        output_dir = project_root / "tests" / "output"
        output_dir.mkdir(exist_ok=True)

        output_file = output_dir / "wikipedia_einstein_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print(f"\n结果已保存到: {output_file}")

        # 保存报告到 Markdown 文件
        if result.get("markdown_report"):
            report_file = output_dir / "wikipedia_einstein_report.md"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(result["markdown_report"])
            print(f"报告已保存到: {report_file}")

    except Exception as e:
        print(f"\n执行失败: {e}")
        import traceback
        traceback.print_exc()


async def test_with_stream():
    """测试流式输出模式"""

    print_section("流式输出测试")

    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("跳过流式测试（未设置 API Key）")
        return

    agent = SiteAgent()

    print("\n开始流式执行...\n")

    async for event in agent.stream({
        "site_url": "https://en.wikipedia.org/wiki/Albert_Einstein",
        "user_goal": "提取历史名人传记信息",
    }):
        stage = event.get("stage", "unknown")
        print(f"  [阶段] {stage}")

        if stage == "verify":
            print(f"    质量分数: {event.get('quality', 'N/A')}")
        elif stage == "report":
            print(f"    完成!")

    print("\n流式执行完成!")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Single Agent 测试")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="使用流式输出模式"
    )

    args = parser.parse_args()

    if args.stream:
        asyncio.run(test_with_stream())
    else:
        asyncio.run(test_wikipedia_einstein())


if __name__ == "__main__":
    main()
