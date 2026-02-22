from playwright.sync_api import sync_playwright
import json
import time
import random

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
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            # 访问页面，使用 networkidle 等待动态资源加载
            page.goto(url, wait_until='networkidle', timeout=60000)

            # 等待关键元素
            try:
                page.wait_for_selector('body', timeout=10000)
            except:
                pass

            # 模拟人类滚动行为，触发懒加载和 iframe 渲染
            # Datawrapper features 页面较长，图表可能需要滚动才能加载
            for _ in range(5):
                page.mouse.wheel(0, 1000)
                time.sleep(random.uniform(0.5, 1.0))
            
            # 回到顶部，确保顶部元素也被加载
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(1)

            # === 数据提取 ===
            
            # 策略 1: 尝试从 iframe 中提取 SVG (针对上次失败原因的修复)
            # 很多图表网站使用 iframe 封装图表
            try:
                iframes = page.locator('iframe').all()
                for iframe in iframes:
                    try:
                        frame = iframe.content_frame()
                        if frame:
                            # 等待 frame 内部加载 SVG
                            try:
                                frame.wait_for_selector('svg', timeout=2000)
                                svgs = frame.locator('svg').all()
                                for svg in svgs:
                                    # 获取 SVG 完整代码
                                    svg_code = svg.evaluate("el => el.outerHTML")
                                    if svg_code and "<svg" in svg_code:
                                        results.append({
                                            "type": "svg_chart",
                                            "source": "iframe",
                                            "content": svg_code
                                        })
                            except:
                                continue
                    except Exception:
                        continue
            except Exception:
                pass

            # 策略 2: 尝试直接在主文档中提取 SVG (如果是内联 SVG)
            if not results:
                try:
                    svgs = page.locator('svg').all()
                    for svg in svgs:
                        try:
                            svg_code = svg.evaluate("el => el.outerHTML")
                            if svg_code and len(svg_code) > 100: # 过滤掉小图标
                                results.append({
                                    "type": "svg_chart",
                                    "source": "inline",
                                    "content": svg_code
                                })
                        except:
                            continue
                except Exception:
                    pass

            # 策略 3: 使用已验证的选择器 link[href$=".svg"]
            # 如果图表 SVG 难以提取，至少提取相关的 SVG 资源链接
            try:
                svg_links = page.locator('link[href$=".svg"]').all()
                for link in svg_links:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            results.append({
                                "type": "svg_resource",
                                "source": "link_tag",
                                "url": href
                            })
                    except:
                        continue
            except Exception:
                pass

            # 策略 4: 尝试查找通用的卡片容器，获取文本信息作为补充
            # 尝试建议的选择器 .card, .item, [data-id]
            selectors_to_try = [".card", ".item", "[data-id]", "article"]
            for sel in selectors_to_try:
                if len(results) >= 10: # 如果已经有足够数据，停止尝试
                    break
                try:
                    items = page.locator(sel).all()
                    for item in items:
                        try:
                            text = item.text_content()
                            if text and len(text.strip()) > 20:
                                results.append({
                                    "type": "text_content",
                                    "selector": sel,
                                    "content": text.strip()
                                })
                        except:
                            continue
                except:
                    continue

    except Exception as e:
        error = str(e)
        # 可以选择记录错误日志
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    # 去重，避免重复提取同一个 SVG
    seen_contents = set()
    valid_results = []
    for r in results:
        content_key = r.get("content") or r.get("url") or r.get("text")
        if content_key and content_key not in seen_contents:
            seen_contents.add(content_key)
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
    url = sys.argv[1] if len(sys.argv) > 1 else "https://www.datawrapper.de/features"
    result = scrape(url)
    print(json.dumps(result, ensure_ascii=False, indent=2))