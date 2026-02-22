"""
Validators - 验证工具模块

提供 CodeAct 风格的验证代码模板和工具函数。

设计原则：
1. 所有验证逻辑以可执行 Python 代码形式提供
2. 代码在沙箱中执行，确保安全性
3. 提供详细的验证结果和问题列表
4. 支持自定义验证规则
"""

from typing import Dict, List, Any, Optional
import json


# ============================================================================
# 验证代码模板
# ============================================================================

# ----------------------------------------------------------------------------
# 深度验证模板（沙箱代码执行）
# ----------------------------------------------------------------------------

IMAGE_DEEP_VALIDATION_TEMPLATE = """
import requests
from PIL import Image
from io import BytesIO
import json

def validate_image_deep(url: str, user_goal: str) -> dict:
    '''深度验证图片：下载并检查分辨率、格式、大小'''
    result = {{"url": url, "valid": True}}

    try:
        # 下载图片
        headers = {{"User-Agent": "Mozilla/5.0"}}
        response = requests.get(url, timeout=10, headers=headers)
        response.raise_for_status()

        # PIL 验证
        img = Image.open(BytesIO(response.content))

        result.update({{
            "format": img.format,
            "size": img.size,
            "width": img.width,
            "height": img.height,
            "mode": img.mode,
            "file_size_bytes": len(response.content),
            "is_high_res": img.width >= 1920 and img.height >= 1080,
            "is_medium_res": img.width >= 1280 and img.height >= 720,
            "is_landscape": img.width > img.height,
            "aspect_ratio": round(img.width / img.height, 2) if img.height > 0 else 0
        }})

        # 占位图检测（更精确）
        url_lower = url.lower()
        placeholder_patterns = [
            'placeholder', 'default', 'no-image', 'no_image',
            'generic', 'sample', 'example', 'empty', 'missing',
            '占位', '默认', 'icon', 'logo', 'spinner'
        ]
        result["is_placeholder"] = any(p in url_lower for p in placeholder_patterns)

        # 小图检测（可能是缩略图或占位图）
        result["is_thumbnail"] = img.width < 300 or img.height < 300

        # 综合判断
        if result["is_placeholder"] or result["is_thumbnail"]:
            result["valid"] = False
            result["issue"] = "placeholder" if result["is_placeholder"] else "thumbnail"

    except requests.RequestException as e:
        return {{"url": url, "valid": False, "error": f"下载失败: {{str(e)}}"}}
    except Exception as e:
        return {{"url": url, "valid": False, "error": str(e)}}

    return result

# 验证所有图片
user_goal = "{user_goal_placeholder}"
results = []
for item in {sample_data_placeholder}:
    for key, value in item.items():
        if 'image' in key.lower() and isinstance(value, str) and value:
            results.append(validate_image_deep(value, user_goal))

print(json.dumps({{"images": results}}, ensure_ascii=False))
"""


IMAGE_CLIP_VALIDATION_TEMPLATE = """
import requests
from PIL import Image
from io import BytesIO
import json

def validate_image_with_clip(url: str, user_goal: str) -> dict:
    '''使用 CLIP 验证图片内容与需求的相关性'''
    result = {{"url": url, "valid": True}}

    try:
        # 下载图片
        headers = {{"User-Agent": "Mozilla/5.0"}}
        response = requests.get(url, timeout=10, headers=headers)
        img = Image.open(BytesIO(response.content))

        # 基础验证
        result.update({{
            "width": img.width,
            "height": img.height,
            "format": img.format
        }})

        # 尝试 CLIP 验证（如果可用）
        try:
            import clip
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            model, preprocess = clip.load("ViT-B/32", device=device)

            image_input = preprocess(img).unsqueeze(0).to(device)
            # 构建对比文本：用户需求 vs 占位/无关内容
            text_input = clip.tokenize([user_goal, "placeholder image", "unrelated content", "default icon"]).to(device)

            with torch.no_grad():
                image_features = model.encode_image(image_input)
                text_features = model.encode_text(text_input)
                logits_per_image = (image_features @ text_features.T).squeeze()
                probs = logits_per_image.softmax(dim=0)

            relevance_score = float(probs[0])
            result["relevance_score"] = round(relevance_score, 3)
            result["is_relevant"] = relevance_score > 0.3
            result["method"] = "clip"

        except ImportError:
            # CLIP 未安装，使用基础验证
            result["relevance_score"] = None
            result["clip_skipped"] = True
            result["method"] = "basic"

    except requests.RequestException as e:
        return {{"url": url, "valid": False, "error": f"下载失败: {{str(e)}}"}}
    except Exception as e:
        return {{"url": url, "valid": False, "error": str(e)}}

    return result

# 验证图片
user_goal = "{user_goal_placeholder}"
results = []
for item in {sample_data_placeholder}:
    for key, value in item.items():
        if 'image' in key.lower() and isinstance(value, str) and value:
            results.append(validate_image_with_clip(value, user_goal))

print(json.dumps({{"images": results}}, ensure_ascii=False))
"""


