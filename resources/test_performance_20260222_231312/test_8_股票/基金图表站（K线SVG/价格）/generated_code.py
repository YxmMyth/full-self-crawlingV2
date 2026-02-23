from playwright.sync_api import sync_playwright
import json
import time
import random

# 定义常用的User-Agent列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
]

def scrape(url: str) -> dict:
    results = []
    metadata = {
        "url": url,
        "timestamp": time.time()
    }
    browser = None
    
    try:
        with sync_playwright() as p:
            # 使用正确的 API 启动浏览器
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            # 使用正确的 API 创建新页面
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            # 访问目标页面
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素加载，针对图表页面，等待SVG或价格流数据
            try:
                # 等待价格数据或图表出现
                page.wait_for_selector('fin-streamer', timeout=15000)
                page.wait_for_selector('svg', timeout=15000)
            except Exception:
                # 如果特定元素未加载，至少等待body
                try:
                    page.wait_for_selector('body', timeout=10000)
                except:
                    pass

            # 人类行为延迟
            time.sleep(random.uniform(2, 3))

            # === 数据提取 ===
            
            # 1. 提取股票基本信息 (价格/变化) - 尝试使用Yahoo Finance特有的fin-streamer
            try:
                price_elements = page.locator('fin-streamer[data-field="regularMarketPrice"]').all()
                for el in price_elements:
                    text = el.text_content()
                    if text:
                        results.append({
                            "type": "price",
                            "content": text.strip(),
                            "selector": "fin-streamer[data-field='regularMarketPrice']"
                        })
            except Exception:
                pass

            # 2. 提取K线图表 SVG (根据用户需求)
            try:
                # 尝试获取主要的SVG图表，通常在页面中比较大或者包含path
                svgs = page.locator("svg").all()
                for i, svg in enumerate(svgs):
                    # 过滤掉小的图标SVG，只取可能包含图表的SVG
                    # 通过检查SVG内部是否有path元素来判断是否为图表
                    has_path = svg.locator("path").count() > 0
                    if has_path:
                        svg_code = svg.evaluate("el => el.outerHTML")
                        if len(svg_code) > 500: # 简单过滤，确保不是极小的图标
                            results.append({
                                "type": "chart_svg",
                                "content": svg_code[:500] + "...", # 截断过长内容以便展示
                                "full_length": len(svg_code),
                                "selector": "svg"
                            })
                            break # 通常只需要取第一个主图表
            except Exception:
                pass

            # 3. 使用已验证的选择器: div#switcher a (链接)
            try:
                switcher_links = page.locator("div#switcher a").all()
                for link in switcher_links:
                    try:
                        href = link.get_attribute("href")
                        text = link.text_content()
                        if href or text:
                            results.append({
                                "type": "link",
                                "text": text.strip() if text else "",
                                "url": href,
                                "selector": "div#switcher a"
                            })
                    except Exception:
                        continue
            except Exception:
                pass

            # 4. 使用已验证的选择器: img (图片)
            try:
                images = page.locator("img").all()
                for img in images:
                    try:
                        src = img.get_attribute("src")
                        alt = img.get_attribute("alt")
                        if src:
                            results.append({
                                "type": "image",
                                "src": src,
                                "alt": alt if alt else "",
                                "selector": "img"
                            })
                    except Exception:
                        continue
            except Exception:
                pass

            # 5. 使用已验证的选择器: title (页面标题)
            try:
                title_text = page.locator("title").text_content()
                if title_text:
                    results.append({
                        "type": "title",
                        "content": title_text.strip(),
                        "selector": "title"
                    })
            except Exception:
                pass

            metadata["status"] = "success"

    except Exception as e:
        metadata["status"] = "error"
        metadata["error_message"] = str(e)
    finally:
        if browser:
            browser.close()

    return {
        "results": results,
        "metadata": metadata
    }