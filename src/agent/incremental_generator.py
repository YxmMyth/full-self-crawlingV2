"""
Incremental Code Generator - 增量代码生成器

只修复出错的部分，而不是全量重生成代码。
"""

from typing import Dict, List, Optional, Any, Tuple
from .code_differ import CodeDiffer, CodeChange


class IncrementalCodeGenerator:
    """
    增量代码生成器

    分析代码执行失败的原因，只修复出错的部分，
    保留正确的代码，避免全量重生成。
    """

    def __init__(self):
        self.differ = CodeDiffer()

    def should_use_incremental_fix(
        self,
        state: Dict[str, Any],
    ) -> bool:
        """
        判断是否应该使用增量修复

        Args:
            state: 当前状态

        Returns:
            是否使用增量修复
        """
        iteration = state.get("sool_iteration", 0)
        execution_result = state.get("execution_result", {})

        # 第2次及以后的尝试才考虑增量修复
        if iteration < 1:
            return False

        # 如果之前有部分成功，考虑增量修复
        if execution_result.get("success") or execution_result.get("partial_success"):
            return True

        # 检查是否有相同代码签名（避免重复尝试）
        signatures = state.get("attempt_signatures", [])
        if len(signatures) > 1:
            # 如果已经尝试过多次，尝试增量修复
            return True

        return False

    def analyze_error(
        self,
        code: str,
        execution_result: Dict[str, Any],
        error_diagnosis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        分析错误原因

        Args:
            code: 当前代码
            execution_result: 执行结果
            error_diagnosis: 错误诊断信息

        Returns:
            错误分析结果
        """
        error = execution_result.get("error", "") or execution_result.get("stderr", "")
        stdout = execution_result.get("stdout", "")

        # 如果有诊断信息，使用它
        if error_diagnosis:
            error_type = error_diagnosis.get("error_type", "unknown")
            root_cause = error_diagnosis.get("root_cause", "")
        else:
            # 自行分析错误类型
            error_type = self._classify_error(error, stdout)
            root_cause = error[:200]

        return {
            "error_type": error_type,
            "root_cause": root_cause,
            "has_data": execution_result.get("success", False),
            "partial_success": self._check_partial_success(stdout),
            "error_location": self._find_error_location(code, error),
        }

    def _classify_error(self, error: str, stdout: str) -> str:
        """分类错误类型"""
        error_lower = error.lower() + stdout.lower()

        if "selector" in error_lower or "no elements" in error_lower:
            return "selector_error"
        elif "timeout" in error_lower:
            return "timeout"
        elif "syntax" in error_lower:
            return "syntax_error"
        elif "import" in error_lower or "module" in error_lower:
            return "import_error"
        elif "browser" in error_lower or "playwright" in error_lower:
            return "api_error"
        elif "blocked" in error_lower or "cloudflare" in error_lower:
            return "blocked"
        else:
            return "unknown"

    def _check_partial_success(self, stdout: str) -> bool:
        """检查是否有部分成功"""
        try:
            import json
            if stdout.strip():
                data = json.loads(stdout)
                if isinstance(data, dict):
                    results = data.get("results", [])
                    return len(results) > 0
        except:
            pass
        return False

    def _find_error_location(self, code: str, error: str) -> Optional[int]:
        """从错误信息中找出错误位置"""
        import re

        # 尝试从错误信息中提取行号
        line_match = re.search(r'line (\d+)', error)
        if line_match:
            return int(line_match.group(1))

        return None

    def generate_incremental_fix(
        self,
        code: str,
        error_analysis: Dict[str, Any],
        previous_attempts: List[str] = None,
        validated_selectors: List[str] = None,
    ) -> str:
        """
        生成增量修复

        Args:
            code: 当前代码
            error_analysis: 错误分析结果
            previous_attempts: 之前的代码尝试
            validated_selectors: 已验证有效的选择器

        Returns:
            修复后的代码
        """
        error_type = error_analysis["error_type"]

        # 根据错误类型生成不同的修复策略
        if error_type == "selector_error":
            return self._fix_selector_error(code, error_analysis, validated_selectors)
        elif error_type == "timeout":
            return self._fix_timeout(code, error_analysis)
        elif error_type == "import_error":
            return self._fix_import_error(code, error_analysis)
        elif error_type == "api_error":
            return self._fix_api_error(code, error_analysis)
        elif error_type == "blocked":
            return self._fix_blocked_error(code, error_analysis)
        else:
            return self._fix_generic_error(code, error_analysis)

    def _fix_selector_error(
        self,
        code: str,
        error_analysis: Dict[str, Any],
        validated_selectors: List[str] = None,
    ) -> str:
        """修复选择器错误"""
        lines = code.splitlines()

        # 如果有验证过的选择器，使用它们
        if validated_selectors:
            # 找出代码中可能错误的选择器并替换
            for i, line in enumerate(lines):
                if '.locator(' in line and 'page.locator' in line:
                    # 提取当前选择器
                    start = line.find('.locator(') + 9
                    end = line.find(')', start)
                    if end > start:
                        old_selector = line[start:end].strip('"\'')
                        # 用验证过的选择器替换
                        if validated_selectors:
                            new_selector = validated_selectors[0]
                            lines[i] = line.replace(old_selector, new_selector, 1)
                            break

        return "\n".join(lines)

    def _fix_timeout(self, code: str, error_analysis: Dict[str, Any]) -> str:
        """修复超时错误"""
        # 增加所有wait_for_*的超时时间
        lines = code.splitlines()

        for i, line in enumerate(lines):
            if 'wait_for_selector(' in line or 'wait_for_load_state(' in line:
                # 增加超时时间
                line = line.replace('timeout=10000', 'timeout=30000')
                line = line.replace('timeout=15000', 'timeout=30000')
                line = line.replace('timeout=5000', 'timeout=15000')
                lines[i] = line
            elif 'time.sleep(' in line:
                # 增加等待时间
                import re
                match = re.search(r'time\.sleep\((\d+)\)', line)
                if match:
                    old_time = int(match.group(1))
                    new_time = min(old_time * 2, 10)
                    lines[i] = line.replace(f'time.sleep({old_time}', f'time.sleep({new_time}')

        return "\n".join(lines)

    def _fix_import_error(self, code: str, error_analysis: Dict[str, Any]) -> str:
        """修复导入错误"""
        lines = code.splitlines()
        imports = set()

        # 收集现有的导入
        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                imports.add(line.strip())

        # 添加缺失的导入
        missing_imports = []

        # 检查代码中使用了哪些模块
        code_lower = code.lower()
        if 'json.dumps' in code_lower and 'import json' not in str(imports):
            missing_imports.append('import json')
        if 'sync_playwright' in code_lower and 'from playwright.sync_api' not in str(imports):
            missing_imports.append('from playwright.sync_api import sync_playwright')
        if 'time.sleep' in code_lower and 'import time' not in str(imports):
            missing_imports.append('import time')
        if 'random.' in code_lower and 'import random' not in str(imports):
            missing_imports.append('import random')
        if 'beautifulsoup' in code_lower or 'bs4' in code_lower:
            if 'import bs4' not in str(imports) and 'from bs4' not in str(imports):
                missing_imports.append('from bs4 import BeautifulSoup')

        # 在代码开头添加缺失的导入
        if missing_imports:
            # 找到第一个非导入行
            insert_pos = 0
            for i, line in enumerate(lines):
                if not line.strip().startswith(('import', 'from', '#', '"""', "'''")):
                    insert_pos = i
                    break

            # 插入导入
            for imp in reversed(missing_imports):
                lines.insert(insert_pos, imp)

        return "\n".join(lines)

    def _fix_api_error(self, code: str, error_analysis: Dict[str, Any]) -> str:
        """修复API错误"""
        # 修复常见的Playwright API使用错误
        lines = code.splitlines()

        for i, line in enumerate(lines):
            # 修复 browser.new_context() -> browser.new_page()
            if 'browser.new_context()' in line:
                lines[i] = line.replace('browser.new_context()', 'browser.new_page()')

            # 修复 await (同步模式)
            if line.strip().startswith('await ') and 'async def' not in code:
                lines[i] = line.replace('await ', '', 1)

            # 修复 async def -> def (同步模式)
            if 'async def scrape(' in line:
                lines[i] = line.replace('async def scrape(', 'def scrape(')

        return "\n".join(lines)

    def _fix_blocked_error(self, code: str, error_analysis: Dict[str, Any]) -> str:
        """修复被阻止错误"""
        # 添加或增强隐身配置
        lines = code.splitlines()

        # 检查是否已有隐身配置
        has_stealth = any('stealth' in line.lower() or 'automationcontrolled' in line.lower()
                         for line in lines)

        if not has_stealth:
            # 在 browser.launch() 中添加隐身参数
            for i, line in enumerate(lines):
                if 'browser = p.chromium.launch(' in line:
                    # 添加隐身参数
                    if 'args=' in line:
                        # 在现有args中添加
                        line = line.replace('args=[', 'args=[')
                        line = line.replace('[]', '"--disable-blink-features=AutomationControlled"]')
                    else:
                        # 添加args参数
                        line = line.replace('launch(', 'launch(args=["--disable-blink-features=AutomationControlled"], ')
                    lines[i] = line
                    break

        return "\n".join(lines)

    def _fix_generic_error(self, code: str, error_analysis: Dict[str, Any]) -> str:
        """通用错误修复"""
        # 添加更好的错误处理
        lines = code.splitlines()

        # 在关键操作周围添加try-except
        for i, line in enumerate(lines):
            if '.locator(' in line and 'try:' not in "\n".join(lines[max(0, i-3):i]):
                # 在之前几行没有try的情况下，添加
                indent = len(line) - len(line.lstrip())
                try_block = ' ' * indent + 'try:\n'
                lines.insert(i, try_block)

                # 添加except
                except_block = ' ' * indent + 'except:\n'
                except_block += ' ' * (indent + 4) + 'continue\n'
                lines.insert(i + 2, except_block)

                # 缩进原有代码
                lines[i + 1] = ' ' * (indent + 4) + lines[i + 1].lstrip()

                break

        return "\n".join(lines)

    def generate_targeted_prompt(
        self,
        code: str,
        error_analysis: Dict[str, Any],
        validated_selectors: List[str] = None,
    ) -> str:
        """
        生成针对性的修复Prompt

        只要求LLM修复出错的部分，而不是生成整个代码。

        Args:
            code: 当前代码
            error_analysis: 错误分析
            validated_selectors: 已验证的选择器

        Returns:
            针对性的Prompt
        """
        error_type = error_analysis["error_type"]
        root_cause = error_analysis["root_cause"]
        error_location = error_analysis.get("error_location")

        selector_hint = ""
        if validated_selectors:
            selector_hint = f"""

【✅ 已验证有效的选择器】
请优先使用以下选择器：
{chr(10).join(f"- {s}" for s in validated_selectors[:3])}
"""

        if error_type == "selector_error":
            return f"""你是代码修复专家。请修复以下爬虫代码中的选择器错误。

【错误类型】{error_type}
【根本原因】{root_cause}
{selector_hint}
【当前代码】
```python
{code}
```

【任务】
只需要修复出错的**选择器部分**，其他代码保持不变。

【修复要求】
1. 使用已验证的选择器或更通用的选择器
2. 保持代码的其他部分不变
3. 只输出修改后的完整代码

请只输出修复后的完整Python代码。
"""

        elif error_type == "timeout":
            return f"""你是代码修复专家。请修复以下爬虫代码中的超时问题。

【错误类型】{error_type}
【根本原因】{root_cause}

【当前代码】
```python
{code}
```

【任务】
增加wait_for_*和time.sleep的超时时间/等待时间，确保页面内容能加载完成。

【修复要求】
1. 将所有timeout增加到30000ms
2. 增加time.sleep的等待时间
3. 保持其他代码不变
4. 只输出修改后的完整代码

请只输出修复后的完整Python代码。
"""

        elif error_type == "import_error":
            return f"""你是代码修复专家。请修复以下爬虫代码中的导入错误。

【错误类型】{error_type}
【根本原因】{root_cause}

【当前代码】
```python
{code}
```

【任务】
添加缺失的import语句，确保代码能正常运行。

【修复要求】
1. 在代码开头添加缺失的导入
2. 保持其他代码不变
3. 只输出修改后的完整代码

请只输出修复后的完整Python代码。
"""

        elif error_type == "api_error":
            return f"""你是代码修复专家。请修复以下爬虫代码中的Playwright API使用错误。

【错误类型】{error_type}
【根本原因】{root_cause}

【当前代码】
```python
{code}
```

【任务】
修复Playwright API使用错误，确保使用正确的同步API。

【修复要求】
1. 使用 browser.new_page() 而不是 browser.new_context()
2. 使用 page.goto() 而不是 await page.goto()
3. 使用 def 而不是 async def
4. 只输出修改后的完整代码

请只输出修复后的完整Python代码。
"""

        else:
            # 通用修复
            return f"""你是代码修复专家。请修复以下爬虫代码。

【错误类型】{error_type}
【根本原因】{root_cause}

【当前代码】
```python
{code}
```

【任务】
修复代码中的错误，确保能正常运行。

【修复要求】
1. 针对错误类型进行修复
2. 保持其他正确的代码不变
3. 只输出修复后的完整代码

请只输出修复后的完整Python代码。
"""