PDF_DEEP_VALIDATION_TEMPLATE = """
import requests
import PyPDF2
from io import BytesIO
import json

def validate_pdf_deep(url: str) -> dict:
    '''深度验证 PDF：下载并检查内容'''
    try:
        headers = {{"User-Agent": "Mozilla/5.0"}}
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()

        pdf_reader = PyPDF2.PdfReader(BytesIO(response.content))

        # 提取第一页文本判断内容
        first_page_text = ""
        if len(pdf_reader.pages) > 0:
            first_page_text = pdf_reader.pages[0].extract_text() or ""

        return {{
            "url": url,
            "valid": True,
            "pages": len(pdf_reader.pages),
            "has_content": len(first_page_text.strip()) > 50,
            "is_encrypted": pdf_reader.is_encrypted,
            "file_size_bytes": len(response.content),
            "preview_text": first_page_text[:200] if first_page_text else "",
            "metadata": dict(pdf_reader.metadata) if pdf_reader.metadata else {{}}
        }}
    except requests.RequestException as e:
        return {{"url": url, "valid": False, "error": f"下载失败: {{str(e)}}"}}
    except Exception as e:
        return {{"url": url, "valid": False, "error": str(e)}}

# 验证所有 PDF
results = []
for item in {sample_data_placeholder}:
    for key, value in item.items():
        if 'pdf' in key.lower() and isinstance(value, str) and value:
            results.append(validate_pdf_deep(value))

print(json.dumps({{"pdfs": results}}, ensure_ascii=False))
"""


VIDEO_DEEP_VALIDATION_TEMPLATE = """
import requests
import json

def validate_video_deep(url: str) -> dict:
    '''深度验证视频：检查元数据（需要网络请求）'''
    try:
        headers = {{"User-Agent": "Mozilla/5.0"}}
        # HEAD 请求获取文件信息
        response = requests.head(url, timeout=10, headers=headers, allow_redirects=True)

        content_type = response.headers.get("Content-Type", "")
        content_length = response.headers.get("Content-Length")

        # 检查是否是视频
        video_types = ["video/", "application/octet-stream"]
        is_video = any(ct in content_type for ct in video_types)

        return {{
            "url": url,
            "valid": is_video,
            "content_type": content_type,
            "file_size_bytes": int(content_length) if content_length else None,
            "accessible": response.status_code == 200
        }}
    except Exception as e:
        return {{"url": url, "valid": False, "error": str(e)}}

# 验证所有视频
results = []
for item in {sample_data_placeholder}:
    for key, value in item.items():
        if 'video' in key.lower() or 'movie' in key.lower():
            if isinstance(value, str) and value:
                results.append(validate_video_deep(value))

print(json.dumps({{"videos": results}}, ensure_ascii=False))
"""


# ============================================================================
# 代码片段验证模板（SVG/HTML代码片段）
# ============================================================================

