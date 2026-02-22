from playwright.sync_api import sync_playwright
import json
import time
import random

# 模拟真实浏览器的 User-Agent 列表
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    error_msg = None
    
    try:
        with sync_playwright() as p:
            # 根据历史反思，使用 headless=False 绕过部分检测，并添加反爬虫参数
            browser = p.chromium.launch(
                headless=False, 
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York"
            )
            
            page = context.new_page()

            # 增加超时时间并使用 networkidle 等待策略，确保动态内容加载完成
            try:
                page.goto(url, wait_until='networkidle', timeout=60000)
            except Exception as e:
                # 即使超时也可能加载了部分内容，继续尝试提取
                error_msg = f"Navigation timeout or error: {str(e)}"

            # 检测是否被重定向到验证码页面
            if "captcha" in page.url.lower() or "sorry" in page.title().lower():
                error_msg = "Blocked by CAPTCHA or human verification page."
                return {
                    "results": [],
                    "metadata": {
                        "total_extracted": 0,
                        "valid_count": 0,
                        "url": url,
                        "error": error_msg
                    }
                }

            # 等待关键商品容器出现，增加随机延迟模拟人类行为
            try:
                page.wait_for_selector('[data-component-type="s-search-result"]', timeout=15000)
            except Exception:
                pass # 继续尝试，可能部分已加载

            time.sleep(random.uniform(2, 4))

            # === 数据提取 ===
            # 选择器策略：使用 Amazon 标准的搜索结果容器
            items = page.locator('[data-component-type="s-search-result"]').all()
            
            for item in items:
                try:
                    result = {}
                    
                    # 1. 名称 - 尝多种选择器以增加健壮性
                    try:
                        name_elem = item.locator('h2 a span').first
                        if name_elem.count() > 0:
                            result["name"] = name_elem.text_content().strip()
                        else:
                            result["name"] = None
                    except:
                        result["name"] = None

                    # 2. 价格 - 提取整数部分或完整价格
                    try:
                        price_elem = item.locator('.a-price .a-offscreen').first
                        if price_elem.count() > 0:
                            result["price"] = price_elem.text_content().strip()
                        else:
                            # 尝试从价格区间获取
                            price_range = item.locator('.a-price-range').first
                            if price_range.count() > 0:
                                result["price"] = price_range.text_content().strip()
                            else:
                                result["price"] = None
                    except:
                        result["price"] = None

                    # 3. 规格 - 通常在标题下方的描述中
                    try:
                        # 尝试获取规格文本（如存储大小、颜色等），通常在特定 div 中
                        spec_elem = item.locator('div.a-row.a-size-base.a-color-base').first
                        if spec_elem.count() > 0:
                            result["specs"] = spec_elem.text_content().strip()
                        else:
                            result["specs"] = None
                    except:
                        result["specs"] = None

                    # 4. 主图 URL
                    try:
                        img_elem = item.locator('.s-image').first
                        if img_elem.count() > 0:
                            result["image_url"] = img_elem.get_attribute('src')
                        else:
                            result["image_url"] = None
                    except:
                        result["image_url"] = None

                    # 5. PDF - 列表页通常没有 PDF，尝试提取产品链接以便后续爬取
                    # 如果必须找 PDF，通常需要进入详情页，这里提取详情页链接作为替代
                    try:
                        link_elem = item.locator('h2 a').first
                        if link_elem.count() > 0:
                            href = link_elem.get_attribute('href')
                            if href:
                                result["product_url"] = f"https://www.amazon.com{href}"
                            else:
                                result["product_url"] = None
                        else:
                            result["product_url"] = None
                    except:
                        result["product_url"] = None
                    
                    result["pdf_url"] = None # 列表页默认无 PDF

                    # 数据验证：至少要有名称才视为有效
                    if result.get("name"):
                        results.append(result)

                except Exception as e:
                    # 单个商品提取失败不影响其他商品
                    continue

    except Exception as e:
        error_msg = str(e)
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("name")]

    metadata = {
        "total_extracted": len(results),
        "valid_count": len(valid_results),
        "url": url
    }
    
    if error_msg:
        metadata["error"] = error_msg

    return {
        "results": valid_results,
        "metadata": metadata
    }

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.amazon.com/s?k=smartphone"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))