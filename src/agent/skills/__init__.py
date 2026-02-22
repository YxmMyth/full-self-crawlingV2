"""
Agent Skills Package - 可复用的Agent技能模块

实现Agent Skills模式，将常用的爬虫逻辑封装为可复用的技能模块。
"""

from .base_skill import BaseSkill, SkillMetadata
from .skill_manager import SkillManager

# 导入可用的技能
from .skills.web_scraping import StealthBrowserSkill, PaginationSkill, FormInteractionSkill

__all__ = [
    "BaseSkill",
    "SkillMetadata",
    "SkillManager",
    "StealthBrowserSkill",
    "PaginationSkill",
    "FormInteractionSkill",
]