SVG_HTML_VALIDATION_TEMPLATE = """
import json
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

def validate_svg_html_field(field_value: str, field_name: str, user_goal: str) -> dict:
    '''验证 SVG 或 HTML 代码片段'''
    result = {{
        "field": field_name,
        "valid": False,
        "score": 0.0,
        "issues": [],
        "is_svg": False,
        "is_html": False,
        "has_malicious_tags": False,
        "structure_valid": False,
        "content_length": len(field_value)
    }}

    try:
        value_stripped = field_value.strip()

        # 检测是否是 SVG
        if value_stripped.startswith("<svg") or "<svg" in value_stripped[:200].lower():
            result["is_svg"] = True

            # SVG 语法验证
            try:
                soup = BeautifulSoup(field_value, "xml")
                svg_root = soup.find("svg")

                if svg_root is None:
                    result["issues"].append("缺少<svg>根标签")
                else:
                    result["structure_valid"] = True
                    result["valid"] = True

                    # 检查常见属性
                    has_width = svg_root.get("width") is not None
                    has_height = svg_root.get("height") is not None
                    has_viewbox = svg_root.get("viewBox") is not None

                    if not any([has_width, has_height, has_viewbox]):
                        result["issues"].append("SVG缺少尺寸属性(width/height/viewBox)")

                    # 检查内容
                    children = list(svg_root.children)
                    if len(children) == 0:
                        result["issues"].append("SVG为空，没有内容")

                    result["score"] = 9.0 if result["structure_valid"] and len(result["issues"]) == 0 else 6.0

            except Exception as e:
                result["issues"].append(f"SVG解析失败: {{str(e)[:100]}}")

        # 检测是否是 HTML 片段
        elif value_stripped.startswith("<") and any(tag in value_stripped[:100] for tag in ["<div", "<span", "<p", "<a ", "<img", "<h1", "<h2", "<h3", "<section", "<article"]):
            result["is_html"] = True

            # HTML 语法验证
            try:
                soup = BeautifulSoup(field_value, "html.parser")
                tags = soup.find_all()

                if len(tags) == 0:
                    result["issues"].append("不是有效HTML片段")
                else:
                    result["structure_valid"] = True
                    result["valid"] = True

                    # 安全检查（防XSS）
                    dangerous_tags = ["script", "iframe", "object", "embed", "form"]
                    found_dangerous = [tag.name for tag in tags if tag.name in dangerous_tags]

                    if found_dangerous:
                        result["has_malicious_tags"] = True
                        result["issues"].append(f"包含潜在恶意标签: {{', '.join(found_dangerous)}}")
                        result["valid"] = False
                        result["score"] = 2.0
                    else:
                        # 结构完整性评分
                        text_content = soup.get_text(strip=True)
                        result["score"] = 8.5 if len(text_content) > 20 else 5.0

            except Exception as e:
                result["issues"].append(f"HTML解析失败: {{str(e)[:100]}}")

        else:
            result["issues"].append("不是有效的SVG或HTML代码片段")

    except Exception as e:
        result["issues"].append(f"验证失败: {{str(e)[:100]}}")

    return result


def validate_code_snippets(items: list, user_goal: str) -> dict:
    '''验证所有代码片段字段'''
    results = {{
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "svg_count": 0,
        "html_count": 0,
        "malicious_count": 0,
        "details": []
    }}

    code_keywords = ["svg", "html", "code", "snippet", "content", "description"]

    for item in items:
        for key, value in item.items():
            if not isinstance(value, str):
                continue

            # 检查是否可能是代码片段
            is_code_field = any(kw in key.lower() for kw in code_keywords)
            starts_with_tag = value.strip().startswith("<")

            if is_code_field or starts_with_tag:
                validation = validate_svg_html_field(value, key, user_goal)
                results["details"].append(validation)
                results["total"] += 1

                if validation["valid"]:
                    results["valid"] += 1
                else:
                    results["invalid"] += 1

                if validation["is_svg"]:
                    results["svg_count"] += 1
                if validation["is_html"]:
                    results["html_count"] += 1
                if validation["has_malicious_tags"]:
                    results["malicious_count"] += 1

    return results


# 主程序
user_goal = "{user_goal_placeholder}"
items = {sample_data_placeholder}
results = validate_code_snippets(items, user_goal)

print(json.dumps(results, ensure_ascii=False, indent=2))
"""


# ----------------------------------------------------------------------------
# 基础验证模板（原有）
# ----------------------------------------------------------------------------

IMAGE_VALIDATION_TEMPLATE = """
import json
from urllib.parse import urlparse

# 数据定义
items = {sample_data_placeholder}

def is_valid_image_url(url: str) -> bool:
    '''检查图片 URL 格式有效性'''
    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def is_placeholder_image(url: str) -> bool:
    '''检测占位图'''
    url_lower = url.lower()
    placeholder_keywords = [
        'placeholder', 'default', 'no-image', 'no_image',
        'generic', 'sample', 'example', 'empty', 'missing',
        '占位', '默认', '空'
    ]
    return any(keyword in url_lower for keyword in placeholder_keywords)

def validate_images(items: list) -> dict:
    '''验证图片质量'''
    stats = {{"total": 0, "valid": 0, "placeholder": 0, "invalid": 0}}

    for item in items:
        for key, value in item.items():
            if 'image' in key.lower() or 'img' in key.lower() or 'picture' in key.lower() or 'photo' in key.lower():
                if isinstance(value, str) and value:
                    stats["total"] += 1
                    if is_valid_image_url(value):
                        if is_placeholder_image(value):
                            stats["placeholder"] += 1
                        else:
                            stats["valid"] += 1
                    else:
                        stats["invalid"] += 1

    return stats

# 执行验证
result = validate_images(items)
print(json.dumps(result, ensure_ascii=False, indent=2))
"""


