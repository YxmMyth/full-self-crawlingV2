from playwright.sync_api import sync_playwright
import json
import time
import random
import sys
import re

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

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

            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素 dl#articles 加载完成
            try:
                page.wait_for_selector('dl#articles', timeout=10000)
            except Exception:
                pass

            # 人类行为延迟
            time.sleep(random.uniform(1, 2))

            # === 数据提取 ===
            # 根据 DOM 分析，ArXiv 使用 dl#articles 作为容器
            # 内部结构为交替的 dt (元数据/ID) 和 dd (内容/标题/摘要)
            
            # 获取所有 dt 和 dd 元素
            dts = page.locator("dl#articles > dt").all()
            dds = page.locator("dl#articles > dd").all()

            # 确保 dt 和 dd 数量匹配，防止索引越界
            min_len = min(len(dts), len(dds))

            for i in range(min_len):
                try:
                    dt = dts[i]
                    dd = dds[i]
                    
                    result = {}

                    # --- 1. 提取 ID 和 PDF 链接 (从 dt 元素) ---
                    paper_id = ""
                    pdf_link = ""
                    
                    try:
                        # 尝试直接查找 PDF 链接
                        pdf_anchor = dt.locator("a[href*='/pdf/']").first
                        if pdf_anchor.count() > 0:
                            href = pdf_anchor.get_attribute("href")
                            if href:
                                pdf_link = href if href.startswith("http") else "https://arxiv.org" + href
                                # 从链接中提取 ID (例如 2301.00001)
                                match = re.search(r'(\d+\.\d+)', pdf_link)
                                if match:
                                    paper_id = match.group(1)
                        
                        # 如果没找到 PDF 链接，尝试从 Abstract 链接提取 ID 并构造 PDF 链接
                        if not paper_id:
                            abs_anchor = dt.locator("a[href*='/abs/']").first
                            if abs_anchor.count() > 0:
                                href = abs_anchor.get_attribute("href")
                                match = re.search(r'(\d+\.\d+)', href)
                                if match:
                                    paper_id = match.group(1)
                                    pdf_link = f"https://arxiv.org/pdf/{paper_id}.pdf"
                        
                        # 备选方案：直接从 dt 文本中提取 ID (格式如 arXiv:2301.00001)
                        if not paper_id:
                            text_content = dt.text_content()
                            match = re.search(r'arXiv:(\d+\.\d+)', text_content)
                            if match:
                                paper_id = match.group(1)
                                pdf_link = f"https://arxiv.org/pdf/{paper_id}.pdf"

                    except Exception:
                        pass

                    result["id"] = paper_id
                    result["pdf_url"] = pdf_link

                    # --- 2. 提取标题 (从 dd 元素) ---
                    # 使用 .list-title 选择器，这是 ArXiv 的标准类名
                    try:
                        title_div = dd.locator("div.list-title").first
                        if title_div.count() > 0:
                            title_text = title_div.text_content()
                            # 清理 "Title:" 前缀和多余空白
                            title_text = title_text.replace("Title:", "").strip()
                            result["title"] = title_text
                        else:
                            # 容错：如果标准类名失效，尝试查找包含 "Title:" 文本的 div
                            fallback_title = dd.locator("div:has-text('Title:')").first
                            if fallback_title.count() > 0:
                                result["title"] = fallback_title.text_content().replace("Title:", "").strip()
                    except Exception:
                        pass

                    # --- 3. 提取摘要 (从 dd 元素) ---
                    # 使用 blockquote.abstract 选择器
                    # 注意：摘要可能在 DOM 中但不可见，使用 text_content() 可直接提取无需点击
                    try:
                        abstract_bq = dd.locator("blockquote.abstract").first
                        if abstract_bq.count() > 0:
                            abs_text = abstract_bq.text_content()
                            # 清理 "Abstract:" 前缀和多余空白
                            abs_text = abs_text.replace("Abstract:", "").strip()
                            result["abstract"] = abs_text
                        else:
                            # 容错：查找任何 blockquote
                            fallback_bq = dd.locator("blockquote").first
                            if fallback_bq.count() > 0:
                                result["abstract"] = fallback_bq.text_content().replace("Abstract:", "").strip()
                    except Exception:
                        pass

                    # 数据验证：确保至少有标题或 ID
                    if result.get("title") or result.get("id"):
                        results.append(result)

                except Exception as e:
                    # 单个条目提取失败，跳过继续下一个
                    continue

    except Exception as e:
        # 全局异常处理
        error = str(e)
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("title") or r.get("id")]

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
    url = sys.argv[1] if len(sys.argv) > 1 else "https://arxiv.org/list/cs/recent"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))