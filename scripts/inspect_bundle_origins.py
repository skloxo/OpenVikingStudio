from pathlib import Path
import json

skills_dir = Path("/home/skloxo/.openviking/data/viking/default/agent/skills")
for d in sorted(skills_dir.iterdir()):
    if not d.is_dir():
        continue
    prov_file = d / "ABSORPTION_PROVENANCE.json"
    sk_file = d / "SKILL.md"
    sc_dir = d / "scenarios"
    sc_count = len(list(sc_dir.glob("*.md"))) if sc_dir.is_dir() else 0

    if prov_file.exists():
        try:
            data = json.loads(prov_file.read_text(encoding="utf-8"))
            engine = data.get("engine_version", "")
            c_at = data.get("crystallized_at", "")
            sc_provenance = data.get("total_member_scenarios", 0)
            print(f"[PROV]    {d.name:26} | c_at={c_at} | sc_dir={sc_count:3d} | prov_sc={sc_provenance:3d} | {engine}")
        except Exception as e:
            print(f"[ERR]     {d.name:26} | {e}")
    else:
        # Check SKILL.md
        sk_desc = ""
        if sk_file.exists():
            for line in sk_file.read_text(encoding="utf-8").splitlines()[:10]:
                if line.startswith("description:"):
                    sk_desc = line[:70]
                    break
        print(f"[NO_PROV] {d.name:26} | sc_dir={sc_count:3d} | {sk_desc}")
