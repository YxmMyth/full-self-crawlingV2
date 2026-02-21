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
