from playwright.sync_api import sync_playwright
import json
import time
import random
import sys
import re

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    error_log = []
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security"]
            )
            context = browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080},
                locale="en-US"
            )
            page = context.new_page()

            # 1. 访问初始页面
            try:
                page.goto(url, wait_until='networkidle', timeout=60000)
            except Exception as e:
                error_log.append(f"Initial navigation timeout or error: {e}")
                # 尝试回退策略
                page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 2. 处理弹窗
            try:
                # AllRecipes 常见的 Cookie 弹窗选择器
                accept_btn = page.locator("button#onetrust-accept-btn-handler, button.onetrust-close-btn-handler, button:has-text('Accept')").first
                if accept_btn.is_visible(timeout=5000):
                    accept_btn.click(force=True)
                    time.sleep(1)
            except:
                pass # 没有弹窗或处理失败，继续

            # 3. 判断页面类型并导航
            # 如果是首页 (列表页)，我们需要进入一个详情页来获取配料和步骤
            current_url = page.url
            is_detail_page = "/recipe/" in current_url
            
            if not is_detail_page:
                try:
                    # 尝试寻找第一个菜谱链接
                    page.wait_for_selector("a[href*='/recipe/']", timeout=10000)
                    first_recipe_link = page.locator("a[href*='/recipe/']").first
                    detail_url = first_recipe_link.get_attribute("href")
                    
                    if detail_url:
                        if not detail_url.startswith("http"):
                            detail_url = "https://www.allrecipes.com" + detail_url
                        
                        print(f"Navigating to detail page: {detail_url}", file=sys.stderr)
                        page.goto(detail_url, wait_until='networkidle', timeout=60000)
                    else:
                        error_log.append("No recipe link found on homepage.")
                except Exception as e:
                    error_log.append(f"Failed to navigate to detail page: {e}")

            # 4. 等待核心内容加载
            try:
                # 等待配料或步骤容器出现
                page.wait_for_selector(".mntl-structured-ingredients__list, .recipe__steps-content, script[type='application/ld+json']", timeout=15000)
            except:
                pass # 容错，继续尝试提取

            # 5. 数据提取
            recipe_data = {}
            
            # === 提取 JSON-LD (最健壮的数据源) ===
            try:
                scripts = page.locator("script[type='application/ld+json']").all()
                for script in scripts:
                    try:
                        data = json.loads(script.text_content())
                        # Schema.org 结构可能是一个对象或包含对象的数组
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            if item.get("@type") == "Recipe":
                                recipe_data["title"] = item.get("name")
                                recipe_data["ingredients_json"] = item.get("recipeIngredient", [])
                                recipe_data["image"] = item.get("image")
                                
                                # 处理步骤
                                instructions = item.get("recipeInstructions", [])
                                steps_html = []
                                for step in instructions:
                                    if isinstance(step, dict):
                                        text = step.get("text") or step.get("name", "")
                                        steps_html.append(f"<p>{text}</p>")
                                    elif isinstance(step, str):
                                        steps_html.append(f"<p>{step}</p>")
                                recipe_data["steps_html"] = "".join(steps_html)
                                break
                    except:
                        continue
            except Exception as e:
                error_log.append(f"Schema extraction failed: {e}")

            # === 如果 Schema 提取失败或不完整，使用 DOM 选择器回退 ===
            
            # 标题
            if not recipe_data.get("title"):
                try:
                    recipe_data["title"] = page.locator("h1.headline").text_content(timeout=5000).strip()
                except:
                    pass

            # 图片
            if not recipe_data.get("image"):
                try:
                    img = page.locator("img.primary-image__image, div.mntl-sc-block-image img").first
                    recipe_data["image"] = img.get_attribute("src", timeout=5000)
                except:
                    pass

            # 配料
            if not recipe_data.get("ingredients_json"):
                ingredients_list = []
                try:
                    items = page.locator(".mntl-structured-ingredients__list-item, ul.ingredients-section li").all()
                    for item in items:
                        text = item.text_content().strip()
                        if text:
                            ingredients_list.append(text)
                    recipe_data["ingredients_json"] = ingredients_list
                except:
                    pass

            # 步骤
            if not recipe_data.get("steps_html"):
                steps_html_list = []
                try:
                    # 尝试选择步骤列表项
                    steps = page.locator(".comp.recipe__steps .mntl-sc-block, .recipe__steps-content li, .instruction-section li").all()
                    for step in steps:
                        # 获取 outer HTML 以保留标签结构，或者 text_content
                        # 这里根据需求返回 HTML 片段
                        html_content = step.evaluate("el => el.outerHTML")
                        steps_html_list.append(html_content)
                    recipe_data["steps_html"] = "".join(steps_html_list)
                except Exception as e:
                    error_log.append(f"DOM Steps extraction failed: {e}")

            # 6. 数据组装
            if recipe_data.get("title") or recipe_data.get("ingredients_json"):
                results.append(recipe_data)

    except Exception as e:
        error_log.append(f"Critical Error: {str(e)}")
    finally:
        if browser:
            browser.close()

    # 数据清洗和验证
    valid_results = [r for r in results if r.get("title") or r.get("ingredients_json")]

    return {
        "results": valid_results,
        "metadata": {
            "total_extracted": len(results),
            "valid_count": len(valid_results),
            "url": url,
            "errors": error_log
        }
    }

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://www.allrecipes.com/"
    result = scrape(target_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))