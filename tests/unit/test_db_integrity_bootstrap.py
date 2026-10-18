# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Test SQLite Database Integrity Self-Check and Bot Gateway Manager.

Card-35 (v1.5.99): RSI-Holdout-Benchmark-And-Bootstrap-SelfCheck-Closure.
"""

from pathlib import Path
import sqlite3
import pytest

from openviking.server.db_integrity_check import (
    check_single_database_integrity,
    get_last_database_check_report,
    run_database_integrity_self_check,
)
from openviking.server.bot_gateway_manager import (
    BotProcess,
    resolve_cli_config_for_bot,
    resolve_default_bot_log_dir,
    stop_vikingbot_gateway,
)


def test_check_single_database_integrity_clean(tmp_path: Path):
    """Clean SQLite database passes PRAGMA quick_check."""
    db_file = tmp_path / "test_clean.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);")
    conn.execute("INSERT INTO users (name) VALUES ('viking');")
    conn.commit()
    conn.close()

    res = check_single_database_integrity(db_file)
    assert res["passed"] is True
    assert res["quick_check"] == ["ok"]
    assert res["fts5_tables"] == []
    assert res["error"] is None


def test_check_single_database_with_fts5(tmp_path: Path):
    """SQLite database with FTS5 table passes integrity check."""
    db_file = tmp_path / "test_fts.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE VIRTUAL TABLE docs USING fts5(content);")
    conn.execute("INSERT INTO docs (content) VALUES ('OpenViking RSI Policy');")
    conn.commit()
    conn.close()

    res = check_single_database_integrity(db_file)
    assert res["passed"] is True
    assert "docs" in res["fts5_tables"]
    assert res["quick_check"] == ["ok"]


def test_run_database_integrity_self_check(tmp_path: Path):
    """Self-check aggregates all databases in target directory."""
    db1 = tmp_path / "db1.db"
    db2 = tmp_path / "db2.db"

    for p in (db1, db2):
        c = sqlite3.connect(str(p))
        c.execute("CREATE TABLE kv (k TEXT, v TEXT);")
        c.commit()
        c.close()

    report = run_database_integrity_self_check(custom_dir=tmp_path)
    assert report["total_databases"] >= 2
    assert report["passed_databases"] >= 2
    assert report["status"] == "healthy"
    assert report["duration_ms"] >= 0

    cached = get_last_database_check_report()
    assert cached["total_databases"] == report["total_databases"]


def test_bot_gateway_manager_helpers():
    """Bot gateway manager utility functions execute safely."""
    # stop_vikingbot_gateway safely handles None process
    stop_vikingbot_gateway(None)

    # resolve_default_bot_log_dir returns a valid string path
    log_dir = resolve_default_bot_log_dir(None)
    assert isinstance(log_dir, str)
    assert len(log_dir) > 0

    # resolve_cli_config_for_bot safely executes with None
    cli_conf = resolve_cli_config_for_bot(None)
    assert cli_conf is None or isinstance(cli_conf, str)

