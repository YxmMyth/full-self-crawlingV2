"""
Web Scraping Skills - Web爬取技能

实现常用的Web爬取技能。
"""

from typing import Dict, Any, List
from ..base_skill import BaseSkill, SkillCategory, SkillMetadata


class StealthBrowserSkill(BaseSkill):
    """
    隐身浏览器技能

    提供反爬虫绕过能力，包括UA轮换、反检测脚本等。
    """

    def _define_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="stealth_browser",
            category=SkillCategory.ANTI_DETECTION,
            description="隐身浏览器，提供反爬虫绕过能力",
            version="1.0.0",
            tags=["anti-bot", "stealth", "browser", "ua-rotation"],
            dependencies=[],
            applicable_websites=["*"],  # 适用于所有网站
            success_rate=0.7,
        )

    def _generate_code_template(self) -> str:
        return """# 隐身浏览器配置
import random

# User-Agent轮换池
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
]

# 浏览器启动参数
launch_args = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
]

# 创建页面并应用反检测
page = browser.new_page(
    user_agent=random.choice(USER_AGENTS),
    viewport={"width": 1920, "height": 1080},
)

# 注入反检测脚本
page.add_init_script('''
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    window.chrome = {runtime: {}, loadTimes: function() {}};
    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]};
    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en'};
''')

# 人类行为延迟
time.sleep(random.uniform(1, 2))
"""

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "stealth_level": {
                "type": "str",
                "default": "medium",
                "description": "隐身等级 (none/low/medium/high)",
                "options": ["none", "low", "medium", "high"],
            },
            "delay_range": {
                "type": "tuple",
                "default": (1, 2),
                "description": "随机延迟范围(秒)",
            },
        }


class PaginationSkill(BaseSkill):
    """
    分页处理技能

    处理网页分页，自动翻页并提取数据。
    """

    def _define_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="pagination",
            category=SkillCategory.INTERACTION,
            description="处理网页分页，支持多种分页模式",
            version="1.0.0",
            tags=["pagination", "multiple-pages", "scroll"],
            dependencies=[],
            applicable_websites=["ecommerce", "news", "blog", "job_board"],
            success_rate=0.75,
        )

    def _generate_code_template(self) -> str:
        return """# 分页处理
max_pages = {max_pages}
current_page = 1
all_results = []

while current_page <= max_pages:
    # 提取当前页数据
    # ... 数据提取代码 ...
    # all_results.extend(page_results)

    # 查找下一页按钮
    next_buttons = [
        "a.next:visible",
        "a[aria-label='Next']:visible",
        "button[aria-label='Next']:visible",
        ".pagination .next:not(.disabled)",
    ]

    next_page = None
    for selector in next_buttons:
        try:
            next_btn = page.locator(selector).first
            if next_btn.count() > 0:
                next_page = next_btn
                break
        except:
            continue

    if not next_page:
        break

    # 点击下一页
    try:
        next_page.click()
        time.sleep(random.uniform(1, 2))
        current_page += 1
    except:
        break
"""

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "max_pages": {
                "type": "int",
                "default": 5,
                "description": "最大翻页数",
            },
            "wait_between_pages": {
                "type": "float",
                "default": 1.5,
                "description": "翻页间隔(秒)",
            },
        }


class FormInteractionSkill(BaseSkill):
    """
    表单交互技能

    处理表单填写和提交，包括搜索、登录等。
    """

    def _define_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="form_interaction",
            category=SkillCategory.INTERACTION,
            description="处理表单交互，填写和提交表单",
            version="1.0.0",
            tags=["form", "input", "submit", "search", "login"],
            dependencies=[],
            applicable_websites=["*"],
            success_rate=0.7,
        )

    def _generate_code_template(self) -> str:
        return """# 表单交互
# 查找表单元素
form_selectors = [
    "form",
    "[data-form]",
    ".search-form",
    ".login-form",
]

form = None
for selector in form_selectors:
    try:
        form_element = page.locator(selector).first
        if form_element.count() > 0:
            form = form_element
            break
    except:
        continue

if form:
    # 填写表单字段
    fields = {fields}  # {"field_name": "value", ...}

    for field_name, field_value in fields.items():
        field_selectors = [
            f"[name='{field_name}']",
            f"[id='{field_name}']",
            f"[placeholder*='{field_name}']",
        ]

        for selector in field_selectors:
            try:
                field = form.locator(selector).first
                if field.count() > 0:
                    field.fill(field_value)
                    time.sleep(0.5)
                    break
            except:
                continue

    # 提交表单
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Submit')",
        "button:has-text('Search')",
    ]

    for selector in submit_selectors:
        try:
            submit_btn = page.locator(selector).first
            if submit_btn.count() > 0:
                submit_btn.click()
                time.sleep(2)
                break
        except:
            continue
"""

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "fields": {
                "type": "dict",
                "default": {},
                "description": "表单字段字典 {field_name: value}",
            },
            "submit_delay": {
                "type": "float",
                "default": 2.0,
                "description": "提交后等待时间(秒)",
            },
        }


