from playwright.sync_api import sync_playwright
import json
import time
import random
import sys
from datetime import datetime

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
]

def scrape(url: str) -> dict:
    results = []
    error_message = None
    status = "success"
    
    try:
        # 使用 with sync_playwright() as p: 确保资源自动管理
        # 修复点：删除了手动调用的 browser.close()，依赖 with 语句自动关闭
        with sync_playwright() as p:
            # 使用正确的 API 启动浏览器
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security"]
            )
            # 使用正确的 API 创建新页面
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待页面稳定
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except:
                pass

            # 人类行为延迟
            time.sleep(random.uniform(1.5, 3.0))

            # === 数据提取策略 ===
            # 策略1: 尝试提取结构化数据 (JSON-LD) - 最健壮的方式
            try:
                json_ld_scripts = page.locator('script[type="application/ld+json"]').all()
                for script in json_ld_scripts:
                    try:
                        content = script.text_content()
                        if content:
                            data = json.loads(content)
                            # 处理单个对象或数组
                            items_list = data if isinstance(data, list) else [data]
                            for item in items_list:
                                if item.get('@type') == 'JobPosting':
                                    org = item.get('hiringOrganization', {})
                                    salary_info = item.get('baseSalary', {})
                                    
                                    # 提取薪资文本
                                    salary_text = None
                                    if isinstance(salary_info, dict):
                                        salary_text = salary_info.get('value', {}).get('text') or salary_info.get('text')
                                    elif isinstance(salary_info, str):
                                        salary_text = salary_info

                                    result = {
                                        "title": item.get("title"),
                                        "company": org.get("name"),
                                        "logo": org.get("logo"),
                                        "salary": salary_text,
                                        "jd_html": item.get("description"),
                                        "link": item.get("url")
                                    }
                                    if result.get("title"): # 只有标题存在才认为是有效数据
                                        results.append(result)
                    except:
                        continue
            except Exception as e:
                pass

            # 策略2: 如果JSON-LD未获取到数据，尝试DOM选择器 (针对列表页或单页)
            if not results:
                # 尝试查找列表容器
                list_selectors = [
                    "div.jobsearch-SerpJobCard", 
                    ".job_seen_beacon", 
                    "div.job-item",
                    "li.job",
                    "ul.jobsearch-ResultsList > li"
                ]
                
                items = []
                for sel in list_selectors:
                    try:
                        found = page.locator(sel).all()
                        if found:
                            items = found
                            break
                    except:
                        continue

                # 如果找到列表，遍历列表
                if items:
                    for item in items:
                        try:
                            result = {}
                            # 标题
                            title_sel = item.locator("h2.jobTitle, h2 a, [data-testid='job-title'], a.jcs-JobTitle").first
                            if title_sel.count() > 0:
                                result["title"] = title_sel.text_content()
                                result["link"] = title_sel.get_attribute("href")

                            # 公司
                            comp_sel = item.locator("span.companyName, [data-testid='company-name'], [class*='companyName']").first
                            if comp_sel.count() > 0:
                                result["company"] = comp_sel.text_content()

                            # Logo (Indeed列表通常没有Logo，尝试找img)
                            img_sel = item.locator("img").first
                            if img_sel.count() > 0:
                                result["logo"] = img_sel.get_attribute("src")
                            
                            # 薪资
                            sal_sel = item.locator(".salary-snippet, [data-testid='salary-snippet'], span.salary, div.salary-text").first
                            if sal_sel.count() > 0:
                                result["salary"] = sal_sel.text_content()

                            # 描述片段
                            desc_sel = item.locator("div.job-snippet, table.jobCard main, div.summary").first
                            if desc_sel.count() > 0:
                                result["jd_html"] = desc_sel.text_content()

                            if result.get("title"):
                                results.append(result)
                        except:
                            continue
                
                # 策略3: 如果列表未找到，尝试单页详情提取
                else:
                    try:
                        result = {}
                        # 尝试获取单页标题
                        title = page.locator("h1").first.text_content()
                        if title:
                            result["title"] = title
                            
                            # 公司
                            comp_sel = page.locator("div[data-testid='company-name'], .company-name, header h4").first
                            if comp_sel.count() > 0:
                                result["company"] = comp_sel.text_content()
                            
                            # 描述
                            desc_sel = page.locator("#jobDescriptionText, #job-details, .description").first
                            if desc_sel.count() > 0:
                                result["jd_html"] = desc_sel.inner_html()
                            
                            result["link"] = url
                            results.append(result)
                    except:
                        pass

    except Exception as e:
        status = "error"
        error_message = str(e)
    
    # 返回包含 results 和 metadata 的 JSON 格式
    return {
        "results": results,
        "metadata": {
            "url": url,
            "status": status,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "count": len(results)
        }
    }

# 示例调用 (实际使用时可根据需要调整)
if __name__ == "__main__":
    # 这里需要一个测试URL，实际运行时请替换
    target_url = "https://example.com/job-listing"
    data = scrape(target_url)
    print(json.dumps(data, indent=2, ensure_ascii=False))