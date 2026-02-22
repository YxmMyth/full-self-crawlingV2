"""
Selector Validator - 选择器验证器

在实际 DOM 上测试 CSS 选择器的有效性，避免 LLM 猜测错误的选择器。

功能：
1. 在实际 HTML 上测试选择器
2. 返回选择器的匹配数量和样本数据
3. 分析 DOM 结构提供最佳选择器建议
4. 支持在沙箱中执行
"""

from typing import Dict, Any, List, Optional, Tuple
from bs4 import BeautifulSoup
import re


class SelectorValidator:
    """
    选择器验证器

    用于在实际 HTML 上测试 CSS 选择器，确保选择器有效。
    """

    def __init__(self, html: str):
        """
        初始化验证器

        Args:
            html: 要验证的 HTML 内容
        """
        self.html = html
        self.soup = BeautifulSoup(html, 'lxml')

    def test_selector(self, selector: str) -> Dict[str, Any]:
        """
        测试单个选择器

        Args:
            selector: CSS 选择器

        Returns:
            验证结果字典，包含 count, sample, valid 等
        """
        try:
            elements = self.soup.select(selector)

            samples = []
            for el in elements[:3]:  # 最多返回 3 个样本
                sample = {
                    "tag": el.name,
                    "text": el.get_text(strip=True)[:100],
                    "classes": el.get("class", []),
                    "id": el.get("id", ""),
                }

                # 如果是链接，提取 href
                if el.name == 'a':
                    sample["href"] = el.get("href", "")[:200]
                # 如果是图片，提取 src
                elif el.name == 'img':
                    sample["src"] = el.get("src", "")[:200]

                samples.append(sample)

            return {
                "selector": selector,
                "valid": len(elements) > 0,
                "count": len(elements),
                "samples": samples,
            }
        except Exception as e:
            return {
                "selector": selector,
                "valid": False,
                "error": str(e),
                "count": 0,
                "samples": [],
            }

    def test_selectors(self, selectors: List[str]) -> List[Dict[str, Any]]:
        """
        批量测试选择器

        Args:
            selectors: CSS 选择器列表

        Returns:
            验证结果列表
        """
        results = []
        for selector in selectors:
            result = self.test_selector(selector)
            results.append(result)
        return results

    def find_best_selector(
        self,
        target_type: str = "article",
        min_count: int = 1,
    ) -> Dict[str, Any]:
        """
        自动查找最佳选择器

        Args:
            target_type: 目标类型 (article, link, image, etc.)
            min_count: 最小匹配数量

        Returns:
            最佳选择器及结果
        """
        candidates = self._generate_candidates(target_type)

        best_result = None
        best_score = 0

        for candidate in candidates:
            result = self.test_selector(candidate)

            if not result["valid"]:
                continue

            # 评分：数量适中，样本质量高
            score = self._score_selector(result, target_type)

            if score > best_score and result["count"] >= min_count:
                best_score = score
                best_result = result

        return best_result or {
            "selector": None,
            "valid": False,
            "count": 0,
            "samples": [],
        }

    def _generate_candidates(self, target_type: str) -> List[str]:
        """生成候选选择器"""
        candidates = []

        if target_type == "article":
            # 常见的文章/条目选择器
            patterns = [
                "article",
                "[class*='article']",
                "[class*='post']",
                "[class*='item']",
                "[class*='card']",
                "[class*='entry']",
                "[class*='story']",
            ]
        elif target_type == "link":
            patterns = [
                "a[href]",
                "[class*='link']",
                "[href*='/p/']",
                "[href*='/article']",
            ]
        elif target_type == "image":
            patterns = [
                "img[src]",
                "[class*='image']",
                "[class*='photo']",
                "picture img",
            ]
        else:
            patterns = ["div", "section", "article"]

        # 生成具体的选择器
        for pattern in patterns:
            candidates.append(pattern)
            # 添加组合选择器
            if not pattern.startswith("a") and not pattern.startswith("img"):
                candidates.append(f"div {pattern}")
                candidates.append(f"li {pattern}")

        return candidates

    def _score_selector(self, result: Dict[str, Any], target_type: str) -> float:
        """给选择器打分"""
        score = 0

        count = result["count"]
        samples = result.get("samples", [])

        # 数量得分（3-50 个比较理想）
        if 3 <= count <= 50:
            score += 10
        elif count > 0:
            score += 5

        # 样本质量得分
        for sample in samples:
            text = sample.get("text", "")
            if text and len(text) > 10:
                score += 2
            if target_type == "link" and sample.get("href"):
                score += 3
            if target_type == "image" and sample.get("src"):
                score += 3

        return score

    def analyze_dom_structure(self) -> Dict[str, Any]:
        """
        分析 DOM 结构

        返回页面的结构信息，帮助理解页面布局。
        """
        # 找出主要的容器
        containers = []

        for div in self.soup.find_all('div', limit=50):
            classes = div.get('class', [])
            if not classes:
                continue

            class_str = ' '.join(classes)
            children = len(div.find_all(recursive=False))

            # 查找可能是容器的 div（有多个子元素）
            if children >= 3:
                containers.append({
                    "selector": f"div.{class_str.replace(' ', '.')}",
                    "class": class_str,
                    "children": children,
                    "tag_sample": div.name,
                })

        # 排序：子元素多的优先
        containers.sort(key=lambda x: x["children"], reverse=True)

        # 分析链接结构
        links = self.soup.find_all('a', href=True, limit=20)
        link_patterns = {}

        for link in links:
            href = link.get('href', '')
            classes = link.get('class', [])

            # 分析 URL 模式
            if '/p/' in href:
                link_patterns['/p/'] = link_patterns.get('/p/', 0) + 1
            if '/article' in href:
                link_patterns['/article'] = link_patterns.get('/article', 0) + 1
            if '/post' in href:
                link_patterns['/post'] = link_patterns.get('/post', 0) + 1

        return {
            "containers": containers[:10],  # 最多 10 个
            "link_patterns": link_patterns,
            "total_links": len(self.soup.find_all('a')),
            "total_images": len(self.soup.find_all('img')),
        }

    def suggest_selectors(self, user_goal: str) -> List[str]:
        """
        根据用户目标建议选择器

        Args:
            user_goal: 用户需求描述

        Returns:
            建议的选择器列表
        """
        goal_lower = user_goal.lower()

        suggestions = []

        # 根据关键词推断
        if any(kw in goal_lower for kw in ['article', '文章', 'post', '博客']):
            suggestions.extend([
                "article",
                "[class*='article']",
                "[class*='post']",
                "[class*='entry']",
            ])

        if any(kw in goal_lower for kw in ['link', '链接', 'url', 'href']):
            suggestions.extend([
                "a[href]",
                "[class*='link']",
            ])

        if any(kw in goal_lower for kw in ['image', '图片', 'photo', 'img']):
            suggestions.extend([
                "img[src]",
                "[class*='image']",
                "picture img",
            ])

        if any(kw in goal_lower for kw in ['title', '标题', 'heading']):
            suggestions.extend([
                "h1, h2, h3",
                "[class*='title']",
                "[class*='heading']",
            ])

        # 如果没有特定建议，返回通用选择器
        if not suggestions:
            suggestions = [
                "article",
                "[class*='item']",
                "[class*='card']",
                "div[class]",
            ]

        return list(set(suggestions))  # 去重


