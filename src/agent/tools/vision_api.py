"""
Vision API 客户端 - 预留接口（后续实现）

支持的 API:
- OpenAI Vision API (gpt-4-vision-preview)
- 阿里云视觉智能开放平台
- 腾讯云图像分析
- 百度智能云图像理解

使用场景：
1. 图片内容描述（当沙箱中 CLIP 不可用时）
2. 图片风格分析
3. 物体检测
4. OCR 文字识别
"""

import os
import json
from typing import Dict, List, Any, Optional
from abc import ABC, abstractmethod


class VisionAPIClient(ABC):
    """Vision API 客户端抽象基类"""

    @abstractmethod
    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """
        分析图片内容

        Args:
            image_url: 图片 URL
            prompt: 分析提示词

        Returns:
            分析结果字典
        """
        pass

    @abstractmethod
    async def check_style(self, image_url: str, style_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """检查图片风格"""
        pass

    @abstractmethod
    async def detect_objects(self, image_url: str) -> List[Dict[str, Any]]:
        """检测图片中的物体"""
        pass


class OpenAIVisionClient(VisionAPIClient):
    """
    OpenAI Vision API 客户端

    使用 gpt-4-vision-preview 或 gpt-4o 模型分析图片
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        初始化 OpenAI Vision 客户端

        Args:
            api_key: OpenAI API Key（从环境变量 OPENAI_API_KEY 读取）
            model: 使用的模型，默认 gpt-4o（支持视觉）
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._client = None

    def _get_client(self):
        """懒加载 OpenAI 客户端"""
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "请安装 openai 库: pip install openai"
                )
        return self._client

    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """
        使用 OpenAI Vision API 分析图片

        Args:
            image_url: 图片 URL（需要公网可访问）
            prompt: 分析提示词，例如 "描述这张图片的内容"

        Returns:
            {
                "success": bool,
                "description": str,  # 图片描述
                "error": str | None
            }
        """
        try:
            client = self._get_client()

            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=500
            )

            description = response.choices[0].message.content

            return {
                "success": True,
                "description": description,
                "model": self.model,
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "description": None,
                "error": str(e)
            }

    async def check_style(self, image_url: str, style_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查图片风格

        Args:
            image_url: 图片 URL
            style_requirements: 风格要求，例如 {"style": "minimalist", "colors": ["blue", "white"]}

        Returns:
            {
                "matches": bool,
                "detected_style": str,
                "confidence": float
            }
        """
        # 预留实现
        raise NotImplementedError("OpenAI Vision 风格检查待实现")

    async def detect_objects(self, image_url: str) -> List[Dict[str, Any]]:
        """
        检测图片中的物体

        Args:
            image_url: 图片 URL

        Returns:
            物体列表，例如 [{"object": "cat", "confidence": 0.95}]
        """
        # 预留实现
        raise NotImplementedError("OpenAI Vision 物体检测待实现")


class AliyunVisionClient(VisionAPIClient):
    """
    阿里云视觉智能开放平台客户端

    支持功能：
    - 图像内容理解
    - 商品理解
    - 图像打标
    """

    def __init__(self, access_key_id: Optional[str] = None, access_key_secret: Optional[str] = None):
        """
        初始化阿里云 Vision 客户端

        Args:
            access_key_id: 阿里云 AccessKey ID
            access_key_secret: 阿里云 AccessKey Secret
        """
        self.access_key_id = access_key_id or os.getenv("ALIYUN_ACCESS_KEY_ID")
        self.access_key_secret = access_key_secret or os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        self._client = None

    def _get_client(self):
        """懒加载阿里云客户端"""
        if self._client is None:
            try:
                from alibabacloud_tea_openapi import models as open_api_models
                from alibabacloud_imagerecog20190930.client import Client as ImageRecogClient
                from alibabacloud_tea_util import models as util_models

                config = open_api_models.Config(
                    access_key_id=self.access_key_id,
                    access_key_secret=self.access_key_secret
                )
                config.endpoint = f'imagerecog.cn-shanghai.aliyuncs.com'
                self._client = ImageRecogClient(config)
            except ImportError:
                raise ImportError(
                    "请安装阿里云 SDK: pip install alibabacloud-imagerecog20190930"
                )
        return self._client

    async def analyze_image(self, image_url: str, prompt: str) -> Dict[str, Any]:
        """使用阿里云分析图片"""
        # 预留实现
        raise NotImplementedError("阿里云 Vision API 集成待实现")

    async def check_style(self, image_url: str, style_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """检查图片风格"""
        raise NotImplementedError("阿里云风格检查待实现")

    async def detect_objects(self, image_url: str) -> List[Dict[str, Any]]:
        """检测图片中的物体"""
        raise NotImplementedError("阿里云物体检测待实现")


def create_vision_client(provider: str = "none", **kwargs) -> Optional[VisionAPIClient]:
    """
    创建 Vision API 客户端工厂函数

    Args:
        provider: API 提供商，可选 "none", "openai", "aliyun", "tencent"
        **kwargs: 传递给客户端的额外参数

    Returns:
        VisionAPIClient 实例或 None（当 provider="none" 时）

    Raises:
        ValueError: 不支持的 provider
    """
    providers = {
        "openai": OpenAIVisionClient,
        "aliyun": AliyunVisionClient,
        "none": None,
    }

    client_class = providers.get(provider.lower())
    if client_class is None:
        if provider.lower() == "none":
            return None
        raise ValueError(f"不支持的 Vision API 提供商: {provider}。可选: {list(providers.keys())}")

    if provider.lower() == "none":
        return None

    return client_class(**kwargs)


async def analyze_image_with_mcp(image_url: str, prompt: str) -> Dict[str, Any]:
    """
    使用 MCP 工具分析图片（如果可用）

    这是默认选项，使用 Claude Code 的 MCP 工具 mcp__4_5v_mcp__analyze_image

    Args:
        image_url: 图片 URL
        prompt: 分析提示词

    Returns:
        分析结果
    """
    # 预留：在支持 MCP 调用的环境中使用
    # 当前返回占位结果
    return {
        "success": False,
        "description": None,
        "error": "MCP 分析需要在外部环境中调用"
    }


# ============================================================================
# 辅助函数
# ============================================================================

def should_use_vision_api(user_goal: str) -> bool:
    """
    判断是否需要使用 Vision API

    根据用户需求判断是否需要进行图片内容分析

    Args:
        user_goal: 用户需求描述

    Returns:
        是否需要使用 Vision API
    """
    keywords = [
        "描述图片", "图片内容", "图片描述",
        "describe image", "image content", "image description",
        "图片风格", "image style",
        "图片质量", "image quality"
    ]

    goal_lower = user_goal.lower()
    return any(keyword in goal_lower for keyword in keywords)


def get_vision_config() -> Dict[str, Any]:
    """
    从环境变量获取 Vision API 配置

    Returns:
        配置字典
    """
    return {
        "provider": os.getenv("VISION_API_PROVIDER", "none"),
        "enabled": os.getenv("ENABLE_VISION_API", "false").lower() == "true",
        "model": os.getenv("VISION_MODEL", "gpt-4o"),
    }


__all__ = [
    "VisionAPIClient",
    "OpenAIVisionClient",
    "AliyunVisionClient",
    "create_vision_client",
    "analyze_image_with_mcp",
    "should_use_vision_api",
    "get_vision_config",
]