FORMAT_VALIDATION_TEMPLATE = """
import json
import re
from datetime import datetime
from urllib.parse import urlparse

# 数据定义
items = {sample_data_placeholder}

def validate_date(date_str: str) -> bool:
    '''验证日期格式'''
    date_patterns = [
        r'^\\d{{4}}-\\d{{2}}-\\d{{2}}$',           # YYYY-MM-DD
        r'^\\d{{4}}/\\d{{2}}/\\d{{2}}$',           # YYYY/MM/DD
        r'^\\d{{4}}年\\d{{1,2}}月\\d{{1,2}}日$',  # 中文日期
        r'^\\d{{4}}-\\d{{2}}-\\d{{2}}T\\d{{2}}:\\d{{2}}:\\d{{2}}',  # ISO 8601
    ]
    return any(re.match(p, str(date_str).strip()) for p in date_patterns)

def validate_price(price_str: str) -> bool:
    '''验证价格格式'''
    # 匹配: $99.99, 99.99元, ¥99, 99 USD 等
    pattern = r'^[¥$€£]?\s*\\d+(\\.\\d+)?\\s*[元美元EURGBPUSD]?$'
    return bool(re.match(pattern, str(price_str).strip()))

def validate_url(url_str: str) -> bool:
    '''验证 URL 格式'''
    try:
        result = urlparse(url_str)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False

def validate_formats(items: list) -> dict:
    '''验证数据格式'''
    stats = {{
        "date_valid": 0, "date_total": 0,
        "price_valid": 0, "price_total": 0,
        "url_valid": 0, "url_total": 0
    }}

    for item in items:
        for key, value in item.items():
            if not isinstance(value, str):
                continue

            if 'date' in key.lower() or 'time' in key.lower() or '时间' in key or '日期' in key:
                stats["date_total"] += 1
                if validate_date(value):
                    stats["date_valid"] += 1

            elif 'price' in key.lower() or '成本' in key or '价格' in key or '费用' in key:
                stats["price_total"] += 1
                if validate_price(value):
                    stats["price_valid"] += 1

            elif 'url' in key.lower() or 'link' in key.lower() or 'href' in key.lower() or '链接' in key:
                stats["url_total"] += 1
                if validate_url(value):
                    stats["url_valid"] += 1

    return stats

# 执行验证
result = validate_formats(items)
print(json.dumps(result, ensure_ascii=False, indent=2))
"""


CONTENT_VALIDATION_TEMPLATE = """
import json

# 数据定义
items = {sample_data_placeholder}

def validate_content(items: list) -> dict:
    '''验证内容质量'''
    stats = {{
        "empty_fields": 0,
        "duplicates": 0,
        "invalid_content": 0,
        "total_items": len(items)
    }}

    seen = set()
    null_values = ["n/a", "null", "none", "待补充", "暂无", "tbd", "-", "—",
                   "undefined", "unknown", "?", "无"]

    for item in items:
        # 检查重复（基于标题或链接）
        identifier = (
            item.get("title") or
            item.get("url") or
            item.get("link") or
            str(item.get("id", ""))
        )
        if identifier and identifier in seen:
            stats["duplicates"] += 1
        seen.add(identifier)

        # 检查空字段和无意义内容
        for value in item.values():
            if value is None or value == "":
                stats["empty_fields"] += 1
            elif isinstance(value, str):
                val_stripped = value.strip()
                if not val_stripped:
                    stats["empty_fields"] += 1
                elif val_stripped.lower() in null_values:
                    stats["invalid_content"] += 1

    return stats

# 执行验证
result = validate_content(items)
print(json.dumps(result, ensure_ascii=False, indent=2))
"""


