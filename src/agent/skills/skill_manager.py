"""
Skill Manager - 技能管理器

管理所有可用的技能，根据上下文推荐和组合技能。
"""

from typing import Dict, List, Any, Optional, Type
from pathlib import Path
import json

from .base_skill import BaseSkill, SkillCategory, SkillMetadata


class SkillManager:
    """
    技能管理器

    负责：
    1. 注册和发现技能
    2. 根据上下文推荐技能
    3. 组合多个技能
    4. 跟踪技能使用统计
    """

    def __init__(self, skills_dir: Optional[str] = None):
        """
        初始化技能管理器

        Args:
            skills_dir: 技能定义文件目录
        """
        self._skills: Dict[str, BaseSkill] = {}
        self._skills_by_category: Dict[SkillCategory, List[str]] = {
            category: [] for category in SkillCategory
        }
        self._skills_dir = skills_dir or "./src/agent/skills/skills"

        # 自动发现和加载技能
        self._discover_skills()

    def _discover_skills(self):
        """发现并加载所有技能"""
        skills_path = Path(self._skills_dir)

        if not skills_path.exists():
            return

        # 遍历技能目录
        for skill_file in skills_path.glob("*.py"):
            if skill_file.name.startswith("_"):
                continue

            try:
                # 动态导入技能模块
                module_name = f"src.agent.skills.skills.{skill_file.stem}"
                module = __import__(module_name, fromlist=[""])

                # 查找技能类
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and
                        issubclass(attr, BaseSkill) and
                        attr != BaseSkill):

                        # 实例化并注册技能
                        skill_instance = attr()
                        self.register_skill(skill_instance)

            except Exception as e:
                # 静默失败，继续加载其他技能
                pass

    def register_skill(self, skill: BaseSkill):
        """
        注册技能

        Args:
            skill: 技能实例
        """
        skill_name = skill.metadata.name
        self._skills[skill_name] = skill

        # 按类别索引
        category = skill.metadata.category
        self._skills_by_category[category].append(skill_name)

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """
        获取技能

        Args:
            name: 技能名称

        Returns:
            技能实例或None
        """
        return self._skills.get(name)

    def get_skills_by_category(self, category: SkillCategory) -> List[BaseSkill]:
        """
        获取指定类别的所有技能

        Args:
            category: 技能类别

        Returns:
            技能列表
        """
        skill_names = self._skills_by_category.get(category, [])
        return [self._skills[name] for name in skill_names if name in self._skills]

    def recommend_skills(
        self,
        context: Dict[str, Any],
        max_skills: int = 5,
    ) -> List[BaseSkill]:
        """
        根据上下文推荐技能

        Args:
            context: 上下文信息
            max_skills: 最多返回多少个技能

        Returns:
            推荐的技能列表，按成功概率排序
        """
        # 计算每个技能的适用性和成功概率
        skill_scores = []

        for skill in self._skills.values():
            if not skill.is_applicable(context):
                continue

            probability = skill.estimate_success_probability(context)
            skill_scores.append((skill, probability))

        # 按成功概率排序
        skill_scores.sort(key=lambda x: x[1], reverse=True)

        # 返回top N
        return [skill for skill, _ in skill_scores[:max_skills]]

    def get_skill_combination(
        self,
        context: Dict[str, Any],
        required_categories: List[SkillCategory] = None,
    ) -> Dict[str, BaseSkill]:
        """
        获取技能组合

        Args:
            context: 上下文信息
            required_categories: 需要的技能类别

        Returns:
            技能字典 {category: skill}
        """
        required_categories = required_categories or [
            SkillCategory.BROWSER,
            SkillCategory.EXTRACTION,
        ]

        combination = {}

        for category in required_categories:
            skills = self.get_skills_by_category(category)

            # 找到最适用的技能
            best_skill = None
            best_probability = 0.0

            for skill in skills:
                if skill.is_applicable(context):
                    probability = skill.estimate_success_probability(context)
                    if probability > best_probability:
                        best_probability = probability
                        best_skill = skill

            if best_skill:
                combination[category.value] = best_skill

        return combination

    def generate_code_with_skills(
        self,
        context: Dict[str, Any],
        skill_params: Dict[str, Dict[str, Any]] = None,
    ) -> str:
        """
        使用推荐技能生成代码

        Args:
            context: 上下文信息
            skill_params: 各技能的参数 {skill_name: {param: value}}

        Returns:
            组合后的Python代码
        """
        skill_params = skill_params or {}

        # 获取推荐的技能组合
        skills = self.recommend_skills(context)
        if not skills:
            return ""

        # 组合代码
        code_parts = []

        # 1. 导入部分
        imports = set()
        for skill in skills:
            # 从技能模板中提取import语句
            template = skill.get_code_template()
            for line in template.split("\n"):
                if line.strip().startswith("import ") or line.strip().startswith("from "):
                    imports.add(line.strip())

        code_parts.extend(sorted(imports))
        code_parts.append("")

        # 2. 主函数框架
        code_parts.append("def scrape_with_skills(url: str, context: dict) -> dict:")
        code_parts.append("    results = []")
        code_parts.append("    browser = None")
        code_parts.append("")
        code_parts.append("    try:")
        code_parts.append("        from playwright.sync_api import sync_playwright")
        code_parts.append("        with sync_playwright() as p:")
        code_parts.append("            browser = p.chromium.launch(headless=True)")
        code_parts.append("            page = browser.new_page()")
        code_parts.append("")
        code_parts.append("            page.goto(url, wait_until='domcontentloaded')")
        code_parts.append("")

        # 3. 技能代码（按优先级）
        for skill in skills:
            params = skill_params.get(skill.metadata.name, {})
            skill_code = skill.get_code_template(**params)

            # 缩进并添加到主函数
            indented = "\n".join(f"            {line}" for line in skill_code.split("\n"))
            code_parts.append(f"            # === {skill.metadata.name} ===")
            code_parts.append(indented)
            code_parts.append("")

        # 4. 清理和返回
        code_parts.append("    except Exception as e:")
        code_parts.append("        print(f'Error: {e}')")
        code_parts.append("    finally:")
        code_parts.append("        if browser:")
        code_parts.append("            browser.close()")
        code_parts.append("")
        code_parts.append("    return {'results': results}")

        return "\n".join(code_parts)

    def record_skill_usage(self, skill_name: str, success: bool):
        """
        记录技能使用

        Args:
            skill_name: 技能名称
            success: 使用是否成功
        """
        skill = self.get_skill(skill_name)
        if skill:
            skill.record_usage(success)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取技能使用统计

        Returns:
            统计信息
        """
        stats = {
            "total_skills": len(self._skills),
            "skills_by_category": {
                category.value: len(skills)
                for category, skills in self._skills_by_category.items()
            },
            "top_performers": [],
            "most_used": [],
        }

        # 按成功率排序
        by_success_rate = sorted(
            self._skills.values(),
            key=lambda s: s.metadata.success_rate,
            reverse=True
        )
        stats["top_performers"] = [
            {
                "name": s.metadata.name,
                "success_rate": s.metadata.success_rate,
                "usage_count": s.metadata.usage_count,
            }
            for s in by_success_rate[:5]
        ]

        # 按使用次数排序
        by_usage = sorted(
            self._skills.values(),
            key=lambda s: s.metadata.usage_count,
            reverse=True
        )
        stats["most_used"] = [
            {
                "name": s.metadata.name,
                "usage_count": s.metadata.usage_count,
                "success_rate": s.metadata.success_rate,
            }
            for s in by_usage[:5]
        ]

        return stats

    def export_skills_metadata(self, filepath: str = None):
        """
        导出技能元数据到JSON

        Args:
            filepath: 导出文件路径
        """
        if filepath is None:
            filepath = "./skills_metadata.json"

        metadata = {
            skill_name: skill.metadata.to_dict()
            for skill_name, skill in self._skills.items()
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def __repr__(self) -> str:
        return f"SkillManager(skills={len(self._skills)}, categories={list(self._skills_by_category.keys())})"
