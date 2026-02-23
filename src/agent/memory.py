"""
Memento模式：失败经验积累和复用

基于2026年优秀Agent设计模式，实现失败经验的系统化存储和检索，
避免Agent重复犯错。

参考:
- Reflexion: Act-Reflect-Remember 三阶段循环
- Memento模式: 设计模式中的备忘录模式
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib
import json


class FailureMemory:
    """
    失败经验存储

    功能:
    - 存储结构化失败记录
    - 按失败类型分组
    - 检索相似失败
    - 提供修复建议
    """

    def __init__(self):
        self.failures: List[Dict[str, Any]] = []
        self.patterns: Dict[str, List[str]] = {}  # 按失败类型分组的建议

    def add_failure(
        self,
        failure_type: str,
        root_cause: str,
        suggested_fix: str,
        code_signature: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加失败记录

        Args:
            failure_type: 失败类型 (selector_error/js_rendering/timeout等)
            root_cause: 根本原因分析
            suggested_fix: 建议的修复方案
            code_signature: 代码签名（用于检测重复）
            context: 额外上下文信息
        """
        record = {
            "failure_type": failure_type,
            "root_cause": root_cause,
            "suggested_fix": suggested_fix,
            "code_signature": code_signature,
            "context": context or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.failures.append(record)

        # 按类型分组存储建议
        if failure_type not in self.patterns:
            self.patterns[failure_type] = []
        self.patterns[failure_type].append(suggested_fix)

    def get_recent_failures(self, n: int = 3) -> List[Dict[str, Any]]:
        """获取最近N次失败记录"""
        return self.failures[-n:]

    def get_failures_by_type(self, failure_type: str) -> List[Dict[str, Any]]:
        """按类型获取失败记录"""
        return [f for f in self.failures if f["failure_type"] == failure_type]

    def get_suggested_fixes(self, failure_type: str) -> List[str]:
        """获取特定类型的所有修复建议"""
        return self.patterns.get(failure_type, [])

    def has_similar_failure(
        self,
        failure_type: str,
        root_cause: str,
        similarity_threshold: int = 50,
    ) -> bool:
        """
        检查是否有相似的失败记录

        Args:
            failure_type: 失败类型
            root_cause: 根本原因
            similarity_threshold: 相似度阈值（字符数）

        Returns:
            是否存在相似失败
        """
        for failure in self.failures:
            if failure["failure_type"] == failure_type:
                # 检查根本原因的前N个字符是否相同
                if (
                    failure["root_cause"][:similarity_threshold]
                    == root_cause[:similarity_threshold]
                ):
                    return True
        return False

    def get_summary(self) -> Dict[str, Any]:
        """获取失败记忆的统计摘要"""
        if not self.failures:
            return {"total": 0, "by_type": {}}

        by_type: Dict[str, int] = {}
        for failure in self.failures:
            ftype = failure["failure_type"]
            by_type[ftype] = by_type.get(ftype, 0) + 1

        return {
            "total": len(self.failures),
            "by_type": by_type,
            "latest": self.failures[-1] if self.failures else None,
        }


def generate_code_signature(code: str) -> str:
    """
    生成代码签名（用于检测重复尝试）

    算法:
    1. 移除空白行和注释
    2. 计算MD5哈希
    3. 返回前8位

    Args:
        code: Python代码字符串

    Returns:
        8位十六进制签名
    """
    # 移除注释和空白行
    lines = []
    for line in code.split("\n"):
        stripped = line.strip()
        # 跳过空行和注释
        if stripped and not stripped.startswith("#"):
            lines.append(stripped)

    cleaned = "\n".join(lines)
    return hashlib.md5(cleaned.encode()).hexdigest()[:8]


def is_similar_failure(
    f1: Dict[str, Any], f2: Dict[str, Any], threshold: int = 50
) -> bool:
    """
    判断两次失败是否相似

    Args:
        f1: 失败记录1
        f2: 失败记录2
        threshold: 相似度阈值

    Returns:
        是否相似
    """
    return (
        f1.get("failure_type") == f2.get("failure_type")
        and (f1.get("root_cause") or "")[:threshold]
        == (f2.get("root_cause") or "")[:threshold]
    )


def is_duplicate_attempt(
    code_signature: str, previous_signatures: List[str]
) -> bool:
    """
    检查是否是重复的代码尝试

    Args:
        code_signature: 当前代码签名
        previous_signatures: 之前的所有代码签名

    Returns:
        是否重复
    """
    return code_signature in previous_signatures


# ===== 失败类型常量 =====

class FailureType:
    """失败类型常量"""

    SELECTOR_ERROR = "selector_error"      # CSS选择器不匹配
    JS_RENDERING = "js_rendering"          # JavaScript内容未渲染
    TIMEOUT = "timeout"                    # 执行超时
    RATE_LIMIT = "rate_limit"              # 被速率限制
    EMPTY_RESULT = "empty_result"          # 执行成功但无数据
    SYNTAX_ERROR = "syntax_error"          # 代码语法错误
    NETWORK_ERROR = "network_error"        # 网络错误
    BLOCKED = "blocked"                    # 被反爬虫阻止
    UNKNOWN = "unknown"                    # 未知错误


def parse_reflection(llm_output: str) -> Dict[str, str]:
    """
    解析LLM输出的反思文本

    尝试从LLM输出中提取结构化的反思信息。

    Args:
        llm_output: LLM的原始输出

    Returns:
        包含 failure_type, root_cause, suggested_fix, avoid_repeat 的字典
    """
    result = {
        "failure_type": FailureType.UNKNOWN,
        "root_cause": "",
        "suggested_fix": "",
        "avoid_repeat": "",
        "text": llm_output,
    }

    # 尝试解析JSON格式
    try:
        # 查找JSON代码块
        if "```json" in llm_output:
            json_start = llm_output.find("```json") + 7
            json_end = llm_output.find("```", json_start)
            json_str = llm_output[json_start:json_end].strip()
        elif "```" in llm_output:
            json_start = llm_output.find("```") + 3
            json_end = llm_output.find("```", json_start)
            json_str = llm_output[json_start:json_end].strip()
        else:
            # 尝试直接解析整个输出
            json_str = llm_output.strip()

        parsed = json.loads(json_str)
        result.update(parsed)
    except (json.JSONDecodeError, ValueError):
        # JSON解析失败，使用文本解析
        lines = llm_output.split("\n")
        for i, line in enumerate(lines):
            if "失败类型" in line or "failure_type" in line:
                if i + 1 < len(lines):
                    result["failure_type"] = lines[i + 1].strip(" -*:")
            elif "根本原因" in line or "root_cause" in line:
                if i + 1 < len(lines):
                    result["root_cause"] = lines[i + 1].strip(" -*:")
            elif "建议" in line or "suggested_fix" in line:
                if i + 1 < len(lines):
                    result["suggested_fix"] = lines[i + 1].strip(" -:")

    return result