class WaitForContentSkill(BaseSkill):
    """
    等待内容技能

    处理动态加载的内容，等待特定元素出现。
    """

    def _define_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="wait_for_content",
            category=SkillCategory.BROWSER,
            description="等待动态内容加载完成",
            version="1.0.0",
            tags=["wait", "dynamic", "loading"],
            dependencies=[],
            applicable_websites=["*"],
            success_rate=0.85,
        )

    def _generate_code_template(self) -> str:
        return """# 等待内容加载
# 等待特定选择器
wait_selectors = {wait_selectors}

for selector in wait_selectors:
    try:
        page.wait_for_selector(selector, timeout={timeout})
        break
    except:
        continue

# 额外等待确保JS渲染完成
time.sleep({extra_delay})
"""

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "wait_selectors": {
                "type": "list",
                "default": ["body"],
                "description": "等待的选择器列表",
            },
            "timeout": {
                "type": "int",
                "default": 15000,
                "description": "等待超时时间(毫秒)",
            },
            "extra_delay": {
                "type": "float",
                "default": 1.0,
                "description": "额外等待时间(秒)",
            },
        }


class ScrollToLoadSkill(BaseSkill):
    """
    滚动加载技能

    处理懒加载页面，通过滚动触发内容加载。
    """

    def _define_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="scroll_to_load",
            category=SkillCategory.INTERACTION,
            description="处理懒加载页面，滚动触发内容加载",
            version="1.0.0",
            tags=["scroll", "lazy-load", "infinite"],
            dependencies=[],
            applicable_websites=["ecommerce", "social_media"],
            success_rate=0.7,
        )

    def _generate_code_template(self) -> str:
        return """# 滚动加载
last_height = 0
scroll_count = 0
max_scrolls = {max_scrolls}

while scroll_count < max_scrolls:
    # 滚动到底部
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep({scroll_delay})

    # 检查是否还有新内容加载
    new_height = page.evaluate("document.body.scrollHeight")
    if new_height == last_height:
        break

    last_height = new_height
    scroll_count += 1
"""

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "max_scrolls": {
                "type": "int",
                "default": 10,
                "description": "最大滚动次数",
            },
            "scroll_delay": {
                "type": "float",
                "default": 1.0,
                "description": "滚动间隔(秒)",
            },
        }


class DataExtractionSkill(BaseSkill):
    """
    数据提取技能

    提供常用的数据提取模式。
    """

    def _define_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="data_extraction",
            category=SkillCategory.EXTRACTION,
            description="数据提取技能，支持多种提取模式",
            version="1.0.0",
            tags=["extract", "parse", "data"],
            dependencies=[],
            applicable_websites=["*"],
            success_rate=0.8,
        )

    def _generate_code_template(self) -> str:
        return """# 数据提取
# 提取模式: {extraction_mode}

if extraction_mode == "container_items":
    # 从容器元素中提取项目
    container_selector = "{container_selector}"
    items = page.locator(container_selector).all()

    for item in items:
        try:
            result = {{}}
            # 提取字段
            result["title"] = item.locator("{title_selector}").text_content()
            result["link"] = item.locator("{link_selector}").get_attribute("href")
            results.append(result)
        except:
            continue

elif extraction_mode == "separate_lists":
    # 分别提取各个字段列表
    titles = [el.text_content() for el in page.locator("{title_selector}").all()]
    links = [el.get_attribute("href") for el in page.locator("{link_selector}").all()]

    for title, link in zip(titles, links):
        results.append({{"title": title, "link": link}})

elif extraction_mode == "table_rows":
    # 从表格中提取行
    rows = page.locator("table tr").all()
    for row in rows[1:]:  # 跳过表头
        cells = row.locator("td").all()
        results.append({{"cells": [cell.text_content() for cell in cells]}})
"""

    def get_parameters(self) -> Dict[str, Any]:
        return {
            "extraction_mode": {
                "type": "str",
                "default": "container_items",
                "description": "提取模式",
                "options": ["container_items", "separate_lists", "table_rows"],
            },
            "container_selector": {
                "type": "str",
                "default": ".item",
                "description": "容器选择器",
            },
            "title_selector": {
                "type": "str",
                "default": "h2, .title",
                "description": "标题选择器",
            },
            "link_selector": {
                "type": "str",
                "default": "a[href]",
                "description": "链接选择器",
            },
        }
