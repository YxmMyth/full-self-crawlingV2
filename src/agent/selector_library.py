"""
Selector Library - 常用网站选择器模式库

积累常见网站的选择器模式，提高代码生成成功率。
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SelectorPattern:
    """选择器模式"""
    name: str
    selector: str
    description: str
    website_types: List[str]  # 适用的网站类型
    confidence: float  # 置信度 0-1


# 常用选择器模式库
SELECTOR_PATTERNS = {
    # 电商平台
    "product_card": SelectorPattern(
        name="product_card",
        selector=".product-card, .item, [data-product], .goods-item",
        description="商品卡片",
        website_types=["ecommerce"],
        confidence=0.8
    ),
    "product_title": SelectorPattern(
        name="product_title",
        selector=".product-title, .goods-name, h2.title, [data-title]",
        description="商品标题",
        website_types=["ecommerce"],
        confidence=0.85
    ),
    "product_price": SelectorPattern(
        name="product_price",
        selector=".price, .product-price, [data-price], .current-price",
        description="商品价格",
        website_types=["ecommerce"],
        confidence=0.9
    ),
    "product_image": SelectorPattern(
        name="product_image",
        selector=".product-image img, .goods-img img, .p-picture img",
        description="商品图片",
        website_types=["ecommerce"],
        confidence=0.8
    ),

    # 新闻/文章
    "article_card": SelectorPattern(
        name="article_card",
        selector="article, .article, .post, .entry, [data-article]",
        description="文章卡片",
        website_types=["news", "blog"],
        confidence=0.85
    ),
    "article_title": SelectorPattern(
        name="article_title",
        selector="h1, h2.title, .article-title, .entry-title, [data-title]",
        description="文章标题",
        website_types=["news", "blog"],
        confidence=0.9
    ),
    "article_content": SelectorPattern(
        name="article_content",
        selector=".article-content, .entry-content, .post-content, article p",
        description="文章正文",
        website_types=["news", "blog"],
        confidence=0.8
    ),
    "article_author": SelectorPattern(
        name="article_author",
        selector=".author, .by-author, [data-author], .writer",
        description="文章作者",
        website_types=["news", "blog"],
        confidence=0.7
    ),

    # 招聘网站
    "job_card": SelectorPattern(
        name="job_card",
        selector=".job-card, .job-item, [data-job], .posting",
        description="职位卡片",
        website_types=["job_board"],
        confidence=0.8
    ),
    "job_title": SelectorPattern(
        name="job_title",
        selector=".job-title, h2, .position, [data-position]",
        description="职位名称",
        website_types=["job_board"],
        confidence=0.85
    ),
    "company_name": SelectorPattern(
        name="company_name",
        selector=".company, .employer, [data-company], .company-name",
        description="公司名称",
        website_types=["job_board"],
        confidence=0.75
    ),
    "salary": SelectorPattern(
        name="salary",
        selector=".salary, .pay, [data-salary], .compensation",
        description="薪资",
        website_types=["job_board"],
        confidence=0.7
    ),

    # 社交媒体
    "post": SelectorPattern(
        name="post",
        selector=".post, .tweet, [data-post], .status",
        description="帖子",
        website_types=["social_media"],
        confidence=0.75
    ),
    "username": SelectorPattern(
        name="username",
        selector=".username, .user, [data-user], .author-name",
        description="用户名",
        website_types=["social_media"],
        confidence=0.8
    ),

    # 通用元素
    "link": SelectorPattern(
        name="link",
        selector="a[href]",
        description="链接",
        website_types=["*"],
        confidence=0.95
    ),
    "image": SelectorPattern(
        name="image",
        selector="img[src]",
        description="图片",
        website_types=["*"],
        confidence=0.95
    ),
    "button": SelectorPattern(
        name="button",
        selector="button, .btn, [role='button']",
        description="按钮",
        website_types=["*"],
        confidence=0.9
    ),
}

# 网站特定的选择器模式
WEBSITE_SPECIFIC_SELECTORS = {
    "amazon.com": {
        "product_card": "[data-component-type='s-search-result']",
        "product_title": "h2 a span",
        "product_price": ".a-price .a-offscreen",
    },
    "indeed.com": {
        "job_card": ".job_seen_beacon",
        "job_title": "[id='jobTitle'] h2",
        "company_name": "[data-testid='company-name']",
    },
    "zillow.com": {
        "property_card": "[data-test='property-card']",
        "price": "[data-test='property-card-price']",
    },
    "linkedin.com": {
        "job_card": ".job-card-container",
        "job_title": ".job-title span",
    },
    "medium.com": {
        "article": "article",
        "title": "h1",
        "author": ".author-name",
    },
    "twitter.com": {
        "tweet": "[data-testid='tweet']",
        "text": "[data-testid='tweetText']",
    },
    "youtube.com": {
        "video": "ytd-video-renderer",
        "title": "#video-title",
        "channel": "ytd-channel-name",
    },
}


def get_selector_pattern(pattern_name: str) -> Optional[SelectorPattern]:
    """获取选择器模式"""
    return SELECTOR_PATTERNS.get(pattern_name)


def get_patterns_for_website_type(website_type: str) -> List[SelectorPattern]:
    """根据网站类型获取适用的选择器模式"""
    return [
        p for p in SELECTOR_PATTERNS.values()
        if website_type in p.website_types or "*" in p.website_types
    ]


def get_website_specific_selectors(domain: str) -> Optional[Dict[str, str]]:
    """获取网站特定的选择器"""
    from urllib.parse import urlparse

    parsed = urlparse(domain if "://" in domain else f"https://{domain}")
    netloc = parsed.netloc.lower()

    # 移除 www. 前缀
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # 精确匹配
    if netloc in WEBSITE_SPECIFIC_SELECTORS:
        return WEBSITE_SPECIFIC_SELECTORS[netloc]

    # 域名匹配
    domain_parts = netloc.split(".")
    if len(domain_parts) >= 2:
        base_domain = ".".join(domain_parts[-2:])
        if base_domain in WEBSITE_SPECIFIC_SELECTORS:
            return WEBSITE_SPECIFIC_SELECTORS[base_domain]

    return None


def suggest_selectors(
    user_goal: str,
    website_type: str,
    domain: Optional[str] = None,
) -> List[str]:
    """
    根据用户目标和网站类型建议选择器

    Args:
        user_goal: 用户需求描述
        website_type: 网站类型
        domain: 域名（可选）

    Returns:
        建议的选择器列表
    """
    suggestions = []

    # 首先检查是否有网站特定的选择器
    if domain:
        specific = get_website_specific_selectors(domain)
        if specific:
            suggestions.extend(specific.values())

    # 根据网站类型添加通用模式
    patterns = get_patterns_for_website_type(website_type)

    # 根据用户需求筛选
    goal_lower = user_goal.lower()

    for pattern in patterns:
        # 根据需求关键词匹配
        if "商品" in goal_lower or "product" in goal_lower:
            if "product" in pattern.name:
                suggestions.append(pattern.selector)
        elif "文章" in goal_lower or "article" in goal_lower:
            if "article" in pattern.name:
                suggestions.append(pattern.selector)
        elif "职位" in goal_lower or "job" in goal_lower:
            if "job" in pattern.name:
                suggestions.append(pattern.selector)
        elif "图片" in goal_lower or "image" in goal_lower:
            if "image" in pattern.name:
                suggestions.append(pattern.selector)

    # 添加通用选择器作为备选
    if not suggestions:
        generic = ["article", ".item", ".card", "[data-id]"]
        suggestions.extend(generic)

    return list(set(suggestions))  # 去重


def generate_selector_suggestion_prompt(
    url: str,
    user_goal: str,
    website_type: str,
) -> str:
    """
    生成选择器建议的Prompt补充

    用于在代码生成时提供选择器参考。
    """
    suggested = suggest_selectors(user_goal, website_type, url)

    if not suggested:
        return ""

    suggestions_text = "\n".join(f"- {s}" for s in suggested[:5])

    return f"""

