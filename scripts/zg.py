#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
zg (zvec-grep) - Local-First AST Code Semantic Search & TieredLazyFetch CLI.
(Card-Retrieval-LocalFirst-zgSemanticSearch / v1.5.17)

Usage:
    python3 scripts/zg.py "心跳会话" --depth 1
    python3 scripts/zg.py "is_heartbeat_session" --depth 0
    python3 scripts/zg.py "RRF" --depth 2 --limit 3
"""

import argparse
import sys
import time
from pathlib import Path

# Add project root to sys.path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from openviking.search.zg_engine import ZGSearchEngine
from openviking.search.tiered_fetch import TierLevel


def main():
    parser = argparse.ArgumentParser(
        description="zg: Local-First AST Code Semantic Search with TieredLazyFetch (0-VRAM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", type=str, help="Search query (intent, concept, or code symbol)")
    parser.add_argument(
        "--depth", "-d",
        type=int,
        choices=[0, 1, 2],
        default=1,
        help="Lazy fetch depth: 0=Meta (pointers), 1=Fingerprint (~80%% savings, default), 2=Full Block",
    )
    parser.add_argument("--limit", "-n", type=int, default=5, help="Max results (default: 5)")
    parser.add_argument("--path", "-p", type=str, default=None, help="Filter by relative path substring")
    parser.add_argument("--reindex", action="store_true", help="Force re-scan and re-index codebase AST")

    args = parser.parse_args()

    engine = ZGSearchEngine.get_instance(repo_root=repo_root)

    if args.reindex:
        print("Scanning and indexing codebase AST symbols...")
        t0 = time.monotonic()
        count = engine.index_directory(max_files=400)
        dur = round((time.monotonic() - t0) * 1000.0, 1)
        print(f"Indexed {count} symbols in {dur}ms.")

    t0 = time.monotonic()
    summary = engine.search(
        query=args.query,
        depth=args.depth,
        limit=args.limit,
        path_filter=args.path,
    )
    elapsed_ms = round((time.monotonic() - t0) * 1000.0, 1)

    depth_labels = {0: "0 (Meta)", 1: "1 (Fingerprint · ~80% Savings)", 2: "2 (Full Block)"}
    print("=" * 72)
    print(f"  ⚡ zg (zvec-grep) | Query: '{args.query}' | Depth: {depth_labels.get(args.depth, str(args.depth))}")
    print(f"  📊 Found: {summary.total_results} symbols | Latency: {elapsed_ms}ms")
    print(
        f"  🛡️ Token Reduction: {summary.savings_percentage}% "
        f"({summary.actual_tokens_total} vs {summary.baseline_tokens_total} tokens baseline, saved {summary.total_tokens_saved})"
    )
    print("=" * 72)

    if not summary.results:
        print("  No symbols matched query.")
        return

    for idx, item in enumerate(summary.results, start=1):
        print(f"\n[#{idx}] {item.file_path}:{item.start_line}-{item.end_line} [{item.symbol_type} {item.symbol_name}] (score: {item.score:.3f}, fp: {item.fingerprint})")
        print("-" * 72)
        print(item.rendered_content)


if __name__ == "__main__":
    main()
