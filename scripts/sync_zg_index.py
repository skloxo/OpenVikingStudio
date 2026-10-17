#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Sync ZG AST Code Semantic Search Index (scripts/sync_zg_index.py).
Scans Python and TypeScript/JS source directories, extracts discrete AST symbols,
and builds the SQLite FTS5 code symbol index (~/.openviking/data/viking/default/zg_code_fts.db).
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.30)
"""

import argparse
import os
from pathlib import Path
import sys
import time

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from openviking.search.ast_chunker import ASTChunker, CodeSymbolChunk
from openviking.search.zg_engine import ZGSearchEngine
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)


def sync_zg_code_index(
    repo_root: Path,
    max_files: int = 500,
    clean: bool = False,
) -> None:
    """Build or refresh local-first zg code symbol index."""
    t0 = time.monotonic()
    db_dir = Path(os.path.expanduser("~/.openviking/data/viking/default"))
    db_dir.mkdir(parents=True, exist_ok=True)
    db_file = db_dir / "zg_code_fts.db"

    if clean and db_file.exists():
        logger.info("Cleaning existing zg_code_fts.db: %s", db_file)
        try:
            db_file.unlink()
        except Exception as e:
            logger.warning("Failed to remove old index db: %s", e)

    # Initialize engine
    engine = ZGSearchEngine.get_instance(repo_root=repo_root)

    # Target source directories
    scan_dirs = [
        repo_root / "openviking",
        repo_root / "scripts",
    ]

    total_chunks = 0
    total_files = 0

    print("======================================================================")
    print("🚀 [zg-index] Starting AST Code Symbol Index Sync...")
    print(f"   Repository Root : {repo_root}")
    print(f"   Database File   : {db_file}")
    print("======================================================================")

    for s_dir in scan_dirs:
        if not s_dir.exists():
            continue
        print(f"\n📂 Scanning directory: {s_dir.name}/ ...")
        n = engine.index_directory(s_dir, max_files=max_files)
        total_chunks += n
        print(f"   ✓ Extracted & indexed {n} AST symbols from {s_dir.name}")

    stats = engine.get_stats()
    elapsed = time.monotonic() - t0

    print("\n======================================================================")
    print("✅ [zg-index] Index Sync Complete!")
    print(f"   • Total Files Indexed : {stats.total_files}")
    print(f"   • Total Symbols       : {stats.total_symbols}")
    print(f"   • Total Code Lines    : {stats.total_lines:,}")
    print(f"   • Avg Lines / Symbol  : {stats.avg_lines_per_symbol} lines")
    print(f"   • Indexing Latency    : {elapsed:.2f}s")
    print(f"   • Status              : {'Ready ⚡' if stats.is_ready else 'Empty'}")
    print("======================================================================")


def main():
    parser = argparse.ArgumentParser(description="Synchronize zg code semantic search index.")
    parser.add_argument(
        "--root",
        type=str,
        default=str(REPO_ROOT),
        help="Path to code repository root",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=600,
        help="Maximum files to scan per directory",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Purge existing index and rebuild from scratch",
    )
    args = parser.parse_args()

    sync_zg_code_index(
        repo_root=Path(args.root),
        max_files=args.max_files,
        clean=args.clean,
    )


if __name__ == "__main__":
    main()
