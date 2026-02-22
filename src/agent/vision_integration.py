"""
Vision Integration - 视觉模型集成

集成Vision API进行页面视觉理解，辅助爬虫代码生成。
"""

from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
import base64
import io


@dataclass
class VisualAnalysis:
    """视觉分析结果"""
    page_type: str  # 页面类型
    layout_description: str  # 布局描述
    key_elements: List[Dict[str, Any]]  # 关键元素
    suggested_selectors: List[str]  # 建议的选择器
    confidence: float  # 置信度


class VisionIntegration:
    """
    视觉集成模块

    提供页面视觉分析能力，辅助爬虫代码生成。
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = "openai"):
        """
        初始化视觉集成

        Args:
            api_key: API密钥
            provider: Vision服务提供商 (openai, aliyun, tencent, etc.)
        """
        self.api_key = api_key
        self.provider = provider
        self._client = None

    def _get_client(self):
        """获取Vision API客户端"""
        if self._client is None:
            if self.provider == "openai":
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            elif self.provider == "aliyun":
                # 阿里云Vision API
                import requests
                self._client = requests
            elif self.provider == "tencent":
                # 腾讯云Vision API
                import requests
                self._client = requests

        return self._client

    async def analyze_screenshot(
        self,
        screenshot_data: bytes,
        user_goal: str,
        url: str = "",
    ) -> VisualAnalysis:
        """
        分析页面截图

        Args:
            screenshot_data: 截图二进制数据
            user_goal: 用户目标
            url: 页面URL

        Returns:
            视觉分析结果
        """
        # 转换截图为base64
        base64_image = base64.b64encode(screenshot_data).decode('utf-8')

        # 构建分析prompt
        prompt = self._build_analysis_prompt(user_goal, url)

        # 调用Vision API
        if self.provider == "openai":
            return await self._analyze_with_openai(base64_image, prompt)
        elif self.provider == "aliyun":
            return await self._analyze_with_aliyun(base64_image, prompt)
        else:
            # 默认使用简单的规则分析
            return self._rule_based_analysis(screenshot_data, user_goal)

    def _build_analysis_prompt(self, user_goal: str, url: str) -> str:
        """构建分析prompt"""
        return f"""请分析这个网页截图，帮助我生成爬虫代码。

【目标URL】{url}
【用户需求】{user_goal}

【请分析】
1. 页面类型是什么？（新闻列表、商品列表、文章详情、表格等）
2. 页面布局是怎样的？（列表式、卡片式、表格式等）
3. 哪些元素是需要提取的数据？（用位置和颜色描述）
4. 建议使用什么选择器？（基于视觉特征推测）

