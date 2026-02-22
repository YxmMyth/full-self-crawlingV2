from playwright.sync_api import sync_playwright
import json
import time
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

def scrape(url: str) -> dict:
    results = []
    browser = None
    error_msg = None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-web-security"]
            )
            page = browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1920, "height": 1080}
            )

            page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 等待关键元素
            try:
                page.wait_for_selector('body', timeout=10000)
            except:
                pass

            # 人类行为延迟
            time.sleep(random.uniform(1.5, 3.0))

            # === 策略判断 ===
            # 检查是否为搜索结果页 (列表页)
            is_search_page = False
            try:
                if page.locator(".job_seen_beacon").count() > 0:
                    is_search_page = True
            except:
                pass

            # === 数据提取 ===
            
            if is_search_page:
                # 模式1: 搜索结果列表页
                items = page.locator(".job_seen_beacon").all()
                for item in items:
                    try:
                        result = {}
                        
                        # 职位 Title
                        try:
                            title_sel = item.locator("h2.jobTitle span, h2.jobTitle")
                            if title_sel.count() > 0:
                                result["title"] = title_sel.first.inner_text().strip()
                            else:
                                result["title"] = title_sel.inner_text().strip()
                        except:
                            result["title"] = None

                        # 公司 Company
                        try:
                            result["company"] = item.locator("[data-testid='company-name']").inner_text().strip()
                        except:
                            result["company"] = None

                        # 薪资 Salary
                        try:
                            result["salary"] = item.locator(".salary-snippet, [data-testid='job-salary']").inner_text().strip()
                        except:
                            result["salary"] = None

                        # 公司 Logo
                        try:
                            logo_elem = item.locator("img.company-logo, img[src*='logo']")
                            if logo_elem.count() > 0:
                                result["logo_url"] = logo_elem.first.get_attribute("src")
                            else:
                                result["logo_url"] = None
                        except:
                            result["logo_url"] = None
                            
                        # JD HTML (列表页通常只有片段，尝试获取)
                        try:
                            result["jd_html"] = item.locator("table td div").first.inner_html()
                        except:
                            result["jd_html"] = None

                        if result.get("title"):
                            results.append(result)
                    except Exception as e:
                        continue
            else:
                # 模式2: 单个职位详情页 或 Hire 模板页
                result = {}
                
                # 职位 Title - 尝试多种常见选择器
                title_selectors = ["h1.jobsearch-JobInfoHeader-title", "h1", ".job-title", "h2.jobTitle"]
                for sel in title_selectors:
                    try:
                        elem = page.locator(sel).first
                        if elem.count() > 0 and elem.inner_text().strip():
                            result["title"] = elem.inner_text().strip()
                            break
                    except:
                        continue
                
                # 公司 Company
                try:
                    comp = page.locator("[data-testid='company-name'], .jobsearch-CompanyInfoWithoutHeaderImage a").first
                    if comp.count() > 0:
                        result["company"] = comp.inner_text().strip()
                except:
                    result["company"] = None

                # 薪资 Salary
                try:
                    sal = page.locator("[data-testid='job-salary'], .jobsearch-JobMetadataHeader-item").first
                    if sal.count() > 0:
                        result["salary"] = sal.inner_text().strip()
                except:
                    result["salary"] = None

                # 职位描述 HTML (详情页特有)
                try:
                    jd_elem = page.locator("#jobDescriptionText, .jobsearch-jobDescriptionText, #description").first
                    if jd_elem.count() > 0:
                        result["jd_html"] = jd_elem.inner_html()
                    else:
                        result["jd_html"] = None
                except:
                    result["jd_html"] = None

                if result.get("title"):
                    results.append(result)

    except Exception as e:
        error_msg = str(e)
    finally:
        if browser:
            browser.close()

    return {
        "results": results,
        "metadata": {
            "url": url,
            "count": len(results),
            "error": error_msg
        }
    }