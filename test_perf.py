# -*- coding: utf-8 -*-
import asyncio
import json
from src.agent.agent import SiteAgent

async def test():
    print('[INFO] 启动 Agent 测试...')
    agent = SiteAgent()

    result = await agent.run({
        'site_url': 'https://example.com',
        'user_goal': '获取页面标题',
    })

    print()
    print('[结果] 最终状态:', result.get('stage'))
    print('[结果] 成功:', result.get('success'))

    final_state = result.get('final_state', {})
    print('[结果] 质量分数:', final_state.get('quality_score', 0))
    print('[结果] 样本数量:', len(final_state.get('sample_data', [])))

    perf = final_state.get('performance_data', {})
    print()
    print('[性能] 性能数据键:', list(perf.keys()) if perf else '无')

    if perf:
        print('[性能] 节点耗时:')
        for key, value in sorted(perf.items()):
            if 'duration' in key:
                node = key.replace('_duration', '')
                print(f'  {node}: {value:.2f}s')

    # 保存结果到文件
    with open('test_performance_result.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print()
    print('[INFO] 结果已保存到 test_performance_result.json')

if __name__ == "__main__":
    asyncio.run(test())
