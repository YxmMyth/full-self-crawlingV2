from playwright.sync_api import sync_playwright
import json
import time
import random
import sys

# 模拟真实用户代理
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

def scrape(url: str) -> dict:
    results = []
    try:
        with sync_playwright() as p:
            # 修复：使用标准的 launch API
            browser = p.chromium.launch(headless=True)
            
            # 修复：确保 API 调用正确，直接使用 new_page
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            # 访问页面
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素加载
            try:
                # TechCrunch 通常使用 article 标签或 .post-block
                page.wait_for_selector('article, .post-block, .card', timeout=15000)
            except Exception:
                pass

            # 模拟人类行为延迟
            time.sleep(random.uniform(1.5, 3.0))

            # === 数据提取 ===
            
            # 策略1: 尝试使用通用 article 标签
            items = page.locator("article").all()
            
            # 策略2: 如果没有 article，尝试 TechCrunch 特有的类名
            if not items:
                items = page.locator(".post-block").all()
            
            # 策略3: 尝试通用的卡片类
            if not items:
                items = page.locator(".card, .item, [data-id]").all()

            for item in items:
                try:
                    result = {}
                    
                    # 1. 提取标题和链接
                    # 尝试多种常见标题选择器
                    title_el = item.locator("h2 a, h3 a, .title a, [class*='title'] a").first
                    if title_el.count() > 0:
                        result["title"] = title_el.text_content().strip()
                        result["link"] = title_el.get_attribute("href")
                    else:
                        # 如果找不到链接，尝试直接找文本
                        title_text = item.locator("h2, h3, .title").first
                        if title_text.count() > 0:
                            result["title"] = title_text.text_content().strip()
                        else:
                            continue # 没有标题跳过

                    # 2. 提取图片
                    img_el = item.locator("img").first
                    if img_el.count() > 0:
                        result["image"] = img_el.get_attribute("src") or img_el.get_attribute("data-src")

                    # 3. 提取富文本HTML片段
                    # 优先查找摘要或内容区域
                    content_el = item.locator(".excerpt, .post-excerpt, p, [class*='content']").first
                    if content_el.count() > 0:
                        result["html_snippet"] = content_el.inner_html().strip()

                    # 4. 提取视频 (如果有)
                    video_el = item.locator("video, iframe[src*='youtube'], iframe[src*='vimeo']").first
                    if video_el.count() > 0:
                        result["video"] = video_el.get_attribute("src")

                    results.append(result)
                except Exception as e:
                    continue

            # 如果循环提取失败，尝试全页匹配（针对某些SPA或特殊布局）
            if not results:
                try:
                    # 直接查找所有标题链接作为最后的备选
                    all_links = page.locator("h2 a, h3 a").all()
                    for link in all_links[:20]: # 限制数量防止过多
                        try:
                            results.append({
                                "title": link.text_content().strip(),
                                "link": link.get_attribute("href")
                            })
                        except:
                            continue
                except:
                    pass

    except Exception as e:
        # 记录错误但继续
        print(f"Critical Error: {str(e)}", file=sys.stderr)
    
    # 修复：移除了 finally 块中的 browser.close()。
    # Playwright 的 with 上下文管理器会在退出时自动处理浏览器关闭和资源清理。

    # 数据清洗和验证
    # 必须包含标题或链接才视为有效
    valid_results = [r for r in results if r.get("title") or r.get("link")]

    return {
        "results": valid_results,
        "metadata": {
            "total_extracted": len(results),
            "valid_count": len(valid_results),
            "url": url
        }
    }

if __name__ == "__main__":
    # 默认 URL 为 TechCrunch
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://techcrunch.com/"
    result = scrape(target_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))