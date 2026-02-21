"""
LLM - 智谱 GLM API 客户端

提供代码生成、代码修复、报告生成等功能。
"""

from .client import ZhipuClient, get_client, generate_code

__all__ = ["ZhipuClient", "get_client", "generate_code"]
