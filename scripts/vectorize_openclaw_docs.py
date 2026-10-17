#!/usr/bin/env python3
"""
vectorize_openclaw_docs.py — High-Performance Parallel Ingestion (Proper Queue Mode)
Discovers all high-value documents, skills, trade references, and MCP schemas across:
  - ~/aho (Openclaw, TideTrading, SkillOpt, etc.)
  - ~/.openclaw
  - ~/.gemini
  - ~/services

Queues them into OpenViking via the proper queue flow:
  create session → add doc content → commit → PENDING task

Uses ThreadPoolExecutor for 20x faster task queuing.
"""

import os
import time
import hashlib
import requests
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

OV_BASE = "http://127.0.0.1:1933/api/v1"
CONCURRENT_THREADS = 12

OPENCLAW_SEARCH_ROOTS = [
    "/home/skloxo/aho",
    "/home/skloxo/.openclaw",
    "/home/skloxo/.gemini",
    "/home/skloxo/services",
]

KEY_SUBDIRS = [
    "wiki", "docs", "documentation", "references",
    "archive", "archives", "migrated-backup", "backup",
    "roles", "planner", "designer", "evaluator", "researcher", "developer", "product-manager",
    "skills", "knowledge", "cases", "events", "preferences", "entities", "patterns",
    "task-receipts", "dreaming", "tidetrading", "mcp", "strategies", "attempts", "shared-skills",
]

IGNORE_DIRS = {'node_modules', '.git', 'venv', '.venv', '__pycache__', 'dist', 'build', '.next', '.npm'}


def ov_post(path: str, body: dict, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = requests.post(f"{OV_BASE}{path}", json=body, timeout=20)
            if resp.ok:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return {"error": "connection failed after retries"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "max retries exceeded"}


def get_existing_session_ids() -> set:
    try:
        resp = requests.get(f"{OV_BASE}/sessions?limit=5000", timeout=15)
        if resp.ok:
            result = resp.json().get("result", [])
            return {s.get("session_id") for s in result if isinstance(s, dict)}
    except Exception as e:
        print(f"  [Warning] Could not fetch existing sessions: {e}")
    return set()


def make_session_id(abs_path: str) -> str:
    """Create a stable session ID from file path."""
    h = hashlib.md5(abs_path.encode()).hexdigest()[:12]
    name = Path(abs_path).stem[:30].replace(" ", "-").replace("/", "-")
    return f"doc-{name}-{h}"


def import_doc_as_session(item: tuple) -> bool:
    """Create session, add doc content, commit to queue."""
    abs_path, session_id = item
    try:
        content = open(abs_path, errors="ignore").read().strip()
    except Exception:
        return False

    if len(content) < 30:
        return False

    title = f"Doc: {Path(abs_path).name} ({Path(abs_path).parent.name})"

    # 1. Create session (409 = already exists, proceed to commit)
    r = ov_post("/sessions", {"session_id": session_id, "title": title})
    if r.get("error"):
        err_msg = str(r["error"])
        if "409" not in err_msg:
            return False

    # 2. Add doc content as a single message (truncate to 12k to be safe)
    msg = {
        "role": "user",
        "content": f"# {title}\n\nSource: {abs_path}\n\n---\n\n{content[:12000]}"
    }
    r2 = ov_post(f"/sessions/{session_id}/messages/batch", {"messages": [msg]})
    if r2.get("error"):
        return False

    # 3. Commit → creates PENDING session_commit task
    r3 = ov_post(f"/sessions/{session_id}/commit", {})
    return not bool(r3.get("error"))


def discover_openclaw_docs() -> list:
    """Discover high-value markdown/text/json docs across search roots."""
    valid_paths = set()

    for base_root in OPENCLAW_SEARCH_ROOTS:
        if not os.path.exists(base_root):
            continue

        for root, dirs, files in os.walk(base_root):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            rel = os.path.relpath(root, base_root).lower()
            is_target = any(k in rel for k in KEY_SUBDIRS) or root == base_root

            for f in files:
                if f.endswith('.md') or f.endswith('.txt') or f.endswith('.json'):
                    if is_target:
                        abs_p = os.path.abspath(os.path.join(root, f))
                        try:
                            if os.path.getsize(abs_p) > 50:
                                valid_paths.add(abs_p)
                        except Exception:
                            pass

    return sorted(valid_paths)


def main():
    print("=== Openclaw Docs Vectorizer (High-Speed Parallel Queue Mode) ===")
    print("  Using: 12-thread parallel push → create session → add content → commit")
    print()

    print("[1/4] Fetching existing doc sessions from OpenViking...")
    existing = get_existing_session_ids()
    doc_sessions = {s for s in existing if s.startswith("doc-")}
    print(f"       Already imported: {len(doc_sessions)} doc sessions")

    print("\n[2/4] Discovering Openclaw docs & knowledge...")
    all_docs = discover_openclaw_docs()
    print(f"       Discovered: {len(all_docs)} documents")

    pending_docs = []
    for doc_path in all_docs:
        sid = make_session_id(doc_path)
        if sid not in doc_sessions:
            pending_docs.append((doc_path, sid))

    print(f"       To import:   {len(pending_docs)} (skipping {len(all_docs) - len(pending_docs)} already imported)")

    if not pending_docs:
        print("\n✅ All docs already imported. Nothing to do.")
        return

    print(f"\n[3/4] Queueing docs as pending session_commit tasks (12 threads)...")
    ok = 0
    err = 0
    total = len(pending_docs)
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
        futures = {executor.submit(import_doc_as_session, item): item for item in pending_docs}
        for i, future in enumerate(as_completed(futures), 1):
            try:
                if future.result():
                    ok += 1
                else:
                    err += 1
            except Exception:
                err += 1

            if i % 100 == 0 or i == total:
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"  [{i:>5}/{total}] OK={ok:<5} ERR={err:<3} ({rate:.1f} docs/sec)", flush=True)

    elapsed = time.time() - start_time
    print(f"\n[4/4] Done in {elapsed:.1f}s! Queued {ok} docs as PENDING tasks. Errors: {err}")
    print(f"      Tasks will be processed by OpenViking workers at maximum speed.")


if __name__ == "__main__":
    main()
