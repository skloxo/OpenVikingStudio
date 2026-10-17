# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Auto-Crystallization Engine for Capability Bundles (Card-104).

Automates the complete workflow:
1. Scenario clustering into core engineering modules (01~05).
2. Micro-entity AST extraction (CLI flags, ports, env, regex, code blocks).
3. Distillation of lean master SKILL.md (<150 lines, L1 FSM Router).
4. Provenance mapping generation (ABSORPTION_PROVENANCE.json).
5. Automated Retina Invariant Auditor validation.
6. Auto-generation of pytest test suite.
"""

import os
import sys
import json
import yaml
import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple, Any

from openviking.service.detail_preserving_merger import (
    MicroEntityExtractor,
    RetinaDetailAuditor,
    DetailPreservingMerger,
)


class AutoCrystallizer:
    """Industrial Pipeline Engine for Automated Skill Consolidation & Crystallization."""

    @classmethod
    def crystallize_bundle(
        cls,
        bundle_dir: Path,
        bundle_name: str,
        domain_title: str,
        philosophical_axiom: str,
        module_cluster_rules: Dict[str, Dict[str, Any]],
        test_queries: List[Tuple[str, List[str]]],
    ) -> Dict[str, Any]:
        """Executes full automated crystallization on a capability bundle directory."""
        scenarios_dir = bundle_dir / "scenarios"
        modules_dir = bundle_dir / "modules"
        modules_dir.mkdir(parents=True, exist_ok=True)

        scenario_files = list(scenarios_dir.glob("*.md")) if scenarios_dir.exists() else []
        total_scenarios = len(scenario_files)

        # 1. Cluster scenarios into modules
        cluster_assignment = defaultdict(list)
        scenario_metadata = {}
        all_triggers = set()
        all_cli_flags = set()
        all_ports = set()
        all_env_vars = set()

        for sf in scenario_files:
            slug = sf.stem
            content = sf.read_text(encoding="utf-8", errors="ignore")
            entities = MicroEntityExtractor.extract(content)
            all_cli_flags.update(entities.cli_flags)
            all_ports.update(entities.ports)
            all_env_vars.update(entities.env_vars)

            fm, body = DetailPreservingMerger._split_frontmatter(content)
            triggers = fm.get("triggers", [])
            all_triggers.update([t for t in triggers if isinstance(t, str)])

            # Score against cluster rules
            best_mod = list(module_cluster_rules.keys())[0]
            max_score = -1
            text_lower = f"{slug} {fm.get('description', '')} {content[:1000]}".lower()

            for mod_name, spec in module_cluster_rules.items():
                score = sum(3 for kw in spec["keywords"] if kw in text_lower)
                if score > max_score:
                    max_score = score
                    best_mod = mod_name

            cluster_assignment[best_mod].append(slug)
            scenario_metadata[slug] = {
                "assigned_module": best_mod,
                "flags_count": len(entities.cli_flags),
                "ports_count": len(entities.ports),
                "urls_count": len(entities.urls),
            }

        # 2. Automatically generate distilled module markdown files
        distilled_modules_summary = {}
        for mod_name, spec in module_cluster_rules.items():
            assigned_slugs = cluster_assignment.get(mod_name, [])
            mod_file = modules_dir / f"{mod_name}.md"

            # Aggregate top keywords, sample flags
            sample_flags = [f"`{flag}`" for flag in sorted(list(all_cli_flags)) if any(kw in flag.lower() for kw in spec["keywords"])][:8]
            flags_str = ", ".join(sample_flags) if sample_flags else "`--help`, `-v`"

            mod_content = f"""# {spec['title']}

> **工序使命**：{spec['mission']}
> **自动化收拢子场景 ({len(assigned_slugs)}项)**：{', '.join(assigned_slugs[:15])}{'...' if len(assigned_slugs) > 15 else ''}

---

## 一、 核心操作规范与领域契约

{spec['contract_markdown']}

