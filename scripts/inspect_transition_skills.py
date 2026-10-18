from pathlib import Path
import json

skills_dir = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
dirs = [d.name for d in skills_dir.iterdir() if d.is_dir()]
bundles = [d for d in dirs if (skills_dir / d / "scenarios").is_dir()]
transition = [d for d in dirs if not (skills_dir / d / "scenarios").is_dir()]

print(f"Total: {len(dirs)}, Bundles: {len(bundles)}, Transition: {len(transition)}")
print("Bundles:", sorted(bundles))
print("Transition:", sorted(transition))

# Check which bundle each transition skill maps to
from openviking.service.skill_aliasing_router import SkillAliasingRouter
router = SkillAliasingRouter(skills_root=skills_dir)
alias_map = router.get_alias_map(force_refresh=True)

print(f"\nTotal Alias Map entries: {len(alias_map)}")
unmapped = []
for t in sorted(transition):
    res = router.resolve(t)
    # Note: resolve checks direct_path first, so resolve(t) would say "bundle" because directory t exists!
    # Let's see if t is in alias_map directly
    if t in alias_map:
        bundle, path = alias_map[t]
        print(f"  [MAPPED] {t} -> {bundle} ({path.name})")
    else:
        unmapped.append(t)
        print(f"  [UNMAPPED] {t}")

print(f"\nUnmapped count: {len(unmapped)}")
