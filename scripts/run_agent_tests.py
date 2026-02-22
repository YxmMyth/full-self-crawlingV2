"""
Recon Agent 自主能力测试

让 Agent 自己去执行10个不同类型的数据采集任务，
记录它的表现，而不是预先写好解决方案。
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Windows console UTF-8 fix
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agent import SiteAgent


# 10个真实测试任务
TEST_TASKS = [
    # Phase 1: 基础验证
    {
        "id": 5,
        "name": "arXiv学术论文",
        "url": "https://arxiv.org/list/cs/recent",
        "goal": "提取AI/CS论文列表，包括标题、作者、摘要、PDF链接",
        "phase": 1,
    },
    {
        "id": 9,
        "name": "Medium博客",
        "url": "https://medium.com",
        "goal": "提取博客文章列表，包括标题、作者、摘要、封面图片",
        "phase": 1,
    },

    # Phase 2: 扩展验证
    {
        "id": 2,
        "name": "TechCrunch新闻",
        "url": "https://techcrunch.com",
        "goal": "提取科技新闻文章，包括标题、正文片段、图片、视频链接",
        "phase": 2,
    },
    {
        "id": 7,
        "name": "AllRecipes菜谱",
        "url": "https://www.allrecipes.com/recipes/17562/dinner/main-dish/",
        "goal": "提取菜谱列表，包括名称、配料、步骤、成品图片",
        "phase": 2,
    },
    {
        "id": 10,
        "name": "英国政府招标",
        "url": "https://www.find-tender.service.gov.uk",
        "goal": "提取招标公告，包括标题、PDF链接、金额信息",
        "phase": 2,
    },

    # Phase 3: 增强功能
    {
        "id": 4,
        "name": "Indeed招聘",
        "url": "https://www.indeed.com/jobs?q=software+engineer",
        "goal": "提取招聘职位，包括职位名称、薪资、公司Logo、职位描述",
        "phase": 3,
    },
    {
        "id": 3,
        "name": "Datawrapper图表",
        "url": "https://www.datawrapper.de",
        "goal": "提取数据可视化图表的SVG代码",
        "phase": 3,
    },
    {
        "id": 6,
        "name": "Zillow房产",
        "url": "https://www.zillow.com/",
        "goal": "提取房产信息，包括价格、户型图链接",
        "phase": 3,
    },

    # Phase 4: 高级挑战
    {
        "id": 1,
        "name": "Amazon电商",
        "url": "https://www.amazon.com/s?k=smartphone",
        "goal": "提取商品列表，包括名称、价格、主图",
        "phase": 4,
    },
    {
        "id": 8,
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/quote/AAPL/chart",
        "goal": "提取股票信息，包括当前价格、图表相关内容",
        "phase": 4,
    },
]


async def run_single_task(agent: SiteAgent, task: dict, results_dir: Path, timestamp: str):
    """让Agent执行单个任务并保存详细日志"""
    print(f"\n{'='*60}")
    print(f"  任务 #{task['id']}: {task['name']} (Phase {task['phase']})")
    print(f"{'='*60}")
    print(f"URL: {task['url']}")
    print(f"目标: {task['goal']}")

    start_time = time.time()

    try:
        # 让Agent自己解决问题
        result = await agent.run({
            "site_url": task["url"],
            "user_goal": task["goal"],
        })

        duration = time.time() - start_time

        # 分析结果
        success = result.get("success", False)
        error = result.get("error", "")
        report = result.get("report", {})
        final_state = result.get("final_state", {})

        # 获取提取的数据
        sample_data = report.get("sample_data", []) or final_state.get("sample_data", [])
        data_count = len(sample_data) if isinstance(sample_data, list) else 0

        print(f"\n结果:")
        print(f"  状态: {'✅ 成功' if success else '❌ 失败'}")
        print(f"  耗时: {duration:.1f}秒")
        print(f"  数据量: {data_count}条")

        if error:
            print(f"  错误: {error[:100]}")

        if sample_data and len(sample_data) > 0:
            print(f"\n  样本数据预览:")
            for i, item in enumerate(sample_data[:2]):
                print(f"    [{i+1}] {list(item.keys())[:5]}...")

        # ===== 新增：保存详细日志 =====
        detailed_log = {
            "summary": {
                "task_id": task["id"],
                "task_name": task["name"],
                "phase": task["phase"],
                "url": task["url"],
                "goal": task["goal"],
                "success": success,
                "duration": round(duration, 1),
                "data_count": data_count,
                "error": error[:500] if error else "",
                "sample_keys": list(sample_data[0].keys()) if sample_data else [],
            },
            "details": {
                "generated_code": result.get("generated_code", ""),
                "markdown_report": result.get("markdown_report", ""),
                "quality_score": final_state.get("quality_score", 0),
                "sool_iteration": final_state.get("sool_iteration", 0),
                "failure_history": final_state.get("failure_history", []),
                "reflection_memory": final_state.get("reflection_memory", []),
                "attempt_signatures": final_state.get("attempt_signatures", []),
                "quality_issues": final_state.get("quality_issues", []),
                "sample_data": sample_data[:5],  # 只保存前5条
            }
        }

        # 保存详细日志到独立文件
        detail_file = results_dir / f"task_{task['id']:02d}_{task['name']}_{timestamp}_detail.json"
        with open(detail_file, "w", encoding="utf-8") as f:
            json.dump(detailed_log, f, ensure_ascii=False, indent=2)
        print(f"  详细日志: {detail_file}")

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "phase": task["phase"],
            "success": success,
            "duration": round(duration, 1),
            "data_count": data_count,
            "error": error[:200] if error else "",
            "sample_keys": list(sample_data[0].keys()) if sample_data else [],
            "detail_file": str(detail_file),
        }

    except Exception as e:
        duration = time.time() - start_time
        error_msg = str(e)
        print(f"\n❌ 异常: {error_msg[:100]}")

        return {
            "task_id": task["id"],
            "task_name": task["name"],
            "phase": task["phase"],
            "success": False,
            "duration": round(duration, 1),
            "data_count": 0,
            "error": error_msg[:200],
            "sample_keys": [],
        }


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Recon Agent 自主能力测试")
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4], help="只测试指定阶段")
    parser.add_argument("--id", type=int, help="只测试指定任务")
    args = parser.parse_args()

    print("="*60)
    print("  Recon Agent 自主能力测试")
    print("  让Agent自己解决问题，而非预设方案")
    print("="*60)

    # 检查API密钥
    if not os.getenv("ZHIPU_API_KEY"):
        print("\n⚠️  未设置 ZHIPU_API_KEY")
        print("请设置后再运行: export ZHIPU_API_KEY=xxx")
        return

    # 筛选任务
    tasks_to_run = TEST_TASKS
    if args.id:
        tasks_to_run = [t for t in TEST_TASKS if t["id"] == args.id]
    elif args.phase:
        tasks_to_run = [t for t in TEST_TASKS if t["phase"] == args.phase]

    print(f"\n将执行 {len(tasks_to_run)} 个任务")

    # 创建Agent
    agent = SiteAgent()

    # 创建结果目录
    results_dir = project_root / "agent_test_results"
    results_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 执行测试
    all_results = []
    start_time = time.time()

    for task in tasks_to_run:
        result = await run_single_task(agent, task, results_dir, timestamp)
        all_results.append(result)

        # 间隔一下，避免请求过快
        await asyncio.sleep(2)

    total_duration = time.time() - start_time

    # 汇总报告
    print(f"\n{'='*60}")
    print("  测试汇总")
    print(f"{'='*60}")

    # 按阶段统计
    for phase in [1, 2, 3, 4]:
        phase_results = [r for r in all_results if r["phase"] == phase]
        if phase_results:
            passed = sum(1 for r in phase_results if r["success"])
            print(f"Phase {phase}: {passed}/{len(phase_results)} 通过")

    # 总体
    passed = sum(1 for r in all_results if r["success"])
    print(f"\n总计: {passed}/{len(all_results)} 通过 ({passed/len(all_results)*100:.0f}%)")
    print(f"总耗时: {total_duration:.1f}秒")

    # 保存汇总结果
    result_file = results_dir / f"agent自主测试_{timestamp}.json"

    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": timestamp,
            "total_duration": round(total_duration, 1),
            "total_tasks": len(all_results),
            "passed_tasks": passed,
            "pass_rate": round(passed / len(all_results), 2) if all_results else 0,
            "results": all_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {result_file}")


if __name__ == "__main__":
    asyncio.run(main())
