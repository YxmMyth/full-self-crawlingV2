from playwright.sync_api import sync_playwright
import json
import time
import random
import sys

# 伪装浏览器头
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    try:
        with sync_playwright() as p:
            # 修复要求3: 直接使用 browser.new_page()，不使用 new_context()
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security"]
            )
            
            # 直接在 new_page 中设置 user_agent 和 viewport
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )

            # 访问页面
            page.goto(url, wait_until='domcontentloaded', timeout=60000)

            # 等待页面加载，针对动态内容
            try:
                # 等待任意一个菜谱链接出现，确保列表已加载
                page.wait_for_selector('a[href*="/recipe/"]', timeout=15000)
            except Exception:
                # 如果找不到特定选择器，至少等待body加载
                try:
                    page.wait_for_selector('body', timeout=5000)
                except:
                    pass

            # 模拟人类行为滚动，触发懒加载
            page.mouse.wheel(0, 500)
            time.sleep(random.uniform(1.5, 3.0))
            page.mouse.wheel(0, 500)
            time.sleep(random.uniform(1.0, 2.0))

            # === 数据提取 ===
            
            # 尝试策略1: 使用参考选择器 (AllRecipes常用结构)
            # 选择包含 recipe 链接的卡片容器
            card_selectors = [
                'a.mntl-card-list-items', 
                'div.mntl-card-list-items',
                'a[data-tracking-id="recipe-card"]',
                'article'
            ]
            
            items = []
            for selector in card_selectors:
                try:
                    count = page.locator(selector).count()
                    if count > 0:
                        items = page.locator(selector).all()
                        print(f"Found {count} items using selector: {selector}", file=sys.stderr)
                        break
                except:
                    continue

            # 如果策略1失败，尝试策略2: 直接查找所有指向 recipe 的链接
            if not items:
                print("Primary selectors failed, falling back to generic links.", file=sys.stderr)
                raw_links = page.locator('a[href*="/recipe/"]').all()
                # 简单去重逻辑或只取前N个，这里简单处理
                items = raw_links

            for item in items:
                try:
                    result = {}
                    
                    # 提取链接
                    link_el = item
                    # 安全获取 tagName
                    try:
                        tag_name = item.element_handle().evaluate("el => el.tagName")
                    except:
                        tag_name = ""

                    if tag_name != "A":
                        # 如果容器不是A标签，尝试在内部找A标签
                        link_el = item.locator('a[href*="/recipe/"]').first
                    
                    href = link_el.get_attribute('href')
                    if not href:
                        continue
                    
                    # 规范化链接
                    if href.startswith('/'):
                        href = "https://www.allrecipes.com" + href
                    
                    result["link"] = href

                    # 提取标题
                    # 尝试多个可能的选择器
                    title = ""
                    title_selectors = ['h2.mntl-text-block', 'h3', 'span.card__title-text', '.mntl-card__title-text', 'span.mntl-text-block']
                    for ts in title_selectors:
                        try:
                            t_el = item.locator(ts).first
                            if t_el.count() > 0:
                                title = t_el.text_content().strip()
                                if title:
                                    break
                        except:
                            continue
                    
                    # 如果容器内没找到标题，尝试用链接文本（作为最后的手段）
                    if not title and tag_name == "A":
                        title = item.text_content().strip()

                    result["title"] = title

                    # 提取图片
                    img_url = ""
                    try:
                        img_el = item.locator('img').first
                        if img_el.count() > 0:
                            # 优先获取 src，其次 data-src
                            img_url = img_el.get_attribute('src') or img_el.get_attribute('data-src') or ""
                    except:
                        pass
                    
                    result["image"] = img_url
                    results.append(result)
                except Exception as e:
                    # 捕获并跳过单个项目提取中的错误，防止整个循环中断
                    print(f"Error extracting item: {e}", file=sys.stderr)
                    pass

            return {
                "results": results,
                "metadata": {
                    "url": url,
                    "count": len(results),
                    "timestamp": time.time()
                }
            }

    except Exception as e:
        # 捕获整体流程错误
        error_msg = f"Scraping failed: {str(e)}"
        print(error_msg, file=sys.stderr)
        return {
            "results": [],
            "metadata": {
                "url": url,
                "error": error_msg
            }
        }
    finally:
        if browser:
            browser.close()