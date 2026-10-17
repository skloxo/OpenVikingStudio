import os
import yaml
from pathlib import Path
from openviking.service.detail_preserving_merger import DetailPreservingMerger

skills_dir = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

for bundle_dir in sorted(skills_dir.iterdir()):
    if not bundle_dir.is_dir() or bundle_dir.name.startswith("."):
        continue
    skill_md = bundle_dir / "SKILL.md"
    if not skill_md.exists():
        continue
    content = skill_md.read_text(encoding="utf-8", errors="ignore")
    fm, _ = DetailPreservingMerger._split_frontmatter(content)
    
    abstract_meta = {
        "name": fm.get("name") or bundle_dir.name,
        "description": fm.get("description", f"Domain Capability Bundle for {bundle_dir.name}"),
        "tags": fm.get("tags") or [],
        "allowed_tools": fm.get("allowed_tools") or [],
        "triggers": fm.get("triggers") or [],
    }
    
    abstract_path = bundle_dir / ".abstract.md"
    abstract_path.write_text(yaml.safe_dump(abstract_meta, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Generated .abstract.md for {bundle_dir.name}")

print("All .abstract.md generated.")
