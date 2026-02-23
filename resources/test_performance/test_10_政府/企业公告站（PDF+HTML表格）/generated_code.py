from playwright.sync_api import sync_playwright
import json
import time
import random
import sys

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    try:
        with sync_playwright() as p:
            # API 调用：使用标准的 launch(headless=True)
            browser = p.chromium.launch(headless=True)
            
            # API 调用：使用标准的 new_page()
            page = browser.new_page()

            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素
            try:
                page.wait_for_selector('body', timeout=10000)
            except Exception:
                pass

            # 人类行为延迟
            time.sleep(random.uniform(1.5, 3.0))

            # === 数据提取 ===
            selectors_to_try = ["a.govuk-link", "a[href]", "a"]
            
            items = []
            for selector in selectors_to_try:
                try:
                    located_items = page.locator(selector).all()
                    if located_items and len(located_items) > 0:
                        items = located_items
                        break
                except Exception:
                    continue

            for item in items:
                try:
                    result = {}
                    
                    # 提取文本
                    raw_text = item.text_content()
                    if raw_text:
                        result["title"] = raw_text.strip()
                    else:
                        continue 

                    # 提取链接
                    href = item.get_attribute("href")
                    if href:
                        # 处理相对路径
                        if href.startswith("/"):
                            result["link"] = f"https://www.find-tender.service.gov.uk{href}"
                        elif href.startswith("http"):
                            result["link"] = href
                        else:
                            continue 
                    else:
                        continue

                    # 提取其他可能的属性（如PDF标识）
                    if ".pdf" in result.get("link", "").lower():
                        result["file_type"] = "PDF"
                    
                    results.append(result)
                except Exception:
                    continue

    except Exception as e:
        # 捕获异常，防止程序崩溃
        error_msg = str(e)
        pass
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    # 去重（基于链接）
    seen_links = set()
    valid_results = []
    for r in results:
        link = r.get("link")
        title = r.get("title")
        if link and title and link not in seen_links:
            seen_links.add(link)
            valid_results.append(r)

    return {
        "results": valid_results,
        "metadata": {
            "total_extracted": len(results),
            "valid_count": len(valid_results),
            "url": url
        }
    }

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.find-tender.service.gov.uk/"
    result = scrape(target_url)
    
    # 增加 Unicode 编码处理，防止 Windows 控制台输出乱码或崩溃
    try:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(json.dumps(result, ensure_ascii=True, indent=2))