from playwright.sync_api import sync_playwright
import json
import sys
import time
import random

# 常见的 User-Agent 列表，用于模拟真实用户
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    error_msg = None
    
    # 定义多组备选选择器，优先使用语义化标签，然后是特定类名
    container_selectors = [
        "article",           # 标准 HTML5 语义标签
        ".post-block",       # TechCrunch 旧版常用类
        "[class*='PostCard']", # 现代组件化类名
        ".wp-block-post",     # WordPress 新版编辑器块
        "[data-id]"           # 通用数据属性
    ]

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

            # 访问页面，使用 networkidle 确保大部分 JS 加载完成
            # 设置较长超时以应对慢速网络或反爬延迟
            page.goto(url, wait_until='networkidle', timeout=60000)

            # 尝试等待主要内容容器出现，增加容错时间
            try:
                # 等待 body 标签加载
                page.wait_for_selector('body', timeout=15000)
                
                # 模拟人类行为，随机滚动
                page.evaluate("window.scrollBy(0, 500)")
                time.sleep(random.uniform(1.5, 3.0))
            except Exception as e:
                # 即使等待失败也继续尝试提取
                pass

            # === 数据提取 ===
            items = []
            
            # 策略：遍历选择器列表，找到能匹配元素的选择器
            for selector in container_selectors:
                try:
                    # 检查选择器是否匹配到元素
                    count = page.locator(selector).count()
                    if count > 0:
                        items = page.locator(selector).all()
                        print(f"Found {count} items using selector: {selector}", file=sys.stderr)
                        break
                except:
                    continue

            # 如果常规选择器都失败，尝试根据已验证的 iframe 选择器或回退方案
            if not items:
                # 尝试查找任何包含链接和图片的块级元素作为最后手段
                items = page.locator("div:has(a):has(img)").all()

            for item in items:
                try:
                    result = {
                        "title": None,
                        "html_snippet": None,
                        "image": None,
                        "video": None,
                        "link": None
                    }

                    # 1. 提取标题 (尝试多种可能的标签)
                    title_selectors = ["h2 a", "h3 a", "h2", "h3", ".post-block__title__link", "[class*='title'] a"]
                    title_text = None
                    for t_sel in title_selectors:
                        try:
                            title_el = item.locator(t_sel).first
                            if title_el.count() > 0:
                                title_text = title_el.text_content()
                                if title_text:
                                    # 如果是链接元素，尝试获取 href
                                    if "a" in t_sel:
                                        result["link"] = title_el.get_attribute("href")
                                    break
                        except:
                            continue
                    
                    result["title"] = title_text.strip() if title_text else None

                    # 2. 提取 HTML 片段 (提取容器内的部分 HTML)
                    try:
                        # 获取内部 HTML，限制长度以防过大
                        raw_html = item.inner_html()
                        if raw_html:
                            result["html_snippet"] = raw_html[:5000] # 限制长度
                    except:
                        pass

                    # 3. 提取图片
                    try:
                        img_el = item.locator("img").first
                        if img_el.count() > 0:
                            # 优先获取 src，如果没有则尝试 data-src (懒加载)
                            img_src = img_el.get_attribute("src") or img_el.get_attribute("data-src")
                            result["image"] = img_src
                    except:
                        pass

                    # 4. 提取视频 (检查 video 标签或 iframe)
                    try:
                        video_el = item.locator("video").first
                        if video_el.count() > 0:
                            result["video"] = video_el.get_attribute("src")
                        else:
                            # 检查 iframe (根据已验证选择器提示)
                            iframe_el = item.locator("iframe").first
                            if iframe_el.count() > 0:
                                result["video"] = iframe_el.get_attribute("src")
                    except:
                        pass

                    # 数据验证：必须有标题或图片或视频才视为有效
                    if result["title"] or result["image"] or result["video"]:
                        results.append(result)

                except Exception as e:
                    # 单个条目提取失败不影响其他条目
                    continue

    except Exception as e:
        error_msg = str(e)
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("title") or r.get("image")]

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
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://techcrunch.com/"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))