from playwright.sync_api import sync_playwright
import json
import time
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security"]
            )
            
            # 修复：直接使用 browser.new_page()，不使用 browser.new_context()
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            # Navigate to URL
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # Wait for body to ensure basic load
            try:
                page.wait_for_selector('body', timeout=10000)
            except Exception:
                pass

            # Human behavior simulation
            time.sleep(random.uniform(2, 4))

            # === 数据提取 ===
            
            # 尝试等待列表容器加载
            try:
                page.wait_for_selector("[data-test='property-card']", timeout=5000)
            except:
                pass

            # 提取房产卡片
            # 使用建议的选择器 [data-test='property-card']
            items = page.locator("[data-test='property-card']").all()
            
            # 如果没有找到，尝试更通用的选择器作为回退
            if not items:
                items = page.locator("li[role='group']").all()

            for item in items:
                try:
                    result = {}
                    
                    # 1. 提取价格 [data-test='property-card-price']
                    try:
                        price_el = item.locator("[data-test='property-card-price']").first
                        if price_el.count() > 0:
                            result["price"] = price_el.text_content().strip()
                    except:
                        pass

                    # 2. 提取地址/标题 (尝试多个可能的选择器)
                    try:
                        addr_el = item.locator("[data-test='property-card-addr']").first
                        if addr_el.count() > 0:
                            result["address"] = addr_el.text_content().strip()
                        else:
                            # 备选选择器
                            addr_el = item.locator("address").first
                            if addr_el.count() > 0:
                                result["address"] = addr_el.text_content().strip()
                    except:
                        pass

                    # 3. 提取详情链接
                    try:
                        link_el = item.locator("a").first
                        if link_el.count() > 0:
                            href = link_el.get_attribute("href")
                            if href:
                                result["link"] = href if href.startswith("http") else "https://www.zillow.com" + href
                    except:
                        pass

                    # 4. 提取 SVG (户型图或图标)
                    # Zillow 列表页通常包含 SVG 图标(床/浴/面积)，这里提取它们
                    try:
                        svgs = item.locator("svg").all()
                        svg_codes = []
                        for svg in svgs:
                            # 获取 SVG 的 outerHTML
                            code = svg.evaluate("el => el.outerHTML")
                            svg_codes.append(code)
                        
                        if svg_codes:
                            result["svg_icons"] = svg_codes
                    except:
                        pass

                    # 数据验证：至少有价格或地址
                    if result.get("price") or result.get("address"):
                        results.append(result)

                except Exception as e:
                    # 单个卡片提取失败，跳过继续下一个
                    continue

            # === 备选方案：如果单个卡片提取失败，尝试全局提取 ===
            if not results:
                try:
                    prices = page.locator("[data-test='property-card-price']").all()
                    for p in prices:
                        try:
                            results.append({"price": p.text_content()})
                        except:
                            pass
                except:
                    pass

    except Exception as e:
        # 记录全局错误但不中断程序流程
        error = str(e)
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("price") or r.get("address")]

    # 修复：补全被截断的返回语句
    return {
        "results": valid_results,
        "metadata": {
            "total_extracted": len(valid_results)
        }
    }