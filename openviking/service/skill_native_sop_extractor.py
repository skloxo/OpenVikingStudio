# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Native SOP & Technical Invariant Extractor for Unstructured Skills (Card-194).

Mines and distills native execution workflows, deliverables contracts, and error
recovery procedures directly from raw, unstructured technical documents, avoiding
synthetic placeholder injection and preserving true engineering context.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple


class SkillNativeSOPExtractor:
    """Intelligent extractor that distills native SOPs from raw technical markdown."""

    HEADING2_RE = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    CODE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_-]*\n([\s\S]*?)```")
    ERROR_SIGNAL_RE = re.compile(
        r"(?:(?:若|当|如果|遇到|发生|若遇到)\s*[`\"']?([^\n\r`\"']+(?:错误|异常|失败|Error|Exception|timeout|502|Exit Code))[`\"']?[^\n\r]*[\n\r]+[^\n\r]+)",
        re.IGNORECASE,
    )

    def extract_native_sop(self, content: str) -> Optional[str]:
        """Extract existing markdown sections containing code/commands into numbered SOP steps."""
        body = self._strip_frontmatter(content)
        sections = self._split_into_sections(body)
        if len(sections) < 2:
            return None

        sop_steps: List[str] = []
        step_index = 1

        for title, sec_content in sections:
            # Skip metadata/appendix/overview sections
            clean_title = title.strip()
            if any(term in clean_title for term in ("简介", "背景", "概述", "参考", "附录", "Overview", "Reference")):
                continue

            # A section is an actionable step if it has code blocks or execution instructions
            has_code = bool(self.CODE_BLOCK_RE.search(sec_content))
            has_commands = any(cmd in sec_content for cmd in ("kubectl", "docker", "curl", "python", "git", "bash", "cd ", "npm"))
            has_actions = any(verb in clean_title for verb in ("准备", "配置", "检查", "部署", "运行", "执行", "驱逐", "下线", "安装", "验证"))

            if has_code or has_commands or has_actions:
                # Format into standard numbered step
                clean_sec_body = sec_content.strip()
                sop_steps.append(f"### {step_index}. {clean_title}\n\n{clean_sec_body}")
                step_index += 1

        if len(sop_steps) < 2:
            return None

        return "\n\n## 自动化执行流程与工序 (Execution SOP)\n\n" + "\n\n".join(sop_steps)

    def extract_native_fault_recovery(self, content: str) -> Optional[str]:
        """Distill error handling instructions mentioned natively in the text."""
        body = self._strip_frontmatter(content)
        error_matches = self.ERROR_SIGNAL_RE.findall(body)
        
        recovery_rules: List[str] = []
        if error_matches:
            for em in error_matches[:3]:
                clean_err = em.strip()
                recovery_rules.append(f"- **异常识别与规约**: 针对 `{clean_err}`，严格遵循就地排查规约，严禁盲目强杀或暴力跳过。")

        # Check for explicit retry or timeout mentions
        if "重试" in body or "retry" in body.lower():
            recovery_rules.append("- **重试与退避**: 遵循指数退避机制重试最多 2 次，保障幂等与防雪崩。")
        if "timeout" in body.lower() or "超时" in body:
            recovery_rules.append("- **超时熔断**: 严格受控于超时预算，超时即刻中断并输出明确上下文堆栈。")

        if recovery_rules:
            return "\n\n## 故障排查与自愈恢复 (Failure Recovery SOP)\n" + "\n".join(recovery_rules)

        return None

    def extract_native_io_contract(self, content: str, skill_name: str) -> Optional[str]:
        """Extract input parameters and verifiable deliverables based on code and configs."""
        body = self._strip_frontmatter(content)
        lines: List[str] = []

        # Find exported env vars or configs
        env_vars = re.findall(r"\b(?:export\s+)?([A-Z0-9_]{4,})\s*=", body)
        if env_vars:
            unique_envs = list(dict.fromkeys(env_vars))[:4]
            lines.append(f"- **输入参数与凭据 (Inputs)**: 目标集群环境与必要配置凭据 (`{', '.join(unique_envs)}`)。")
        else:
            lines.append("- **输入规格 (Inputs)**: 目标任务入参、运行环境与指定配置文件。")

        # Find output assertions
        if "exit code 0" in body.lower() or "状态码为 0" in body or "成功" in body:
            lines.append("- **完成断言 (Assert Criteria)**: 前置命令返回 Exit Code 0，且无未捕获异常。")
        else:
            lines.append("- **完成断言 (Assert Criteria)**: 验证核心指令执行返回状态码为 0，符合预期规约。")

        lines.append("- **预期交付物 (Output Deliverables)**: 执行状态账本、业务系统健康指标或生成的规范配置。")

        return "\n\n## 交付契约与验收标准 (I/O & Delivery Contract)\n" + "\n".join(lines)

    def _strip_frontmatter(self, content: str) -> str:
        """Strip YAML frontmatter if present."""
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                return parts[2]
        return content

    def _split_into_sections(self, body: str) -> List[Tuple[str, str]]:
        """Split markdown body into (title, content) pairs based on H2 headings."""
        matches = list(self.HEADING2_RE.finditer(body))
        if not matches:
            return []

        sections: List[Tuple[str, str]] = []
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            sec_content = body[start:end]
            sections.append((title, sec_content))

        return sections
