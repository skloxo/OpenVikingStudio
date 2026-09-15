#!/usr/bin/env python3
"""
Quarantine and purge legacy zombie session memories (antigravity_master_* and antigravity_session_*)
from VikingFS resources.

Key Principles:
1. Safety First: NEVER hard-delete without backup. Archives all targets to ~/.openviking/data/archive/zombie_sessions/
2. Audit Trail: Generates quarantine_manifest.json with item metadata.
3. Clean Vector State: Uses VikingFS REST API DELETE /api/v1/fs to purge vector embeddings & semantic markers.
4. Idempotent & Reversible: Supports --restore and --dry-run modes.
"""

import argparse
import asyncio
import datetime
import json
import os
from pathlib import Path
import shutil
import sys
import urllib.parse
import httpx


def get_api_and_key() -> tuple[str, str]:
    """Dynamically resolve OpenViking API base and API Key without hardcoding secrets."""
    api = os.environ.get("OPENVIKING_API", "http://127.0.0.1:1933")
    key = os.environ.get("OPENVIKING_API_KEY", "")
    if not key:
        mcp_cfg = Path.home() / ".gemini" / "config" / "mcp_config.json"
        if mcp_cfg.exists():
            try:
                with open(mcp_cfg, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                ov_env = cfg.get("mcpServers", {}).get("openviking", {}).get("env", {})
                key = (
                    ov_env.get("OPENVIKING_API_KEY", "")
                    or ov_env.get("OPENVIKING_ROOT_API_KEY", "")
                )
            except Exception:
                pass
    return api, key


RESOURCES_DIR = Path.home() / ".openviking" / "data" / "viking" / "default" / "resources"
ARCHIVE_BASE = Path.home() / ".openviking" / "data" / "archive" / "zombie_sessions"


def is_zombie_target(name: str) -> bool:
    """Identify legacy July 2026 raw session dumps."""
    lower = name.lower()
    return lower.startswith("antigravity_master_") or lower.startswith("antigravity_session_")


def scan_targets(resources_dir: Path) -> list[str]:
    """Scan resources directory for zombie session folders."""
    if not resources_dir.exists():
        return []
    targets = [
        item.name
        for item in resources_dir.iterdir()
        if item.is_dir() and is_zombie_target(item.name)
    ]
    targets.sort()
    return targets


def backup_targets(targets: list[str], resources_dir: Path, archive_dir: Path) -> dict:
    """Safely archive target directories to archive_dir before removal."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_targets": len(targets),
        "archive_dir": str(archive_dir),
        "items": [],
    }

    print(f"📦 Archiving {len(targets)} targets to {archive_dir} ...")
    total_bytes = 0
    total_files = 0

    for idx, name in enumerate(targets, 1):
        src = resources_dir / name
        dst = archive_dir / name
        if not src.exists():
            continue

        shutil.copytree(src, dst, dirs_exist_ok=True)

        item_bytes = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
        item_files = sum(1 for f in dst.rglob("*") if f.is_file())
        total_bytes += item_bytes
        total_files += item_files

        manifest["items"].append({
            "name": name,
            "source": str(src),
            "destination": str(dst),
            "size_bytes": item_bytes,
            "file_count": item_files,
        })

        if idx % 200 == 0 or idx == len(targets):
            print(f"   Archived {idx}/{len(targets)} ({total_bytes / (1024 * 1024):.1f} MB copied)")

    manifest["total_size_bytes"] = total_bytes
    manifest["total_files"] = total_files

    manifest_file = archive_dir / "quarantine_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Archive complete: {len(targets)} targets, {total_files} files, {total_bytes / 1024:.1f} KB")
    print(f"📄 Manifest saved: {manifest_file}")
    return manifest


async def delete_vikingfs_resource(
    client: httpx.AsyncClient, api_base: str, name: str, sem: asyncio.Semaphore
) -> tuple[bool, str, str]:
    """Delete resource via standard VikingFS REST API so vectors and markers are purged."""
    uri = f"viking://resources/{name}"
    encoded_uri = urllib.parse.quote(uri, safe="")
    url = f"{api_base}/api/v1/fs?uri={encoded_uri}&recursive=true"

    async with sem:
        try:
            resp = await client.delete(url, timeout=30.0)
            if resp.status_code in (200, 404):
                return True, name, f"HTTP {resp.status_code}"
            return False, name, f"HTTP {resp.status_code}: {resp.text}"
        except Exception as exc:
            return False, name, str(exc)


async def purge_targets_via_api(
    targets: list[str], api_base: str, api_key: str, concurrency: int = 10
) -> tuple[int, int]:
    """Concurrently purge targets via VikingFS REST API."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    sem = asyncio.Semaphore(concurrency)
    success_count = 0
    fail_count = 0

    print(f"🚀 Purging {len(targets)} targets via VikingFS API ({api_base}) ...")
    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [delete_vikingfs_resource(client, api_base, t, sem) for t in targets]
        for i, coro in enumerate(asyncio.as_completed(tasks), 1):
            ok, name, info = await coro
            if ok:
                success_count += 1
            else:
                fail_count += 1
                print(f"[FAIL] {name}: {info}")
            if i % 100 == 0 or i == len(targets):
                print(f"   Progress: {i}/{len(targets)} (Success: {success_count}, Failed: {fail_count})")

    return success_count, fail_count


def restore_archive(archive_path: Path, resources_dir: Path) -> None:
    """Restore archived session memories back to resources directory."""
    manifest_file = archive_path / "quarantine_manifest.json"
    if not manifest_file.exists():
        print(f"❌ Manifest not found in {archive_path}")
        sys.exit(1)

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    items = manifest.get("items", [])
    print(f"🔄 Restoring {len(items)} items from {archive_path} to {resources_dir} ...")
    restored = 0
    for it in items:
        name = it["name"]
        src = archive_path / name
        dst = resources_dir / name
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            restored += 1

    print(f"✅ Restoration completed: {restored}/{len(items)} restored.")


def main():
    parser = argparse.ArgumentParser(description="Quarantine & purge legacy zombie session memories.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and display stats without modifying.")
    parser.add_argument("--restore", type=str, nargs="?", const="latest", help="Restore archive (specify path or 'latest').")
    parser.add_argument("--concurrency", type=int, default=10, help="Concurrent API delete requests (default 10).")
    args = parser.parse_args()

    api_base, api_key = get_api_and_key()

    if args.restore:
        if args.restore == "latest":
            subdirs = sorted([d for d in ARCHIVE_BASE.iterdir() if d.is_dir()])
            if not subdirs:
                print(f"❌ No archives found in {ARCHIVE_BASE}")
                sys.exit(1)
            target_archive = subdirs[-1]
        else:
            target_archive = Path(args.restore)
        restore_archive(target_archive, RESOURCES_DIR)
        return

    targets = scan_targets(RESOURCES_DIR)
    print(f"🔍 Discovered {len(targets)} zombie session memories in {RESOURCES_DIR}")

    if not targets:
        print("✨ No zombie session memories found. System is already clean!")
        return

    if args.dry_run:
        sample = targets[:5]
        print(f"ℹ️ [DRY RUN] First 5 targets: {sample}")
        print(f"ℹ️ [DRY RUN] Would archive and purge {len(targets)} targets. Exiting without changes.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = ARCHIVE_BASE / timestamp

    # Step 1: Backup & Quarantine
    backup_targets(targets, RESOURCES_DIR, archive_dir)

    # Step 2: Purge via standard API
    succ, fail = asyncio.run(
        purge_targets_via_api(targets, api_base, api_key, concurrency=args.concurrency)
    )

    print(f"\n🎉 Quarantine & Purge Summary:")
    print(f"   Archived to: {archive_dir}")
    print(f"   API Deleted: {succ}")
    print(f"   API Failed:  {fail}")

    # Step 3: Check remaining
    remaining = scan_targets(RESOURCES_DIR)
    print(f"   Remaining on disk: {len(remaining)}")


if __name__ == "__main__":
    main()
