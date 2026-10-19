import shutil
from pathlib import Path

def purge_unneeded_bundles():
    skills_root = Path(r"\\wsl.localhost\Ubuntu-24.04\home\skloxo\.openviking\data\viking\default\agent\skills")
    if not skills_root.exists():
        skills_root = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")

    # 1. 物理移除 3 个独立大包
    targets = ["cloud-data-analytics", "mobile-app-dev", "science-research"]
    for t in targets:
        p = skills_root / t
        if p.exists():
            shutil.rmtree(str(p))
            print(f"[PURGED BUNDLE] {t}")

    # 2. 从 cloud-infra-ops 移除 13 个 firebase 相关场景
    infra_scenarios = skills_root / "cloud-infra-ops" / "scenarios"
    firebase_stems = [
        "extension_to_functions_codebase",
        "firebase_ai_logic_basics",
        "firebase_app_hosting_basics",
        "firebase_auth_basics",
        "firebase_basics",
        "firebase_crashlytics",
        "firebase_data_connect_basics",
        "firebase_firestore",
        "firebase_hosting_basics",
        "firebase_remote_config_basics",
        "firebase_security_rules_auditor",
        "firestore_rules_creation",
        "xcode_project_setup",
    ]
    if infra_scenarios.exists():
        for fb in firebase_stems:
            f = infra_scenarios / f"{fb}.md"
            if f.exists():
                f.unlink()
                print(f"[PURGED SCENARIO] {fb}.md")

    # 3. 清理 modules 中的死链
    infra_modules = skills_root / "cloud-infra-ops" / "modules"
    if infra_modules.exists():
        for mf in infra_modules.glob("*.md"):
            lines = mf.read_text(encoding="utf-8").splitlines(keepends=True)
            clean_lines = []
            for l in lines:
                if any(fb in l for fb in firebase_stems):
                    continue
                clean_lines.append(l)
            mf.write_text("".join(clean_lines), encoding="utf-8")

    # 4. 统计现存母包
    remaining = [d.name for d in skills_root.iterdir() if d.is_dir() and not d.name.startswith(".")]
    print(f"\n[REMAINING BUNDLES] Count: {len(remaining)}")
    for r in sorted(remaining):
        print(f"  - {r}")

if __name__ == "__main__":
    purge_unneeded_bundles()
