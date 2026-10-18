from pathlib import Path
import json
import urllib.request
import re

conf_file = Path("/home/skloxo/.openviking/ov.conf")
conf_text = conf_file.read_text(encoding="utf-8") if conf_file.exists() else ""
match = re.search(r'"root_api_key":\s*"([^"]+)"', conf_text)
key = match.group(1) if match else ""

req = urllib.request.Request(
    "http://127.0.0.1:1933/api/v1/skills",
    headers={
        "Authorization": f"Bearer {key}",
        "X-API-Key": key,
    } if key else {}
)

try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        skills = data.get("result", {}).get("skills", [])
        print(f"Total skills returned from API: {len(skills)}")
        bundle_skills = [s for s in skills if s.get("is_bundle")]
        non_bundle_skills = [s for s in skills if not s.get("is_bundle")]
        print(f"Bundles: {len(bundle_skills)}, Non-bundles: {len(non_bundle_skills)}")
        for s in non_bundle_skills:
            print(f"  Loose skill: {s.get('name')}")
        all_scs = set()
        for b in bundle_skills:
            for sc in b.get("scenarios") or []:
                all_scs.add(sc)
                all_scs.add(sc.replace("_", "-"))
                all_scs.add(sc.replace("-", "_"))
        targets = [
            "agent-governance-guardrails",
            "capability-bundle-crystallizer",
            "clash_verge_governance",
            "deepseek-harness-ops",
            "global-agent-core",
            "web-search-pro",
        ]
        print("\nChecking Target Scenarios across all bundles:")
        for t in targets:
            print(f"  {t:32} -> in_scenarios: {t in all_scs}")
except Exception as e:
    print(f"API request failed: {e}")
