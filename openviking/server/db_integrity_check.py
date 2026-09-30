# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""SQLite database integrity verification and FTS5 index self-healing engine."""

from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional

from openviking_cli.utils import get_logger

logger = get_logger(__name__)

_LAST_DB_CHECK_REPORT: Optional[Dict[str, Any]] = None


def check_single_database_integrity(db_path: Path) -> Dict[str, Any]:
    """Check integrity of a single SQLite database with quick_check and FTS5 verification."""
    result: Dict[str, Any] = {
        "path": str(db_path),
        "name": db_path.name,
        "exists": db_path.is_file(),
        "passed": False,
        "quick_check": None,
        "fts5_tables": [],
        "fts5_rebuilt": [],
        "error": None,
    }

    if not db_path.is_file():
        result["error"] = "File not found"
        return result

    try:
        conn = sqlite3.connect(str(db_path), timeout=5.0)
        cursor = conn.cursor()

        # 1. PRAGMA quick_check
        cursor.execute("PRAGMA quick_check;")
        qc_rows = cursor.fetchall()
        qc_status = [row[0] for row in qc_rows] if qc_rows else ["empty"]
        result["quick_check"] = qc_status
        is_qc_ok = len(qc_status) == 1 and qc_status[0].lower() == "ok"

        # 2. Check FTS5 tables if present
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%fts5%';"
        )
        fts_tables = [row[0] for row in cursor.fetchall()]
        result["fts5_tables"] = fts_tables

        fts_ok = True
        for table in fts_tables:
            try:
                cursor.execute(f"INSERT INTO {table}({table}) VALUES('integrity-check');")
            except Exception as fts_err:
                logger.warning(f"FTS5 table {table} in {db_path.name} failed integrity check: {fts_err}. Attempting rebuild...")
                try:
                    cursor.execute(f"INSERT INTO {table}({table}) VALUES('rebuild');")
                    conn.commit()
                    result["fts5_rebuilt"].append(table)
                    logger.info(f"FTS5 table {table} in {db_path.name} successfully rebuilt.")
                except Exception as rebuild_err:
                    fts_ok = False
                    result["error"] = f"FTS5 rebuild failed for {table}: {rebuild_err}"

        conn.close()
        result["passed"] = is_qc_ok and fts_ok
    except Exception as exc:
        result["error"] = str(exc)
        result["passed"] = False

    return result


def run_database_integrity_self_check(
    custom_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Execute complete database integrity probe across OpenViking SQLite stores."""
    global _LAST_DB_CHECK_REPORT
    started_at = time.monotonic()

    base_dirs = [
        custom_dir or (Path.home() / ".openviking" / "data"),
        Path.home() / ".openviking",
    ]

    target_dbs: List[Path] = []
    seen = set()
    for b_dir in base_dirs:
        if b_dir.is_dir():
            for p in b_dir.glob("**/*.db"):
                if p.is_file() and p.resolve() not in seen:
                    target_dbs.append(p)
                    seen.add(p.resolve())

    db_results: List[Dict[str, Any]] = []
    for db in target_dbs:
        db_results.append(check_single_database_integrity(db))

    total = len(db_results)
    passed_count = sum(1 for r in db_results if r.get("passed", False))
    rebuilt_count = sum(len(r.get("fts5_rebuilt", [])) for r in db_results)

    report = {
        "status": "healthy" if (total == 0 or passed_count == total) else "warning",
        "total_databases": total,
        "passed_databases": passed_count,
        "fts5_rebuilt_count": rebuilt_count,
        "duration_ms": round((time.monotonic() - started_at) * 1000, 2),
        "databases": db_results,
    }
    _LAST_DB_CHECK_REPORT = report
    return report


def get_last_database_check_report() -> Dict[str, Any]:
    """Return the cached startup or latest database integrity check report."""
    global _LAST_DB_CHECK_REPORT
    if _LAST_DB_CHECK_REPORT is None:
        return run_database_integrity_self_check()
    return _LAST_DB_CHECK_REPORT
