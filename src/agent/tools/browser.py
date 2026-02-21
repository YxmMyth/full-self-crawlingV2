"""
Browser Tool - Playwright 浏览器工具

提供访问页面、检测特征等基础能力。
"""

from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import re


class BrowserTool:
    """Playwright 浏览器工具"""

    def __init__(self):
        self.browser = None
        self.page = None

    async def init(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.page = await self.browser.new_page()

    async def browse(
        self,
        url: str,
        wait_for: Optional[str] = None,
        wait_for_timeout: int = 5000,
        screenshot: bool = False,
    ) -> Dict[str, Any]:
        """访问页面并返回信息"""
        if not self.page:
            await self.init()

        # 访问页面
        await self.page.goto(url, wait_until="domcontentloaded")

        # 等待选择器
        if wait_for:
            try:
                await self.page.wait_for_selector(wait_for, timeout=wait_for_timeout)
            except:
                pass  # 超时继续

        # 获取内容
        html = await self.page.content()
        current_url = self.page.url

        # 截图
        screenshot_data = None
        if screenshot:
            screenshot_data = await self.page.screenshot()

        # 检测特征
        features = self.detect_features(html)

        return {
            "html": html,
            "url": current_url,
            "screenshot": screenshot_data,
            "features": features,
        }

    def detect_features(self, html: str) -> List[str]:
        """检测页面特征"""
        features = []

        try:
            soup = BeautifulSoup(html, 'lxml')

            # 检测表格
            if soup.find('table'):
                features.append("table")

            # 检测 JSON-LD
            if soup.find('script', type='application/ld+json'):
                features.append("json-ld")

            # 检测图片
            imgs = soup.find_all('img')
            if len(imgs) > 0:
                features.append(f"images({len(imgs)})")

            # 检测分页
            if soup.find('a', class_=re.compile(r'pag|next', re.I)):
                features.append("pagination")

            # 检测列表
            if soup.find(['ul', 'ol'], class_=re.compile(r'list|item', re.I)):
                features.append("list")

        except Exception:
            pass

        return features

    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
