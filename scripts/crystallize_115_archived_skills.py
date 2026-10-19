import os
import re
import yaml
from pathlib import Path

def crystallize_115_archived_skills():
    # 目标技能库路径 (WSL 映射路径)
    wsl_skills_root = Path(r"\\wsl.localhost\Ubuntu-24.04\home\skloxo\.openviking\data\viking\default\agent\skills")
    if not wsl_skills_root.exists():
        # 本地 fallback 路径
        wsl_skills_root = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

    sources = [
        ("data-agent-kit", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\data-agent-kit-plugin\skills"), "cloud-data-analytics"),
        ("firebase", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\firebase\skills"), "cloud-infra-ops"),
        ("flutter", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\flutter\skills"), "mobile-app-dev"),
        ("science", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\science\skills"), "science-research"),
    ]

    # 定义新自立母包的元数据底册
    new_bundle_meta = {
        "science-research": {
            "name": "science-research",
            "description": "生命科学、生物医学数据库与前沿科研文献检索综合母包 (AlphaFold, PubMed, PubChem, BLAST, UniProt 等 40 大科研场景)。",
            "triggers": ["pubmed", "alphafold", "pubchem", "blast", "uniprot", "chembl", "clinvar", "生命科学", "生物医药", "文献检索"],
            "module_name": "database-retrieval.md"
        },
        "mobile-app-dev": {
            "name": "mobile-app-dev",
            "description": "Flutter 与 Dart 跨平台移动端应用研发、状态管理、响应式布局与自动化测试母包 (25 大移动研发场景)。",
            "triggers": ["flutter", "dart", "移动端", "app开发", "flutter测试", "responsive layout", "ffi"],
            "module_name": "cross-platform.md"
        },
        "cloud-data-analytics": {
            "name": "cloud-data-analytics",
            "description": "GCP 云端大数据工程、分析流水线与数据治理母包 (BigQuery, Dataflow, Airflow, Spark, dbt 等 37 大数据场景)。",
            "triggers": ["bigquery", "dataflow", "airflow", "spark", "dbt", "dataform", "大数据", "数据管道", "gcp数据"],
            "module_name": "data-pipelines.md"
        }
    }

    total_crystallized = 0
    bundle_scenario_counts = {}

    for src_label, src_path, target_bundle in sources:
        if not src_path.exists():
            print(f"[MISSING SOURCE] {src_path}")
            continue

        target_bundle_dir = wsl_skills_root / target_bundle
        scenarios_dir = target_bundle_dir / "scenarios"
        modules_dir = target_bundle_dir / "modules"
        scenarios_dir.mkdir(parents=True, exist_ok=True)
        modules_dir.mkdir(parents=True, exist_ok=True)

        # 确保 Master SKILL.md 存在
        master_skill_md = target_bundle_dir / "SKILL.md"
        if not master_skill_md.exists():
            b_meta = new_bundle_meta.get(target_bundle, {
                "name": target_bundle,
                "description": f"专业领域能力母包: {target_bundle}",
                "triggers": [target_bundle.replace("-", " ")],
                "module_name": "core.md"
            })
            triggers_yaml = "\n".join([f"  - \"{t}\"" for t in b_meta["triggers"]])
            master_content = f"""---
name: {target_bundle}
description: "{b_meta['description']}"
version: 1.0.0
triggers:
{triggers_yaml}
allowed-tools:
  - run_command
  - view_file
  - search_web
---

# 🏛️ {b_meta['name']} 领域能力中枢 (Domain Master Spec)

本母包严格收敛 {b_meta['description']}，遵循单一事实源 (SSOT) 与模块化解耦规范。

## 🧩 核心功能模块 (Modules)

- [`modules/{b_meta['module_name']}`](modules/{b_meta['module_name']}): 核心业务场景与操作指引
"""
            master_skill_md.write_text(master_content, encoding="utf-8")
            print(f"[NEW BUNDLE SPAWNED] {target_bundle} at {master_skill_md}")

        # 获取默认模块文件
        mod_file = modules_dir / new_bundle_meta.get(target_bundle, {}).get("module_name", "general.md")
        if not mod_file.exists():
            mod_file.write_text(f"# {target_bundle} 核心场景索引\n\n", encoding="utf-8")

        mod_content = mod_file.read_text(encoding="utf-8")

        for skill_dir in src_path.iterdir():
            if not skill_dir.is_dir():
                continue
            src_md = skill_dir / "SKILL.md"
            if not src_md.exists():
                continue

            raw_text = src_md.read_text(encoding="utf-8")
            s_name = skill_dir.name
            target_scenario_file = scenarios_dir / f"{s_name}.md"

            # 写入 scenarios
            target_scenario_file.write_text(raw_text, encoding="utf-8")
            total_crystallized += 1
            bundle_scenario_counts[target_bundle] = bundle_scenario_counts.get(target_bundle, 0) + 1

            # 挂载链接到 module
            link_entry = f"- [`{s_name}`](../scenarios/{s_name}.md): {s_name} 业务工序指引\n"
            if s_name not in mod_content:
                mod_content += link_entry

        mod_file.write_text(mod_content, encoding="utf-8")
        print(f"[{src_label} -> {target_bundle}] Processed {bundle_scenario_counts.get(target_bundle, 0)} scenarios.")

    print(f"\n[CRYSTALLIZATION COMPLETE] Total Scenarios Processed: {total_crystallized}")
    for b, cnt in bundle_scenario_counts.items():
        print(f"  - {b}: +{cnt} scenarios")

if __name__ == "__main__":
    crystallize_115_archived_skills()
