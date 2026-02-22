"""
Stealth Browser - 反爬虫绕过浏览器工具

提供反爬虫绕过能力，包括：
1. playwright-stealth 集成
2. User-Agent 轮换
3. Cookie 管理
4. 反检测特性

用于绕过 Cloudflare 等反爬虫系统。
"""

from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
import random
import json


# User-Agent 轮换池
USER_AGENTS = [
    # Windows Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # macOS Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:133.0) Gecko/20100101 Firefox/133.0",
    # Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
]


class StealthBrowserTool:
    """
    隐身浏览器工具 - 反爬虫绕过

    特性：
    1. playwright-stealth 插件伪装
    2. 随机 User-Agent
    3. 反自动化检测
    4. Cookie 持久化
    """

    def __init__(
        self,
        use_stealth: bool = True,
        random_ua: bool = True,
        headless: bool = True,
    ):
        """
        初始化隐身浏览器

        Args:
            use_stealth: 是否使用 playwright-stealth
            random_ua: 是否随机 User-Agent
            headless: 是否无头模式
        """
        self.use_stealth = use_stealth
        self.random_ua = random_ua
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None

    def _get_launch_args(self) -> List[str]:
        """获取反检测启动参数"""
        return [
            "--disable-blink-features=AutomationControlled",  # 禁用自动化控制标记
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]

    def _get_user_agent(self) -> str:
        """获取随机 User-Agent"""
        if self.random_ua:
            return random.choice(USER_AGENTS)
        return USER_AGENTS[0]

    async def init(self):
        """初始化浏览器"""
        from playwright.async_api import async_playwright

        self.playwright = await async_playwright().start()

        launch_args = self._get_launch_args() if self.use_stealth else []

        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        user_agent = self._get_user_agent() if self.random_ua else None

        self.page = await self.browser.new_page(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
        )

        # 应用 stealth 伪装
        if self.use_stealth:
            await self._apply_stealth()

    async def _apply_stealth(self):
        """应用反检测伪装"""
        try:
            from playwright_stealth import stealth_async
            await stealth_async(self.page)
        except ImportError:
            # 如果 playwright-stealth 不可用，使用手动伪装
            await self._manual_stealth()

    async def _manual_stealth(self):
        """手动反检测伪装（当 playwright-stealth 不可用时）"""
        # 隐藏 webdriver 特征
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // 伪装 Chrome 对象
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };

            // 伪装 permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );

            // 伪装 plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });

            // 伪装 languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        """)

    async def browse(
        self,
        url: str,
        wait_for: Optional[str] = None,
        wait_for_timeout: int = 10000,
        screenshot: bool = False,
        wait_for_stability: bool = True,
    ) -> Dict[str, Any]:
        """
        访问页面并返回信息

        Args:
            url: 目标 URL
            wait_for: 等待的选择器
            wait_for_timeout: 等待超时时间（毫秒）
            screenshot: 是否截图
            wait_for_stability: 是否等待页面稳定

        Returns:
            包含 html, url, screenshot, features 的字典
        """
        if not self.page:
            await self.init()

        # 访问页面
        await self.page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        # 等待页面稳定（模拟人类行为）
        if wait_for_stability:
            await self.page.wait_for_timeout(random.randint(1000, 2000))

        # 等待选择器
        if wait_for:
            try:
                await self.page.wait_for_selector(wait_for, timeout=wait_for_timeout)
            except Exception:
                pass  # 超时继续

        # 获取内容
        html = await self.page.content()
        current_url = self.page.url

        # 截图
        screenshot_data = None
        if screenshot:
            screenshot_data = await self.page.screenshot(full_page=False)

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
        import re

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

            # 检测反爬虫特征
            if soup.find('script', src=re.compile(r'challenge|turnstile|captcha', re.I)):
                features.append("anti-bot(detected)")

        except Exception:
            pass

        return features

    async def load_cookies(self, cookies_file: str):
        """从文件加载 Cookies"""
        try:
            with open(cookies_file, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            await self.page.context.add_cookies(cookies)
        except FileNotFoundError:
            pass

    async def save_cookies(self, cookies_file: str):
        """保存 Cookies 到文件"""
        cookies = await self.page.context.cookies()
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright') and self.playwright:
            await self.playwright.stop()

    async def __aenter__(self):
        await self.init()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# 同步版本（用于沙箱执行）
def create_stealth_browser_sync():
    """
    创建同步版本的隐身浏览器

    用于在沙箱中生成的代码使用。

    Returns:
        配置好的 Playwright browser 实例
    """
    from playwright.sync_api import sync_playwright

    p = sync_playwright().start()

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
    ]

    browser = p.chromium.launch(
        headless=True,
        args=launch_args,
    )

    # 创建新页面
    page = browser.new_page(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1920, "height": 1080},
    )

    # 应用反检测脚本
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });

        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {}
        };

        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });

        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
    """)

    return browser, page, p


# 代码模板 - 用于 LLM 生成隐身浏览器代码
STEALTH_BROWSER_TEMPLATE = '''
from playwright.sync_api import sync_playwright
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

def scrape_with_stealth(url: str) -> dict:
    """使用隐身模式爬取"""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        page = browser.new_page(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
        )

        # 反检测脚本
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = {runtime: {}, loadTimes: function() {}};
        """)

        page.goto(url, wait_until='domcontentloaded')
        page.wait_for_timeout(2000)  # 模拟人类延迟

        # ... 爬取逻辑 ...

        browser.close()
        return {"results": []}
'''
