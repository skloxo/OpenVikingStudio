import urllib.request
import json
from pathlib import Path
import os

api_key = os.environ.get("OPENVIKING_API_KEY", "")
if not api_key:
    # Try reading from default env file or local token
    env_file = Path("/home/skloxo/.openviking/data/root_key.txt")
    if env_file.exists():
        api_key = env_file.read_text().strip()

headers = {
    "Authorization": f"Bearer {api_key}" if api_key else ""
}

test_virtuals = ["auto-pr", "cellular-cpe-ops", "openviking-master", "tide-trading-dev", "capability-bundle-crystallizer"]
print("Testing individual virtual skill GET endpoints:")
for name in test_virtuals:
    u = f"http://127.0.0.1:1933/api/v1/skills/{name}"
    r = urllib.request.Request(u, headers=headers)
    try:
        with urllib.request.urlopen(r) as res:
            res_data = json.loads(res.read().decode())
            status = res_data.get("status")
            skill_info = res_data.get("result", {})
            p_bundle = skill_info.get("parent_bundle")
            is_virt = skill_info.get("is_virtual")
            desc = skill_info.get("description", "")[:60]
            print(f"  [HTTP 200 OK] {name:32} -> status={status}, parent={p_bundle}, is_virtual={is_virt}, desc={desc}...")
    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
