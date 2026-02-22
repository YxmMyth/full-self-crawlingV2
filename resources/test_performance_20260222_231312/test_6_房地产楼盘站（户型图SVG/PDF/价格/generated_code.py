from playwright.sync_api import sync_playwright
import json
import time
import random

# 模拟真实用户代理
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/114.0"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    metadata = {
        "total_extracted": 0,
        "valid_count": 0,
        "url": url,
        "captcha_detected": False,
        "errors": []
    }

    try:
        with sync_playwright() as p:
            # 启动浏览器，添加反爬虫参数
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            page = context.new_page()

            # 访问目标页面
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
            except Exception as e:
                metadata["errors"].append(f"Navigation timeout or error: {str(e)}")

            # 检查验证码 (根据DOM分析结果)
            try:
                captcha_selector = ".px-captcha-container"
                if page.locator(captcha_selector).count() > 0:
                    metadata["captcha_detected"] = True
                    metadata["errors"].append("Captcha detected (PerimeterX/Human Security). Scraping may be limited.")
                    # 即使有验证码，也尝试等待片刻看是否能通过
                    time.sleep(5)
            except:
                pass

            # 模拟人类滚动以触发无限加载
            try:
                for _ in range(3):
                    page.mouse.wheel(0, 1000)
                    time.sleep(random.uniform(1.5, 2.5))
            except Exception as e:
                metadata["errors"].append(f"Scrolling error: {str(e)}")

            # 等待关键元素加载 (房产卡片)
            try:
                # 使用建议的选择器 [data-test='property-card']
                page.wait_for_selector("div[data-test='property-card']", timeout=15000, state="attached")
            except Exception:
                # 如果超时，记录但不中断，尝试提取现有内容
                metadata["errors"].append("Timeout waiting for property cards. Content might be empty.")

            # === 数据提取 ===
            
            # 1. 提取房产列表
            try:
                # 使用建议的选择器
                cards = page.locator("div[data-test='property-card']").all()
                
                for card in cards:
                    item_data = {}
                    try:
                        # 提取价格
                        try:
                            price_el = card.locator("[data-test='property-card-price']").first
                            item_data["price"] = price_el.text_content().strip()
                        except:
                            item_data["price"] = None

                        # 提取地址
                        try:
                            addr_el = card.locator("[data-test='property-card-addr']").first
                            item_data["address"] = addr_el.text_content().strip()
                        except:
                            item_data["address"] = None

                        # 提取链接
                        try:
                            link_el = card.locator("a").first
                            item_data["link"] = link_el.get_attribute("href")
                            if item_data["link"] and not item_data["link"].startswith("http"):
                                item_data["link"] = "https://www.zillow.com" + item_data["link"]
                        except:
                            item_data["link"] = None
                        
                        # 提取图片 (作为户型图/房源图的备选)
                        try:
                            img_el = card.locator("img").first
                            item_data["image_url"] = img_el.get_attribute("src")
                        except:
                            item_data["image_url"] = None

                        results.append(item_data)
                    except Exception as e:
                        continue

            except Exception as e:
                metadata["errors"].append(f"Error extracting property cards: {str(e)}")

            # 2. 提取页面中的 SVG (满足用户对户型图SVG的需求)
            # 注意：Zillow列表页通常使用img标签，但我们也检查SVG以防万一
            try:
                svgs = page.locator("svg").all()
                for svg in svgs[:5]: # 限制提取数量防止过大
                    try:
                        svg_code = svg.evaluate("el => el.outerHTML")
                        results.append({
                            "svg_code": svg_code,
                            "type": "svg",
                            "source": "page_inline"
                        })
                    except:
                        continue
            except Exception as e:
                metadata["errors"].append(f"Error extracting SVGs: {str(e)}")

            # 3. 提取元数据 (使用已验证的选择器)
            try:
                viewport = page.locator("meta[name='viewport']").first.get_attribute("content")
                metadata["page_viewport"] = viewport
            except:
                pass

            context.close()

    except Exception as e:
        metadata["errors"].append(f"General Exception: {str(e)}")
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = []
    for r in results:
        # 验证房产数据
        if "price" in r or "address" in r:
            if r.get("price") or r.get("address"):
                valid_results.append(r)
        # 验证SVG数据
        elif r.get("type") == "svg":
            valid_results.append(r)

    metadata["total_extracted"] = len(results)
    metadata["valid_count"] = len(valid_results)

    return {
        "results": valid_results,
        "metadata": metadata
    }

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.zillow.com/"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))