#!/usr/bin/env python3
"""
Batch Session Importer for OpenViking.
Imports historical transcripts using Rate-Limiting and Single Final Commit.
"""

import asyncio
import glob
import json
import os
import sys
import time
import urllib.request
import urllib.error

OPENVIKING_API = os.getenv("OV_BASE_URL", "http://127.0.0.1:1933")
BRAIN_DIRS = [
    "/home/skloxo/.gemini/antigravity-ide/brain",
    "/mnt/c/Users/Skl/.gemini/antigravity/brain",
]

CONCURRENCY_LIMIT = 2  # Max parallel session imports
DELAY_BETWEEN_MSGS = 0.01  # Small delay between messages to prevent event loop starvation

def fetch_existing_sessions() -> set:
    """Fetch set of session IDs already stored in OpenViking."""
    try:
        req = urllib.request.Request(f"{OPENVIKING_API}/api/v1/sessions")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            result = data.get("result", [])
            if isinstance(result, list):
                return {s.get("session_id") for s in result if isinstance(s, dict)}
    except Exception as e:
        print(f"[Warning] Failed to fetch existing sessions: {e}")
    return set()

def create_session_if_not_exists(session_id: str) -> bool:
    """Ensure session exists in OpenViking."""
    url = f"{OPENVIKING_API}/api/v1/sessions"
    payload = json.dumps({"session_id": session_id}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status in (200, 201)
    except urllib.error.HTTPError as e:
        if e.code == 409: # Already exists
            return True
        return False
    except Exception:
        return False

def post_message(session_id: str, role: str, content: str) -> bool:
    """Post single message to session without immediate heavy commit."""
    url = f"{OPENVIKING_API}/api/v1/sessions/{session_id}/messages"
    payload = json.dumps({"role": role, "content": content[:4000]}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "X-OpenViking-Actor-Peer": "antigravity"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def commit_session(session_id: str) -> bool:
    """Issue a SINGLE final commit for session after all messages are posted."""
    url = f"{OPENVIKING_API}/api/v1/sessions/{session_id}/commit"
    payload = json.dumps({}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def extract_messages_from_transcript(path: str) -> list:
    msgs = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.strip():
                    continue
                d = json.loads(line)
                t, c = d.get("type"), d.get("content", "")
                if t == "USER_INPUT" and c:
                    msgs.append(("user", c))
                elif t == "PLANNER_RESPONSE" and c:
                    msgs.append(("assistant", c))
    except Exception:
        pass
    return msgs

def main():
    print("=== OpenViking High-Performance Session Importer ===")
    existing_sessions = fetch_existing_sessions()
    print(f"Found {len(existing_sessions)} sessions already in OpenViking.")

    session_files = {}
    for base_dir in BRAIN_DIRS:
        if not os.path.exists(base_dir):
            continue
        patterns = [
            os.path.join(base_dir, "*", ".system_generated", "logs", "transcript.jsonl"),
            os.path.join(base_dir, "*", "system_generated", "logs", "transcript.jsonl"),
        ]
        for p in patterns:
            for f in glob.glob(p):
                sid = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(f))))
                if sid not in session_files:
                    session_files[sid] = f

    all_items = list(session_files.items())
    pending_items = [(sid, path) for sid, path in all_items if sid not in existing_sessions]
    print(f"Total transcript sessions found: {len(all_items)}")
    print(f"Sessions pending sync: {len(pending_items)}")

    if not pending_items:
        print("All sessions are already up-to-date! Zero work needed.")
        return

    start_time = time.time()
    synced_sessions = 0
    synced_messages = 0

    for idx, (sid, path) in enumerate(pending_items, 1):
        msgs = extract_messages_from_transcript(path)
        if not msgs:
            continue

        create_session_if_not_exists(sid)
        posted_count = 0
        for role, content in msgs:
            if post_message(sid, role, content):
                posted_count += 1
            time.sleep(DELAY_BETWEEN_MSGS)

        # Single final commit
        commit_session(sid)

        synced_sessions += 1
        synced_messages += posted_count

        if idx % 10 == 0 or idx == len(pending_items):
            elapsed = time.time() - start_time
            rate = synced_sessions / elapsed if elapsed > 0 else 0
            print(f"[Progress] {idx}/{len(pending_items)} sessions synced ({synced_messages} msgs) in {elapsed:.1f}s ({rate:.1f} sess/s)", flush=True)

    print(f"\nDone! Successfully synced {synced_sessions} new sessions with {synced_messages} messages in {time.time()-start_time:.2f}s.")

if __name__ == "__main__":
    main()
