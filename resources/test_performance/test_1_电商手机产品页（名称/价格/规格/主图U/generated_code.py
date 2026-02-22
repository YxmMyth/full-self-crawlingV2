from playwright.sync_api import sync_playwright
import json
import time
import random
import sys

# 模拟真实浏览器的 User-Agent
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
            # 启动浏览器，添加反爬虫参数
            browser = p.chromium.launch(
                headless=True, 
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process"
                ]
            )
            
            # 创建页面并设置反爬虫属性
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )

            # 注入 JavaScript 以隐藏自动化特征
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                window.chrome = {
                    runtime: {}
                };
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
            """)

            # 访问页面
            page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # 检查是否被重定向到验证码页面
            try:
                if "captcha" in page.title().lower() or "validateCaptcha" in page.url:
                    error_msg = "Redirected to CAPTCHA page"
                    time.sleep(2)
            except:
                pass

            # 等待关键元素加载，增加超时时间
            try:
                page.wait_for_selector('div[data-component-type="s-search-result"]', timeout=30000)
            except Exception:
                pass

            # 模拟人类行为滚动
            page.mouse.wheel(0, 500)
            time.sleep(random.uniform(1, 3))

            # === 数据提取 ===
            
            # 选择所有产品容器
            items = page.locator('div[data-component-type="s-search-result"]').all()
            
            for item in items:
                try:
                    result = {}
                    
                    # 1. 标题
                    try:
                        title_elem = item.locator('h2 a span').first
                        result["name"] = title_elem.text_content().strip()
                    except:
                        result["name"] = None

                    # 2. 链接
                    try:
                        link_elem = item.locator('h2 a').first
                        href = link_elem.get_attribute('href')
                        if href:
                            if href.startswith('/'):
                                result["link"] = "https://www.amazon.com" + href
                            else:
                                result["link"] = href
                        else:
                            result["link"] = None
                    except:
                        result["link"] = None

                    # 3. 价格
                    try:
                        price_elem = item.locator('.a-price .a-offscreen').first
                        result["price"] = price_elem.text_content().strip()
                    except:
                        result["price"] = None

                    # 4. 主图 URL
                    try:
                        img_elem = item.locator('.s-image').first
                        result["image_url"] = img_elem.get_attribute('src')
                    except:
                        result["image_url"] = None

                    # 5. 规格 - 尝试提取搜索卡片中的简要描述
                    try:
                        specs_list = []
                        # 尝试匹配常见的规格列表容器
                        spec_items = item.locator('div.a-section.a-spacing-none.a-spacing-top-micro span').all()
                        for s in spec_items:
                            txt = s.text_content().strip()
                            if txt and len(txt) > 3: # 过滤掉纯符号
                                specs_list.append(txt)
                        
                        # 备选：尝试获取副标题
                        if not specs_list:
                             try:
                                 subtitle = item.locator('h2 + div span').first.text_content()
                                 if subtitle:
                                     specs_list.append(subtitle)
                             except:
                                 pass

                        result["specs"] = " | ".join(specs_list) if specs_list else None
                    except:
                        result["specs"] = None

                    # 6. PDF - 搜索结果中很少直接有PDF，尝试查找链接
                    try:
                        pdf_links = []
                        all_links = item.locator('a').all()
                        for link in all_links:
                            href = link.get_attribute('href')
                            if href and '.pdf' in href.lower():
                                if href.startswith('/'):
                                    pdf_links.append("https://www.amazon.com" + href)
                                else:
                                    pdf_links.append(href)
                        
                        result["pdf"] = pdf_links[0] if pdf_links else None
                    except:
                        result["pdf"] = None

                    # 数据验证：只要有标题或价格就认为是有效数据
                    if result.get("name") or result.get("price"):
                        results.append(result)
                        
                except Exception:
                    continue

            # 如果主选择器没抓到数据，尝试备用方案（兜底）
            if not results:
                try:
                    titles = page.locator('h2 a span').all()
                    for t in titles:
                        try:
                            txt = t.text_content()
                            if txt and len(txt) > 5:
                                results.append({"name": txt, "price": None, "link": None, "image_url": None, "specs": None, "pdf": None})
                        except:
                            pass
                except:
                    pass

    except Exception as e:
        error_msg = str(e)
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("name")]

    return {
        "results": valid_results,
        "metadata": {
            "total_extracted": len(results),
            "valid_count": len(valid_results),
            "url": url,
            "error": error_msg
        }
    }

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.amazon.com/s?k=smartphone"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))