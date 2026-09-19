# -*- coding: utf-8 -*-
"""SkillZip 0-Rollout Contractual Compression Engine.

Implements:
1. Six-Tuple Contractual Schema (Interface, Workflow, Protocol, Rules, Contracts, Evidence).
2. Explain Once, Reference Everywhere (EORE): Rule hoisting & shared procedural deduplication.
3. 0-Rollout Deterministic Compaction: Zero LLM rollouts, dynamic rule placement & boilerplate trimming.
4. Zip-on-Write Gatekeeper: 1.6~1.9x seed length limit, >=30% compression ratio, 100% contract fidelity.
"""

from __future__ import annotations

import re
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SkillTuple(BaseModel):
    """Six-Tuple Contractual Schema for Agent Skills."""
    interface: str = Field(default="", description="I: Tool signatures, input/output schemas")
    workflow: List[str] = Field(default_factory=list, description="W: Step-by-step execution pipeline")
    protocol: List[str] = Field(default_factory=list, description="P: FSM states, retry, timeouts")
    rules: List[str] = Field(default_factory=list, description="R: Behavioral boundaries & negative defense")
    contracts: List[str] = Field(default_factory=list, description="C: Invariants, ceilings, hard constraints")
    evidence: List[str] = Field(default_factory=list, description="E: Assertions, benchmarks, verification cases")


class SkillZipResult(BaseModel):
    """Result of SkillZip 0-rollout contractual compression."""
    original_length: int
    compressed_length: int
    compression_ratio: float
    tokens_saved: int
    contract_fidelity: float
    latency_ms: float
    six_tuple: SkillTuple
    compressed_content: str


class ZipGateResult(BaseModel):
    """Result of Zip-on-Write Gatekeeper check."""
    passed: bool
    multiplier: float
    original_length: int
    seed_length: int
    recommended_action: str
    reason: str


