"""
Sandbox - Docker 容器沙箱执行器（支持 Playwright 爬虫）
"""

import asyncio
import tempfile
import os
import json
import sys
from typing import Dict, Any, Optional
from pathlib import Path


class DockerSandbox:
    """
    Docker 沙箱执行器 - 支持 Playwright 爬虫

    使用预构建的 crawler-sandbox 镜像，包含：
    - Python 3.12
    - Playwright + Chromium
    - BeautifulSoup4
    """

    def __init__(
        self,
        image: str = "crawler-sandbox:latest",
        network: str = "bridge",  # 需要 bridge 网络访问外网
        timeout: int = 120,
    ):
        self.image = image
        self.network = network
        self.timeout = timeout

    async def execute(
        self,
        code: str,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        在 Docker 容器中执行爬虫代码

        Args:
            code: 要执行的 Python 代码
            timeout: 超时时间（秒）
            env: 环境变量

        Returns:
            执行结果
        """
        timeout = timeout or self.timeout

        # 创建临时工作目录
        work_dir = Path(tempfile.mkdtemp(prefix="crawler_"))
        code_file = work_dir / "scrape.py"
        stdout_file = work_dir / "stdout.txt"
        stderr_file = work_dir / "stderr.txt"

        try:
            # 写入代码文件
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(code)

            # 构建 Docker 命令
            docker_cmd = [
                "docker", "run", "--rm",
                f"--network={self.network}",
                "--memory=1g",
                "--shm-size=512m",  # Chromium 需要 shared memory
                "-v", f"{work_dir}:/workspace",
                "-w", "/workspace",
                self.image,
                "python", "scrape.py",
            ]

            # 添加环境变量
            if env:
                for k, v in env.items():
                    docker_cmd.extend(["-e", f"{k}={v}"])

            # 执行
            process = await asyncio.create_subprocess_exec(
                *docker_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )

                stdout_text = stdout.decode("utf-8", errors="ignore")
                stderr_text = stderr.decode("utf-8", errors="ignore")

                # 尝试解析 JSON
                parsed_data = None
                if stdout_text.strip():
                    try:
                        parsed_data = json.loads(stdout_text)
                    except json.JSONDecodeError:
                        parsed_data = stdout_text

                return {
                    "success": process.returncode == 0,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "returncode": process.returncode,
                    "parsed_data": parsed_data,
                    "error": stderr_text if process.returncode != 0 else None,
                }

            except asyncio.TimeoutError:
                try:
                    process.kill()
                    await asyncio.wait_for(process.wait(), timeout=5)
                except:
                    pass

                return {
                    "success": False,
                    "error": f"Execution timeout after {timeout}s",
                    "stderr": "Timeout",
                }

        finally:
            # 清理临时目录
            try:
                import shutil
                shutil.rmtree(work_dir)
            except:
                pass

    async def run_python_code(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        便捷方法：运行 Python 代码并解析 JSON 输出

        CodeAct 模式：LLM 生成代码 → 沙箱执行 → 返回结构化结果

        Args:
            code: Python 代码字符串
            timeout: 超时时间（秒）

        Returns:
            {
                "success": bool,
                "output": dict | str,  # 尝试解析为 JSON，失败则返回原始字符串
                "error": str | None,
                "stdout": str,
                "stderr": str
            }
        """
        result = await self.execute(code, timeout=timeout)

        # 提取 parsed_data 作为 output
        output = result.get("parsed_data")
        if output is None:
            # 如果解析失败，尝试从 stdout 提取 JSON
            stdout = result.get("stdout", "")
            if stdout.strip():
                try:
                    output = json.loads(stdout)
                except:
                    output = stdout

        return {
            "success": result["success"],
            "output": output,
            "error": result.get("error"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
        }


class SimpleSandbox:
    """
    简化版沙箱（本地执行，适合开发）
    """

    async def execute(
        self,
        code: str,
        timeout: int = 120,
    ) -> Dict[str, Any]:
        """本地执行代码"""
        work_dir = Path(tempfile.mkdtemp(prefix="crawler_"))
        code_file = work_dir / "scrape.py"

        try:
            with open(code_file, "w", encoding="utf-8") as f:
                f.write(code)

            process = await asyncio.create_subprocess_exec(
                sys.executable,
                str(code_file),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            stdout_text = stdout.decode("utf-8", errors="ignore")
            stderr_text = stderr.decode("utf-8", errors="ignore")

            # 尝试解析 JSON
            parsed_data = None
            if stdout_text.strip():
                try:
                    parsed_data = json.loads(stdout_text)
                except json.JSONDecodeError:
                    pass

            return {
                "success": process.returncode == 0,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "returncode": process.returncode,
                "parsed_data": parsed_data,
                "error": stderr_text if process.returncode != 0 else None,
            }

        except asyncio.TimeoutError:
            try:
                process.kill()
            except:
                pass

            return {
                "success": False,
                "error": f"Execution timeout after {timeout}s",
            }

        finally:
            try:
                import shutil
                shutil.rmtree(work_dir)
            except:
                pass

    async def run_python_code(
        self,
        code: str,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        便捷方法：运行 Python 代码并解析 JSON 输出

        CodeAct 模式：LLM 生成代码 → 沙箱执行 → 返回结构化结果

        Args:
            code: Python 代码字符串
            timeout: 超时时间（秒）

        Returns:
            {
                "success": bool,
                "output": dict | str,
                "error": str | None,
                "stdout": str,
                "stderr": str
            }
        """
        result = await self.execute(code, timeout=timeout)

        output = result.get("parsed_data")
        if output is None:
            stdout = result.get("stdout", "")
            if stdout.strip():
                try:
                    output = json.loads(stdout)
                except:
                    output = stdout

        return {
            "success": result["success"],
            "output": output,
            "error": result.get("error"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
        }


def create_sandbox(use_docker: bool = True) -> DockerSandbox | SimpleSandbox:
    """
    创建沙箱实例

    Args:
        use_docker: 是否使用 Docker 沙箱（需要先构建镜像）
    """
    if use_docker:
        return DockerSandbox()
    else:
        return SimpleSandbox()
