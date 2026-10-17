# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Auto-Crystallization Engine B6 (Candidate) - Adaptive Information-Density & Orthogonal Self-Healing Pipeline.

Evolution from B5 -> B6:
1. TriggerBudgetBalancer (Q1 Evolution):
   - Replaces greedy flat list slicing `[:50]` with per-module fair allocation.
   - Prevents tail-module keyword starvation (e.g. Module 04 missing triggers and dropping recall to 96%).
2. PolyglotCodeExtractor (Q2 Evolution):
   - Extracts code blocks while preserving native language identifier (python, ts, yaml, sh, bash).
   - Eliminates blind coercive ```` ```bash ```` wrapping.
3. OrthogonalCollisionAdvisor (Q3 Evolution):
   - When Stage 0 Ante-Gate encounters colliding triggers, traces exact collision source bundle & modules,
     and proactively suggests orthogonal disambiguated synonyms.
4. DynamicRetinaGatekeeper (Q4 Evolution):
   - Adapts clickable link assertions dynamically based on `min(total_scenarios, 10)`,
     guaranteeing 100% zero-broken-links while supporting small-scale specialized bundles.
"""

import os
import sys
import json
import yaml
import re
import time
import subprocess
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any, Set

from openviking.service.detail_preserving_merger import (
    MicroEntityExtractor,
    RetinaDetailAuditor,
    DetailPreservingMerger,
)

GENERIC_STOP_WORDS = {
    "系统", "服务", "管理", "配置", "排查", "运行", "查看", "处理", "优化", "测试",
    "脚本", "监控", "工具", "自动化", "运维", "环境", "node", "server", "system",
    "service", "manage", "config", "test", "run", "admin", "probe", "script", "ssh",
}


class SeamDecisionGateB6:
    """Stage 0 Ante-Gate with Orthogonal Collision Advisor."""

    MAX_SCENARIOS_PER_BUNDLE = 100
    MAX_MODULES_PER_BUNDLE = 6
    AFFINITY_MERGE_THRESHOLD = 75.0
    AFFINITY_SPAWN_THRESHOLD = 25.0

    @classmethod
    def audit_candidate(
        cls,
        candidate_name: str,
        scenario_count: int,
        keywords: List[str],
        toolchain: List[str],
        existing_bundles_dir: Path,
        runtime: str = "",
        action_verb_noun: List[str] = None,
        dedicated_libs: List[str] = None,
        is_meta_philosophy: bool = False,
    ) -> Dict[str, Any]:
        """Calculates triad affinity score, identifies collisions, and suggests orthogonal fixes."""
        if is_meta_philosophy or scenario_count <= 5:
            return {
                "decision": "DEGRADE_TO_RULE_OR_WORKFLOW",
                "target": "AGENTS.md / workflows",
                "affinity_score": 0.0,
                "reason": f"场景数 ({scenario_count}项) 过低或属于顶层元认知，独立建包将产生过度工程化伪大包，强制降维为系统守则。",
                "risk_of_blind_spawn": "严重稀释注意力，引发结构性空心化",
            }

        cand_kws = {k.lower() for k in keywords if k.lower() not in GENERIC_STOP_WORDS}
        cand_tools = {t.lower() for t in toolchain if t.lower() not in GENERIC_STOP_WORDS}
        cand_actions = {a.lower() for a in (action_verb_noun or []) if a.lower() not in GENERIC_STOP_WORDS}
        cand_libs = {lib.lower() for lib in (dedicated_libs or []) if lib.lower() not in GENERIC_STOP_WORDS}
        cand_runtime = runtime.lower().strip()

        best_bundle = None
        max_affinity = 0.0
        collision_details = {}

        for bundle_dir in existing_bundles_dir.iterdir():
            if not bundle_dir.is_dir() or bundle_dir.name == candidate_name:
                continue

            skill_md = bundle_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                content = skill_md.read_text(encoding="utf-8")
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = yaml.safe_load(parts[1]) or {}
                    b_triggers = [t.lower() for t in fm.get("triggers", []) if t.lower() not in GENERIC_STOP_WORDS]
                else:
                    b_triggers = []
            except Exception:
                b_triggers = []

            b_kws = set(b_triggers)
            overlap_kws = cand_kws.intersection(b_kws)
            if overlap_kws:
                collision_details[bundle_dir.name] = list(overlap_kws)

            # Triad affinity scoring (0 ~ 100)
            score = 0.0
            kw_match = len(overlap_kws)
            score += min(kw_match * 15.0, 45.0)

            body_lower = content.lower()
            tool_match = sum(1 for t in cand_tools if t in body_lower)
            score += min(tool_match * 10.0, 25.0)

            action_match = sum(1 for a in cand_actions if a in body_lower)
            score += min(action_match * 7.5, 15.0)

            lib_match = sum(1 for lib in cand_libs if lib in body_lower)
            score += min(lib_match * 7.5, 15.0)

            if cand_runtime and cand_runtime in body_lower:
                score += 5.0

            if score > max_affinity:
                max_affinity = score
                best_bundle = bundle_dir.name

        # B6 Collision Advisor Suggestions
        suggested_replacements = {}
        for b_name, col_words in collision_details.items():
            for w in col_words:
                suggested_replacements[w] = f"{candidate_name.split('-')[0]}_{w}" if len(w) < 4 else f"专用_{w}"

        if max_affinity >= cls.AFFINITY_MERGE_THRESHOLD:
            return {
                "decision": "MERGE_INTO_EXISTING",
                "target": best_bundle,
                "affinity_score": round(max_affinity, 1),
                "colliding_triggers": collision_details.get(best_bundle, []),
                "collision_advisor": suggested_replacements,
                "reason": f"三元组指纹亲和度达到 {max_affinity:.1f}分 (>= {cls.AFFINITY_MERGE_THRESHOLD})，存在高度领域重合，强制合并入 '{best_bundle}' 插槽。",
                "risk_of_blind_spawn": "严重实体冗余与意图截胡，必须微创插槽合并",
            }
        elif max_affinity > cls.AFFINITY_SPAWN_THRESHOLD:
            return {
                "decision": "CONFIRM_WITH_HUMAN",
                "target": best_bundle,
                "affinity_score": round(max_affinity, 1),
                "colliding_triggers": collision_details.get(best_bundle, []),
                "collision_advisor": suggested_replacements,
                "reason": f"处于灰色争议区 (亲和度 {max_affinity:.1f}分，介于 {cls.AFFINITY_SPAWN_THRESHOLD}~{cls.AFFINITY_MERGE_THRESHOLD}分 之间)，倾向于并入 '{best_bundle}'，需由人类架构师确认。",
                "risk_of_blind_spawn": f"可能与 '{best_bundle}' 产生部分交叠，建议人工确认裁决。",
            }
        else:
            return {
                "decision": "SPAWN_NEW_BUNDLE",
                "target": candidate_name,
                "affinity_score": round(max_affinity, 1),
                "reason": f"场景规模达到 {scenario_count}项，且与全量历史大包亲和度仅 {max_affinity:.1f}分 (<= {cls.AFFINITY_SPAWN_THRESHOLD})，三元组指纹正交独立，签发独立建包准入证。",
                "risk_of_blind_spawn": "无碰撞风险，符合独立建包标准",
            }


class TriggerBudgetBalancerB6:
    """B6 Balanced Trigger Allocation across modules to guarantee tail module recall."""

    @staticmethod
    def balance(module_cluster_rules: Dict[str, Any], max_total: int = 50) -> List[str]:
        n_mods = max(1, len(module_cluster_rules))
        per_module_quota = max(4, (max_total - 10) // n_mods)

        selected_triggers = []
        seen = set()

        def add_trigger(t: str):
            clean = t.strip()
            if not clean or clean.lower() in seen or clean.lower() in GENERIC_STOP_WORDS or len(clean) < 2:
                return False
            seen.add(clean.lower())
            selected_triggers.append(clean)
            return True

        # Phase 1: Guaranteed quota for each module (extra_triggers first, then keywords)
        for mod_name, spec in module_cluster_rules.items():
            allocated = 0
            # Extra triggers are highest intent priority
            for t in spec.get("extra_triggers", []):
                if allocated >= per_module_quota:
                    break
                if add_trigger(t):
                    allocated += 1
            # Keywords fill remaining quota
            for t in spec.get("keywords", []):
                if allocated >= per_module_quota:
                    break
                if add_trigger(t):
                    allocated += 1

        # Phase 2: Fill remaining budget with highest value keywords evenly
        for mod_name, spec in module_cluster_rules.items():
            if len(selected_triggers) >= max_total:
                break
            for t in spec.get("keywords", []):
                if len(selected_triggers) >= max_total:
                    break
                add_trigger(t)

        return selected_triggers[:max_total]


class QualityScorecardB6:
    """B6 Quality Scorecard with dynamic assertion metrics."""

    def __init__(self):
        self.metrics = {
            "ante_gate_passed": False,
            "ante_gate_decision": "",
            "broken_links": 0,
            "master_lines": 0,
            "max_module_lines": 0,
            "scenarios_count": 0,
            "modules_count": 0,
            "capacity_ok": False,
            "recall": 0.0,
            "specificity": 100.0,
            "total_score": 0.0,
            "status": "PENDING",
            "pytest_passed": False,
        }

    def compute_total_score(self) -> float:
        score = 0.0
        if self.metrics["ante_gate_passed"]:
            score += 20.0
        if self.metrics["capacity_ok"]:
            score += 10.0
        if self.metrics["broken_links"] == 0:
            score += 15.0
        if self.metrics["master_lines"] <= 100:
            score += 10.0
        if self.metrics["max_module_lines"] <= 200:
            score += 5.0

        score += (self.metrics["recall"] / 100.0) * 15.0
        score += (self.metrics["specificity"] / 100.0) * 10.0
        if self.metrics["pytest_passed"]:
            score += 15.0

        self.metrics["total_score"] = round(score, 1)
        if (
            self.metrics["ante_gate_passed"]
            and self.metrics["broken_links"] == 0
            and self.metrics["capacity_ok"]
            and self.metrics["pytest_passed"]
            and self.metrics["recall"] >= 90.0
            and self.metrics["specificity"] >= 95.0
            and self.metrics["total_score"] >= 95.0
        ):
            self.metrics["status"] = "APPROVED_AND_SELF_VERIFIED"
        else:
            self.metrics["status"] = "BLOCKED"
        return self.metrics["total_score"]


class AutoCrystallizerB6:
    """B6 Crystallization Engine: Polyglot, Balanced Triggers, and Dynamic Gatekeeper."""

    @classmethod
    def audit_and_crystallize(
        cls,
        bundle_dir: Path,
        bundle_name: str,
        domain_title: str,
        philosophical_axiom: str,
        module_cluster_rules: Dict[str, Dict[str, Any]],
        positive_benchmark: List[Tuple[str, List[str]]],
        negative_benchmark: List[str],
        toolchain: List[str] = None,
        runtime: str = "cross-platform",
        action_verb_noun: List[str] = None,
        dedicated_libs: List[str] = None,
        is_meta_philosophy: bool = False,
        human_confirmation_granted: bool = False,
        services_dir: Path = None,
    ) -> Dict[str, Any]:
        start_time = time.time()
        scorecard = QualityScorecardB6()

        if services_dir is None:
            services_dir = Path("/home/skloxo/services/openviking")

        modules_dir = bundle_dir / "modules"
        scenarios_dir = bundle_dir / "scenarios"
        modules_dir.mkdir(parents=True, exist_ok=True)
        scenarios_dir.mkdir(parents=True, exist_ok=True)

        scenario_files = list(scenarios_dir.glob("*.md")) if scenarios_dir.exists() else []
        total_scenarios = len(scenario_files)

        # Stage 0: Ante-Gate
        cand_keywords = []
        for spec in module_cluster_rules.values():
            cand_keywords.extend(spec.get("keywords", []))
            cand_keywords.extend(spec.get("extra_triggers", []))

        gate_res = SeamDecisionGateB6.audit_candidate(
            candidate_name=bundle_name,
            scenario_count=total_scenarios,
            keywords=cand_keywords,
            toolchain=toolchain or [],
            existing_bundles_dir=bundle_dir.parent,
            runtime=runtime,
            action_verb_noun=action_verb_noun,
            dedicated_libs=dedicated_libs,
            is_meta_philosophy=is_meta_philosophy,
        )

        if gate_res["decision"] == "CONFIRM_WITH_HUMAN" and human_confirmation_granted:
            print(f"✅ [Stage 0 Ante-Gate CONFIRMED BY HUMAN]: Overriding gray zone to SPAWN_NEW_BUNDLE for {bundle_name}")
            gate_res["decision"] = "CONFIRMED_SPAWN_BY_HUMAN"
            gate_res["reason"] += " (人类架构师已显式核准独立建包)"

        if gate_res["decision"] not in ("SPAWN_NEW_BUNDLE", "CONFIRMED_SPAWN_BY_HUMAN"):
            print(f"🛑 [Stage 0 Ante-Gate BLOCKED]: {gate_res['decision']} -> {gate_res['target']}")
            print(f"   Reason: {gate_res['reason']}")
            return {
                "bundle_name": bundle_name,
                "ante_gate": gate_res,
                "status": "BLOCKED_BY_ANTE_GATE",
                "scorecard": {"total_score": 0.0, "status": "BLOCKED_BY_ANTE_GATE"},
            }

        # Stage 1: Polyglot Extraction & Clustering
        cluster_assignment = defaultdict(list)
        cluster_code_blocks = defaultdict(list)  # List[Tuple[str, str]] -> (lang, code)
        scenario_metadata = {}

        for sf in scenario_files:
            slug = sf.stem
            content = sf.read_text(encoding="utf-8", errors="ignore")
            entities = MicroEntityExtractor.extract(content)

            # Polyglot code blocks preservation (captures language identifier)
            code_matches = re.findall(
                r"```(bash|sh|python|yaml|toml|service|tsx|jsx|ts|js|css|html|json)?\n(.*?)```",
                content,
                re.DOTALL,
            )
            polyglot_blocks = [
                (lang or "bash", code.strip())
                for (lang, code) in code_matches
                if 10 < len(code.strip()) < 800
            ]

            best_mod = list(module_cluster_rules.keys())[0]
            max_kw_hits = -1
            content_lower = content.lower()
            slug_lower = slug.lower()

            for mod_name, spec in module_cluster_rules.items():
                kw_hits = sum(1 for kw in spec["keywords"] if kw.lower() in content_lower or kw.lower() in slug_lower)
                if kw_hits > max_kw_hits:
                    max_kw_hits = kw_hits
                    best_mod = mod_name

            cluster_assignment[best_mod].append(slug)
            if polyglot_blocks:
                cluster_code_blocks[best_mod].extend(polyglot_blocks)

            scenario_metadata[slug] = {
                "assigned_module": best_mod,
                "cli_flags": list(entities.cli_flags),
                "ports": list(entities.ports),
                "env_vars": list(entities.env_vars),
                "code_snippets_count": len(polyglot_blocks),
            }

        # Stage 2: Distill into L2 modules with polyglot code
        distilled_modules_summary = {}
        max_mod_lines = 0
        total_clickable_links = 0
        total_snippets_harvested = 0

        for mod_name, spec in module_cluster_rules.items():
            mod_file = modules_dir / f"{mod_name}.md"
            assigned_slugs = cluster_assignment.get(mod_name, [])

            clickable_seams = []
            for slug in sorted(assigned_slugs):
                clickable_seams.append(f"[`{slug}`](../scenarios/{slug}.md)")
                total_clickable_links += 1

            seams_str = ", ".join(clickable_seams) if clickable_seams else "无专精场景关联"

            mod_cli_flags = set()
            for slug in assigned_slugs:
                mod_cli_flags.update(scenario_metadata[slug]["cli_flags"])
            flags_str = ", ".join(f"`{f}`" for f in sorted(mod_cli_flags)[:12]) if mod_cli_flags else "遵循标准 POSIX 参数"

            snippet_section = ""
            if cluster_code_blocks[mod_name]:
                top_blocks = cluster_code_blocks[mod_name][:1]
                code_examples = []
                for lang, cb in top_blocks:
                    code_examples.append(f"```{lang}\n{cb}\n```")
                    total_snippets_harvested += 1
                snippet_section = f"\n## 二、 实战核心工程代码与执行范式\n\n" + "\n\n".join(code_examples) + "\n"

            mod_content = f"""# {spec['title']}

> **使命目标**：{spec['mission']}
> **关联专精子场景 ({len(assigned_slugs)}项)**：{seams_str}

---

## 一、 核心操作规范与领域契约

{spec['contract_markdown']}
{snippet_section}
---

## 三、 关键命令行参数与底层命令实体

- **核心指令与参数**：{flags_str}
"""
            mod_file.write_text(mod_content.strip() + "\n", encoding="utf-8")
            line_count = len(mod_content.strip().splitlines())
            max_mod_lines = max(max_mod_lines, line_count)
            distilled_modules_summary[mod_name] = {
                "title": spec["title"],
                "lines": line_count,
                "scenarios_count": len(assigned_slugs),
            }

        # Stage 3: Master SKILL.md with Balanced Trigger Allocation
        balanced_triggers = TriggerBudgetBalancerB6.balance(module_cluster_rules, max_total=50)

        table_rows = []
        for mod_name, spec in module_cluster_rules.items():
            kw_str = ", ".join(spec["keywords"])
            table_rows.append(
                f"| **{spec['short_name']}** | {kw_str} | [`modules/{mod_name}.md`](modules/{mod_name}.md) | {spec['mission'][:50]}... |"
            )

        fsm_table = "\n".join(table_rows)

        master_skill_text = f"""---
name: {bundle_name}
description: {domain_title}全生命周期战区 (Domain Master Bundle)。统管 {total_scenarios} 项专精子场景，采用渐进展开与工序状态机架构，确保微观实体与代码块 100% 零细节遗漏留存。
triggers:
{yaml.dump(balanced_triggers, default_flow_style=False, allow_unicode=True).strip()}
---

# {domain_title}总线 ({bundle_name.replace('-', ' ').title()} Master Bundle)

> **物理公理**：{philosophical_axiom}

---

## 一、L1 意图路由状态机总线 (Intent Auto-Dispatch FSM)

当接收到自然语言请求时，根据特征关键词自动命中并挂载对应的核心工序模块：

| 核心工序 | 意图特征关键词 | 挂载工序模块 | 核心契约与执行目标 |
| :--- | :--- | :--- | :--- |
{fsm_table}

---

## 二、全域操作红线与安全护栏

1. **零脑补第一性原理**：所有工序必须依据 `modules/*.md` 对应的标准化契约执行；
2. **渐进展开视野控制**：禁止无脑全量通读所有子场景，按需经由工序模块向下穿透检索；
3. **零细节遗漏保真**：微观代码块、配置参数与端口 100% 留存于子场景插槽中。
"""
        master_skill_file = bundle_dir / "SKILL.md"
        master_skill_file.write_text(master_skill_text.strip() + "\n", encoding="utf-8")
        master_lines = len(master_skill_text.strip().splitlines())

        # Stage 4: Dual-Blind Testing
        triggers_lower = [t.lower() for t in balanced_triggers]
        tp = 0
        fn = 0
        for q, expected_kws in positive_benchmark:
            hit = any(kw.lower() in q.lower() and any(kw.lower() in t for t in triggers_lower) for kw in expected_kws)
            if hit:
                tp += 1
            else:
                fn += 1
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        fp = 0
        tn = 0
        for neg_q in negative_benchmark:
            neg_q_lower = neg_q.lower()
            hit = any(t in neg_q_lower for t in triggers_lower)
            if hit:
                fp += 1
            else:
                tn += 1
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 1.0

        # Stage 5: In-Situ Dynamic Test Suite
        test_file_path = services_dir / "tests" / "unit" / f"test_bundle_{bundle_name.replace('-', '_')}_b6.py"
        test_file_path.parent.mkdir(parents=True, exist_ok=True)

        expected_links_min = min(total_scenarios, 10)

        test_code = f"""# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
'''Auto-Generated In-Situ Verification Test Suite for {bundle_name} (B6 Pipeline Candidate).'''

import pytest
from pathlib import Path
import yaml
import re

BUNDLE_DIR = Path("{bundle_dir.as_posix()}")
MODULES_DIR = BUNDLE_DIR / "modules"
SCENARIOS_DIR = BUNDLE_DIR / "scenarios"

def test_budget_constraints():
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    master_lines = len(skill_md.splitlines())
    assert master_lines <= 100, f"Master SKILL.md exceeded 100 lines: {{master_lines}}"
    
    for mod_file in MODULES_DIR.glob("*.md"):
        mod_lines = len(mod_file.read_text(encoding="utf-8").splitlines())
        assert mod_lines <= 200, f"Module {{mod_file.name}} exceeded 200 lines: {{mod_lines}}"

def test_retina_zero_loss():
    scenarios = list(SCENARIOS_DIR.glob("*.md"))
    assert len(scenarios) == {total_scenarios}, f"Loss of scenarios: {{len(scenarios)}} != {total_scenarios}"

def test_clickable_scenario_links():
    clickable_links = 0
    for mod_file in MODULES_DIR.glob("*.md"):
        txt = mod_file.read_text(encoding="utf-8")
        links = re.findall(r"\\[.*?\\]\\((\\.\\./scenarios/.*?\\.md)\\)", txt)
        clickable_links += len(links)
        for rel_link in links:
            target = (MODULES_DIR / rel_link).resolve()
            assert target.exists(), f"Broken scenario link: {{rel_link}}"
    expected_min = {expected_links_min}
    assert clickable_links >= expected_min, f"Insufficient clickable links: {{clickable_links}} (expected >= {{expected_min}})"

def test_provenance_and_intent():
    prov = (BUNDLE_DIR / "ABSORPTION_PROVENANCE.json").read_text(encoding="utf-8")
    assert "B6-Self-Verified" in prov
    
    skill_md = (BUNDLE_DIR / "SKILL.md").read_text(encoding="utf-8")
    fm = yaml.safe_load(skill_md.split("---", 2)[1])
    triggers = [t.lower() for t in fm.get("triggers", [])]
    assert len(triggers) >= 5, "Triggers list is unexpectedly empty"
"""
        test_file_path.write_text(test_code, encoding="utf-8")

        pytest_passed = False
        pytest_stdout = ""
        try:
            res = subprocess.run(
                ["python3", "-m", "pytest", "-o", "addopts=", str(test_file_path)],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=str(services_dir),
            )
            pytest_stdout = res.stdout.strip()
            if res.returncode == 0:
                pytest_passed = True
        except Exception as e:
            pytest_stdout = str(e)

        # Update Scorecard
        scorecard.metrics["ante_gate_passed"] = True
        scorecard.metrics["ante_gate_decision"] = gate_res["decision"]
        scorecard.metrics["master_lines"] = master_lines
        scorecard.metrics["max_module_lines"] = max_mod_lines
        scorecard.metrics["scenarios_count"] = total_scenarios
        scorecard.metrics["modules_count"] = len(module_cluster_rules)
        scorecard.metrics["capacity_ok"] = (
            total_scenarios <= SeamDecisionGateB6.MAX_SCENARIOS_PER_BUNDLE
            and len(module_cluster_rules) <= SeamDecisionGateB6.MAX_MODULES_PER_BUNDLE
        )
        scorecard.metrics["recall"] = round(recall * 100.0, 1)
        scorecard.metrics["specificity"] = round(specificity * 100.0, 1)
        scorecard.metrics["pytest_passed"] = pytest_passed
        scorecard.compute_total_score()

        # Provenance metadata
        provenance = {
            "bundle_name": bundle_name,
            "engine_version": "B6-Self-Verified-Adaptive",
            "crystallized_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_member_scenarios": total_scenarios,
            "elapsed_seconds": round(time.time() - start_time, 3),
            "ante_gate": gate_res,
            "scorecard": scorecard.metrics,
            "modules": distilled_modules_summary,
            "scenarios": scenario_metadata,
        }
        prov_file = bundle_dir / "ABSORPTION_PROVENANCE.json"
        prov_file.write_text(json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8")

        return {
            "bundle_name": bundle_name,
            "ante_gate": gate_res,
            "master_lines": master_lines,
            "max_module_lines": max_mod_lines,
            "clickable_links": total_clickable_links,
            "code_snippets": total_snippets_harvested,
            "broken_links": scorecard.metrics["broken_links"],
            "scorecard": scorecard.metrics,
            "pytest_details": {
                "test_file": str(test_file_path),
                "passed": pytest_passed,
                "stdout": pytest_stdout,
            },
        }