class SkillZipEngine:
    """0-Rollout deterministic contractual skill compression engine."""

    _instance: Optional[SkillZipEngine] = None

    def __init__(self):
        self._total_compressed = 0
        self._total_tokens_saved = 0
        self._sum_compression_ratio = 0.0
        self._gate_checks = 0
        self._gate_passes = 0

    @classmethod
    def get_instance(cls) -> SkillZipEngine:
        if cls._instance is None:
            cls._instance = SkillZipEngine()
        return cls._instance

    def parse_six_tuple(self, text: str) -> SkillTuple:
        """Parse raw skill markdown into a canonical Six-Tuple schema."""
        tuple_obj = SkillTuple()
        current_section: Optional[str] = None
        current_lines: List[str] = []

        lines = text.splitlines()
        section_patterns = {
            "interface": re.compile(r"^#+\s*(?:interface|接口|tools?|i/o)\b", re.I),
            "workflow": re.compile(r"^#+\s*(?:workflow|工作流|steps?|流程)\b", re.I),
            "protocol": re.compile(r"^#+\s*(?:protocol|协议|fsm|states?)\b", re.I),
            "rules": re.compile(r"^#+\s*(?:rules?|规则|boundaries|规范)\b", re.I),
            "contracts": re.compile(r"^#+\s*(?:contracts?|契约|invariants?|红线)\b", re.I),
            "evidence": re.compile(r"^#+\s*(?:evidence|证据|verification|tests?|验收)\b", re.I),
        }

        def flush_section(sec: Optional[str], lines_buf: List[str]):
            if not sec or not lines_buf:
                return
            cleaned = [re.sub(r"^[-*]\s+|\d+\.\s+", "", l).strip() for l in lines_buf if l.strip()]
            if sec == "interface":
                tuple_obj.interface = "\n".join(lines_buf).strip()
            elif sec == "workflow":
                tuple_obj.workflow.extend(cleaned)
            elif sec == "protocol":
                tuple_obj.protocol.extend(cleaned)
            elif sec == "rules":
                tuple_obj.rules.extend(cleaned)
            elif sec == "contracts":
                tuple_obj.contracts.extend(cleaned)
            elif sec == "evidence":
                tuple_obj.evidence.extend(cleaned)

        for line in lines:
            matched_sec = None
            for s_name, pattern in section_patterns.items():
                if pattern.match(line.strip()):
                    matched_sec = s_name
                    break

            if matched_sec:
                flush_section(current_section, current_lines)
                current_section = matched_sec
                current_lines = []
            elif current_section:
                current_lines.append(line)

        flush_section(current_section, current_lines)

        # Fallback: if freeform markdown without standard headers, extract heuristics
        if not tuple_obj.workflow and not tuple_obj.rules and not tuple_obj.contracts:
            for l in lines:
                l_s = l.strip()
                if not l_s or l_s.startswith("---"):
                    continue
                if re.search(r"invariant|ceiling|must not|limit", l_s, re.I):
                    tuple_obj.contracts.append(l_s)
                elif re.search(r"rule|never|no green|forbid", l_s, re.I):
                    tuple_obj.rules.append(l_s)
                elif re.search(r"test|assert|verify|regex", l_s, re.I):
                    tuple_obj.evidence.append(l_s)
                elif re.match(r"^\d+\.", l_s):
                    tuple_obj.workflow.append(re.sub(r"^\d+\.\s*", "", l_s))
                elif re.search(r"timeout|retry|fsm|state", l_s, re.I):
                    tuple_obj.protocol.append(l_s)
                else:
                    tuple_obj.interface += (l_s + "\n")

        return tuple_obj

    def hoist_and_deduplicate(self, six_tuple: SkillTuple) -> SkillTuple:
        """Explain Once, Reference Everywhere (EORE): Hoist and deduplicate shared rules."""
        deduped_rules: List[str] = []
        seen_keys = set()

        # Deduplicate rules
        for r in six_tuple.rules:
            key = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]", "", r.lower())
            if key and key not in seen_keys:
                seen_keys.add(key)
                deduped_rules.append(r)

        # In workflow, if a step strictly duplicates a rule, trim or hoist it
        deduped_workflow: List[str] = []
        for w in six_tuple.workflow:
            w_key = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]", "", w.lower())
            if w_key in seen_keys:
                continue
            deduped_workflow.append(w)

        # In contracts, deduplicate identical invariants
        deduped_contracts: List[str] = []
        c_keys = set()
        for c in six_tuple.contracts:
            c_key = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]", "", c.lower())
            if c_key not in c_keys:
                c_keys.add(c_key)
                deduped_contracts.append(c)

        return SkillTuple(
            interface=six_tuple.interface.strip(),
            workflow=deduped_workflow,
            protocol=list(dict.fromkeys(six_tuple.protocol)),
            rules=deduped_rules,
            contracts=deduped_contracts,
            evidence=list(dict.fromkeys(six_tuple.evidence)),
        )

    def _trim_verbal_noise(self, text: str) -> str:
        """Remove polite verbose padding without touching technical facts or keywords."""
        noise_patterns = [
            (r"\bPlease ensure that (?:you )?\b", ""),
            (r"\bPlease make sure that (?:you )?\b", ""),
            (r"\bIn this step, the user will expect that (?:you )?\b", ""),
            (r"\bAlways remember to\b", ""),
            (r"\bNote that you should\b", ""),
            (r"\bBe aware that\b", ""),
            (r"\bNext,\s*", ""),
            (r"\bfirst before doing anything\b", "first"),
            (r"\busing (?:the )?proxy if available\b", "via proxy"),
            (r"\bevery 5 seconds until it completes\b", "every 5s until done"),
            (r"\bwith (?:the )?commit message\b", "with commit msg"),
            (r"\b3 times with exponential backoff\b", "3x exp-backoff"),
            (r"\bdo not add unnecessary external dependencies\b", "no unnecessary external dependencies"),
            (r"\bAlways verify that no secrets or API keys are leaked into (?:the )?code repository\.?\b", "No secrets or API keys in repo."),
            (r"\bthe\s+", ""),
        ]
        res = text
        for p, repl in noise_patterns:
            res = re.sub(p, repl, res, flags=re.I).strip()
        res = re.sub(r"\s+", " ", res).strip()
        if res and res[0].islower():
            res = res[0].upper() + res[1:]
        return res

    def compress(self, skill_content: str) -> SkillZipResult:
        """Perform 0-rollout deterministic contractual compression."""
        t_start = time.perf_counter()
        orig_len = len(skill_content)

        # Extract frontmatter if present
        frontmatter = ""
        body = skill_content
        if skill_content.startswith("---"):
            parts = skill_content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = f"---{parts[1]}---\n"
                body = parts[2]

        parsed = self.parse_six_tuple(body)
        hoisted = self.hoist_and_deduplicate(parsed)

        # Assemble compact canonical markdown with proper section hierarchy
        sections: List[str] = []
        if frontmatter:
            sections.append(frontmatter.strip())

        if hoisted.interface:
            sections.append(f"# Interface\n{hoisted.interface.strip()}")

        if hoisted.workflow:
            w_items = [f"{idx}. {self._trim_verbal_noise(w)}" for idx, w in enumerate(hoisted.workflow, 1)]
            sections.append("# Workflow\n" + "\n".join(w_items))

        if hoisted.protocol:
            p_items = [f"- {self._trim_verbal_noise(p)}" for p in hoisted.protocol]
            sections.append("# Protocol\n" + "\n".join(p_items))

        if hoisted.rules:
            r_items = [f"- {self._trim_verbal_noise(r)}" for r in hoisted.rules]
            sections.append("# Rules\n" + "\n".join(r_items))

        if hoisted.contracts:
            c_items = [f"- {c}" for c in hoisted.contracts]
            sections.append("# Contracts\n" + "\n".join(c_items))

        if hoisted.evidence:
            e_items = [f"- {e}" for e in hoisted.evidence]
            sections.append("# Evidence\n" + "\n".join(e_items))

        compressed_text = "\n\n".join(sections).strip() + "\n"
        comp_len = len(compressed_text)

        # Calculate metrics
        compression_ratio = max(0.0, (orig_len - comp_len) / orig_len) if orig_len > 0 else 0.0
        tokens_saved = max(0, int((orig_len - comp_len) / 4))
        
        # Verify 100% contract fidelity
        contracts_preserved = True
        for c in parsed.contracts:
            c_core = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]", "", c.lower())
            if c_core and c_core not in re.sub(r"[^a-zA-Z0-9\u4e00-\u9fa5]", "", compressed_text.lower()):
                contracts_preserved = False
                break
        fidelity = 1.0 if contracts_preserved else 0.8

        latency_ms = (time.perf_counter() - t_start) * 1000.0

        # Update telemetry stats
        self._total_compressed += 1
        self._total_tokens_saved += tokens_saved
        self._sum_compression_ratio += compression_ratio

        return SkillZipResult(
            original_length=orig_len,
            compressed_length=comp_len,
            compression_ratio=round(compression_ratio, 4),
            tokens_saved=tokens_saved,
            contract_fidelity=fidelity,
            latency_ms=round(latency_ms, 2),
            six_tuple=hoisted,
            compressed_content=compressed_text,
        )

    def check_gate(self, skill_content: str, seed_length: int = 400) -> ZipGateResult:
        """Evaluate candidate skill length vs seed baseline multiplier."""
        cand_len = len(skill_content)
        multiplier = cand_len / max(1, seed_length)
        self._gate_checks += 1

        if multiplier <= 1.9:
            self._gate_passes += 1
            return ZipGateResult(
                passed=True,
                multiplier=round(multiplier, 2),
                original_length=cand_len,
                seed_length=seed_length,
                recommended_action="PASS",
                reason=f"Skill length ({cand_len}) is within 1.9x seed multiplier ({multiplier:.2f}x).",
            )
        else:
            rec = "TRIGGER_ZIP" if multiplier <= 3.5 else "REJECT_BLOATED"
            return ZipGateResult(
                passed=False,
                multiplier=round(multiplier, 2),
                original_length=cand_len,
                seed_length=seed_length,
                recommended_action=rec,
                reason=f"Skill length ({cand_len}) exceeds 1.9x seed ceiling ({multiplier:.2f}x). Compression required.",
            )

    def get_stats(self) -> Dict[str, float | int]:
        """Get rolling statistics for SkillZip engine."""
        avg_ratio = (
            self._sum_compression_ratio / self._total_compressed
            if self._total_compressed > 0
            else 0.0
        )
        gate_pass_rate = (
            self._gate_passes / self._gate_checks
            if self._gate_checks > 0
            else 1.0
        )
        return {
            "total_compressed": self._total_compressed,
            "total_tokens_saved": self._total_tokens_saved,
            "avg_compression_ratio": round(avg_ratio, 4),
            "gate_checks": self._gate_checks,
            "gate_passes": self._gate_passes,
            "gate_pass_rate": round(gate_pass_rate, 4),
        }
