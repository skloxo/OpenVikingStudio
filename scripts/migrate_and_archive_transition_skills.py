from pathlib import Path
import shutil
import json

skills_dir = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
archive_dir = Path("/home/skloxo/.openviking/data/viking/default/agent/skills_archive_transition")
archive_dir.mkdir(parents=True, exist_ok=True)

transition = [
    'adversarial-learning', 'agent-friendly-code-org', 'agent-governance-guardrails',
    'auto-pr', 'capability-bundle-crystallizer', 'cellular-cpe-ops',
    'clash_verge_governance', 'cluster-network-ops', 'cpa-squad',
    'deepseek-harness-ops', 'dev-runtime-decoupling', 'dify-ops',
    'global-agent-core', 'homepage-ops', 'keepass-vault', 'komari-ops',
    'mac-studio-remote-ops', 'master-dev', 'n8n-ops', 'network-search-ops',
    'openviking-master', 'openviking-memory-benchmark',
    'openviking-memory-plugin-architecture', 'openviking-model-evaluator',
    'openviking-ops', 'openviking-plugin-ops', 'openviking-studio-dev',
    'oracle-cloud-ops', 'satellite-fleet-ops', 'skill-state-fsm',
    'tide-trading-dev', 'wechat-article-reader', 'wikiskill-evolution'
]

print(f"Beginning safe migration of {len(transition)} transition directories to {archive_dir}...")
moved = []
for name in transition:
    src = skills_dir / name
    if src.exists() and src.is_dir():
        dst = archive_dir / name
        if dst.exists():
            shutil.rmtree(dst)
        shutil.move(str(src), str(dst))
        moved.append(name)
        print(f"  [MOVED] {name} -> {dst}")
    else:
        print(f"  [SKIPPED/NOT_FOUND] {name}")

print(f"\nSuccessfully moved {len(moved)} transition folders into archive.")

# Inspect remaining directories
remaining_dirs = sorted([d.name for d in skills_dir.iterdir() if d.is_dir()])
print(f"\nRemaining directories in skills root: {len(remaining_dirs)}")
for i, d in enumerate(remaining_dirs, 1):
    sc_count = len(list((skills_dir / d / "scenarios").glob("*.md"))) if (skills_dir / d / "scenarios").is_dir() else 0
    print(f"  {i:2d}. {d:26} ({sc_count} scenarios)")

# Test router
from openviking.service.skill_aliasing_router import SkillAliasingRouter
router = SkillAliasingRouter(skills_root=skills_dir)
alias_map = router.get_alias_map(force_refresh=True)

print(f"\nTotal Alias Map entries: {len(alias_map)}")
test_skills = ["auto-pr", "cellular-cpe-ops", "openviking-master", "tide-trading-dev", "capability-bundle-crystallizer"]
for s in test_skills:
    res = router.resolve(s)
    v_skill = router.get_virtual_skill(s)
    print(f"\nVirtual Projection Test for '{s}':")
    print(f"  resolve result: {res}")
    if v_skill:
        print(f"  v_skill name: {v_skill.get('name')}, parent: {v_skill.get('parent_bundle')}, is_virtual: {v_skill.get('is_virtual')}")
        print(f"  content preview: {v_skill.get('content')[:120].replace(chr(10), ' ')}...")
    else:
        print(f"  ERROR: v_skill is None!")
