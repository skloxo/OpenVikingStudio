import os
from pathlib import Path

paths = {
    "Global Config Skills": Path(r"C:\Users\Skl\.gemini\config\skills"),
    "Builtin Skills": Path(r"C:\Users\Skl\.gemini\antigravity-ide\builtin\skills"),
    "Work Workspace Skills": Path(r"C:\Users\Skl\Desktop\Work\.agents\skills"),
    "One Workspace Skills": Path(r"C:\Users\Skl\Desktop\One\.agents\skills"),
    "Coding Studio Skills": Path(r"C:\Users\Skl\Desktop\coding\OpenVikingStudio\.agents\skills"),
}

grand_total = 0
all_skill_names = []

for label, p in paths.items():
    if p.exists():
        dirs = [d.name for d in p.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
        print(f"[{label}] Count: {len(dirs)}")
        for d in dirs:
            all_skill_names.append((label, d))
        grand_total += len(dirs)
    else:
        print(f"[{label}] (Not Found)")

# Plugins skills
p_plugins = Path(r"C:\Users\Skl\.gemini\config\plugins")
if p_plugins.exists():
    p_skills_count = 0
    print("\n[Plugins Skills]")
    for pl in p_plugins.iterdir():
        if pl.is_dir():
            sk_dir = pl / "skills"
            if sk_dir.exists():
                sks = [d.name for d in sk_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]
                p_skills_count += len(sks)
                for s in sks:
                    all_skill_names.append((f"plugin:{pl.name}", s))
                print(f"  - {pl.name}: {len(sks)} skills ({', '.join(sks)})")
    print(f"Total Plugins Skills: {p_skills_count}")
    grand_total += p_skills_count

print(f"\n==========================================")
print(f"Grand Total Antigravity Skills: {grand_total}")
print(f"Unique Skill Names: {len(set(s[1] for s in all_skill_names))}")
print(f"==========================================")
