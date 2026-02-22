# -*- coding: utf-8 -*-
"""
详细调试 Agent 运行过程
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path.cwd() / '.env'
load_dotenv(dotenv_path=env_path)
print(f"[ENV] API Key: {os.getenv('ZHIPU_API_KEY', 'None')[:20]}...")

sys.path.insert(0, str(Path.cwd()))

from src.agent.agent import SiteAgent

async def debug_test():
    print("\n" + "="*70)
    print("  Agent 详细调试测试")
    print("="*70)

    agent = SiteAgent()

    # 直接运行并获取完整结果
    print("\n[开始] 运行 Agent...")
    result = await agent.run({
        'site_url': 'https://techcrunch.com',
        'user_goal': '提取最新的科技新闻标题和链接，至少5条',
    })

    print(f"\n[最终结果]")
    print(f"  状态: {result.get('stage')}")
    print(f"  成功: {result.get('success')}")

    final_state = result.get('final_state', {})
    print(f"  样本数: {len(final_state.get('sample_data', []))}")
    print(f"  质量分数: {final_state.get('quality_score', 0)}")
    print(f"  SOOAL 迭代: {final_state.get('sool_iteration', 0)}")

    # 显示失败历史
    failure_history = final_state.get('failure_history', [])
    if failure_history:
        print(f"\n[失败历史] 共 {len(failure_history)} 次:")
        for i, fail in enumerate(failure_history):
            print(f"  {i+1}. {fail.get('failure_type')}: {fail.get('root_cause')[:100]}")

    # 显示生成的代码
    if result.get('generated_code'):
        print(f"\n[生成的代码] ({len(result['generated_code'])} 字符):")
        print(result['generated_code'][:500] + "...")

    # 显示执行结果
    execution_result = final_state.get('execution_result')
    if execution_result:
        print(f"\n[执行结果]")
        print(f"  成功: {execution_result.get('success')}")
        if execution_result.get('error'):
            print(f"  错误: {execution_result.get('error')[:200]}")
        if execution_result.get('stderr'):
            print(f"  Stderr: {execution_result.get('stderr')[:200]}")

    print("\n" + "="*70)
    print("  测试完成")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(debug_test())
