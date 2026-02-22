"""
Run Capability Test - 能力测试入口脚本

快速运行 Recon Agent 能力检测测试的入口脚本。

使用方法:
    python run_capability_test.py              # 运行所有测试
    python run_capability_test.py --phase 1    # 只运行Phase 1
    python run_capability_test.py --id 5       # 只运行测试#5
"""

import asyncio
import os
import sys
from pathlib import Path

# 修复 Windows 控制台编码问题
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tests.capability_test import CapabilityTestRunner, TEST_CASES


def print_banner():
    """打印横幅"""
    print("\n" + "=" * 60)
    print("  Recon Agent 能力检测测试")
    print("  10个不同类型的数据采集需求验证")
    print("=" * 60)
    print("\n测试用例列表:")
    for tc in TEST_CASES:
        stars = "⭐" * tc.difficulty
        print(f"  #{tc.id:2d} | Phase {tc.phase} | {stars} | {tc.name}")
    print()


def print_usage():
    """打印使用说明"""
    print("""
使用方法:
    python run_capability_test.py              # 运行所有测试
    python run_capability_test.py --phase 1    # 只运行Phase 1
    python run_capability_test.py --id 5       # 只运行测试#5
    python run_capability_test.py --help       # 显示帮助

测试阶段说明:
    Phase 1: 基础验证 (arXiv, Medium)         - 预期通过率 >= 80%
    Phase 2: 扩展验证 (TechCrunch, AllRecipes, UK Gov) - 预期通过率 >= 80%
    Phase 3: 增强功能 (Indeed, Datawrapper, Zillow) - 预期通过率 >= 50%
    Phase 4: 高级挑战 (Amazon, Yahoo Finance)  - 识别能力边界
    """)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Recon Agent 能力检测测试",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--phase", type=int, choices=[1, 2, 3, 4],
                        help="只运行指定阶段 (1-4)")
    parser.add_argument("--id", type=int,
                        help="只运行指定ID的测试")
    parser.add_argument("--list", action="store_true",
                        help="列出所有测试用例")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="详细输出")

    args = parser.parse_args()

    # 打印横幅
    print_banner()

    if args.list:
        # 列出测试用例后退出
        return

    if args.id:
        print(f"运行单个测试: #{args.id}")
    elif args.phase:
        print(f"运行 Phase {args.phase} 测试")
    else:
        print("运行所有测试 (Phase 1-4)")

    # 检查API密钥
    api_key = os.environ.get("ZHIPU_API_KEY")
    if not api_key:
        print("\n⚠️  警告: 未设置 ZHIPU_API_KEY 环境变量")
        print("请设置后再运行测试:")
        print("  PowerShell: $env:ZHIPU_API_KEY='your_api_key_here'")
        print("  CMD: set ZHIPU_API_KEY=your_api_key_here")
        print("\n如果继续运行，可能会在 LLM 调用阶段失败。\n")

        # 询问是否继续
        try:
            response = input("是否继续? (y/N): ")
            if response.lower() != 'y':
                print("已取消。")
                return
        except (EOFError, KeyboardInterrupt):
            print("\n已取消。")
            return

    print("\n开始测试...\n")

    # 运行测试
    runner = CapabilityTestRunner()

    if args.id:
        # 运行单个测试
        from tests.capability_test import get_test_case_by_id
        test_case = get_test_case_by_id(args.id)
        if test_case:
            result = await runner.run_single_test(test_case)
            runner.results.append(result)
            runner._save_single_result(result)
        else:
            print(f"❌ 未找到 ID 为 {args.id} 的测试用例")
    else:
        # 运行所有测试或指定阶段
        await runner.run_all(phase_filter=args.phase)

    print("\n测试完成！")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被中断。")
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