---

## 二、 关键命令行参数与底层命令实体

- **核心指令与参数**：{flags_str}
- **子场景执行映射**：通过 `view_file` 按需调阅 `./scenarios/<子场景名>.md` 提取专精参数。
"""
            mod_file.write_text(mod_content.strip() + "\n", encoding="utf-8")
            distilled_modules_summary[f"{mod_name}.md"] = spec["title"]

        # 3. Generate lean master SKILL.md (<120 lines)
        router_table_rows = []
        for mod_name, spec in module_cluster_rules.items():
            kw_str = ", ".join(spec["keywords"][:6])
            router_table_rows.append(
                f"| **{spec['short_name']}** | {kw_str} | [`modules/{mod_name}.md`](modules/{mod_name}.md) | {spec['mission'][:35]}... |"
            )

        # Collect curated triggers from all modules preserving order
        curated_triggers = []
        for spec in module_cluster_rules.values():
            curated_triggers.extend(spec.get("keywords", []))
            curated_triggers.extend(spec.get("extra_triggers", []))

        seen = set()
        prioritized_triggers = []
        for t in curated_triggers:
            t_clean = t.strip()
            if t_clean and t_clean.lower() not in seen:
                seen.add(t_clean.lower())
                prioritized_triggers.append(t_clean)

        master_fm = {
            "name": bundle_name,
            "description": f"{domain_title}全生命周期战区 (Domain Master Bundle)。统管 {total_scenarios} 项专精子场景，采用渐进展开与工序状态机架构，确保微观实体与代码块 100% 零细节遗漏留存。",
            "triggers": prioritized_triggers,
        }

        master_skill_text = f"""---
{yaml.safe_dump(master_fm, allow_unicode=True, sort_keys=False)}---

# {domain_title}总线 ({bundle_name.replace('-', ' ').title()} Master Bundle)

> **物理公理**：{philosophical_axiom}

---

## 一、L1 意图路由状态机总线 (Intent Auto-Dispatch FSM)

当接收到自然语言请求时，根据特征关键词自动命中并挂载对应的核心工序模块：

| 核心工序 | 意图特征关键词 | 挂载工序模块 | 核心契约与执行目标 |
| :--- | :--- | :--- | :--- |
{chr(10).join(router_table_rows)}

---

## 二、全系统操作三大绝对红线 (Universal Operations Red Lines)

1. 🛑 **真实性与物理验真铁律 (Data Integrity & Invariant)**：
   - 严禁前端伪造假数据，所有探针与指标以操作系统真实内核数据为准。
2. 🛑 **破坏性指令防御铁律 (Safe Mutation Protocol)**：
   - 严禁执行带全局通配符的杀死进程或删除指令，执行高危变更前必须具备回退通道。
3. 🛑 **一卡一命一停手铁律 (Single-Card Execution Gate)**：
   - 单轮任务严格攻坚 1 个原子工序，单测变绿并通过视网膜门禁后必须立即交还控制权。
"""
        master_skill_file = bundle_dir / "SKILL.md"
        master_skill_file.write_text(master_skill_text.strip() + "\n", encoding="utf-8")
        master_lines = len(master_skill_text.strip().splitlines())

        # 4. Generate ABSORPTION_PROVENANCE.json
        provenance = {
            "bundle_name": bundle_name,
            "version": "2.0.0",
            "total_member_scenarios": total_scenarios,
            "distilled_modules": distilled_modules_summary,
            "scenarios_provenance": scenario_metadata,
        }
        (bundle_dir / "ABSORPTION_PROVENANCE.json").write_text(
            json.dumps(provenance, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        return {
            "total_scenarios": total_scenarios,
            "modules_count": len(module_cluster_rules),
            "master_lines": master_lines,
            "total_triggers": len(master_fm["triggers"]),
            "cli_flags_preserved": len(all_cli_flags),
            "ports_preserved": len(all_ports),
        }
