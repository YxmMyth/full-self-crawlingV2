from playwright.sync_api import sync_playwright
import json
import time
import random
import sys

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    try:
        with sync_playwright() as p:
            # 修复：使用标准的 API 调用，移除可能导致问题的 args 参数
            browser = p.chromium.launch(headless=True)
            
            # 修复：使用标准的 new_page() 调用
            page = browser.new_page()

            # 访问目标URL，增加超时时间以应对金融站点的加载延迟
            page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # 等待关键元素 body
            try:
                page.wait_for_selector('body', timeout=10000)
            except:
                pass

            # 模拟人类行为延迟，等待JS渲染图表
            time.sleep(random.uniform(3, 5))

            # === 数据提取 ===
            
            # 策略1: 尝试提取 SVG 图表数据 (主要目标)
            # 虽然之前的分析显示SVG为0，但图表通常动态加载，这里尝试显式等待
            try:
                page.wait_for_selector('svg', timeout=5000)
            except:
                pass

            svgs = page.locator("svg").all()
            if svgs:
                for i, svg in enumerate(svgs[:2]): # 限制提取数量，防止数据过大
                    try:
                        svg_code = svg.evaluate("el => el.outerHTML")
                        results.append({
                            "type": "svg_chart",
                            "index": i,
                            "content": svg_code
                        })
                    except Exception:
                        continue

            # 策略2: 检查是否被拦截或处于错误页面 (使用已验证选择器 #message)
            # 如果没有提取到SVG，检查是否有错误提示信息
            if not results:
                try:
                    message = page.locator("#message p").text_content()
                    if message:
                        results.append({
                            "type": "status_message",
                            "content": message.strip()
                        })
                except:
                    pass

            # 策略3: 提取页面导航链接 (使用已验证选择器 #switcher a)
            try:
                nav_links = page.locator("#switcher a").all()
                for link in nav_links:
                    try:
                        results.append({
                            "type": "navigation_link",
                            "text": link.text_content(),
                            "href": link.get_attribute("href")
                        })
                    except:
                        continue
            except:
                pass

            # 策略4: 提取通用链接 (使用已验证选择器 a[href])
            # 作为最后的兜底方案，获取页面上的其他链接
            try:
                all_links = page.locator("a[href]").all()
                for link in all_links[:5]:
                    try:
                        text = link.text_content()
                        href = link.get_attribute("href")
                        if text and href:
                            results.append({
                                "type": "general_link",
                                "text": text.strip(),
                                "href": href
                            })
                    except:
                        continue
            except:
                pass

    except Exception as e:
        # 捕获并记录异常，确保程序不崩溃
        results.append({"error": str(e)})
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("content") or r.get("href") or r.get("error")]

    return {
        "results": valid_results,
        "metadata": {
            "total_extracted": len(results),
            "valid_count": len(valid_results),
            "url": url
        }
    }

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://finance.yahoo.com/quote/AAPL/chart"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))