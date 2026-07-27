#!/usr/bin/env python3
"""
vectorize_openclaw_docs.py
Vectorize all Openclaw wiki/docs/archives into OpenViking via the proper queue:
  For each document:
    1. POST /api/v1/sessions          → create a synthetic session
    2. POST /sessions/{id}/messages/batch → add doc content as a message
    3. POST /sessions/{id}/commit     → queue as PENDING session_commit task

Tasks appear as "pending" in the Task Center and are processed at their own pace.
"""

import os
import time
import requests
from pathlib import Path

OV_BASE = "http://127.0.0.1:1933/api/v1"
DELAY_BETWEEN_DOCS = 0.3  # seconds between session commits

OPENCLAW_SEARCH_ROOTS = [
    "/home/skloxo/aho/openclaw",
    "/home/skloxo/.openclaw",
]

KEY_SUBDIRS = [
    "wiki", "docs", "documentation", "references",
    "archive", "archives", "migrated-backup", "backup",
    "roles", "planner", "designer", "evaluator",
    "skills", "knowledge",
]

IGNORE_DIRS = {'node_modules', '.git', 'venv', '__pycache__', 'dist', 'build', '.next', '.npm'}


def ov_post(path: str, body: dict, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            resp = requests.post(f"{OV_BASE}{path}", json=body, timeout=20)
            if resp.ok:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"error": "connection failed after retries"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "max retries exceeded"}


def get_existing_session_ids() -> set:
    try:
        resp = requests.get(f"{OV_BASE}/sessions?limit=5000", timeout=10)
        if resp.ok:
            result = resp.json().get("result", [])
            return {s.get("session_id") for s in result if isinstance(s, dict)}
    except Exception as e:
        print(f"  [Warning] Could not fetch existing sessions: {e}")
    return set()


def make_session_id(abs_path: str) -> str:
    """Create a stable session ID from file path."""
    import hashlib
    h = hashlib.md5(abs_path.encode()).hexdigest()[:12]
    name = Path(abs_path).stem[:30].replace(" ", "-").replace("/", "-")
    return f"doc-{name}-{h}"


def import_doc_as_session(abs_path: str, session_id: str) -> bool:
    """Create session, add doc content, commit to queue."""
    try:
        content = open(abs_path, errors="ignore").read().strip()
    except Exception as e:
        return False

    if len(content) < 30:
        return False

    title = f"Doc: {Path(abs_path).name} ({Path(abs_path).parent.name})"

    # 1. Create session
    r = ov_post("/sessions", {"session_id": session_id, "title": title})
    if "error" in r:
        return False

    # 2. Add doc content as a single message (truncate to 12k to be safe)
    msg = {
        "role": "user",
        "content": f"# {title}\n\nSource: {abs_path}\n\n---\n\n{content[:12000]}"
    }
    r2 = ov_post(f"/sessions/{session_id}/messages/batch", {"messages": [msg]})
    if "error" in r2:
        return False

    # 3. Commit → creates PENDING session_commit task
    r3 = ov_post(f"/sessions/{session_id}/commit", {})
    return "error" not in r3


def discover_openclaw_docs() -> list:
    """Discover high-value markdown/text docs across Openclaw."""
    valid_paths = set()

    for base_root in OPENCLAW_SEARCH_ROOTS:
        if not os.path.exists(base_root):
            continue

        for root, dirs, files in os.walk(base_root):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            rel = os.path.relpath(root, base_root).lower()
            is_target = any(k in rel for k in KEY_SUBDIRS) or root == base_root

            for f in files:
                if f.endswith('.md') or f.endswith('.txt'):
                    if is_target:
                        abs_p = os.path.abspath(os.path.join(root, f))
                        try:
                            if os.path.getsize(abs_p) > 50:
                                valid_paths.add(abs_p)
                        except Exception:
                            pass

    return sorted(valid_paths)


def main():
    print("=== Openclaw Docs Vectorizer (Proper Queue Mode) ===")
    print(f"  Using: create session → add content → commit (→ pending task)")
    print()

    print("[1/4] Fetching existing doc sessions from OpenViking...")
    existing = get_existing_session_ids()
    doc_sessions = {s for s in existing if s.startswith("doc-")}
    print(f"       Already imported: {len(doc_sessions)} doc sessions")

    print("\n[2/4] Discovering Openclaw docs...")
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

    print(f"\n[3/4] Queueing docs as pending session_commit tasks...")
    ok = 0
    err = 0
    total = len(pending_docs)

    for i, (doc_path, sid) in enumerate(pending_docs, 1):
        if import_doc_as_session(doc_path, sid):
            ok += 1
        else:
            err += 1

        if i % 50 == 0 or i == total:
            print(f"  [{i}/{total}] OK={ok} ERR={err}", flush=True)

        time.sleep(DELAY_BETWEEN_DOCS)

    print(f"\n[4/4] Done. Queued {ok} docs as PENDING tasks. Errors: {err}")
    print(f"      Tasks will be processed by workers at their own pace.")


if __name__ == "__main__":
    main()