COMBINED_VALIDATION_TEMPLATE = """
import json
import re
from urllib.parse import urlparse

# 数据定义
items = {sample_data_placeholder}

def validate_images(items: list) -> dict:
    '''验证图片质量'''
    stats = {{"total": 0, "valid": 0, "placeholder": 0, "invalid": 0}}
    placeholder_keywords = [
        'placeholder', 'default', 'no-image', 'no_image',
        'generic', 'sample', 'example', 'empty', 'missing',
        '占位', '默认'
    ]

    for item in items:
        for key, value in item.items():
            if 'image' in key.lower() or 'img' in key.lower():
                if isinstance(value, str) and value:
                    stats["total"] += 1
                    try:
                        result = urlparse(value)
                        if all([result.scheme in ['http', 'https'], result.netloc]):
                            if any(kw in value.lower() for kw in placeholder_keywords):
                                stats["placeholder"] += 1
                            else:
                                stats["valid"] += 1
                        else:
                            stats["invalid"] += 1
                    except:
                        stats["invalid"] += 1

    return stats

def validate_formats(items: list) -> dict:
    '''验证数据格式'''
    stats = {{
        "date_valid": 0, "date_total": 0,
        "price_valid": 0, "price_total": 0,
        "url_valid": 0, "url_total": 0
    }}

    date_patterns = [r'^\\d{{4}}-\\d{{2}}-\\d{{2}}$', r'^\\d{{4}}/\\d{{2}}/\\d{{2}}$']
    price_pattern = r'^[¥$€£]?\s*\\d+(\\.\\d+)?\s*[元美元EURGBPUSD]?$'

    for item in items:
        for key, value in item.items():
            if not isinstance(value, str):
                continue

            if 'date' in key.lower() or '时间' in key or '日期' in key:
                stats["date_total"] += 1
                if any(re.match(p, value.strip()) for p in date_patterns):
                    stats["date_valid"] += 1
            elif 'price' in key.lower() or '价格' in key:
                stats["price_total"] += 1
                if re.match(price_pattern, value.strip()):
                    stats["price_valid"] += 1
            elif 'url' in key.lower() or 'link' in key.lower() or '链接' in key:
                stats["url_total"] += 1
                try:
                    result = urlparse(value)
                    if all([result.scheme in ['http', 'https'], result.netloc]):
                        stats["url_valid"] += 1
                except:
                    pass

    return stats

def validate_content(items: list) -> dict:
    '''验证内容质量'''
    stats = {{
        "empty_fields": 0,
        "duplicates": 0,
        "invalid_content": 0,
        "total_items": len(items)
    }}

    seen = set()
    null_values = ["n/a", "null", "none", "待补充", "暂无", "tbd", "-"]

    for item in items:
        identifier = item.get("title") or item.get("url") or str(item.get("id", ""))
        if identifier and identifier in seen:
            stats["duplicates"] += 1
        seen.add(identifier)

        for value in item.values():
            if value is None or value == "":
                stats["empty_fields"] += 1
            elif isinstance(value, str) and value.strip().lower() in null_values:
                stats["invalid_content"] += 1

    return stats

def calculate_quality_score(items: list, image_stats: dict, format_stats: dict, content_stats: dict) -> dict:
    '''计算综合质量分数'''
    total_items = len(items)
    if total_items == 0:
        return {{"relevance": 0, "completeness": 0, "accuracy": 0, "content_quality": 0, "overall_score": 0}}

    # relevance: 基于数据丰富度
    avg_fields = sum(len([v for v in item.values() if v not in [None, ""]]) for item in items) / total_items
    relevance = min(1.0, avg_fields / 5)

    # completeness: 基于非空字段比例
    total_fields = sum(len(item) for item in items)
    filled_fields = total_fields - content_stats.get("empty_fields", 0)
    completeness = filled_fields / total_fields if total_fields > 0 else 0

    # accuracy: 基于格式验证通过率
    format_valid = 0
    format_total = 0
    for k in ["date_total", "price_total", "url_total"]:
        if format_stats.get(k, 0) > 0:
            format_total += format_stats[k]
            valid_key = k.replace("_total", "_valid")
            format_valid += format_stats.get(valid_key, 0)
    accuracy = format_valid / format_total if format_total > 0 else 0.8

    # content_quality
    content_quality = 1.0
    if content_stats.get("total_items", 0) > 0:
        dup_ratio = content_stats.get("duplicates", 0) / content_stats["total_items"]
        invalid_ratio = content_stats.get("invalid_content", 0) / max(content_stats["total_items"] * 3, 1)
        content_quality = max(0, 1.0 - dup_ratio - invalid_ratio)

    overall_score = (relevance * 0.4 + completeness * 0.3 + accuracy * 0.2 + content_quality * 0.1)

    return {{
        "relevance": round(relevance, 2),
        "completeness": round(completeness, 2),
        "accuracy": round(accuracy, 2),
        "content_quality": round(content_quality, 2),
        "overall_score": round(overall_score, 2)
    }}

# 主程序
if __name__ == "__main__":
    image_stats = validate_images(items)
    format_stats = validate_formats(items)
    content_stats = validate_content(items)
    scores = calculate_quality_score(items, image_stats, format_stats, content_stats)

    # 收集问题
    issues = []
    if scores["completeness"] < 0.7:
        issues.append(f"数据完整性较低: {{scores['completeness']}}")
    if image_stats.get("placeholder", 0) > 0:
        issues.append(f"发现占位图: {{image_stats['placeholder']}} 个")
    if content_stats.get("duplicates", 0) > 0:
        issues.append(f"发现重复记录: {{content_stats['duplicates']}} 条")

    result = {{
        **scores,
        "image_stats": image_stats,
        "format_stats": format_stats,
        "content_stats": content_stats,
        "issues": issues,
        "suggestions": []
    }}

    print(json.dumps(result, ensure_ascii=False, indent=2))
"""


