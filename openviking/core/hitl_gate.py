# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Human-In-The-Loop (HITL) Gate & High-Risk Guard (Card-Harness-ReadWriteOffload-HookGuard - v1.5.05)

Enforces human authorization boundaries before executing destructive or production actions:
1. Detects dangerous tool names (e.g. rm_rf, drop_table, deploy_production).
2. Inspects command arguments for destructive CLI signatures (e.g. 'rm -rf', 'drop database').
3. Validates explicit approval tokens in context or tool arguments.
4. Physically blocks unauthorized execution with clear guidance for human authorization.
"""

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Set

from openviking.core.hook_aspects import AspectContext, AspectDecision, HookAspect

logger = logging.getLogger(__name__)

DEFAULT_DANGEROUS_TOOLS: Set[str] = {
    "rm_rf",
    "drop_database",
    "truncate_table",
    "deploy_production",
    "git_push_force",
    "format_disk",
    "purge_all_records",
}

DEFAULT_DANGEROUS_CMD_PATTERNS: List[re.Pattern] = [
    re.compile(r"\brm\s+-(?:r[fF]|f[rR]|rf)\s+(?:/|\*|~)", re.IGNORECASE),
    re.compile(r"\bDROP\s+(?:DATABASE|TABLE|SCHEMA)\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bgit\s+push\s+.*--force\b", re.IGNORECASE),
    re.compile(r"\bmkfs\.", re.IGNORECASE),
]


class HITLPermissionError(PermissionError):
    """Raised when an action requires human approval token but none was provided."""
    pass


@dataclass
class DangerousActionPolicy:
    """Configurable policy for high-risk action interception."""
    restricted_tools: Set[str] = field(default_factory=lambda: set(DEFAULT_DANGEROUS_TOOLS))
    prohibited_phases: Set[str] = field(default_factory=lambda: {"planning", "spec_review", "dry_run"})
    valid_approval_tokens: Set[str] = field(default_factory=set)


class HITLGate(HookAspect):
    """
    Human-in-the-loop aspect enforcing explicit human approval for high-risk operations.
    """

    name: str = "hitl_gate"
    priority: int = 10  # Highest priority, gates before any other action

    _shared_policy: Optional[DangerousActionPolicy] = None

    def __init__(self, policy: Optional[DangerousActionPolicy] = None) -> None:
        if policy is not None:
            self.policy = policy
        else:
            if HITLGate._shared_policy is None:
                HITLGate._shared_policy = DangerousActionPolicy()
            self.policy = HITLGate._shared_policy
        try:
            from openviking.core.hitl_offload_telemetry import HITLOffloadTelemetry
            HITLOffloadTelemetry().set_hitl_gate(self)
        except Exception:
            pass

    def grant_approval_token(self, token: str) -> None:
        """Register a valid human approval token."""
        if token.strip():
            self.policy.valid_approval_tokens.add(token.strip())

    def revoke_approval_token(self, token: str) -> None:
        """Revoke an approval token."""
        self.policy.valid_approval_tokens.discard(token.strip())

    def is_dangerous_invocation(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """Check if invocation targets dangerous tools or destructive command lines."""
        if tool_name in self.policy.restricted_tools:
            return f"工具 '{tool_name}' 属于高危受限工具"

        cmd = args.get("CommandLine", args.get("command", args.get("cmd", "")))
        if isinstance(cmd, str):
            for pattern in DEFAULT_DANGEROUS_CMD_PATTERNS:
                if pattern.search(cmd):
                    return f"命令包含高危破坏性指令模式: '{pattern.pattern}'"

        return None

    def get_safe_alternative_guidance(self, tool_name: str, args: Dict[str, Any], danger_reason: str) -> str:
        """Provide non-blocking defensive rerouting guidance for agents to self-heal."""
        reason_lower = danger_reason.lower()
        if "rm" in reason_lower or tool_name == "rm_rf":
            return (
                "【安全自愈导引】系统已物理拦截破坏性全局删除。请勿对根目录或全盘执行通配删除。"
                "如需清理项目构建缓存，请显式指定相对工作区子目录（例如 rm -rf ./dist 或 rm -rf ./build），"
                "或使用 VikingFS 软删除与版本快照管理。"
            )
        elif "git" in reason_lower:
            return (
                "【安全自愈导引】禁止使用 --force 强推主分支。请使用标准 'git push origin <branch>'，"
                "或通过创建 Pull Request 进行协同合并。"
            )
        elif "drop" in reason_lower or "truncate" in reason_lower:
            return (
                "【安全自愈导引】生产环境禁止全量 DROP/TRUNCATE 数据表。如需更新数据结构，"
                "请编写幂等的迁移脚本或向表中添加软删除标记。"
            )
        return (
            "【安全自愈导引】当前操作属于高危受限指令。如果非必须，请调整为安全的只读或相对路径操作；"
            "如果确需执行，请在工作区或会话预授权配置中开启该权限。"
        )

    def before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        ctx: AspectContext,
    ) -> AspectDecision:
        # 1. Phase-based restriction
        if ctx.phase in self.policy.prohibited_phases:
            if tool_name in self.policy.restricted_tools:
                reason = f"当前处于 '{ctx.phase}' 阶段，物理严禁调用生产发布或破坏性工具 '{tool_name}'"
                return AspectDecision.block(
                    reason=reason,
                    override_output=f"🚨 [HITL 阶段拦截] {reason}",
                )

        # 2. Dangerous invocation check
        danger_reason = self.is_dangerous_invocation(tool_name, args)
        if not danger_reason:
            return AspectDecision.allow()

        # 3. Check for approval token
        presented_token = str(args.get("approval_token") or args.get("ApprovalToken") or "").strip()
        has_token = False

        if presented_token and presented_token in self.policy.valid_approval_tokens:
            has_token = True
        elif any(t in self.policy.valid_approval_tokens for t in ctx.auth_tokens):
            has_token = True

        if not has_token:
            guidance = self.get_safe_alternative_guidance(tool_name, args, danger_reason)
            reason = (
                f"高危操作拦截 ({danger_reason})！"
                f"为保障系统物理安全，未授权的高危操作已被拦截。"
            )
            logger.warning(f"[HITLGate] Unauthorized high-risk tool blocked: {reason}")
            try:
                from openviking.core.hitl_offload_telemetry import HITLOffloadTelemetry
                args_summary = str({k: v for k, v in args.items() if k not in ("approval_token", "ApprovalToken")})[:120]
                HITLOffloadTelemetry().record_dangerous_intercept(
                    tool_name=tool_name,
                    args_summary=args_summary,
                    danger_reason=danger_reason,
                    phase=ctx.phase,
                )
            except Exception:
                pass
            return AspectDecision.block(
                reason=reason,
                override_output=(
                    f"🚨 [HITL 权限阻断: 安全护栏拦截] {reason}\n"
                    f"{guidance}\n"
                    f"当前任务未发生崩溃。智能体请依据安全自愈导引自主调整命令继续推进，或携带有效的 approval_token 重试。"
                ),
            )

        logger.info(f"[HITLGate] Authorized dangerous invocation '{tool_name}' with valid approval token.")
        return AspectDecision.allow()
