# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""SkillOpt Attempt / Judge 质量门禁与自动优化引擎核心服务。

实现 Microsoft SkillOpt 论文方法论与 Viking 质量视网膜：
1. 四维质量评分体系 (0~100分，各25分):
   - spec_integrity: YAML Frontmatter 结构与必须字段完整度
   - tool_precision: 工具声明合规性与正文调用示例规范
   - token_density: 单文件行数甜点区 (100~300) 与注意力信噪比
   - trigger_robustness: 意图触发区分度与负向边界约束 (When NOT to use)
2. Attempt 尝试执行与 Judge 判据门禁
3. Auto-Optimization 优化建议与修复 Draft 生成
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from openviking.service.skill_opt_types import (
    BatchAuditSummary,
    DimensionScore,
    SkillOptAttemptRequest,
    SkillOptAttemptResult,
    SkillOptAuditResult,
    SkillOptOptimizeRequest,
    SkillOptOptimizeResult,
)


class SkillOptService:
    """SkillOpt 质量门禁与自动优化核心服务。"""

    def audit_content(self, skill_content: str, skill_name: Optional[str] = None) -> SkillOptAuditResult:
        """对技能文本执行四维全量体检。"""
        lines = [line.rstrip() for line in skill_content.splitlines()]
        line_count = len(lines)

        frontmatter, body = self._parse_frontmatter(skill_content)
        name = skill_name or frontmatter.get("name") or "unnamed-skill"

        d1 = self._eval_spec_integrity(frontmatter)
        d2 = self._eval_tool_precision(frontmatter, body)
        d3 = self._eval_token_density(lines, body)
        d4 = self._eval_trigger_robustness(frontmatter, body)

        total_score = d1.score + d2.score + d3.score + d4.score
        grade = self._calc_grade(total_score)
        passed_gate = total_score >= 70 and d3.status != "critical"

        suggestions: List[str] = []
        for dim in (d1, d2, d3, d4):
            for item in dim.details:
                if item.startswith("⚠️") or item.startswith("🚫"):
                    suggestions.append(f"[{dim.label}] {item}")

        return SkillOptAuditResult(
            skill_name=str(name),
            total_score=total_score,
            grade=grade,
            line_count=line_count,
            dimensions=[d1, d2, d3, d4],
            suggestions=suggestions,
            passed_gate=passed_gate,
        )

    def attempt_execution(self, req: SkillOptAttemptRequest) -> SkillOptAttemptResult:
        """执行测试用例 Attempt 并由 Judge Gate 评判。"""
        frontmatter, body = self._parse_frontmatter(req.skill_content)
        description = str(frontmatter.get("description", "")).lower()
        query = req.test_query.strip().lower()

        clauses = [p for p in re.split(r"[、，, \t\n/；;。与及和]+", query) if p.strip()]
        matched_tokens: List[str] = []
        for clause in clauses:
            for n in (2, 3):
                if len(clause) >= n:
                    for i in range(len(clause) - n + 1):
                        gram = clause[i : i + n]
                        if gram in description or gram in body.lower():
                            if gram not in matched_tokens:
                                matched_tokens.append(gram)

        confidence = min(1.0, len(matched_tokens) * 0.28)
        tools = frontmatter.get("tools", [])
        if not isinstance(tools, list):
            tools = []

        if confidence >= 0.5:
            verdict = "PASS"
            judge_reason = f"意图触发匹配成功 (置信度 {confidence:.0%})，命中特征词: {matched_tokens}"
        elif confidence >= 0.25:
            verdict = "PARTIAL"
            judge_reason = f"意图部分匹配 (置信度 {confidence:.0%})，建议补充更精确的场景触发词"
        else:
            verdict = "FAIL"
            judge_reason = "未能匹配到对应场景，技能描述未覆盖此输入"

        return SkillOptAttemptResult(
            verdict=verdict,
            confidence=confidence,
            matched_intent=confidence >= 0.5,
            judge_reason=judge_reason,
            triggered_tools=[str(t) for t in tools[:3]],
        )

    def optimize_content(self, req: SkillOptOptimizeRequest) -> SkillOptOptimizeResult:
        """基于体检扣分项生成自动修复补丁与优化版 Draft。"""
        orig_audit = self.audit_content(req.skill_content)
        frontmatter, body = self._parse_frontmatter(req.skill_content)

        applied_fixes: List[str] = []
        new_fm = dict(frontmatter)

        if not new_fm.get("name"):
            new_fm["name"] = "optimized-skill"
            applied_fixes.append("补齐缺失的 name 字段")

        if not new_fm.get("description") or len(str(new_fm.get("description"))) < 10:
            new_fm["description"] = "规范化的自动化工程技能，包含明确的触发意图与负向边界。"
            applied_fixes.append("完善技能描述说明 (description)")

        if "tools" not in new_fm:
            new_fm["tools"] = []
            applied_fixes.append("规范 frontmatter tools 列表声明")

        new_body = body
        boundary_pats = ["when not to use", "do not", "边界约束", "负向判定", "严禁"]
        has_boundary = any(re.search(pat, new_body, re.IGNORECASE) for pat in boundary_pats)
        if not has_boundary:
            new_body += (
                "\n\n## 边界约束与负向判定 (Boundary Constraints)\n"
                "- **何时严禁使用**：当任务仅涉及非本领域常规问答，或已有专用底层指令时严禁使用；\n"
                "- **职责隔离**：超出本技能明确声明范围的诉求，必须立即阻断或交由对应领域代理处理。\n"
            )
            applied_fixes.append("注入标准负向边界约束与判定章节")

        if "```" not in new_body:
            new_body += (
                "\n\n## 典型执行示例 (Execution Examples)\n"
                "```bash\n"
                "# 典型工作流调用示例\n"
                "pytest -q\n"
                "```\n"
            )
            applied_fixes.append("注入标准代码块与执行流程示例")

        fm_yaml = yaml.dump(new_fm, allow_unicode=True, sort_keys=False).strip()
        optimized_content = f"---\n{fm_yaml}\n---\n\n{new_body.strip()}\n"

        opt_audit = self.audit_content(optimized_content)
        diff_summary = f"优化前得分 {orig_audit.total_score}分 ({orig_audit.grade}) ➔ 优化后达成 {opt_audit.total_score}分 ({opt_audit.grade})"

        return SkillOptOptimizeResult(
            original_score=orig_audit.total_score,
            optimized_score=opt_audit.total_score,
            applied_fixes=applied_fixes,
            optimized_content=optimized_content,
            diff_summary=diff_summary,
        )

    def batch_audit_skills(self, skills_dir: Optional[str] = None) -> BatchAuditSummary:
        """扫描本地已安装技能并汇总体检概览。"""
        target_dir = Path(skills_dir) if skills_dir else Path.home() / ".openviking" / "skills"
        results: List[SkillOptAuditResult] = []
        grade_counts = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}

        if target_dir.exists() and target_dir.is_dir():
            for skill_path in target_dir.glob("*/SKILL.md"):
                try:
                    content = skill_path.read_text(encoding="utf-8")
                    res = self.audit_content(content, skill_name=skill_path.parent.name)
                    results.append(res)
                    grade_counts[res.grade] = grade_counts.get(res.grade, 0) + 1
                except Exception:
                    continue

        if not results:
            ws_skills = Path.cwd() / ".agents" / "skills"
            if ws_skills.exists():
                for skill_path in ws_skills.glob("*/SKILL.md"):
                    try:
                        content = skill_path.read_text(encoding="utf-8")
                        res = self.audit_content(content, skill_name=skill_path.parent.name)
                        results.append(res)
                        grade_counts[res.grade] = grade_counts.get(res.grade, 0) + 1
                    except Exception:
                        continue

        total = len(results)
        avg_score = round(sum(r.total_score for r in results) / total, 1) if total > 0 else 0.0
        return BatchAuditSummary(
            total_audited=total,
            avg_score=avg_score,
            grade_counts=grade_counts,
            results=results,
        )

    # ------------------------------------------------------------------
    # 内部评估逻辑
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        if not match:
            return {}, content
        fm_text, body = match.group(1), match.group(2)
        try:
            parsed = yaml.safe_load(fm_text)
            return (parsed if isinstance(parsed, dict) else {}), body
        except Exception:
            return {}, body

    @staticmethod
    def _calc_grade(score: int) -> str:
        if score >= 90:
            return "S"
        if score >= 80:
            return "A"
        if score >= 70:
            return "B"
        if score >= 50:
            return "C"
        return "D"

    def _eval_spec_integrity(self, fm: Dict[str, Any]) -> DimensionScore:
        score = 0
        details: List[str] = []
        if fm:
            score += 10
            details.append("YAML Frontmatter 结构格式有效 (+10)")
        else:
            details.append("🚫 缺少或损坏的 YAML Frontmatter 标头 (-10)")

        name = fm.get("name")
        if name and isinstance(name, str) and len(name.strip()) > 0:
            score += 8
            details.append(f"技能名称 '{name}' 合规 (+8)")
        else:
            details.append("⚠️ 缺少有效 name 字段 (-8)")

        desc = fm.get("description")
        if desc and isinstance(desc, str) and len(desc.strip()) >= 10:
            score += 7
            details.append("技能描述详实 (+7)")
        else:
            details.append("⚠️ 描述字段缺失或过短 (-7)")

        status = "good" if score >= 20 else ("warning" if score >= 12 else "critical")
        return DimensionScore(name="spec_integrity", label="规范完整度", score=score, status=status, details=details)

    def _eval_tool_precision(self, fm: Dict[str, Any], body: str) -> DimensionScore:
        score = 0
        details: List[str] = []
        tools = fm.get("tools")
        if isinstance(tools, list):
            score += 10
            details.append(f"声明了 {len(tools)} 个调用工具 (+10)")
        elif "tools" in fm:
            score += 5
            details.append("⚠️ tools 字段类型非标准列表 (-5)")
        else:
            details.append("未显式声明工具列表")

        if any(w in body.lower() for w in ["tool", "mcp", "function", "api", "参数", "接口"]):
            score += 8
            details.append("正文包含工具调用与参数说明 (+8)")
        else:
            details.append("正文未显式说明工具调用契约")

        if "```" in body:
            score += 7
            details.append("提供可执行的代码块示例 (+7)")
        else:
            details.append("⚠️ 缺少具体代码调用示例 (-7)")

        score = min(25, score)
        status = "good" if score >= 18 else ("warning" if score >= 10 else "critical")
        return DimensionScore(name="tool_precision", label="能力与工具精准度", score=score, status=status, details=details)

    def _eval_token_density(self, lines: List[str], body: str) -> DimensionScore:
        score = 0
        details: List[str] = []
        n = len(lines)

        if 100 <= n <= 300:
            score += 12
            details.append(f"行数 {n} 处于 100~300 黄金甜点区 (+12)")
        elif (50 <= n < 100) or (301 <= n <= 400):
            score += 8
            details.append(f"行数 {n} 处于可用范围 (+8)")
        elif 401 <= n <= 500:
            score += 4
            details.append(f"⚠️ 行数 {n} 接近 500 行物理硬上限 (-8)")
        elif n > 500:
            score += 0
            details.append(f"🚫 行数 {n} 超出 500 行物理红线 (-12)")
        else:
            score += 5
            details.append(f"⚠️ 行数 {n} < 50，内容过于简略 (-7)")

        headers = len(re.findall(r"^#{1,3}\s+", body, re.MULTILINE))
        if headers >= 3:
            score += 8
            details.append(f"标题层级清晰 ({headers} 个小节) (+8)")
        else:
            details.append("⚠️ 章节层级过少，结构扁平 (-8)")

        if any(b in body for b in ["- [ ]", "- [x]", "1.", "2.", "- **"]):
            score += 5
            details.append("包含条理清晰的步骤清单 (+5)")

        score = min(25, score)
        if n > 500:
            status = "critical"
        else:
            status = "good" if score >= 18 else ("warning" if score >= 10 else "critical")
        return DimensionScore(name="token_density", label="注意力信噪比", score=score, status=status, details=details)

    def _eval_trigger_robustness(self, fm: Dict[str, Any], body: str) -> DimensionScore:
        score = 0
        details: List[str] = []
        desc = str(fm.get("description", ""))

        if any(w in desc.lower() or w in body.lower() for w in ["trigger", "触发", "关键词", "when to use"]):
            score += 10
            details.append("声明明确的意图触发关键词 (+10)")
        else:
            details.append("⚠️ 缺少明确的触发意图关键词 (-10)")

        boundary_pats = ["when not to use", "do not", "边界约束", "负向判定", "严禁", "禁止"]
        if any(re.search(pat, body, re.IGNORECASE) for pat in boundary_pats):
            score += 10
            details.append("包含负向边界约束 (When NOT to use) (+10)")
        else:
            details.append("⚠️ 缺少负向边界判定规则 (-10)")

        if len(desc) >= 30:
            score += 5
            details.append("意图描述具有高区分度 (+5)")

        score = min(25, score)
        status = "good" if score >= 18 else ("warning" if score >= 10 else "critical")
        return DimensionScore(name="trigger_robustness", label="触发区分度", score=score, status=status, details=details)
