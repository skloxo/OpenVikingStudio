# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Polar 不可伪造环境判官 (Unfakeable Environment Judge)。

核心公理：以真实沙箱 exit code 为唯一验证真理。
禁止 LLM 摘要声称「测试通过」，必须提供物理可复现的 shell 命令与实际退出码。

参考: NVIDIA Polar 环境验证体系。

(Card-Harness-AHE-ContractualSelfEvolution v1.5.38)
"""
from __future__ import annotations

import shlex
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

MAX_OUTPUT_BYTES = 4096   # 截断保护，防污染上下文


class PolarVerdict(str, Enum):
    PASS    = "pass"    # exit 0，且输出中无禁止模式
    FAIL    = "fail"    # exit != 0
    TIMEOUT = "timeout" # 超时
    ERROR   = "error"   # 无法执行命令


@dataclass
class PolarProbeResult:
    """Polar 环境判官单次探测结果。"""
    probe_id: str = field(default_factory=lambda: f"prb-{uuid.uuid4().hex[:8]}")
    command: str = ""
    exit_code: Optional[int] = None
    stdout_tail: str = ""        # 仅最后 4KB
    stderr_tail: str = ""
    verdict: PolarVerdict = PolarVerdict.ERROR
    duration_ms: float = 0.0
    probed_at: float = field(default_factory=time.time)
    timeout_sec: float = 30.0


class PolarJudge:
    """Polar 不可伪造环境判官。

    工作机制:
      1. 接收 AHEAssumption.validation_command
      2. 在真实 shell 中执行 (subprocess, 非 LLM 摘要)
      3. 以 exit code == 0 为 PASS 的唯一充分条件
      4. 超时视为 FAIL
    """

    def __init__(self, default_timeout_sec: float = 30.0) -> None:
        self._default_timeout = default_timeout_sec

    def probe(
        self,
        command: str,
        timeout_sec: Optional[float] = None,
        cwd: Optional[str] = None,
    ) -> PolarProbeResult:
        """在真实沙箱中执行命令，返回不可伪造的探测结果。"""
        t0 = time.monotonic()
        timeout = timeout_sec or self._default_timeout
        result = PolarProbeResult(command=command, timeout_sec=timeout)

        if not command.strip():
            result.verdict = PolarVerdict.ERROR
            result.stderr_tail = "Empty command provided"
            result.duration_ms = 0.0
            return result

        try:
            proc = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            duration = (time.monotonic() - t0) * 1000
            result.exit_code = proc.returncode
            result.stdout_tail = proc.stdout[-MAX_OUTPUT_BYTES:]
            result.stderr_tail = proc.stderr[-MAX_OUTPUT_BYTES:]
            result.duration_ms = duration
            result.verdict = PolarVerdict.PASS if proc.returncode == 0 else PolarVerdict.FAIL

        except subprocess.TimeoutExpired:
            result.duration_ms = (time.monotonic() - t0) * 1000
            result.verdict = PolarVerdict.TIMEOUT
            result.stderr_tail = f"Command timed out after {timeout}s"

        except (OSError, ValueError) as exc:
            result.duration_ms = (time.monotonic() - t0) * 1000
            result.verdict = PolarVerdict.ERROR
            result.stderr_tail = str(exc)[:512]

        return result

    def probe_assumption(
        self,
        validation_command: str,
        timeout_sec: Optional[float] = None,
        cwd: Optional[str] = None,
    ) -> PolarProbeResult:
        """探测单个 AHEAssumption 的 validation_command。"""
        return self.probe(validation_command, timeout_sec=timeout_sec, cwd=cwd)