def validate_selectors_in_sandbox(
    html: str,
    selectors: List[str],
    sandbox=None,
) -> Dict[str, Any]:
    """
    在沙箱中验证选择器

    Args:
        html: HTML 内容
        selectors: 要验证的选择器列表
        sandbox: 沙箱实例（可选）

    Returns:
        验证结果
    """
    validator = SelectorValidator(html)
    results = validator.test_selectors(selectors)

    # 找出有效的选择器
    valid_selectors = [r["selector"] for r in results if r["valid"]]

    return {
        "all_results": results,
        "valid_selectors": valid_selectors,
        "total_tested": len(selectors),
        "total_valid": len(valid_selectors),
    }


# 代码模板 - 用于 LLM 生成选择器验证代码
SELECTOR_VALIDATOR_TEMPLATE = '''
from bs4 import BeautifulSoup
import json

html = """{html}"""
selectors = {selectors}

soup = BeautifulSoup(html, 'lxml')

results = []
for selector in selectors:
    elements = soup.select(selector)
    samples = []

    for el in elements[:3]:
        sample = {{
            "tag": el.name,
            "text": el.get_text(strip=True)[:50],
        }}
        if el.name == "a":
            sample["href"] = el.get("href", "")[:100]
        samples.append(sample)

    results.append({{
        "selector": selector,
        "valid": len(elements) > 0,
        "count": len(elements),
        "samples": samples,
    }})

print(json.dumps({{"results": results}}, ensure_ascii=False))
'''
