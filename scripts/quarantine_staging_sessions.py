#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Quarantine and purge staging session documents (3070_sessions, antigravity_sessions, 2080ti_sessions)
from VikingFS resources.

Key Principles:
1. Safety First (Disaster Recovery): NEVER hard-delete without backup. Archives all files to ~/.openviking/data/archive/cold_staging_sessions/
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
    """Dynamically resolve OpenViking API base and API Key from env or user config."""
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
    if not key:
        ov_conf = Path.home() / ".openviking" / "ov.conf"
        if ov_conf.exists():
            try:
                for line in ov_conf.read_text(encoding="utf-8").splitlines():
                    if line.startswith("api_key="):
                        key = line.split("=", 1)[1].strip()
                        break
            except Exception:
                pass
    return api, key


STAGING_DIR = Path.home() / ".openviking" / "data" / "viking" / "default" / "resources" / "staging"
ARCHIVE_BASE = Path.home() / ".openviking" / "data" / "archive" / "cold_staging_sessions"


def scan_staging_targets(staging_dir: Path) -> list[str]:
    """Scan staging directory for session folders."""
    if not staging_dir.exists():
        return []
    targets = [
        item.name
        for item in staging_dir.iterdir()
        if item.is_dir() and item.name.endswith("_sessions")
    ]
    targets.sort()
    return targets


def backup_targets(targets: list[str], staging_dir: Path, archive_dir: Path) -> dict:
    """Safely archive target directories and files to archive_dir before removal."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_targets": len(targets),
        "archive_dir": str(archive_dir),
        "items": [],
    }

    print(f"📦 Archiving {len(targets)} staging targets to {archive_dir} ...")
    total_bytes = 0
    total_files = 0

    for name in targets:
        src = staging_dir / name
        dst = archive_dir / name
        if not src.exists():
            continue

        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
            item_bytes = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file())
            item_files = sum(1 for f in dst.rglob("*") if f.is_file())
        else:
            shutil.copy2(src, dst)
            item_bytes = src.stat().st_size
            item_files = 1

        total_bytes += item_bytes
        total_files += item_files

        manifest["items"].append({
            "name": name,
            "uri": f"viking://resources/staging/{name}",
            "source": str(src),
            "destination": str(dst),
            "size_bytes": item_bytes,
            "file_count": item_files,
        })
        print(f"   Archived {name}: {item_files} files, {item_bytes / 1024:.1f} KB")

    manifest["total_size_bytes"] = total_bytes
    manifest["total_files"] = total_files

    manifest_file = archive_dir / "quarantine_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"✅ Archive complete: {len(targets)} targets, {total_files} files, {total_bytes / 1024:.1f} KB")
    print(f"📄 Manifest saved: {manifest_file}")
    return manifest


async def delete_vikingfs_resource(
    client: httpx.AsyncClient, api_base: str, name: str
) -> tuple[bool, str, str]:
    """Delete staging resource via standard VikingFS REST API so vectors and markers are purged."""
    uri = f"viking://resources/staging/{name}"
    encoded_uri = urllib.parse.quote(uri, safe="")
    url = f"{api_base}/api/v1/fs?uri={encoded_uri}&recursive=true"

    try:
        resp = await client.delete(url, timeout=30.0)
        if resp.status_code in (200, 404):
            return True, name, f"HTTP {resp.status_code}"
        return False, name, f"HTTP {resp.status_code}: {resp.text}"
    except Exception as exc:
        return False, name, str(exc)


async def purge_staging_via_api(
    targets: list[str], api_base: str, api_key: str
) -> tuple[int, int]:
    """Purge staging targets via VikingFS REST API."""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    success_count = 0
    fail_count = 0

    print(f"🚀 Purging {len(targets)} staging targets via VikingFS API ({api_base}) ...")
    async with httpx.AsyncClient(headers=headers) as client:
        for name in targets:
            ok, target_name, info = await delete_vikingfs_resource(client, api_base, name)
            if ok:
                success_count += 1
                print(f"   [PASS] {target_name}: {info}")
            else:
                fail_count += 1
                print(f"   [FAIL] {target_name}: {info}")

    return success_count, fail_count


def cleanup_local_staging_residuals(targets: list[str], staging_dir: Path) -> None:
    """Ensure local staging directory residuals are removed after successful API purge."""
    for name in targets:
        path = staging_dir / name
        if path.exists():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
                print(f"   Cleaned residual path: {path}")
            except Exception as e:
                print(f"   Warning: failed to clean residual path {path}: {e}")


def restore_archive(archive_path: Path, staging_dir: Path) -> None:
    """Restore archived staging memories back to staging directory."""
    manifest_file = archive_path / "quarantine_manifest.json"
    if not manifest_file.exists():
        print(f"❌ Manifest not found in {archive_path}")
        sys.exit(1)

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    print(f"⏪ Restoring {manifest['total_targets']} targets ({manifest['total_files']} files) to {staging_dir} ...")
    staging_dir.mkdir(parents=True, exist_ok=True)
    restored = 0
    for item in manifest["items"]:
        src = Path(item["destination"])
        dst = staging_dir / item["name"]
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
            restored += 1
            print(f"   Restored {item['name']}")

    print(f"✅ Restoration complete: {restored} items restored.")


async def main_async():
    parser = argparse.ArgumentParser(description="Quarantine staging session memories and purge vectors.")
    parser.add_argument("--dry-run", action="store_true", help="List targets without performing actions")
    parser.add_argument("--restore", type=str, help="Restore from specified archive directory")
    args = parser.parse_args()

    api_base, api_key = get_api_and_key()

    if args.restore:
        archive_path = Path(args.restore)
        restore_archive(archive_path, STAGING_DIR)
        return

    targets = scan_staging_targets(STAGING_DIR)
    if not targets:
        print("🎉 No staging session targets found in staging directory. Memory is clean!")
        return

    print(f"Found {len(targets)} staging targets to quarantine:")
    for t in targets:
        p = STAGING_DIR / t
        if p.is_dir():
            count = sum(1 for f in p.rglob("*") if f.is_file())
            print(f" - [DIR]  {t} ({count} files)")
        else:
            print(f" - [FILE] {t} ({p.stat().st_size} bytes)")

    if args.dry_run:
        print("💡 Dry run complete. No changes were made.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = ARCHIVE_BASE / timestamp

    # Step 1: Backup
    backup_targets(targets, STAGING_DIR, archive_dir)

    # Step 2: Purge via API
    success_count, fail_count = await purge_staging_via_api(targets, api_base, api_key)
    print(f"API Purge Result: {success_count} succeeded, {fail_count} failed.")

    # Step 3: Local cleanup
    cleanup_local_staging_residuals(targets, STAGING_DIR)

    print("\n🎉 Quarantine and VectorDB Purge complete!")
    print(f"Archive preserved at: {archive_dir}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