【参考选择器】
根据目标网站类型({website_type})，建议尝试以下选择器：
{suggestions_text}

如果以上选择器不匹配，请在页面中寻找具有相似语义的class或data属性。
"""


# 选择器验证和修复建议
SELECTOR_FIX_PATTERNS = {
    # 常见问题和修复
    "too_generic": {
        "problem": ["div", "span", "a", "img"],
        "fix": "添加类名或属性限定，如：div.item, a.link"
    },
    "missing_attribute": {
        "problem": ["[href]", "[src]"],
        "fix": "通常需要更具体的限定，如：a[href^='/'], img[src*='/uploads/']"
    },
    "too_specific": {
        "problem": [r"\[class='very-long-specific-class-name-abc123'\]"],
        "fix": "使用部分匹配或属性选择器，如：[class*='specific-class']"
    },
    "pseudoclass_missing": {
        "problem": ["a:first-child", "li:nth-of-type"],
        "fix": "考虑使用 :first-child 或 :nth-child() 等伪类"
    },
}


def get_selector_fix_suggestion(selector: str) -> Optional[str]:
    """
    获取选择器修复建议

    Args:
        selector: 有问题的选择器

    Returns:
        修复建议
    """
    for fix_type, pattern in SELECTOR_FIX_PATTERNS.items():
        for problem in pattern["problem"]:
            if problem in selector:
                return pattern["fix"]

    return None
