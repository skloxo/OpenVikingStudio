from pathlib import Path
import shutil

skills_dir = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

# 1. Ensure capability-bundle-crystallizer is in openviking/scenarios
src_cbc = skills_dir / "capability-bundle-crystallizer" / "SKILL.md"
dst_cbc = skills_dir / "openviking" / "scenarios" / "capability-bundle-crystallizer.md"
if src_cbc.exists() and not dst_cbc.exists():
    shutil.copy2(src_cbc, dst_cbc)
    print(f"Copied {src_cbc} -> {dst_cbc}")

# 2. Ensure web-search-pro scenario is in web-harvest-pro/scenarios
src_wsp = skills_dir / "web-search-pro" / "scenarios" / "web-search-pro.md"
dst_wsp = skills_dir / "web-harvest-pro" / "scenarios" / "web-search-pro.md"
if src_wsp.exists() and not dst_wsp.exists():
    shutil.copy2(src_wsp, dst_wsp)
    print(f"Copied {src_wsp} -> {dst_wsp}")

from openviking.service.skill_aliasing_router import SkillAliasingRouter
router = SkillAliasingRouter(skills_root=skills_dir)
alias_map = router.get_alias_map(force_refresh=True)

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

print(f"Checking all {len(transition)} transition skills against alias map:")
all_ok = True
for t in transition:
    if t in alias_map:
        bundle, path = alias_map[t]
        exists = path.exists()
        print(f"  [OK] {t:35} -> bundle [{bundle:22}], file exists: {exists}")
        if not exists:
            all_ok = False
    else:
        print(f"  [MISSING] {t}")
        all_ok = False

print(f"\nAll 33 Transition Skills Mapped & Exist: {all_ok}")
