"""
Base Skill - Agent技能基类

定义所有技能的基础接口和元数据。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class SkillCategory(Enum):
    """技能类别"""
    BROWSER = "browser"  # 浏览器操作
    EXTRACTION = "extraction"  # 数据提取
    ANTI_DETECTION = "anti_detection"  # 反检测
    INTERACTION = "interaction"  # 页面交互
    VALIDATION = "validation"  # 数据验证
    UTILITY = "utility"  # 工具类


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str  # 技能名称
    category: SkillCategory  # 所属类别
    description: str  # 描述
    version: str = "1.0.0"  # 版本
    author: str = "System"  # 作者
    tags: List[str] = field(default_factory=list)  # 标签
    dependencies: List[str] = field(default_factory=list)  # 依赖的其他技能
    applicable_websites: List[str] = field(default_factory=list)  # 适用网站类型
    success_rate: float = 0.0  # 历史成功率
    usage_count: int = 0  # 使用次数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "dependencies": self.dependencies,
            "applicable_websites": self.applicable_websites,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
        }


class BaseSkill(ABC):
    """
    Agent技能基类

    所有技能都继承自这个基类，实现统一的接口。
    """

    def __init__(self):
        self.metadata: SkillMetadata = self._define_metadata()
        self._code_template: str = self._generate_code_template()

    @abstractmethod
    def _define_metadata(self) -> SkillMetadata:
        """定义技能的元数据"""
        pass

    @abstractmethod
    def _generate_code_template(self) -> str:
        """生成技能的代码模板"""
        pass

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """
        获取技能需要的参数

        Returns:
            参数定义，包含参数名、类型、默认值、描述
        """
        pass

    def get_code_template(self, **kwargs) -> str:
        """
        获取技能的代码实现

        Args:
            **kwargs: 技能参数

        Returns:
            Python代码字符串
        """
        code = self._code_template

        # 替换参数占位符
        for key, value in kwargs.items():
            placeholder = f"{{{key}}}"
            code = code.replace(placeholder, str(value))

        return code

    def is_applicable(self, context: Dict[str, Any]) -> bool:
        """
        判断技能是否适用于当前上下文

        Args:
            context: 上下文信息，包含网站类型、用户需求等

        Returns:
            是否适用
        """
        # 检查适用网站类型
        if context.get("website_type"):
            if context["website_type"] not in self.metadata.applicable_websites:
                # 如果技能指定了适用网站，检查是否匹配
                if self.metadata.applicable_websites:  # 非空列表
                    return False

        return True

    def estimate_success_probability(self, context: Dict[str, Any]) -> float:
        """
        估算技能在当前上下文下的成功概率

        Args:
            context: 上下文信息

        Returns:
            成功概率 0-1
        """
        base_probability = self.metadata.success_rate

        # 如果技能适用于当前上下文，提升概率
        if self.is_applicable(context):
            return min(1.0, base_probability + 0.2)

        return base_probability

    def record_usage(self, success: bool):
        """
        记录技能使用情况

        Args:
            success: 使用是否成功
        """
        self.metadata.usage_count += 1

        # 更新成功率（移动平均）
        alpha = 0.1  # 学习率
        if self.metadata.usage_count == 1:
            self.metadata.success_rate = 1.0 if success else 0.0
        else:
            current = self.metadata.success_rate
            target = 1.0 if success else 0.0
            self.metadata.success_rate = alpha * target + (1 - alpha) * current

    def __repr__(self) -> str:
        return f"Skill({self.metadata.name}, v{self.metadata.version}, category={self.metadata.category.value})"
