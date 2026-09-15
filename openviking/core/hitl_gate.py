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

    def __init__(self, policy: Optional[DangerousActionPolicy] = None) -> None:
        self.policy = policy or DangerousActionPolicy()

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
        presented_token = str(args.get("approval_token", "")).strip()
        has_token = False

        if presented_token and presented_token in self.policy.valid_approval_tokens:
            has_token = True
        elif any(t in self.policy.valid_approval_tokens for t in ctx.auth_tokens):
            has_token = True

        if not has_token:
            reason = (
                f"高危操作未获人类审批 ({danger_reason})！"
                f"根据腾讯 DECO 生产护栏规则，必须提供有效的 approval_token 方可执行。"
            )
            logger.warning(f"[HITLGate] Unauthorized high-risk tool blocked: {reason}")
            return AspectDecision.block(
                reason=reason,
                override_output=(
                    f"🚨 [HITL 权限阻断: 需人工确认] {reason}\n"
                    f"请提示人类用户确认授权，并在确认后携带审批令牌重试。"
                ),
            )

        logger.info(f"[HITLGate] Authorized dangerous invocation '{tool_name}' with valid approval token.")
        return AspectDecision.allow()
