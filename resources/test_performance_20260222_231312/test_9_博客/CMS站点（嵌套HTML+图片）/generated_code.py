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
            )
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            # 访问页面，Medium是SPA，domcontentloaded通常足够，但最好等待网络空闲
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素：Medium首页文章列表容器
            # 根据反思，使用 data-testid="postSnippet"
            try:
                page.wait_for_selector('div[data-testid="postSnippet"]', timeout=15000)
            except Exception:
                # 如果找不到特定容器，可能是页面结构变化或被拦截，尝试等待body
                try:
                    page.wait_for_selector('body', timeout=10000)
                except:
                    pass

            # 人类行为延迟
            time.sleep(random.uniform(1.5, 3.0))

            # === 数据提取 ===
            
            # 方法1: 使用已验证的选择器 (基于反思中的 data-testid="postSnippet")
            # 这是一个健壮的选择器，专门针对Medium的动态加载结构
            items = page.locator('div[data-testid="postSnippet"]').all()
            
            for item in items:
                try:
                    result = {}
                    
                    # 提取标题
                    # 修正逻辑：直接在item容器下查找 h2 或 h3，不要嵌套查找
                    title_elem = item.locator('h2, h3').first
                    if title_elem.count() > 0:
                        result["title"] = title_elem.text_content()
                        
                        # 尝试提取链接 (通常在标题内的 a 标签)
                        link_elem = title_elem.locator('a').first
                        if link_elem.count() > 0:
                            result["link"] = link_elem.get_attribute('href')
                        else:
                            # 备选：尝试在item下找第一个a标签
                            first_link = item.locator('a').first
                            result["link"] = first_link.get_attribute('href') if first_link.count() > 0 else None
                    else:
                        continue # 没有标题则跳过

                    # 提取作者
                    # 尝试建议选择器 .author-name
                    author_elem = item.locator('.author-name').first
                    if author_elem.count() == 0:
                        # 备选：Medium常用的作者名属性或结构
                        author_elem = item.locator('div[data-testid="authorName"]').first
                        if author_elem.count() == 0:
                            # 再次备选：寻找包含作者信息的p标签或a标签
                            author_elem = item.locator('p').filter(has_text="@").first
                    
                    if author_elem.count() > 0:
                        result["author"] = author_elem.text_content()

                    # 提取图片
                    img_elem = item.locator('img').first
                    if img_elem.count() > 0:
                        result["image"] = img_elem.get_attribute('src')

                    results.append(result)
                except Exception as e:
                    # 单个条目提取失败不中断整体流程
                    continue

            # 方法2: 如果没有找到特定容器（回退逻辑）
            if not results:
                # 尝试通用的 article 标签或 h2 标签
                # 这是为了应对Medium再次更新DOM结构的情况
                fallback_items = page.locator('article').all()
                if not fallback_items:
                    # 如果没有article，尝试直接抓取所有h2作为最小可用单元
                    headers = page.locator('h2').all()
                    for h in headers:
                        try:
                            txt = h.text_content()
                            if txt and len(txt.strip()) > 0:
                                results.append({"title": txt.strip()})
                        except:
                            continue
                else:
                    for item in fallback_items:
                        try:
                            title = item.locator('h2, h3').first.text_content()
                            if title:
                                results.append({"title": title.strip()})
                        except:
                            continue

    except Exception as e:
        # 记录错误但继续
        error = str(e)
        # 在实际应用中可以记录日志
        pass
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    # 过滤掉没有标题的无效数据
    valid_results = []
    for r in results:
        # 清理字符串中的空白符
        if isinstance(r.get("title"), str):
            r["title"] = r["title"].strip()
        if isinstance(r.get("author"), str):
            r["author"] = r["author"].strip()
        
        if r.get("title"):
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
    url = sys.argv[1] if len(sys.argv) > 1 else "https://medium.com/"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))