"""
Test Cases - 10个能力检测需求定义

定义10个不同类型的网站数据采集测试用例，用于检测 Recon Agent 的能力边界。
"""

from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field

# Literal 兼容性处理
try:
    from typing import Literal
except ImportError:
    # Python 3.8 兼容
    def Literal(*args):
        return Union[tuple(args)]


@dataclass
class TestCase:
    """测试用例定义"""
    id: int
    name: str
    url: str
    user_goal: str
    data_types: List[str]  # 预期提取的数据类型
    expected_fields: List[str]  # 预期字段
    difficulty: Literal[1, 2, 3, 4, 5]  # 难度等级
    phase: Literal[1, 2, 3, 4]  # 测试阶段
    min_quality_score: float = 0.6  # 最低质量分数
    min_data_count: int = 1  # 最少数据条数
    timeout_seconds: int = 300  # 超时时间
    description: str = ""  # 详细描述
    challenges: List[str] = field(default_factory=list)  # 预期挑战
    capabilities: List[str] = field(default_factory=list)  # 需要的能力

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "user_goal": self.user_goal,
            "data_types": self.data_types,
            "expected_fields": self.expected_fields,
            "difficulty": self.difficulty,
            "phase": self.phase,
            "min_quality_score": self.min_quality_score,
            "min_data_count": self.min_data_count,
            "timeout_seconds": self.timeout_seconds,
            "description": self.description,
            "challenges": self.challenges,
            "capabilities": self.capabilities,
        }


# ============================================================================
# 10个测试用例定义
# ============================================================================

TEST_CASES: List[TestCase] = [
    # Phase 1 - 基础验证（容易）
    TestCase(
        id=5,
        name="arXiv学术论文",
        url="https://arxiv.org/list/cs/recent",
        user_goal="提取AI/CS论文列表，包括标题、作者、摘要、PDF链接",
        data_types=["text", "url"],
        expected_fields=["title", "authors", "abstract", "pdf_url"],
        difficulty=1,
        phase=1,
        min_quality_score=0.7,
        min_data_count=5,
        description="学术论文站点，静态HTML，结构清晰",
        challenges=["HTML解析"],
        capabilities=["basic_html_parsing", "pdf_link_extraction"],
    ),

    TestCase(
        id=9,
        name="Medium博客文章",
        url="https://medium.com",
        user_goal="提取博客文章列表，包括标题、作者、摘要、封面图片URL",
        data_types=["text", "image_url"],
        expected_fields=["title", "author", "excerpt", "cover_image"],
        difficulty=2,
        phase=1,
        min_quality_score=0.6,
        min_data_count=3,
        description="博客/CMS站点，JS渲染，嵌套HTML",
        challenges=["js_rendering", "nested_html"],
        capabilities=["js_rendering", "nested_html_extraction", "image_url_extraction"],
    ),

    # Phase 2 - 扩展验证（中等）
    TestCase(
        id=2,
        name="TechCrunch新闻文章",
        url="https://techcrunch.com",
        user_goal="提取科技新闻文章，包括标题、正文HTML、图片、视频链接",
        data_types=["html", "image_url", "video_url"],
        expected_fields=["title", "content_html", "images", "videos"],
        difficulty=2,
        phase=2,
        min_quality_score=0.6,
        min_data_count=3,
        description="科技新闻站点，富文本内容，嵌入视频",
        challenges=["rich_text", "embedded_video", "multiple_image_sources"],
        capabilities=["rich_html_extraction", "embedded_media_detection"],
    ),

    TestCase(
        id=7,
        name="AllRecipes菜谱",
        url="https://www.allrecipes.com/recipes/17562/dinner/main-dish/",
        user_goal="提取菜谱列表，包括名称、配料、步骤HTML、成品图片",
        data_types=["html", "image_url"],
        expected_fields=["name", "ingredients", "steps_html", "image"],
        difficulty=2,
        phase=2,
        min_quality_score=0.6,
        min_data_count=3,
        description="菜谱网站，混合数据类型（文本+HTML+图片）",
        challenges=["structured_data", "mixed_content_types"],
        capabilities=["structured_data_extraction", "html_content_extraction"],
    ),

    TestCase(
        id=10,
        name="英国政府招标公告",
        url="https://www.find-tender.service.gov.uk",
        user_goal="提取招标公告，包括标题、PDF链接、金额HTML表格",
        data_types=["html", "pdf_url", "table"],
        expected_fields=["title", "pdf_url", "amount_table"],
        difficulty=2,
        phase=2,
        min_quality_score=0.6,
        min_data_count=2,
        description="政府站点，HTML表格+PDF链接",
        challenges=["html_table_parsing", "pdf_detection"],
        capabilities=["table_extraction", "pdf_link_extraction"],
    ),

    # Phase 3 - 增强功能（困难）
    TestCase(
        id=4,
        name="Indeed招聘职位",
        url="https://www.indeed.com/jobs?q=software+engineer",
        user_goal="提取招聘职位，包括职位名称、薪资、公司Logo图片、职位描述HTML",
        data_types=["text", "image_url", "html"],
        expected_fields=["job_title", "salary", "company_logo", "jd_html"],
        difficulty=3,
        phase=3,
        min_quality_score=0.6,
        min_data_count=3,
        description="招聘网站，可能有速率限制",
        challenges=["rate_limiting", "company_logo_extraction"],
        capabilities=["rate_limit_handling", "image_extraction"],
    ),

    TestCase(
        id=3,
        name="Datawrapper数据图表",
        url="https://www.datawrapper.de",
        user_goal="提取数据可视化图表的SVG代码",
        data_types=["svg_code"],
        expected_fields=["chart_title", "svg_code"],
        difficulty=3,
        phase=3,
        min_quality_score=0.5,
        min_data_count=1,
        description="数据可视化站点，图表可能通过API加载",
        challenges=["svg_extraction", "api_detection", "dynamic_content"],
        capabilities=["svg_code_extraction", "dynamic_content_handling"],
    ),

    TestCase(
        id=6,
        name="Zillow房地产楼盘",
        url="https://www.zillow.com/",
        user_goal="提取房产信息，包括价格、户型图SVG/PDF链接",
        data_types=["text", "svg", "pdf_url"],
        expected_fields=["price", "floor_plan_svg", "floor_plan_pdf"],
        difficulty=4,
        phase=3,
        min_quality_score=0.5,
        min_data_count=2,
        description="房地产站点，懒加载，PDF下载",
        challenges=["lazy_loading", "pdf_download_link", "svg_extraction"],
        capabilities=["lazy_loading_detection", "pdf_link_extraction", "svg_extraction"],
    ),

    # Phase 4 - 高级挑战（极难）
    TestCase(
        id=1,
        name="Amazon电商产品",
        url="https://www.amazon.com/s?k=smartphone",
        user_goal="提取商品列表，包括名称、价格、规格、主图URL、规格PDF链接",
        data_types=["text", "image_url", "pdf_url"],
        expected_fields=["name", "price", "specs", "image_url", "pdf_url"],
        difficulty=5,
        phase=4,
        min_quality_score=0.5,
        min_data_count=1,
        description="电商站点，Cloudflare反爬保护",
        challenges=["cloudflare_protection", "anti_scraping", "dynamic_content"],
        capabilities=["anti_bot_handling", "dynamic_content_extraction"],
    ),

    TestCase(
        id=8,
        name="Yahoo Finance股票图表",
        url="https://finance.yahoo.com/quote/AAPL/chart",
        user_goal="提取股票K线图SVG代码、实时价格、成交量",
        data_types=["svg", "text"],
        expected_fields=["chart_svg", "price", "volume"],
        difficulty=5,
        phase=4,
        min_quality_score=0.4,
        min_data_count=1,
        description="金融站点，WebSocket，Canvas绘制",
        challenges=["websocket", "canvas_rendering", "real_time_data"],
        capabilities=["websocket_handling", "canvas_extraction", "real_time_data"],
    ),
]


