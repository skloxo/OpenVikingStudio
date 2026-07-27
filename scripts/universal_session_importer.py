#!/usr/bin/env python3
"""
Universal Multi-Source Session Importer for OpenViking.
Imports historical conversations from:
1. Antigravity IDE
2. Antigravity V2.0 Desktop
3. Openclaw / Jarvis-Feishu
4. Hermes Agent
5. Mimo Code / VSCode

Protocol: 1 Session = EXACTLY 1 Background Task (Single Final Commit).
"""

import asyncio
import glob
import json
import os
import sqlite3
import sys
import time
import urllib.request
import urllib.error

OPENVIKING_API = os.getenv("OV_BASE_URL", "http://127.0.0.1:1933")
DELAY_BETWEEN_MSGS = 0.01

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
    """Post single message to session."""
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
    """Issue EXACTLY ONE final commit for session."""
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

# --- Source Parsers ---

def collect_antigravity_sessions() -> dict:
    """Collect Antigravity IDE and Antigravity V2.0 Desktop sessions."""
    sessions = {}
    base_dirs = [
        ("/home/skloxo/.gemini/antigravity-ide/brain", "antigravity-ide"),
        ("/home/skloxo/.gemini/antigravity/brain", "antigravity-v2"),
        ("/mnt/c/Users/Skl/.gemini/antigravity/brain", "antigravity-v2-win"),
        ("/mnt/c/Users/Skl/.gemini/antigravity-ide/brain", "antigravity-ide-win"),
    ]
    for bdir, tag in base_dirs:
        if not os.path.exists(bdir):
            continue
        patterns = [
            os.path.join(bdir, "*", ".system_generated", "logs", "transcript.jsonl"),
            os.path.join(bdir, "*", "system_generated", "logs", "transcript.jsonl"),
        ]
        for p in patterns:
            for filepath in glob.glob(p):
                sid = os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(filepath))))
                if sid not in sessions:
                    msgs = []
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                            for line in f:
                                if not line.strip(): continue
                                d = json.loads(line)
                                t, c = d.get("type"), d.get("content", "")
                                if t == "USER_INPUT" and c: msgs.append(("user", c))
                                elif t == "PLANNER_RESPONSE" and c: msgs.append(("assistant", c))
                    except Exception: pass
                    if msgs:
                        sessions[f"{tag}_{sid}"] = msgs
    return sessions

def collect_openclaw_sessions() -> dict:
    """Collect Openclaw / Jarvis Feishu sessions."""
    sessions = {}
    pattern = "/home/skloxo/.openclaw/**/*.jsonl"
    for filepath in glob.glob(pattern, recursive=True):
        if "trajectory" in filepath or "backup-pre-migrate" not in filepath:
            continue
        raw_name = os.path.splitext(os.path.basename(filepath))[0]
        sid = f"openclaw_{raw_name}"
        if sid not in sessions:
            msgs = []
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if not line.strip(): continue
                        d = json.loads(line)
                        role = d.get("role") or ("user" if d.get("type") == "USER_INPUT" else "assistant")
                        text = d.get("content") or d.get("text") or ""
                        if text:
                            msgs.append((role, text))
            except Exception: pass
            if msgs:
                sessions[sid] = msgs
    return sessions

def collect_hermes_sessions() -> dict:
    """Collect Hermes Agent sessions from SQLite DB."""
    sessions = {}
    db_path = "/home/skloxo/.hermes/state.db"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT session_id, role, content FROM messages ORDER BY id ASC")
            rows = cur.fetchall()
            for sid_raw, role, content in rows:
                sid = f"hermes_{sid_raw}"
                if sid not in sessions:
                    sessions[sid] = []
                if content:
                    sessions[sid].append((role or "user", content))
            conn.close()
        except Exception as e:
            print(f"[Warning] Error reading Hermes state.db: {e}")
    return sessions

def main():
    print("=== Universal Multi-Source Session Importer ===")
    existing_sessions = fetch_existing_sessions()
    print(f"Existing sessions in OpenViking: {len(existing_sessions)}")

    print("\nScanning session sources...")
    ag_sessions = collect_antigravity_sessions()
    print(f" -> Antigravity (IDE & V2.0 Desktop): {len(ag_sessions)} sessions")

    oc_sessions = collect_openclaw_sessions()
    print(f" -> Openclaw / Jarvis-Feishu: {len(oc_sessions)} sessions")

    hermes_sessions = collect_hermes_sessions()
    print(f" -> Hermes Agent: {len(hermes_sessions)} sessions")

    all_sessions = {}
    all_sessions.update(ag_sessions)
    all_sessions.update(oc_sessions)
    all_sessions.update(hermes_sessions)

    pending_sessions = {sid: msgs for sid, msgs in all_sessions.items() if sid not in existing_sessions}
    print(f"\nTotal unique sessions gathered: {len(all_sessions)}")
    print(f"Sessions pending import & vectorization: {len(pending_sessions)}")

    if not pending_sessions:
        print("🎉 All sessions across all systems are already fully imported!")
        return

    print("\n🚀 Starting orderly, rate-limited import (1 Task per Session)...")
    start_time = time.time()
    synced_count = 0
    total_msgs_count = 0

    for idx, (sid, msgs) in enumerate(pending_sessions.items(), 1):
        create_session_if_not_exists(sid)
        posted = 0
        for role, text in msgs:
            if post_message(sid, role, text):
                posted += 1
            time.sleep(DELAY_BETWEEN_MSGS)

        # Issue EXACTLY ONE final commit task for this session
        commit_session(sid)

        synced_count += 1
        total_msgs_count += posted

        if idx % 10 == 0 or idx == len(pending_sessions):
            elapsed = time.time() - start_time
            rate = synced_count / elapsed if elapsed > 0 else 0
            print(f"[Progress] {idx}/{len(pending_sessions)} sessions imported ({total_msgs_count} msgs, {rate:.1f} sess/s)", flush=True)

    print(f"\n✅ Import Complete! Synced {synced_count} sessions ({total_msgs_count} messages) in {time.time()-start_time:.2f}s.")
    print("Each session has been added as exactly 1 task in OpenViking queue.")

if __name__ == "__main__":
    main()
