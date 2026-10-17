#!/usr/bin/env python3
"""
Purge temporary scratch script resources from VikingFS.
Removes legacy windows_work_干部宿舍_docs_scratch_* folders that polluted vector space.
"""

import asyncio
import json
import os
import urllib.parse
from pathlib import Path
import httpx

def get_api_and_key():
    api = os.environ.get("OPENVIKING_API", "http://127.0.0.1:1933")
    key = os.environ.get("OPENVIKING_API_KEY", "")
    if not key:
        mcp_cfg = Path.home() / ".gemini" / "config" / "mcp_config.json"
        if mcp_cfg.exists():
            try:
                with open(mcp_cfg, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                ov_env = cfg.get("mcpServers", {}).get("openviking", {}).get("env", {})
                key = ov_env.get("OPENVIKING_API_KEY", "") or ov_env.get("OPENVIKING_ROOT_API_KEY", "")
            except Exception:
                pass
    return api, key

API_BASE, API_KEY = get_api_and_key()
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
}

RESOURCES_DIR = os.path.expanduser("~/.openviking/data/viking/default/resources")

async def delete_resource(client: httpx.AsyncClient, folder_name: str, sem: asyncio.Semaphore):
    uri = f"viking://resources/{folder_name}"
    encoded_uri = urllib.parse.quote(uri, safe="")
    url = f"{API_BASE}/api/v1/fs?uri={encoded_uri}&recursive=true"
    async with sem:
        try:
            resp = await client.delete(url, timeout=30.0)
            if resp.status_code in (200, 404):
                return True, folder_name, resp.status_code
            else:
                return False, folder_name, f"HTTP {resp.status_code}: {resp.text}"
        except Exception as e:
            return False, folder_name, str(e)

async def main():
    if not os.path.exists(RESOURCES_DIR):
        print(f"Resources dir not found: {RESOURCES_DIR}")
        return

    items = os.listdir(RESOURCES_DIR)
    targets = [it for it in items if "scratch" in it.lower() or "cmd_encoded" in it.lower()]
    targets.sort()

    print(f"Found {len(targets)} scratch resources to delete.")
    if not targets:
        print("Nothing to delete.")
        return

    sem = asyncio.Semaphore(6)
    success_count = 0
    fail_count = 0

    async with httpx.AsyncClient(headers=HEADERS) as client:
        tasks = [delete_resource(client, t, sem) for t in targets]
        for i, coro in enumerate(asyncio.as_completed(tasks)):
            ok, name, info = await coro
            if ok:
                success_count += 1
            else:
                fail_count += 1
                print(f"[FAIL] {name}: {info}")
            if (i + 1) % 50 == 0 or (i + 1) == len(targets):
                print(f"Progress: {i + 1}/{len(targets)} (Success: {success_count}, Failed: {fail_count})")

    print(f"\nPurge completed! Total deleted: {success_count}, Failed: {fail_count}")

    # Double check disk for any orphaned scratch folders
    remaining = [it for it in os.listdir(RESOURCES_DIR) if "scratch" in it.lower() or "cmd_encoded" in it.lower()]
    print(f"Remaining scratch folders on disk: {len(remaining)}")

if __name__ == "__main__":
    asyncio.run(main())
