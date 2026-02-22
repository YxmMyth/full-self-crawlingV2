"""
Tools - 预置工具链

提供 Browser、Firecrawl、Parser 等工具供 LLM 生成的代码使用。
"""

from .browser import BrowserTool
from .parser import ParserTool
from .vision_api import (
    VisionAPIClient,
    OpenAIVisionClient,
    AliyunVisionClient,
    create_vision_client,
    analyze_image_with_mcp,
    should_use_vision_api,
    get_vision_config,
)

__all__ = [
    "BrowserTool",
    "ParserTool",
    # Vision API（预留）
    "VisionAPIClient",
    "OpenAIVisionClient",
    "AliyunVisionClient",
    "create_vision_client",
    "analyze_image_with_mcp",
    "should_use_vision_api",
    "get_vision_config",
]
