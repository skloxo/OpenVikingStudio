# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from scripts.backfill_context_writes import apply_backfill, collect_backfill_buckets


def _init_usage_db(db_path) -> None:
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE _schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        INSERT INTO _schema_meta (key, value) VALUES ('version', '5');
        CREATE TABLE usage_context_write_bucket (
            account_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            date_utc TEXT NOT NULL,
            hour_utc INTEGER NOT NULL,
            operation TEXT NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (account_id, user_id, date_utc, hour_utc, operation)
        );
        CREATE TABLE request_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            account_id TEXT NOT NULL,
            user_id TEXT,
            method TEXT NOT NULL,
            route TEXT NOT NULL,
            api_type TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            duration_ms REAL NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )
    conn.close()


def test_collect_and_apply_backfill_is_idempotent(tmp_path):
    usage_db = tmp_path / "usage_audit.sqlite3"
    _init_usage_db(usage_db)
    conn = sqlite3.connect(usage_db)
    conn.executemany(
        """
        INSERT INTO request_audit (
            request_id, account_id, user_id, method, route, api_type, status_code, duration_ms, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("r1", "default", "u1", "POST", "/api/v1/skills/ingestion/submit", "skills", 200, 5.0, "2026-11-16T10:00:00+00:00"),
            ("r2", "default", "u1", "POST", "/api/v1/skills/ingestion/submit", "skills", 200, 6.0, "2026-11-16T10:15:00+00:00"),
            ("r3", "default", "u1", "POST", "/api/v1/content/write", "content", 200, 4.0, "2026-11-16T11:00:00+00:00"),
            ("r4", "default", "u1", "POST", "/api/v1/content/write", "content", 400, 4.0, "2026-11-16T11:05:00+00:00"),
        ],
    )
    conn.commit()
    conn.close()

    inbox_db = tmp_path / "skill_ingestion_inbox.db"
    ic = sqlite3.connect(inbox_db)
    ic.execute("CREATE TABLE skill_ingestion_inbox (author TEXT, status TEXT, created_at REAL)")
    ts_old = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc).timestamp()
    ts_overlap = datetime(2026, 11, 16, 10, 0, tzinfo=timezone.utc).timestamp()
    ic.executemany(
        "INSERT INTO skill_ingestion_inbox (author, status, created_at) VALUES (?, ?, ?)",
        [
            ("skloxo", "COMMITTED", ts_old),
            ("skloxo", "COMMITTED", ts_overlap),  # already covered on 2026-11-16 by request_audit
            ("skloxo", "REJECTED", ts_old),
        ],
    )
    ic.commit()
    ic.close()

    viking_root = tmp_path / "viking"
    res_file = viking_root / "resources" / "note.md"
    res_file.parent.mkdir(parents=True)
    res_file.write_text("doc", encoding="utf-8")
    dot_file = viking_root / "resources" / ".abstract.md"
    dot_file.write_text("abstract", encoding="utf-8")
    ts_fs = datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc).timestamp()
    os.utime(res_file, (ts_fs, ts_fs))
    os.utime(dot_file, (ts_fs, ts_fs))

    sess_msg = viking_root / "user" / "alice" / "sessions" / "mcp-store-1" / "messages.jsonl"
    sess_msg.parent.mkdir(parents=True)
    sess_msg.write_text('{"role":"user","content":"hi"}\n', encoding="utf-8")
    os.utime(sess_msg, (ts_fs, ts_fs))

    buckets = collect_backfill_buckets(
        usage_db, viking_root=viking_root, skill_inbox_db=inbox_db, since_date="2026-10-19"
    )
    assert buckets == {
        ("default", "u1", "2026-11-16", 10, "add_skill"): 2,
        ("default", "u1", "2026-11-16", 11, "add_resource"): 1,
        ("default", "skloxo", "2026-10-20", 8, "add_skill"): 1,
        ("default", "default", "2026-10-21", 9, "add_resource"): 1,
        ("default", "alice", "2026-10-21", 9, "session.commit"): 1,
    }

    res1 = apply_backfill(usage_db, buckets)
    res2 = apply_backfill(usage_db, buckets)
    assert res1["applied"] is True and res1["total_count"] == 6
    assert res2["applied"] is False and res2["skipped_already_applied"] is True
