# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Skill Sandbox Runner — Isolated Evaluation & AST Security Gate (SSOT).
Card-89: 动态技能沙箱物理试跑与契约验证闭环 (Skill LiveGen Real Sandbox & Contract Validation / v1.7.43)
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from openviking.core.skill_loader import SkillLoader, validate_skill_format
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

# 高危模块与函数黑名单 (AST 节点特征匹配)
DANGEROUS_CALLS = {
    "os.system",
    "os.popen",
    "os.spawn",
    "shutil.rmtree",
    "subprocess.Popen",
    "subprocess.run",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "builtins.exec",
    "builtins.eval",
    "exec",
    "eval",
}

DANGEROUS_MODULES = {
    "pty",
    "ctypes",
}


class SandboxExecutionReport(BaseModel):
    model_config = ConfigDict(extra="ignore")
    passed: bool = Field(description="沙箱测试是否全部通过")
    duration_ms: float = Field(description="沙箱物理执行耗时 (毫秒)")
    security_blocked_count: int = Field(default=0, description="拦截的高危系统调用数")
    security_issues: List[str] = Field(default_factory=list, description="具体安全拦截详情")
    syntax_valid: bool = Field(default=True, description="语法树与 Frontmatter 是否合法")
    syntax_error: Optional[str] = Field(None, description="语法或格式解析错误")
    tools_declared: List[str] = Field(default_factory=list, description="声明的合法工具契约")
    stdout: str = Field(default="", description="沙箱执行标准输出")
    stderr: str = Field(default="", description="沙箱执行错误输出")


class SkillSandboxRunner:
    """受限只读工作区与 AST 安全沙箱执行器。"""

    CODE_BLOCK_PATTERN = re.compile(r"```(?:python|py)?\s*\n(.*?)\n```", re.DOTALL)

    @classmethod
    def inspect_code_safety(cls, code: str) -> Tuple[bool, List[str]]:
        """利用 Python AST 深度遍历代码，扫描高危系统调用与危险模块。"""
        issues: List[str] = []
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"AST 语法树解析错误: {e.msg} (Line {e.lineno})"]

        for node in ast.walk(tree):
            # 1. 检查危险模块 import
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in DANGEROUS_MODULES:
                        issues.append(f"安全拦截: 禁止导入高危模块 '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                if node.module in DANGEROUS_MODULES:
                    issues.append(f"安全拦截: 禁止从高危模块 '{node.module}' 导入")

            # 2. 检查危险函数调用
            elif isinstance(node, ast.Call):
                call_name = cls._resolve_call_name(node.func)
                if call_name in DANGEROUS_CALLS:
                    issues.append(f"安全拦截: 禁止调用高危指令 '{call_name}()'")

        return len(issues) == 0, issues

    @staticmethod
    def _resolve_call_name(node: ast.AST) -> str:
        """从 Call 节点解析出完整的函数名，如 os.system 或 eval。"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            val = node.value
            if isinstance(val, ast.Name):
                return f"{val.id}.{node.attr}"
            elif isinstance(val, ast.Attribute):
                parent = SkillSandboxRunner._resolve_call_name(val)
                return f"{parent}.{node.attr}"
        return ""

    @classmethod
    def run_isolated_trial(
        cls,
        content: str,
        queries: Optional[List[str]] = None,
        timeout_sec: float = 3.0,
    ) -> SandboxExecutionReport:
        """在受限临时目录中真实试跑技能，捕获执行状态与安全诊断。"""
        t0 = time.perf_counter()
        security_issues: List[str] = []
        stdout_parts: List[str] = []
        stderr_parts: List[str] = []

        # 1. 格式与 Frontmatter 静态审计
        val_res = validate_skill_format(content, strict=True)
        if not val_res.get("valid", False):
            errors = [f"{e.get('field', 'format')}: {e.get('message', '')}" for e in val_res.get("errors", [])]
            return SandboxExecutionReport(
                passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                syntax_valid=False,
                syntax_error="; ".join(errors),
                tools_declared=val_res.get("allowed_tools", []),
            )

        tools_declared = val_res.get("allowed_tools", [])

        # 2. 提取 Python 代码块并执行 AST 深度静态安全检查
        code_blocks = cls.CODE_BLOCK_PATTERN.findall(content)
        for i, code in enumerate(code_blocks):
            safe, issues = cls.inspect_code_safety(code)
            if not safe:
                security_issues.extend([f"CodeBlock#{i+1}: {iss}" for iss in issues])

        # 若命中了高危调用，立即阻断，严禁启动子进程试跑
        if security_issues:
            return SandboxExecutionReport(
                passed=False,
                duration_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                security_blocked_count=len(security_issues),
                security_issues=security_issues,
                syntax_valid=True,
                tools_declared=tools_declared,
                stderr="[SECURITY GATE ABORT] 检测到高危代码注入，沙箱物理阻断执行！",
            )

        # 3. 隔离受限环境真实试跑 (若存在代码块)
        with tempfile.TemporaryDirectory(prefix="ov_skill_sandbox_") as tmp_dir:
            work_dir = Path(tmp_dir)
            skill_file = work_dir / "SKILL.md"
            skill_file.write_text(content, encoding="utf-8")

            if code_blocks:
                # 拼接可安全执行的自检脚本
                runner_code = "\n".join(code_blocks)
                test_script = work_dir / "test_sandbox_run.py"
                test_script.write_text(runner_code, encoding="utf-8")

                try:
                    env = {
                        "PATH": os.environ.get("PATH", ""),
                        "PYTHONPATH": "",
                        "OPENVIKING_SANDBOX": "1",
                    }
                    proc = subprocess.run(
                        [sys.executable, str(test_script)],
                        cwd=str(work_dir),
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=timeout_sec,
                    )
                    stdout_parts.append(proc.stdout)
                    stderr_parts.append(proc.stderr)
                    execution_ok = (proc.returncode == 0)
                    if not execution_ok:
                        security_issues.append(f"沙箱进程退出码异常 (exitcode={proc.returncode})")
                except subprocess.TimeoutExpired:
                    stderr_parts.append(f"[TIMEOUT] 沙箱执行超过 {timeout_sec} 秒硬限制，已物理熔断终止！")
                    security_issues.append(f"执行超时 (> {timeout_sec}s)")
                    execution_ok = False
                except Exception as e:
                    stderr_parts.append(f"沙箱启动异常: {e}")
                    security_issues.append(str(e))
                    execution_ok = False
            else:
                # 纯提示词/纯文档类技能，完成静态契约验证与工具声明核验
                stdout_parts.append(f"[CONTRACT OK] 静态规范校验通过，声明工具数: {len(tools_declared)}")
                execution_ok = True

        duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        all_passed = execution_ok and len(security_issues) == 0

        return SandboxExecutionReport(
            passed=all_passed,
            duration_ms=duration_ms,
            security_blocked_count=len(security_issues),
            security_issues=security_issues,
            syntax_valid=True,
            tools_declared=tools_declared,
            stdout="\n".join(filter(None, stdout_parts)),
            stderr="\n".join(filter(None, stderr_parts)),
        )
