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
    try:
        with sync_playwright() as p:
            # 使用上下文管理器，退出 with 块时会自动停止 Playwright 并关闭浏览器
            browser = p.chromium.launch(
                headless=True,
            )
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            # 访问页面，Medium通常需要等待JS渲染
            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素或body加载
            try:
                # Medium首页通常会有文章列表，尝试等待article标签或通用body
                page.wait_for_selector('article', timeout=10000)
            except Exception:
                # 如果找不到article，可能是单篇文章或结构变化，继续执行
                try:
                    page.wait_for_selector('body', timeout=5000)
                except:
                    pass

            # 人类行为延迟
            time.sleep(random.uniform(1.5, 3.0))

            # === 数据提取 ===
            
            # 方法1: 尝试查找 article 容器
            items = page.locator("article").all()
            
            # 如果没有找到article标签，尝试查找包含标题的块级元素（针对单页或不同布局）
            if not items:
                # 尝试查找包含h2或h3的div，作为备选容器
                items = page.locator("div:has(h2), div:has(h3)").all()

            for item in items:
                try:
                    result = {}
                    
                    # 提取标题: 优先h2(列表), 其次h3, h1(单页/头条)
                    title_node = item.locator("h2, h3, h1").first
                    if title_node.count() > 0:
                        title_text = title_node.text_content()
                        if title_text:
                            result["title"] = title_text.strip()
                    
                    # 提取图片: 查找img标签，优先src，备选data-src
                    img_node = item.locator("img").first
                    if img_node.count() > 0:
                        img_src = img_node.get_attribute("src")
                        if not img_src:
                            img_src = img_node.get_attribute("data-src")
                        if img_src:
                            result["image_url"] = img_src.strip()

                    # 提取作者: 尝试建议的 .author-name，或者包含 'author' 的class
                    author_node = item.locator(".author-name, [class*='author']").first
                    if author_node.count() > 0:
                        author_text = author_node.text_content()
                        if author_text:
                            result["author"] = author_text.strip()
                    
                    # 提取链接: 查找a标签
                    link_node = item.locator("a").first
                    if link_node.count() > 0:
                        href = link_node.get_attribute("href")
                        if href:
                            # 处理相对路径
                            if href.startswith("/"):
                                href = "https://medium.com" + href
                            result["link"] = href.strip()

                    # 只有当存在有效数据（至少有标题或图片）时才添加
                    if result.get("title") or result.get("image_url"):
                        results.append(result)

                except Exception as e:
                    # 单个条目提取失败，跳过继续下一个
                    continue

            # 方法2: 如果上述容器提取失败，尝试全局直接提取（兜底策略）
            if not results:
                # 尝试提取页面上的所有图片
                all_imgs = page.locator("img[src]").all()
                for img in all_imgs:
                    try:
                        src = img.get_attribute("src")
                        if src and "medium" in src: # 简单过滤一下来源
                            results.append({"type": "image_only", "image_url": src})
                    except:
                        continue

    except Exception as e:
        # 记录错误但不中断程序返回
        error_msg = str(e)
        # 可以在这里将错误写入日志
        pass

    # 移除了 finally 块中的手动 browser.close() 调用。
    # 'with sync_playwright()' 上下文管理器会在退出时自动处理浏览器和资源的关闭。

    # 数据清洗和验证
    # 过滤掉既没有标题也没有有效链接的无效数据
    valid_results = []
    for r in results:
        # 清理None值
        r = {k: v for k, v in r.items() if v is not None}
        if r.get("title") or r.get("image_url"):
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
    print(json.dumps(result, indent=2))