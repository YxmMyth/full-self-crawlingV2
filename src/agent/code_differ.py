"""
Code Differ - 代码差异分析

比较两个版本的代码，找出差异部分，支持增量修复。
"""

import ast
import difflib
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class CodeDiff:
    """代码差异"""
    diff_type: str  # "added", "removed", "modified", "unchanged"
    line_number: int
    original: str
    modified: str
    context: str  # 所在的函数/类


@dataclass
class CodeChange:
    """代码变更建议"""
    change_type: str  # "selector", "logic", "import", "timeout"
    description: str
    original_code: str
    suggested_code: str
    line_number: int
    confidence: float


class CodeDiffer:
    """
    代码差异分析器

    分析代码版本之间的差异，识别需要修复的部分。
    """

    def compare(self, code1: str, code2: str) -> List[CodeDiff]:
        """
        比较两个代码版本

        Args:
            code1: 原始代码
            code2: 修改后的代码

        Returns:
            差异列表
        """
        lines1 = code1.splitlines(keepends=True)
        lines2 = code2.splitlines(keepends=True)

        diffs = []
        matcher = difflib.SequenceMatcher(None, lines1, lines2)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "replace":
                # 替换
                for i in range(i1, i2):
                    diffs.append(CodeDiff(
                        diff_type="modified",
                        line_number=i + 1,
                        original=lines1[i] if i < len(lines1) else "",
                        modified=lines2[j1 + (i - i1)] if j1 + (i - i1) < len(lines2) else "",
                        context=self._get_context(code1, i + 1),
                    ))
            elif tag == "delete":
                # 删除
                for i in range(i1, i2):
                    diffs.append(CodeDiff(
                        diff_type="removed",
                        line_number=i + 1,
                        original=lines1[i] if i < len(lines1) else "",
                        modified="",
                        context=self._get_context(code1, i + 1),
                    ))
            elif tag == "insert":
                # 新增
                for j in range(j1, j2):
                    diffs.append(CodeDiff(
                        diff_type="added",
                        line_number=i1 + 1,
                        original="",
                        modified=lines2[j] if j < len(lines2) else "",
                        context=self._get_context(code2, j + 1),
                    ))

        return diffs

    def _get_context(self, code: str, line_number: int) -> str:
        """获取代码所在上下文（函数名等）"""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if hasattr(node, 'lineno') and node.lineno == line_number:
                    # 找到了对应的AST节点
                    if isinstance(node, ast.FunctionDef):
                        return f"function:{node.name}"
                    elif isinstance(node, ast.ClassDef):
                        return f"class:{node.name}"
        except:
            pass
        return "global"

    def find_selector_changes(self, diffs: List[CodeDiff]) -> List[CodeChange]:
        """
        从差异中找出选择器相关的变更

        Args:
            diffs: 代码差异列表

        Returns:
            选择器变更列表
        """
        selector_changes = []

        for diff in diffs:
            # 检查是否是选择器相关
            if self._is_selector_related(diff.original) or self._is_selector_related(diff.modified):
                selector_changes.append(CodeChange(
                    change_type="selector",
                    description=f"选择器变更: 行{diff.line_number}",
                    original_code=diff.original.strip(),
                    suggested_code=diff.modified.strip(),
                    line_number=diff.line_number,
                    confidence=0.8,
                ))

        return selector_changes

    def _is_selector_related(self, code: str) -> bool:
        """检查代码是否与选择器相关"""
        selector_keywords = [
            'locator(', 'page.query', 'select(', 'querySelector',
            '.locator(', 'query_all(', 'CSS', 'selector',
        ]
        return any(kw in code for kw in selector_keywords)

    def find_logic_changes(self, diffs: List[CodeDiff]) -> List[CodeChange]:
        """
        从差异中找出逻辑相关的变更

        Args:
            diffs: 代码差异列表

        Returns:
            逻辑变更列表
        """
        logic_changes = []

        for diff in diffs:
            # 检查是否是逻辑相关
            if self._is_logic_related(diff.original) or self._is_logic_related(diff.modified):
                logic_changes.append(CodeChange(
                    change_type="logic",
                    description=f"逻辑变更: 行{diff.line_number}",
                    original_code=diff.original.strip(),
                    suggested_code=diff.modified.strip(),
                    line_number=diff.line_number,
                    confidence=0.7,
                ))

        return logic_changes

    def _is_logic_related(self, code: str) -> bool:
        """检查代码是否与逻辑相关"""
        logic_keywords = [
            'if ', 'for ', 'while ', 'try:', 'except', 'else:',
            'return ', 'continue', 'break', '.wait_',
        ]
        return any(kw in code for kw in logic_keywords)

    def analyze_imports(self, code: str) -> Dict[str, List[str]]:
        """
        分析代码中的导入语句

        Args:
            code: Python代码

        Returns:
            导入字典 {module: [names]}
        """
        try:
            tree = ast.parse(code)
            imports = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module = alias.name
                        name = alias.asname if alias.asname else alias.name
                        if module not in imports:
                            imports[module] = []
                        imports[module].append(name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        if module not in imports:
                            imports[module] = []
                        imports[module].append(name)

            return imports
        except:
            return {}

    def find_missing_imports(self, code: str, used_symbols: set) -> List[str]:
        """
        找出缺失的导入

        Args:
            code: Python代码
            used_symbols: 代码中使用的符号集合

        Returns:
            缺失的模块列表
        """
        imports = self.analyze_imports(code)
        imported_modules = set(imports.keys())

        # 常见模块映射
        module_symbols = {
            'json': ['json', 'dumps', 'loads'],
            'playwright': ['sync_playwright', 'Browser'],
            'bs4': ['BeautifulSoup'],
            'requests': ['get', 'post'],
            'time': ['sleep', 'time'],
            'random': ['random', 'choice', 'randint'],
        }

        missing = []
        for symbol in used_symbols:
            # 检查符号是否已导入
            found = False
            for module, names in imports.items():
                if symbol in names or '*' in names:
                    found = True
                    break

            if not found:
                # 检查是否需要导入模块
                for module, symbols in module_symbols.items():
                    if symbol in symbols and module not in imported_modules:
                        missing.append(module)
                        break

        return list(set(missing))

    def extract_function(self, code: str, function_name: str) -> Optional[str]:
        """
        提取指定函数的代码

        Args:
            code: Python代码
            function_name: 函数名

        Returns:
            函数代码或None
        """
        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # 找到了函数
                    start = node.lineno - 1
                    end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10

                    lines = code.splitlines()
                    return "\n".join(lines[start:end])

        except:
            pass

        return None

    def get_function_signatures(self, code: str) -> Dict[str, Dict[str, Any]]:
        """
        获取代码中所有函数的签名

        Args:
            code: Python代码

        Returns:
            函数签名字典 {name: {args, returns, docstring}}
        """
        try:
            tree = ast.parse(code)
            signatures = {}

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    returns = ast.unparse(node.returns) if node.returns else None
                    docstring = ast.get_docstring(node)

                    signatures[node.name] = {
                        "args": args,
                        "returns": returns,
                        "docstring": docstring,
                        "lineno": node.lineno,
                    }

            return signatures
        except:
            return {}

    def suggest_incremental_fix(
        self,
        code: str,
        error_type: str,
        error_location: Optional[int] = None,
    ) -> List[CodeChange]:
        """
        建议增量修复方案

        Args:
            code: 当前代码
            error_type: 错误类型
            error_location: 错误位置（行号）

        Returns:
            修复建议列表
        """
        changes = []

        # 根据错误类型生成修复建议
        if error_type == "selector_error":
            # 找出所有选择器
            selectors = self._find_selectors(code)
            for selector_info in selectors:
                changes.append(CodeChange(
                    change_type="selector",
                    description=f"修复选择器: {selector_info['selector']}",
                    original_code=selector_info['code'],
                    suggested_code=selector_info['code'].replace(
                        selector_info['selector'],
                        self._suggest_alternative_selector(selector_info['selector'])
                    ),
                    line_number=selector_info['line'],
                    confidence=0.6,
                ))

        elif error_type == "timeout":
            # 增加超时时间
            changes.append(CodeChange(
                change_type="timeout",
                description="增加超时时间",
                original_code="timeout=10000",
                suggested_code="timeout=30000",
                line_number=0,
                confidence=0.7,
            ))

        elif error_type == "api_error":
            # 检查API使用
            changes.append(CodeChange(
                change_type="logic",
                description="修复Playwright API使用",
                original_code="browser.new_context()",
                suggested_code="browser.new_page()",
                line_number=0,
                confidence=0.9,
            ))

        return changes

    def _find_selectors(self, code: str) -> List[Dict[str, Any]]:
        """找出代码中的所有选择器"""
        selectors = []

        lines = code.splitlines()
        for i, line in enumerate(lines):
            # 查找 locator() 中的选择器
            if '.locator(' in line:
                start = line.find('.locator(') + 9
                end = line.find(')', start)
                if end > start:
                    selector = line[start:end].strip('"\'')
                    selectors.append({
                        'selector': selector,
                        'code': line,
                        'line': i + 1,
                    })

        return selectors

    def _suggest_alternative_selector(self, selector: str) -> str:
        """建议备选选择器"""
        # 通用选择器替换规则
        alternatives = {
            '.item': '[class*="item"]',
            '.card': '[class*="card"]',
            '.title': '[class*="title"]',
            'h1': 'h1, h2, [class*="title"]',
            'a[href]': 'a[href][href!="#"]',
        }

        for pattern, alternative in alternatives.items():
            if pattern in selector:
                return alternative

        return selector
