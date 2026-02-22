# -*- coding: utf-8 -*-
"""
阿里云百炼多模态大模型客户端

使用阿里云百炼 OpenAI 兼容 API 进行页面截图分析。

支持地域：
- 北京: https://dashscope.aliyuncs.com/compatible-mode/v1
- 新加坡: https://dashscope-intl.aliyuncs.com/compatible-mode/v1
"""

import base64
import os
from typing import Dict, Any, Optional
from openai import AsyncOpenAI


class AliyunVLClient:
    """阿里云百炼多模态大模型客户端 (OpenAI 兼容 API)

    用于分析网页截图，提取页面结构、关键元素和建议的 CSS 选择器。

    支持模型：
    - qwen3.5-plus: 基础图像理解
    - qwen3.5-max: 高级图像理解
    - qwen3-omni-flash: 多模态能力（支持视频）
    """

    def __init__(
        self,
        api_key: str,
        model: str = "qwen3.5-plus",
        base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    ):
        """初始化客户端

        Args:
            api_key: 阿里云 API Key
            model: 模型名称，默认 qwen3.5-plus
            base_url: API 端点 URL（根据地域设置）
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = None

    def _get_client(self) -> AsyncOpenAI:
        """获取 OpenAI 兼容客户端"""
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        return self._client

    async def analyze_screenshot(
        self,
        screenshot_data: bytes,
        user_goal: str,
        url: str,
    ) -> Dict[str, Any]:
        """分析页面截图

        Args:
            screenshot_data: PNG 格式的截图数据
            user_goal: 用户需求
            url: 网页 URL

        Returns:
            分析结果，包含：
            - page_type: 页面类型
            - layout_description: 布局描述
            - key_elements: 关键元素列表
            - suggested_selectors: 建议的 CSS 选择器
            - confidence: 置信度 (0-1)
        """
        # 转换截图为 base64
        image_base64 = base64.b64encode(screenshot_data).decode('utf-8')

        # 构建消息
        prompt = self._build_analysis_prompt(user_goal, url)

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]

        try:
            client = self._get_client()

            # 调用 OpenAI 兼容 API
            completion = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True  # 必须开启流式响应
            )

            # 收集流式响应
            full_response = ""
            async for chunk in completion:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        full_response += delta.content

            # 解析结果
            return self._parse_response(full_response)

        except Exception as e:
            return {
                "error": f"Aliyun Vision API error: {str(e)}",
                "page_type": "unknown",
                "layout_description": "",
                "key_elements": [],
                "suggested_selectors": [],
                "confidence": 0.0,
            }

    def _build_analysis_prompt(self, user_goal: str, url: str) -> str:
        """构建分析提示词

        Args:
            user_goal: 用户需求
            url: 网页 URL

        Returns:
            提示词字符串
        """
        return f"""请分析这个网页截图。

用户需求：{user_goal}
网页URL：{url}

请返回JSON格式的分析结果，包含：
1. page_type: 页面类型（可选值：ecommerce/news/blog/forum/social/search/home/other）
2. layout_description: 布局描述（50-100字）
3. key_elements: 关键元素列表（至少5个），每个元素包含 {{"name": "元素名称", "purpose": "用途"}}
4. suggested_selectors: 建议的 CSS 选择器列表（至少3个），针对用户需求的关键内容
5. confidence: 置信度（0-1之间的小数）

请以以下JSON格式返回：
```json
{{
  "page_type": "news",
  "layout_description": "...",
  "key_elements": [...],
  "suggested_selectors": ["selector1", "selector2", ...],
  "confidence": 0.85
}}
```"""

    def _parse_response(self, content: str) -> Dict[str, Any]:
        """解析 API 响应

        Args:
            content: API 返回的文本内容

        Returns:
            解析后的分析结果
        """
        import re
        import json

        try:
            # 尝试提取 JSON
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(1))
            else:
                # 尝试直接解析 JSON
                try:
                    analysis = json.loads(content.strip())
                except json.JSONDecodeError:
                    # 使用文本解析
                    analysis = self._parse_text_response(content)

            # 确保包含必要字段
            if "page_type" not in analysis:
                analysis["page_type"] = "unknown"
            if "confidence" not in analysis:
                analysis["confidence"] = 0.5
            if "key_elements" not in analysis:
                analysis["key_elements"] = []
            if "suggested_selectors" not in analysis:
                analysis["suggested_selectors"] = []
            if "layout_description" not in analysis:
                analysis["layout_description"] = ""

            return analysis

        except Exception as e:
            return {
                "error": f"Failed to parse response: {str(e)}",
                "page_type": "unknown",
                "layout_description": content[:200] if len(content) > 50 else content,
                "key_elements": [],
                "suggested_selectors": [],
                "confidence": 0.0,
            }

    def _parse_text_response(self, text: str) -> Dict[str, Any]:
        """解析文本格式的响应

        Args:
            text: 响应文本

        Returns:
            解析后的结果
        """
        # 简单的文本解析逻辑
        return {
            "page_type": "unknown",
            "layout_description": text[:500] if len(text) > 100 else text,
            "key_elements": [],
            "suggested_selectors": [],
            "confidence": 0.5,
        }

    async def close(self):
        """关闭客户端连接"""
        if self._client is not None:
            await self._client.close()
            self._client = None
