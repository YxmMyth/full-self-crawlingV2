"""
LLM Client - 智谱 GLM 接口

支持 GLM Coding API 调用。
"""

import httpx
import json
import os
from typing import Dict, Any, Optional, List
import asyncio


class ZhipuClient:
    """
    晓谱 GLM API 客户端

    支持代码生成、代码修复、报告生成等功能

    使用 GLM Coding Plan 专属端点：
    - 代码生成/修复: https://open.bigmodel.cn/api/coding/paas/v4
    - 通用对话: https://open.bigmodel.cn/api/paas/v4
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://open.bigmodel.cn/api/coding/paas/v4/",
        model: str = "glm-4.7",
        timeout: float = 120.0,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout

        # 禁用代理
        os.environ['HTTP_PROXY'] = ''
        os.environ['HTTPS_PROXY'] = ''
        os.environ['NO_PROXY'] = '*'

    def _create_client(self) -> httpx.AsyncClient:
        """创建 httpx 客户端，禁用代理"""
        # 使用 httpx 的正确方式禁用代理
        return httpx.AsyncClient(
            timeout=self.timeout,
            trust_env=False  # 不信任环境变量中的代理设置
        )

    async def generate_code(
        self,
        prompt: str,
        temperature: float = 0.3,
        top_p: float = 0.7,
    ) -> str:
        """
        生成代码

        Args:
            prompt: 代码生成 prompt
            temperature: 温度参数
            top_p: top_p 参数

        Returns:
            生成的代码字符串
        """
        url = f"{self.base_url}chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": temperature,
            "top_p": top_p,
        }

        async with self._create_client() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # 提取生成的内容
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]

            raise Exception(f"Invalid response: {data}")

    async def repair_code(
        self,
        original_code: str,
        error_logs: str,
        iteration: int,
        temperature: float = 0.2,
    ) -> str:
        """
        修复代码

        Args:
            original_code: 原始代码
            error_logs: 错误日志
            iteration: 当前迭代次数
            temperature: 温度参数（修复时用较低温度）

        Returns:
            修复后的代码
        """
        # 使用代码修复 prompt
        from ..prompts import CODE_REPAIR_PROMPT

        prompt = CODE_REPAIR_PROMPT.format(
            original_code=original_code,
            error_logs=error_logs,
            iteration=iteration,
        )

        return await self.generate_code(
            prompt=prompt,
            temperature=temperature,
        )

    async def generate_report(
        self,
        site_url: str,
        user_goal: str,
        site_info: Dict[str, Any],
        sample_data: List[Dict],
        temperature: float = 0.7,
    ) -> str:
        """
        生成侦察报告

        Args:
            site_url: 站点 URL
            user_goal: 用户需求
            site_info: 站点信息
            sample_data: 样本数据
            temperature: 温度参数

        Returns:
            Markdown 格式的报告
        """
        from ..prompts import REPORT_GENERATION_PROMPT

        prompt = REPORT_GENERATION_PROMPT.format(
            site_url=site_url,
            user_goal=user_goal,
            site_info=json.dumps(site_info, ensure_ascii=False, indent=2),
            sample_data=json.dumps(sample_data[:5], ensure_ascii=False, indent=2),  # 只传前5条
        )

        return await self.generate_code(
            prompt=prompt,
            temperature=temperature,
        )

    async def evaluate_quality(
        self,
        user_goal: str,
        extracted_data: List[Dict],
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        """
        评估数据质量

        Args:
            user_goal: 用户需求
            extracted_data: 提取的数据
            temperature: 温度参数

        Returns:
            质量评估结果
        """
        from ..prompts import QUALITY_EVALUATION_PROMPT

        prompt = QUALITY_EVALUATION_PROMPT.format(
            user_goal=user_goal,
            extracted_data=json.dumps(extracted_data, ensure_ascii=False, indent=2),
        )

        response = await self.generate_code(
            prompt=prompt,
            temperature=temperature,
        )

        # 解析 JSON 响应
        try:
            # 提取 JSON 部分
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            else:
                # 尝试直接解析
                return json.loads(response)
        except:
            return {
                "relevance": 0.5,
                "completeness": 0.5,
                "accuracy": 0.5,
                "overall_score": 0.5,
                "error": "Failed to parse LLM response",
            }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """
        通用对话接口

        Args:
            messages: 消息列表
            temperature: 温度参数

        Returns:
            LLM 响应
        """
        url = f"{self.base_url}chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        async with self._create_client() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]

            raise Exception(f"Invalid response: {data}")


# ===== 单例模式（可选）=====

_client: Optional[ZhipuClient] = None


def get_client(api_key: Optional[str] = None) -> ZhipuClient:
    """
    获取 LLM 客户端实例

    Args:
        api_key: 智谱 API Key（如不提供则从环境变量读取）

    Returns:
        ZhipuClient 实例
    """
    global _client

    if _client is None:
        import os
        key = api_key or os.environ.get("ZHIPU_API_KEY")
        if not key:
            raise ValueError("ZHIPU_API_KEY not provided")
        _client = ZhipuClient(api_key=key)

    return _client


# ===== 便捷函数 =====

async def generate_code(
    prompt: str,
    api_key: Optional[str] = None,
) -> str:
    """便捷代码生成函数"""
    client = get_client(api_key)
    return await client.generate_code(prompt)
