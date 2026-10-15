#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Quarantine and archive legacy zombie heartbeat/extractor sessions from VikingFS session directory.

Key Principles:
1. Safety First (Disaster Recovery): NEVER hard-delete without backup. Archives all files to ~/.openviking/data/archive/zombie_heartbeats/
2. Audit Trail: Generates quarantine_manifest.json with item metadata.
3. Idempotent & Reversible: Supports --restore and --dry-run modes.
4. Preserves Signals: Only targets zero-diff automated sessions (memories_extracted == 0).
"""

import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import sys

SESSION_DIR = Path.home() / ".openviking" / "data" / "viking" / "default" / "session"
ARCHIVE_BASE = Path.home() / ".openviking" / "data" / "archive" / "zombie_heartbeats"

HEARTBEAT_KEYWORDS = (
    "[openclaw heartbeat poll]",
    "heartbeat poll",
    "cron probe",
    "internal commitment extractor",
    "memory search agent",
    "dream diary",
)


def is_zero_diff_heartbeat(session_path: Path) -> bool:
    """Check if session is an automated routine task with 0 memory additions."""
    if not session_path.is_dir():
        return False

    # 1. Check .meta.json for zero diff
    meta_file = session_path / ".meta.json"
    if meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            memories = meta.get("memories_extracted", {})
            total_extracted = memories.get("total", 0) if isinstance(memories, dict) else 0
            if total_extracted > 0:
                # Escalated session with actual memories! Do not touch!
                return False
        except Exception:
            pass

    # 2. Check prefix
    name_lower = session_path.name.lower()
    if name_lower.startswith(("cron_", "heartbeat_", "probe_", "ping_", "memory-store-")):
        return True

    # 3. Check messages.jsonl / messages.json for automated task signatures
    msg_file = session_path / "messages.jsonl"
    if not msg_file.exists():
        msg_file = session_path / "messages.json"
    if msg_file.exists():
        try:
            with open(msg_file, "r", encoding="utf-8") as f:
                first_line = f.readline()
                if any(kw in first_line.lower() for kw in HEARTBEAT_KEYWORDS):
                    return True
                # Check second line if assistant or system message
                second_line = f.readline()
                if second_line and any(kw in second_line.lower() for kw in HEARTBEAT_KEYWORDS):
                    return True
        except Exception:
            pass

    return False


def scan_heartbeat_targets(session_dir: Path, limit: int = 0) -> list[Path]:
    """Scan session directory for zero-diff routine heartbeats."""
    if not session_dir.exists():
        return []

    targets = []
    for item in session_dir.iterdir():
        if item.is_dir() and is_zero_diff_heartbeat(item):
            targets.append(item)
            if limit > 0 and len(targets) >= limit:
                break
    targets.sort(key=lambda p: p.name)
    return targets


def backup_targets(targets: list[Path], archive_dir: Path) -> dict:
    """Safely archive target directories to archive_dir before removal."""
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_targets": len(targets),
        "archive_dir": str(archive_dir),
        "category": "zombie_heartbeats",
        "items": [],
    }

    for target in targets:
        dest = archive_dir / target.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()

        # Copy directory tree
        shutil.copytree(target, dest)

        files = [f for f in dest.rglob("*") if f.is_file()]
        size_bytes = sum(f.stat().st_size for f in files)

        manifest["items"].append({
            "name": target.name,
            "source": str(target),
            "destination": str(dest),
            "file_count": len(files),
            "size_bytes": size_bytes,
            "archived_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "category": "zombie_heartbeats",
        })

    manifest_file = archive_dir / "quarantine_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def restore_batch(batch_dir: Path) -> None:
    """Restore quarantined items from an archive batch."""
    manifest_file = batch_dir / "quarantine_manifest.json"
    if not manifest_file.exists():
        print(f"Error: manifest file not found in {batch_dir}")
        sys.exit(1)

    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    items = manifest.get("items", [])
    print(f"Restoring {len(items)} items from {batch_dir}...")

    for it in items:
        src = Path(it["destination"])
        dst = Path(it["source"])
        if not src.exists():
            print(f"  Warning: {src} does not exist, skipping")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            if dst.is_dir():
                shutil.rmtree(dst)
            else:
                dst.unlink()
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        print(f"  Restored {it['name']} -> {dst}")

    print("Restore complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Quarantine and archive zero-diff routine heartbeat sessions."
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulate scan without modifying files")
    parser.add_argument("--restore", type=str, help="Restore from batch directory (e.g. ~/.openviking/data/archive/zombie_heartbeats/batch_...)")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of sessions to quarantine (default: all)")
    args = parser.parse_args()

    if args.restore:
        batch_path = Path(args.restore).expanduser().resolve()
        restore_batch(batch_path)
        return

    print(f"Scanning {SESSION_DIR} for zero-diff routine heartbeats/extractors...")
    targets = scan_heartbeat_targets(SESSION_DIR, limit=args.limit)
    print(f"Found {len(targets)} zero-diff routine heartbeat sessions.")

    if not targets:
        print("No zero-diff routine heartbeat sessions found. Exiting.")
        return

    total_est_files = 0
    total_est_bytes = 0
    for t in targets[:100]:
        for f in t.rglob("*"):
            if f.is_file():
                total_est_files += 1
                total_est_bytes += f.stat().st_size
    avg_files = total_est_files / min(100, len(targets))
    avg_bytes = total_est_bytes / min(100, len(targets))
    est_total_bytes = avg_bytes * len(targets)
    est_total_mb = est_total_bytes / (1024 * 1024)

    print(f"Estimated reduction: ~{int(avg_files * len(targets))} files (~{est_total_mb:.2f} MB)")

    if args.dry_run:
        print("\n[DRY RUN] Simulating first 15 targets:")
        for t in targets[:15]:
            print(f"  - {t.name}")
        print(f"\n[DRY RUN] Would archive {len(targets)} targets into {ARCHIVE_BASE}/batch_<timestamp>/")
        print("[DRY RUN] No files were moved or deleted.")
        return

    # Execute quarantine
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_dir = ARCHIVE_BASE / f"batch_{timestamp}"
    print(f"\nArchiving {len(targets)} sessions to {batch_dir}...")
    manifest = backup_targets(targets, batch_dir)
    print(f"Manifest written: {len(manifest['items'])} items safely backed up.")

    # Remove targets from live VikingFS
    print("Purging archived targets from live session directory...")
    removed_count = 0
    for target in targets:
        try:
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            removed_count += 1
        except Exception as e:
            print(f"  Error removing {target.name}: {e}")

    print(f"\nQuarantine complete! Safely purged {removed_count} zero-diff heartbeat sessions.")
    print(f"Archive location: {batch_dir}")
    print(f"To rollback: python3 scripts/quarantine_zombie_heartbeats.py --restore {batch_dir}")


if __name__ == "__main__":
    main()
