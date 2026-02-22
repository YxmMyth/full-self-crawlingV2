# -*- coding: utf-8 -*-
"""
Performance tracking for agent nodes.

This module provides a decorator to track execution time, status, and errors
for each node in the agent graph.
"""

import time
from functools import wraps
from typing import Dict, Any, Callable


def track_performance(node_name: str):
    """装饰器：跟踪节点执行时间和资源使用

    Args:
        node_name: 节点名称，用于记录性能数据

    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(state: Dict[str, Any]) -> Dict[str, Any]:
            start_time = time.time()

            # 记录开始状态
            performance_data = state.get("performance_data", {})
            performance_data[f"{node_name}_start"] = start_time

            try:
                result = await func(state)

                # 记录完成时间和耗时
                end_time = time.time()
                duration = end_time - start_time

                performance_data[f"{node_name}_duration"] = duration
                performance_data[f"{node_name}_end"] = end_time
                performance_data[f"{node_name}_status"] = "success"

                # 记录调用次数
                call_count = performance_data.get(f"{node_name}_calls", 0)
                performance_data[f"{node_name}_calls"] = call_count + 1

                state["performance_data"] = performance_data
                return result

            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time

                performance_data[f"{node_name}_duration"] = duration
                performance_data[f"{node_name}_end"] = end_time
                performance_data[f"{node_name}_status"] = "error"
                performance_data[f"{node_name}_error"] = str(e)

                # 记录调用次数
                call_count = performance_data.get(f"{node_name}_calls", 0)
                performance_data[f"{node_name}_calls"] = call_count + 1

                state["performance_data"] = performance_data
                raise

        return wrapper
    return decorator


def get_performance_summary(performance_data: Dict[str, Any]) -> Dict[str, Any]:
    """从性能数据中提取摘要信息

    Args:
        performance_data: 性能数据字典

    Returns:
        包含各节点耗时摘要的字典
    """
    summary = {
        "nodes": {},
        "total_time": 0,
    }

    nodes = set()
    for key in performance_data.keys():
        if key.endswith("_duration"):
            node_name = key.replace("_duration", "")
            nodes.add(node_name)

    for node in sorted(nodes):
        duration = performance_data.get(f"{node}_duration", 0)
        status = performance_data.get(f"{node}_status", "unknown")
        calls = performance_data.get(f"{node}_calls", 1)
        summary["nodes"][node] = {
            "duration": duration,
            "status": status,
            "calls": calls,
        }
        summary["total_time"] += duration

    return summary


def format_performance_report(performance_data: Dict[str, Any]) -> str:
    """格式化性能报告为可读文本

    Args:
        performance_data: 性能数据字典

    Returns:
        格式化的性能报告字符串
    """
    summary = get_performance_summary(performance_data)

    lines = ["=" * 50]
    lines.append("性能分析报告")
    lines.append("=" * 50)

    # 按耗时排序
    nodes_by_duration = sorted(
        summary["nodes"].items(),
        key=lambda x: x[1]["duration"],
        reverse=True
    )

    for node, data in nodes_by_duration:
        duration = data["duration"]
        status = data["status"]
        calls = data["calls"]
        percentage = (duration / summary["total_time"] * 100) if summary["total_time"] > 0 else 0

        lines.append(f"{node:15s}: {duration:6.2f}s ({percentage:5.1f}%) [调用{calls}次, 状态:{status}]")

    lines.append("=" * 50)
    lines.append(f"总耗时: {summary['total_time']:.2f}s")

    return "\n".join(lines)