# ============================================================================
# 工具函数
# ============================================================================

def get_validator_code_template(validator_type: str) -> str:
    """获取验证代码模板

    Args:
        validator_type: 验证器类型
            - "image": 图片验证（基础）
            - "image_deep": 图片深度验证（PIL）
            - "image_clip": 图片 CLIP 验证（图文匹配）
            - "format": 格式验证
            - "content": 内容验证
            - "combined": 综合验证（包含所有类型）
            - "pdf": PDF 深度验证
            - "video": 视频验证
            - "svg_html": SVG/HTML 代码片段验证

    Returns:
        验证代码模板字符串
    """
    templates = {
        "image": IMAGE_VALIDATION_TEMPLATE,
        "image_deep": IMAGE_DEEP_VALIDATION_TEMPLATE,
        "image_clip": IMAGE_CLIP_VALIDATION_TEMPLATE,
        "format": FORMAT_VALIDATION_TEMPLATE,
        "content": CONTENT_VALIDATION_TEMPLATE,
        "combined": COMBINED_VALIDATION_TEMPLATE,
        "pdf": PDF_DEEP_VALIDATION_TEMPLATE,
        "video": VIDEO_DEEP_VALIDATION_TEMPLATE,
        "svg_html": SVG_HTML_VALIDATION_TEMPLATE,
    }
    return templates.get(validator_type, COMBINED_VALIDATION_TEMPLATE)


def get_deep_validation_template(data_type: str) -> str:
    """获取深度验证模板

    Args:
        data_type: 数据类型
            - "image": 返回 IMAGE_DEEP_VALIDATION_TEMPLATE
            - "pdf": 返回 PDF_DEEP_VALIDATION_TEMPLATE
            - "video": 返回 VIDEO_DEEP_VALIDATION_TEMPLATE

    Returns:
        深度验证代码模板字符串
    """
    template_map = {
        "image": IMAGE_DEEP_VALIDATION_TEMPLATE,
        "pdf": PDF_DEEP_VALIDATION_TEMPLATE,
        "video": VIDEO_DEEP_VALIDATION_TEMPLATE,
    }
    return template_map.get(data_type, IMAGE_DEEP_VALIDATION_TEMPLATE)


def prepare_validator_code(template: str, sample_data: List[Dict[str, Any]]) -> str:
    """准备可执行的验证代码

    将模板中的 {sample_data_placeholder} 替换为实际数据。

    Args:
        template: 验证代码模板
        sample_data: 采样数据

    Returns:
        可执行的 Python 代码
    """
    sample_data_json = json.dumps(sample_data, ensure_ascii=False)
    return template.replace("{sample_data_placeholder}", sample_data_json)


