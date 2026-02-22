from playwright.sync_api import sync_playwright
import json
import time
import random
import re

# 模拟常见的User-Agent
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def scrape(url: str) -> dict:
    results = []
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            page.goto(url, wait_until='networkidle', timeout=60000)

            # 等待关键容器加载
            try:
                page.wait_for_selector('dl#articles', timeout=15000)
            except Exception as e:
                print(f"Timeout waiting for articles container: {e}")
                # 尝试继续，可能页面结构不同

            # 人类行为延迟
            time.sleep(random.uniform(1.5, 3.0))

            # === 数据提取 ===
            # ArXiv 结构分析：主要内容在 dl#articles 中，由 dt (标题/元数据) 和 dd (摘要) 组成
            
            # 获取所有的 dt (定义标题)
            dts = page.locator("dl#articles > dt").all()
            # 获取所有的 dd (定义摘要)
            dds = page.locator("dl#articles > dd").all()
            
            print(f"Found {len(dts)} dt elements and {len(dds)} dd elements.")

            # 遍历 dt 元素
            for i, dt in enumerate(dts):
                try:
                    item_data = {}
                    
                    # 1. 提取标题
                    # 尝试标准选择器 .list-title
                    title_elem = dt.locator(".list-title")
                    if title_elem.count() > 0:
                        item_data["title"] = clean_text(title_elem.text_content())
                    else:
                        # 备选方案：获取 dt 内的所有文本，并尝试清理
                        full_text = clean_text(dt.inner_text())
                        # 简单的启发式方法：标题通常包含 "Title:" 或者是主要的长文本
                        # 这里我们暂时存储原始文本，后续清洗
                        item_data["title"] = full_text

                    # 2. 提取 ID 和 链接
                    # 通常在 span.list-identifier 或 a 标签中
                    link_elem = dt.locator("a[href*='/abs/']").first
                    if link_elem.count() > 0:
                        item_data["link"] = "https://arxiv.org" + link_elem.get_attribute("href")
                        # 从链接或文本中提取 ID
                        id_text = clean_text(link_elem.text_content())
                        item_data["id"] = id_text
                    else:
                        # 备选：查找任何包含 arXiv ID 格式的链接
                        all_links = dt.locator("a").all()
                        for a in all_links:
                            href = a.get_attribute("href") or ""
                            if "/abs/" in href or "/pdf/" in href:
                                item_data["link"] = "https://arxiv.org" + href
                                break

                    # 3. 提取 PDF 链接
                    # PDF 链接通常在 dd 中，或者 dt 的 identifier 部分
                    # 优先在 dd 中查找
                    pdf_url = ""
                    if i < len(dds):
                        dd = dds[i]
                        pdf_elem = dd.locator("a[href*='/pdf/']").first
                        if pdf_elem.count() > 0:
                            pdf_url = "https://arxiv.org" + pdf_elem.get_attribute("href")
                        else:
                            # 备选：在 dt 中查找
                            pdf_elem_dt = dt.locator("a[href*='/pdf/']").first
                            if pdf_elem_dt.count() > 0:
                                pdf_url = "https://arxiv.org" + pdf_elem_dt.get_attribute("href")
                    
                    item_data["pdf_url"] = pdf_url

                    # 4. 提取摘要
                    # 摘要在对应的 dd 中
                    if i < len(dds):
                        dd = dds[i]
                        abs_elem = dd.locator(".list-abstract")
                        if abs_elem.count() > 0:
                            # 移除 "Abstract:" 前缀
                            abstract_text = clean_text(abs_elem.text_content())
                            if abstract_text.startswith("Abstract:"):
                                abstract_text = abstract_text[9:].strip()
                            item_data["abstract"] = abstract_text
                        else:
                            # 备选：尝试获取 dd 的文本
                            item_data["abstract"] = clean_text(dd.inner_text())

                    # 数据验证：必须有标题或ID
                    if item_data.get("title") or item_data.get("id"):
                        results.append(item_data)

                except Exception as e:
                    print(f"Error processing item {i}: {e}")
                    continue

    except Exception as e:
        print(f"Critical scraping error: {e}")
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = []
    for r in results:
        # 进一步清洗标题，移除 "Title:" 前缀
        if "title" in r and r["title"].startswith("Title:"):
            r["title"] = r["title"][6:].strip()
        
        # 确保关键字段存在
        if r.get("title") or r.get("abstract"):
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
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://arxiv.org/list/cs/recent?show=2500"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))