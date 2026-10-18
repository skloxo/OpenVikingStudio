#!/usr/bin/env python3
# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Prune ghost slices and resync vector/BM25 storage with whitelist protection.

Card-104: 存量孤儿切片物理大扫除与向量库深度同步 (Stock Ghost Pruning & Vector Resync)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import requests
except ImportError:
    requests = None

# 物理免疫保护白名单前缀
PROTECTED_WHITELIST_PREFIXES = (
    "viking://resources/master_memory/",
    "viking://resources/skills/",
    "viking://resources/crystals/",
)

# 允许清理的测试遗留白名单例外
TEST_REMNANT_ALLOWLIST = (
    "test_card152_",
    "test_card104_",
)


def _get_api_credentials() -> tuple[str, str]:
    """Retrieve API key following Rule 13: dynamic credential injection."""
    api_key = os.environ.get("OPENVIKING_API_KEY")
    if api_key:
        return "http://127.0.0.1:1933", api_key

    # Try local root_key.txt
    root_key_file = Path.home() / ".openviking" / "data" / "root_key.txt"
    if root_key_file.is_file():
        try:
            key = root_key_file.read_text(encoding="utf-8").strip()
            if key:
                return "http://127.0.0.1:1933", key
        except Exception:
            pass

    # Try ov.conf
    ov_conf = Path.home() / ".openviking" / "ov.conf"
    if ov_conf.is_file():
        try:
            with open(ov_conf, "r", encoding="utf-8") as f:
                conf = json.load(f)
                server_conf = conf.get("server", {})
                key = server_conf.get("root_api_key")
                host = server_conf.get("host", "127.0.0.1")
                if host == "0.0.0.0":
                    host = "127.0.0.1"
                port = server_conf.get("port", 1933)
                if key:
                    return f"http://{host}:{port}", key
        except Exception:
            pass

    return "http://127.0.0.1:1933", ""


def is_protected_uri(uri: str) -> bool:
    """Check if URI falls under absolute physical whitelist protection."""
    # Check if it matches allowed test remnants
    for remnant in TEST_REMNANT_ALLOWLIST:
        if remnant in uri:
            return False

    for prefix in PROTECTED_WHITELIST_PREFIXES:
        if uri.startswith(prefix) or uri == prefix.rstrip("/"):
            return True

    return False


def run_prune(
    base_url: str,
    api_key: str,
    uri: str = "viking://resources",
    execute: bool = False,
) -> Dict[str, Any]:
    """Execute consistency check and optional ghost pruning via REST endpoint."""
    if requests is None:
        raise RuntimeError("requests library is required to run prune_ghost_slices.py")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    payload = {
        "uri": uri,
        "prune": execute,
    }

    url = f"{base_url.rstrip('/')}/api/v1/system/consistency"
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    result = data.get("result") or {}
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prune ghost slices and resync vector/BM25 storage (Card-104)."
    )
    parser.add_argument(
        "--uri",
        default="viking://resources",
        help="Root URI to check/prune (default: viking://resources)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute active pruning of orphan records (default is dry-run)",
    )
    parser.add_argument(
        "--url",
        default="",
        help="Base URL for OpenViking service (default: auto-detected)",
    )
    args = parser.parse_args()

    detected_url, api_key = _get_api_credentials()
    base_url = args.url or detected_url

    if not api_key:
        print("[WARN] No API key detected. Continuing without auth header...")

    mode_str = "ACTIVE PRUNE (EXECUTE)" if args.execute else "DRY-RUN (INSPECT ONLY)"
    print("=" * 60)
    print(f"🧹 [Card-104] 存量孤儿切片大扫除与向量库深度同步")
    print(f"• 目标 URI: {args.uri}")
    print(f"• 运行模式: {mode_str}")
    print(f"• 服务地址: {base_url}")
    print("=" * 60)

    try:
        report = run_prune(base_url, api_key, uri=args.uri, execute=args.execute)
    except Exception as exc:
        print(f"❌ 执行失败: {exc}")
        return 1

    expected_count = report.get("expected_count", 0)
    missing_count = report.get("missing_record_count", 0)
    orphan_vector_count = report.get("orphan_record_count", 0)
    orphan_bm25_count = report.get("bm25_orphan_count", 0)
    pruned_vector_count = report.get("pruned_vector_count", 0)
    pruned_bm25_count = report.get("pruned_bm25_count", 0)
    consistency_score = report.get("consistency_score", 0.0)

    print("\n📊 [扫描结果摘要]")
    print(f"  • 文件系统预期切片数: {expected_count}")
    print(f"  • 缺失索引切片数:     {missing_count}")
    print(f"  • 向量孤儿记录数:     {orphan_vector_count}")
    print(f"  • BM25 孤儿记录数:    {orphan_bm25_count}")
    if args.execute:
        print(f"  • 已清理向量孤儿数:   {pruned_vector_count}")
        print(f"  • 已清理 BM25 孤儿数: {pruned_bm25_count}")
    print(f"  • 一致性健康评分:     {consistency_score}%")

    # Display sample orphans
    bm25_orphans = report.get("bm25_orphan_records", [])
    if bm25_orphans:
        print(f"\n🔍 [BM25 孤儿清单 (前 {len(bm25_orphans)} 条)]:")
        for u in bm25_orphans[:5]:
            protected = " 🛡️ [PROTECTED]" if is_protected_uri(u) else ""
            print(f"    - {u}{protected}")

    vector_orphans = report.get("orphan_records", [])
    if vector_orphans:
        print(f"\n🔍 [向量孤儿清单 (前 {min(5, len(vector_orphans))} 条)]:")
        for u in vector_orphans[:5]:
            protected = " 🛡️ [PROTECTED]" if is_protected_uri(u) else ""
            print(f"    - {u}{protected}")

    print("\n" + "=" * 60)
    if not args.execute and (orphan_vector_count > 0 or orphan_bm25_count > 0):
        print("💡 提示: 当前为预览模式，使用 --execute 执行真实清理与同步。")
    elif args.execute:
        print("✅ 孤儿切片清理完成！")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