def extract_validation_rules(user_goal: str) -> Dict[str, Any]:
    """从用户需求中提取验证规则

    Args:
        user_goal: 用户需求描述

    Returns:
        验证规则字典

    示例:
        >>> extract_validation_rules("提取高清图片，不能有重复")
        {"validate_images": True, "image_quality": "high", "check_duplicates": True}
    """
    rules: Dict[str, Any] = {
        "check_duplicates": True,
        "validate_urls": True,
    }

    goal_lower = user_goal.lower()

    # 图片相关
    if "图片" in goal_lower or "image" in goal_lower or "img" in goal_lower:
        rules["validate_images"] = True
        if "高清" in goal_lower or "high" in goal_lower or "hd" in goal_lower:
            rules["image_quality"] = "high"

    # 价格相关
    if "价格" in goal_lower or "price" in goal_lower or "成本" in goal_lower:
        rules["validate_price"] = True

    # 日期相关
    if "日期" in goal_lower or "date" in goal_lower or "时间" in goal_lower:
        rules["validate_date"] = True

    # 去重相关
    if "不重复" in goal_lower or "unique" in goal_lower or "去重" in goal_lower:
        rules["check_duplicates"] = True

    # 链接相关
    if "链接" in goal_lower or "url" in goal_lower or "link" in goal_lower:
        rules["validate_urls"] = True

    return rules


# ============================================================================
# 快速验证函数（直接在 Python 中执行，无需沙箱）
# ============================================================================

def quick_validate_image_url(url: str) -> Dict[str, bool]:
    """快速验证单个图片 URL

    Args:
        url: 图片 URL

    Returns:
        {"valid": bool, "is_placeholder": bool}
    """
    from urllib.parse import urlparse

    placeholder_keywords = [
        'placeholder', 'default', 'no-image', 'no_image',
        'generic', 'sample', 'example', 'empty', 'missing',
    ]

    try:
        result = urlparse(url)
        is_valid = all([result.scheme in ['http', 'https'], result.netloc])
        is_placeholder = any(kw in url.lower() for kw in placeholder_keywords)
        return {"valid": is_valid, "is_placeholder": is_placeholder}
    except:
        return {"valid": False, "is_placeholder": False}


def quick_validate_url(url: str) -> bool:
    """快速验证 URL 格式

    Args:
        url: URL 字符串

    Returns:
        是否为有效 URL
    """
    from urllib.parse import urlparse

    try:
        result = urlparse(url)
        return all([result.scheme in ['http', 'https'], result.netloc])
    except:
        return False


def quick_detect_duplicates(items: List[Dict[str, Any]]) -> int:
    """快速检测重复记录数量

    Args:
        items: 数据列表

    Returns:
        重复记录数量
    """
    seen = set()
    duplicates = 0

    for item in items:
        identifier = (
            item.get("title") or
            item.get("url") or
            item.get("link") or
            str(item.get("id", ""))
        )
        if identifier and identifier in seen:
            duplicates += 1
        seen.add(identifier)

    return duplicates


def quick_fallback_quality_check(sample_data: List[Dict[str, Any]]) -> float:
    """快速降级质量检查

    当 LLM 评估失败时使用此函数。

    Args:
        sample_data: 采样数据

    Returns:
        质量分数 (0.0 - 1.0)
    """
    if not sample_data:
        return 0.0

    total = len(sample_data)
    issues = 0
    null_values = ["n/a", "null", "none", "待补充", "暂无", "tbd", "-", "—", "undefined"]

    for item in sample_data:
        if not isinstance(item, dict):
            issues += 1
            continue

        # 检查是否有值
        if not item or all(v is None or v == "" for v in item.values()):
            issues += 1
            continue

        # 检查关键字段
        for key in ["title", "name", "url", "link", "href"]:
            if key in item:
                val = str(item.get(key, "")).strip()
                if not val:
                    issues += 1
                elif val.lower() in null_values:
                    issues += 1

    valid_ratio = (total - min(issues, total)) / total
    return round(valid_ratio, 2)


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 基础验证
    "get_validator_code_template",
    "prepare_validator_code",
    "extract_validation_rules",
    "quick_validate_image_url",
    "quick_validate_url",
    "quick_detect_duplicates",
    "quick_fallback_quality_check",
    # 深度验证
    "get_deep_validation_template",
    "IMAGE_DEEP_VALIDATION_TEMPLATE",
    "IMAGE_CLIP_VALIDATION_TEMPLATE",
    "PDF_DEEP_VALIDATION_TEMPLATE",
    "VIDEO_DEEP_VALIDATION_TEMPLATE",
    # 代码片段验证
    "SVG_HTML_VALIDATION_TEMPLATE",
]
