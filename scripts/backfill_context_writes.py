#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Idempotent historical backfill for `usage_context_write_bucket` (Tududi Card-48).

Recovers context write heatmap buckets lost after 2026-10-19 from:
1. `request_audit` rows matching the expanded `context_write_operation_for_http` mapping;
2. Committed skill receipts in `skill_ingestion_inbox.db` on dates not already covered by audit;
3. Physical VikingFS `resources/`, `user/*/memories/`, and `user/*/sessions/*/messages.jsonl` writes.
"""

from __future__ import annotations

import argparse
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from openviking.observability.usage_audit.projection import context_write_operation_for_http

BACKFILL_META_KEY = "context_write_backfill_20261019_v1"
DEFAULT_USAGE_DB = Path.home() / ".openviking" / "data" / "_system" / "usage_audit" / "usage_audit.sqlite3"
DEFAULT_VIKING_ROOT = Path.home() / ".openviking" / "data" / "viking" / "default"
DEFAULT_SKILL_INBOX_DB = DEFAULT_VIKING_ROOT / "skill_ingestion_inbox.db"
IGNORED_SUFFIXES = frozenset({".db", ".sqlite", ".sqlite3", ".wal", ".shm", ".lock"})


def _parse_iso_utc(raw: str) -> datetime | None:
    text = (raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _collect_from_request_audit(
    conn: sqlite3.Connection,
    since_date: str,
) -> tuple[dict[tuple[str, str, str, int, str], int], set[tuple[str, str]]]:
    buckets: dict[tuple[str, str, str, int, str], int] = defaultdict(int)
    covered_op_dates: set[tuple[str, str]] = set()
    rows = conn.execute(
        """
        SELECT account_id, COALESCE(user_id, ''), method, route, status_code, created_at
        FROM request_audit
        WHERE method = 'POST'
          AND status_code >= 200 AND status_code < 400
          AND substr(created_at, 1, 10) >= ?
        """,
        (since_date,),
    ).fetchall()
    for account_id, user_id, method, route, status_code, created_at in rows:
        op = context_write_operation_for_http(str(method), str(route), int(status_code))
        if not op:
            continue
        dt = _parse_iso_utc(str(created_at))
        if dt is None:
            continue
        date_utc = dt.date().isoformat()
        if date_utc < since_date:
            continue
        key = (str(account_id or "default"), str(user_id or ""), date_utc, dt.hour, op)
        buckets[key] += 1
        covered_op_dates.add((op, date_utc))
    return buckets, covered_op_dates


def _collect_from_skill_inbox(
    inbox_db: Path,
    *,
    since_date: str,
    account_id: str,
    skip_dates: set[str],
) -> dict[tuple[str, str, str, int, str], int]:
    buckets: dict[tuple[str, str, str, int, str], int] = defaultdict(int)
    if not inbox_db.is_file():
        return buckets
    conn = sqlite3.connect(inbox_db)
    try:
        rows = conn.execute(
            "SELECT author, created_at FROM skill_ingestion_inbox WHERE status = 'COMMITTED'"
        ).fetchall()
    except sqlite3.Error:
        return buckets
    finally:
        conn.close()

    for author, ts in rows:
        try:
            dt = datetime.fromtimestamp(float(ts), timezone.utc)
        except (TypeError, ValueError, OSError):
            continue
        date_utc = dt.date().isoformat()
        if date_utc < since_date or date_utc in skip_dates:
            continue
        user_id = str(author or "default").strip() or "default"
        buckets[(account_id, user_id, date_utc, dt.hour, "add_skill")] += 1
    return buckets


def _iter_non_dot_files(directory: Path) -> Iterable[Path]:
    if not directory.is_dir():
        return ()
    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.relative_to(directory).parts):
            continue
        if path.suffix.lower() in IGNORED_SUFFIXES:
            continue
        yield path


def _collect_from_viking_fs(
    viking_root: Path,
    *,
    since_date: str,
    account_id: str,
    covered_op_dates: set[tuple[str, str]],
) -> dict[tuple[str, str, str, int, str], int]:
    buckets: dict[tuple[str, str, str, int, str], int] = defaultdict(int)
    if not viking_root.is_dir():
        return buckets

    for path in _iter_non_dot_files(viking_root / "resources"):
        dt = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        date_utc = dt.date().isoformat()
        if date_utc < since_date or ("add_resource", date_utc) in covered_op_dates:
            continue
        buckets[(account_id, "default", date_utc, dt.hour, "add_resource")] += 1

    user_root = viking_root / "user"
    if user_root.is_dir():
        for user_dir in user_root.iterdir():
            if not user_dir.is_dir() or user_dir.name.startswith("."):
                continue
            uid = user_dir.name
            sessions_dir = user_dir / "sessions"
            if sessions_dir.is_dir():
                for sess_dir in sessions_dir.iterdir():
                    msg_file = sess_dir / "messages.jsonl"
                    if not sess_dir.is_dir() or not msg_file.is_file():
                        continue
                    dt = datetime.fromtimestamp(msg_file.stat().st_mtime, timezone.utc)
                    date_utc = dt.date().isoformat()
                    if date_utc < since_date:
                        continue
                    buckets[(account_id, uid, date_utc, dt.hour, "session.commit")] += 1
            for mem_file in _iter_non_dot_files(user_dir / "memories"):
                dt = datetime.fromtimestamp(mem_file.stat().st_mtime, timezone.utc)
                date_utc = dt.date().isoformat()
                if date_utc < since_date:
                    continue
                buckets[(account_id, uid, date_utc, dt.hour, "session.commit")] += 1
    return buckets


def collect_backfill_buckets(
    usage_db: Path,
    *,
    viking_root: Path = DEFAULT_VIKING_ROOT,
    skill_inbox_db: Path = DEFAULT_SKILL_INBOX_DB,
    since_date: str = "2026-10-19",
    account_id: str = "default",
) -> dict[tuple[str, str, str, int, str], int]:
    """Build merged deterministic backfill bucket map keyed by SQLite PK."""
    merged: dict[tuple[str, str, str, int, str], int] = defaultdict(int)
    conn = sqlite3.connect(usage_db)
    try:
        audit_buckets, covered_op_dates = _collect_from_request_audit(conn, since_date)
    finally:
        conn.close()

    for key, val in audit_buckets.items():
        merged[key] += val

    skill_dates_from_audit = {d for op, d in covered_op_dates if op == "add_skill"}
    inbox_buckets = _collect_from_skill_inbox(
        skill_inbox_db,
        since_date=since_date,
        account_id=account_id,
        skip_dates=skill_dates_from_audit,
    )
    for key, val in inbox_buckets.items():
        merged[key] += val

    fs_buckets = _collect_from_viking_fs(
        viking_root,
        since_date=since_date,
        account_id=account_id,
        covered_op_dates=covered_op_dates,
    )
    for key, val in fs_buckets.items():
        merged[key] += val
    return dict(merged)


def apply_backfill(
    usage_db: Path,
    buckets: dict[tuple[str, str, str, int, str], int],
    *,
    force: bool = False,
) -> dict[str, int | bool]:
    """Apply aggregated context-write buckets idempotently into `usage_audit.sqlite3`."""
    now_iso = datetime.now(timezone.utc).isoformat()
    conn = sqlite3.connect(usage_db, timeout=30.0)
    try:
        conn.execute("PRAGMA busy_timeout=30000")
        already = conn.execute(
            "SELECT value FROM _schema_meta WHERE key = ?", (BACKFILL_META_KEY,)
        ).fetchone()
        if already and not force:
            return {"applied": False, "rows": 0, "total_count": 0, "skipped_already_applied": True}

        rows = [
            (acct, uid, d, hr, op, count, now_iso)
            for (acct, uid, d, hr, op), count in buckets.items()
            if count > 0
        ]
        with conn:
            conn.executemany(
                """
                INSERT INTO usage_context_write_bucket (
                    account_id, user_id, date_utc, hour_utc, operation, count, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (account_id, user_id, date_utc, hour_utc, operation)
                DO UPDATE SET
                    count = MAX(usage_context_write_bucket.count, excluded.count),
                    updated_at = excluded.updated_at
                """,
                rows,
            )
            conn.execute(
                "INSERT OR REPLACE INTO _schema_meta (key, value) VALUES (?, ?)",
                (BACKFILL_META_KEY, now_iso),
            )
        return {
            "applied": True,
            "rows": len(rows),
            "total_count": sum(r[5] for r in rows),
            "skipped_already_applied": False,
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill usage_context_write_bucket since 2026-10-19.")
    parser.add_argument("--usage-db", type=Path, default=DEFAULT_USAGE_DB)
    parser.add_argument("--viking-root", type=Path, default=DEFAULT_VIKING_ROOT)
    parser.add_argument("--skill-inbox-db", type=Path, default=DEFAULT_SKILL_INBOX_DB)
    parser.add_argument("--since", default="2026-10-19")
    parser.add_argument("--account-id", default="default")
    parser.add_argument("--apply", action="store_true", help="Write backfilled rows (default: dry-run)")
    parser.add_argument("--force", action="store_true", help="Re-apply even if marker exists")
    args = parser.parse_args()

    buckets = collect_backfill_buckets(
        args.usage_db,
        viking_root=args.viking_root,
        skill_inbox_db=args.skill_inbox_db,
        since_date=args.since,
        account_id=args.account_id,
    )
    by_op: dict[str, int] = defaultdict(int)
    for (_, _, _, _, op), count in buckets.items():
        by_op[op] += count
    print(f"Collected {len(buckets)} buckets (total={sum(buckets.values())}): {dict(by_op)}")
    if not args.apply:
        print("Dry-run only. Re-run with --apply to persist into SQLite.")
        return 0
    result = apply_backfill(args.usage_db, buckets, force=args.force)
    print(f"Apply result: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