# ============================================================================
# 测试分组
# ============================================================================

def get_test_cases_by_phase(phase: int) -> List[TestCase]:
    """获取指定阶段的测试用例（按难度排序）"""
    phase_cases = [tc for tc in TEST_CASES if tc.phase == phase]
    return sorted(phase_cases, key=lambda x: x.difficulty)


def get_test_case_by_id(case_id: int) -> Optional[TestCase]:
    """根据ID获取测试用例"""
    for tc in TEST_CASES:
        if tc.id == case_id:
            return tc
    return None


def get_all_test_cases_sorted() -> List[TestCase]:
    """获取所有测试用例（按阶段和难度排序）"""
    return sorted(TEST_CASES, key=lambda x: (x.phase, x.difficulty))


# ============================================================================
# 预期能力映射
# ============================================================================

CAPABILITY_MATRIX = {
    # 文本/HTML提取
    "text_extraction": {"supported": True, "stability": "high"},
    "html_extraction": {"supported": True, "stability": "high"},
    "basic_html_parsing": {"supported": True, "stability": "high"},

    # 图片相关
    "image_url_extraction": {"supported": True, "stability": "high"},
    "image_deep_validation": {"supported": True, "stability": "medium"},
    "company_logo_extraction": {"supported": True, "stability": "medium"},

    # PDF相关
    "pdf_link_extraction": {"supported": True, "stability": "medium"},
    "pdf_validation": {"supported": True, "stability": "medium"},

    # SVG相关
    "svg_extraction": {"supported": True, "stability": "high"},
    "svg_code_extraction": {"supported": True, "stability": "high"},

    # JS渲染
    "js_rendering": {"supported": True, "stability": "high"},
    "dynamic_content_handling": {"supported": True, "stability": "medium"},

    # 高级功能
    "lazy_loading_detection": {"supported": True, "stability": "medium"},
    "nested_html_extraction": {"supported": True, "stability": "high"},
    "rich_html_extraction": {"supported": True, "stability": "high"},
    "table_extraction": {"supported": True, "stability": "medium"},

    # 未完全支持
    "rate_limit_handling": {"supported": False, "stability": "low"},
    "anti_bot_handling": {"supported": False, "stability": "low"},
    "websocket_handling": {"supported": False, "stability": "low"},
    "canvas_extraction": {"supported": False, "stability": "low"},
}


# ============================================================================
# 测试执行配置
# ============================================================================

TEST_CONFIG = {
    # 并发测试数
    "max_concurrent_tests": 1,

    # 每个测试的超时时间（秒）
    "default_timeout": 300,

    # 重试配置
    "max_retries": 1,
    "retry_delay": 5,

    # 输出配置
    "save_results": True,
    "results_dir": "tests/capability_test/results",
    "save_raw_data": True,

    # 质量阈值
    "quality_threshold": 0.6,

    # 详细日志
    "verbose": True,
}
