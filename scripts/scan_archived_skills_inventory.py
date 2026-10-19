import os
from pathlib import Path

def scan_all_archived_skills():
    sources = [
        ("skills_archive", Path(r"C:\Users\Skl\.gemini\config\skills_archive")),
        ("data-agent-kit", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\data-agent-kit-plugin\skills")),
        ("firebase", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\firebase\skills")),
        ("flutter", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\flutter\skills")),
        ("science", Path(r"C:\Users\Skl\.gemini\config\plugins_archive\science\skills")),
    ]

    all_skills = {}
    duplicates = {}

    for label, base_path in sources:
        if not base_path.exists():
            print(f"[MISSING] {label}: {base_path}")
            continue
        count = 0
        for item in base_path.iterdir():
            if item.is_dir():
                skill_md = item / "SKILL.md"
                s_name = item.name
                if s_name in all_skills:
                    if s_name not in duplicates:
                        duplicates[s_name] = [all_skills[s_name]["source"]]
                    duplicates[s_name].append(label)
                else:
                    all_skills[s_name] = {
                        "source": label,
                        "path": item,
                        "has_skill_md": skill_md.exists(),
                        "skill_md_size": skill_md.stat().st_size if skill_md.exists() else 0
                    }
                count += 1
        print(f"[{label}] Found {count} directories.")

    print(f"\nTotal Unique Skills: {len(all_skills)}")
    print(f"Duplicate Names across sources: {len(duplicates)}")
    for d, srcs in duplicates.items():
        print(f"  - {d}: found in {srcs}")

    no_md = [k for k, v in all_skills.items() if not v["has_skill_md"]]
    print(f"\nSkills without SKILL.md: {len(no_md)}")
    if no_md:
        print("  Missing SKILL.md:", no_md)

if __name__ == "__main__":
    scan_all_archived_skills()