【输出格式】
请按以下JSON格式输出：
{{
  "page_type": "页面类型",
  "layout_description": "布局描述",
  "key_elements": [
    {{"type": "标题", "location": "左上/中间/右下", "color": "颜色", "count": 数量}},
    {{"type": "链接", "location": "位置", "color": "颜色", "count": 数量}}
  ],
  "suggested_selectors": ["选择器1", "选择器2"],
  "confidence": 0.8
}}
"""

    async def _analyze_with_openai(
        self,
        base64_image: str,
        prompt: str,
    ) -> VisualAnalysis:
        """使用OpenAI Vision API分析"""
        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model="gpt-4o",  # 使用GPT-4V
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            },
                        ],
                    }
                ],
                max_tokens=1000,
            )

            # 解析响应
            content = response.choices[0].message.content

            # 尝试解析JSON
            import json
            try:
                # 提取JSON部分
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    json_str = content[start:end].strip()
                elif "```" in content:
                    start = content.find("```") + 3
                    end = content.find("```", start)
                    json_str = content[start:end].strip()
                else:
                    json_str = content.strip()

                data = json.loads(json_str)

                return VisualAnalysis(
                    page_type=data.get("page_type", "unknown"),
                    layout_description=data.get("layout_description", ""),
                    key_elements=data.get("key_elements", []),
                    suggested_selectors=data.get("suggested_selectors", []),
                    confidence=data.get("confidence", 0.7),
                )
            except json.JSONDecodeError:
                # JSON解析失败，使用文本解析
                return self._parse_text_response(content)

        except Exception as e:
            # API调用失败，返回默认分析
            return VisualAnalysis(
                page_type="unknown",
                layout_description="Vision API unavailable",
                key_elements=[],
                suggested_selectors=[],
                confidence=0.0,
            )

    async def _analyze_with_aliyun(
        self,
        base64_image: str,
        prompt: str,
    ) -> VisualAnalysis:
        """使用阿里云Vision API分析（OpenAI 兼容 API）"""
        try:
            # 转换 base64 回 bytes
            import base64
            screenshot_data = base64.b64decode(base64_image)

            # 使用 AliyunVLClient
            from .vision.aliyun import AliyunVLClient

            # 从环境变量获取配置
            import os
            model = os.getenv("VISION_MODEL", "qwen3-omni-flash")
            base_url = os.getenv("ALIYUN_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")

            client = AliyunVLClient(
                api_key=self.api_key,
                model=model,
                base_url=base_url
            )

            # 提取 URL 和 user_goal (从 prompt 中解析)
            url = ""
            user_goal = prompt

            # 调用 API
            result = await client.analyze_screenshot(
                screenshot_data=screenshot_data,
                user_goal=user_goal,
                url=url,
            )

            # 转换为 VisualAnalysis
            return VisualAnalysis(
                page_type=result.get("page_type", "unknown"),
                layout_description=result.get("layout_description", ""),
                key_elements=result.get("key_elements", []),
                suggested_selectors=result.get("suggested_selectors", []),
                confidence=result.get("confidence", 0.0),
            )

        except Exception as e:
            # API调用失败，返回默认分析
            return VisualAnalysis(
                page_type="unknown",
                layout_description=f"Aliyun Vision API error: {str(e)}",
                key_elements=[],
                suggested_selectors=[],
                confidence=0.0,
            )

    def _rule_based_analysis(
        self,
        screenshot_data: bytes,
        user_goal: str,
    ) -> VisualAnalysis:
        """
        基于规则的分析（后备方案）

        当Vision API不可用时使用。
        """
        from PIL import Image
        import io

        try:
            # 加载图片
            img = Image.open(io.BytesIO(screenshot_data))
            width, height = img.size

            # 基于用户需求推测页面类型
            goal_lower = user_goal.lower()

            if any(kw in goal_lower for kw in ["商品", "product", "price", "购物"]):
                page_type = "商品列表"
                suggested = [".product", ".item", ".goods"]
            elif any(kw in goal_lower for kw in ["文章", "article", "新闻", "news"]):
                page_type = "文章列表"
                suggested = ["article", ".post", ".entry"]
            elif any(kw in goal_lower for kw in ["职位", "job", "招聘"]):
                page_type = "招聘列表"
                suggested = [".job", ".position", "[data-job]"]
            else:
                page_type = "通用列表"
                suggested = [".item", ".card", "[data-id]"]

            return VisualAnalysis(
                page_type=page_type,
                layout_description=f"页面尺寸: {width}x{height}",
                key_elements=[
                    {"type": "容器", "location": "推测居中", "count": "multiple"},
                ],
                suggested_selectors=suggested,
                confidence=0.5,
            )

        except Exception as e:
            return VisualAnalysis(
                page_type="unknown",
                layout_description=f"分析失败: {str(e)}",
                key_elements=[],
                suggested_selectors=[],
                confidence=0.0,
            )

    def _parse_text_response(self, content: str) -> VisualAnalysis:
        """解析文本格式的响应"""
        # 简单的文本解析
        suggested_selectors = []

        # 查找选择器模式
        import re
        selector_pattern = r'[.\-[\w="\'\]]+'
        matches = re.findall(selector_pattern, content)

        for match in matches:
            if any(char in match for char in ['.', '[', '=', '#']):
                suggested_selectors.append(match)

        return VisualAnalysis(
            page_type="unknown",
            layout_description=content[:200],
            key_elements=[],
            suggested_selectors=suggested_selectors[:5],
            confidence=0.6,
        )

    async def enhance_dom_analysis_with_vision(
        self,
        html: str,
        screenshot: bytes,
        user_goal: str,
        url: str = "",
    ) -> Dict[str, Any]:
        """
        使用视觉分析增强DOM分析

        Args:
            html: HTML内容
            screenshot: 页面截图
            user_goal: 用户目标
            url: 页面URL

        Returns:
            增强后的分析结果
        """
        # 获取视觉分析
        visual_result = await self.analyze_screenshot(screenshot, user_goal, url)

        # 解析HTML获取基本信息
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')

        # 合并分析结果
        enhanced_analysis = {
            # 视觉分析
            "visual_page_type": visual_result.page_type,
            "visual_layout": visual_result.layout_description,
            "visual_suggested_selectors": visual_result.suggested_selectors,

            # HTML分析
            "html_structure": {
                "total_elements": len(soup.find_all()),
                "has_tables": bool(soup.find('table')),
                "has_images": len(soup.find_all('img')) > 0,
                "has_forms": bool(soup.find('form')),
            },

            # 合并建议
            "recommended_selectors": self._merge_selector_suggestions(
                visual_result.suggested_selectors,
                soup,
                user_goal
            ),

            # 置信度
            "confidence": visual_result.confidence,
        }

        return enhanced_analysis

    def _merge_selector_suggestions(
        self,
        visual_selectors: List[str],
        soup,
        user_goal: str,
    ) -> List[str]:
        """
        合并视觉和HTML分析的选择器建议

        Args:
            visual_selectors: 视觉分析建议的选择器
            soup: BeautifulSoup对象
            user_goal: 用户目标

        Returns:
            合并后的选择器列表
        """
        merged = []

        # 首先添加视觉建议的选择器
        for selector in visual_selectors:
            # 验证选择器是否有效
            try:
                if soup.select(selector):
                    merged.append(selector)
            except:
                # 选择器可能无效，但仍然保留作为尝试
                merged.append(selector)

        # 添加基于HTML结构的建议
        goal_lower = user_goal.lower()

        if "title" in goal_lower or "标题" in goal_lower:
            for tag in ['h1', 'h2', 'h3', '[class*="title"]', '[class*="heading"]']:
                if soup.select(tag):
                    merged.append(tag)
                    break

        if "link" in goal_lower or "链接" in goal_lower:
            if soup.select('a[href]'):
                merged.append('a[href]')

        # 去重
        return list(set(merged))


async def analyze_page_with_vision(
    screenshot: Union[bytes, str],
    user_goal: str,
    url: str = "",
    api_key: Optional[str] = None,
    provider: str = "openai",
) -> VisualAnalysis:
    """
    便捷函数：使用Vision API分析页面

    Args:
        screenshot: 截图数据或文件路径
        user_goal: 用户目标
        url: 页面URL
        api_key: API密钥
        provider: Vision服务提供商

    Returns:
        视觉分析结果
    """
    vision = VisionIntegration(api_key, provider)

    # 如果是文件路径，读取文件
    if isinstance(screenshot, str):
        with open(screenshot, 'rb') as f:
            screenshot = f.read()

    return await vision.analyze_screenshot(screenshot, user_goal, url)
