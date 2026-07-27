#!/usr/bin/env python3
"""
universal_session_importer.py — v3
Imports ALL agent historical sessions into OpenViking via the proper queue:
  create session → batch add messages → commit → PENDING task

Sources:
  1. Antigravity IDE       ~/.gemini/antigravity-ide/brain/
  2. Antigravity V2.0      ~/.gemini/antigravity/brain/  (if exists)
  3. Hermes Agent          ~/.hermes/sessions/*.jsonl
  4. MIMO Code             ~/.local/share/mimocode/mimocode.db
  5. Openclaw Agents       ~/aho/openclaw/*/memory/.dreams/events.jsonl
"""

import os
import json
import time
import sqlite3
import requests
from pathlib import Path

OV_BASE           = "http://127.0.0.1:1933/api/v1"
BATCH_SIZE        = 50    # messages per /messages/batch call
DELAY_PER_SESSION = 0.3   # seconds between sessions
MAX_RETRIES       = 3     # API call retries on timeout


# ─── API helpers ─────────────────────────────────────────────────────────────

def ov_post(path: str, body: dict, retries: int = MAX_RETRIES) -> dict:
    for attempt in range(retries):
        try:
            resp = requests.post(f"{OV_BASE}{path}", json=body, timeout=20)
            if resp.ok:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                return {"error": "timeout after retries"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": "max retries exceeded"}


def get_existing_session_ids() -> set:
    try:
        resp = requests.get(f"{OV_BASE}/sessions?limit=5000", timeout=15)
        if resp.ok:
            return {s.get("session_id") for s in resp.json().get("result", []) if isinstance(s, dict)}
    except Exception as e:
        print(f"  [Warn] fetch existing sessions: {e}")
    return set()


def import_session(session_id: str, title: str, messages: list) -> str:
    """Create + populate + commit one session. Returns 'ok' or 'err:<reason>'."""
    if not messages:
        return "skip:empty"

    # 1. Create — 409 means already exists, still try to commit
    r = ov_post("/sessions", {"session_id": session_id})
    if r.get("error"):
        err_msg = str(r["error"])
        if "409" in err_msg:
            pass  # Already exists, proceed to commit
        else:
            return f"err:create:{err_msg[:60]}"

    # 2. Batch add messages
    for i in range(0, len(messages), BATCH_SIZE):
        chunk = messages[i:i + BATCH_SIZE]
        r2 = ov_post(f"/sessions/{session_id}/messages/batch", {"messages": chunk})
        if r2.get("error"):
            return f"err:messages:{str(r2['error'])[:60]}"

    # 3. Commit → creates PENDING session_commit task
    r3 = ov_post(f"/sessions/{session_id}/commit", {})
    if r3.get("error"):
        return f"err:commit:{str(r3['error'])[:60]}"

    return "ok"


# ─── Source loaders ──────────────────────────────────────────────────────────

def load_antigravity_sessions(app_data_dir: str, prefix: str) -> list:
    sessions = []
    brain = Path(app_data_dir) / "brain"
    if not brain.exists():
        return sessions
    for conv in brain.iterdir():
        if not conv.is_dir():
            continue
        transcript = conv / ".system_generated" / "logs" / "transcript.jsonl"
        if not transcript.exists():
            continue
        messages = []
        try:
            for line in open(transcript, errors="ignore"):
                try:
                    step = json.loads(line)
                    t, c = step.get("type",""), step.get("content","")
                    if not c or not isinstance(c, str):
                        continue
                    if t == "USER_INPUT":
                        messages.append({"role": "user",      "content": c[:8000]})
                    elif t == "PLANNER_RESPONSE":
                        messages.append({"role": "assistant", "content": c[:8000]})
                except Exception:
                    continue
        except Exception:
            continue
        if messages:
            sessions.append({
                "session_id": f"{prefix}_{conv.name}",
                "title":      f"{prefix}: {conv.name[:40]}",
                "messages":   messages,
            })
    return sessions


def load_hermes_sessions() -> list:
    sessions = []
    hermes_dir = Path.home() / ".hermes" / "sessions"
    if not hermes_dir.exists():
        return sessions
    for jf in sorted(hermes_dir.glob("*.jsonl")):
        messages = []
        try:
            for line in open(jf, errors="ignore"):
                try:
                    msg = json.loads(line)
                    role    = msg.get("role", "")
                    content = msg.get("content", "") or ""
                    if isinstance(content, list):
                        content = " ".join(
                            p.get("text","") for p in content
                            if isinstance(p, dict) and p.get("type") == "text"
                        )
                    if role in ("user","assistant") and content.strip():
                        messages.append({"role": role, "content": content[:8000]})
                except Exception:
                    continue
        except Exception:
            continue
        if messages:
            sessions.append({
                "session_id": f"hermes_{jf.stem}",
                "title":      f"Hermes: {jf.stem}",
                "messages":   messages,
            })
    return sessions


def load_mimocode_sessions() -> list:
    sessions = []
    db_path = Path.home() / ".local" / "share" / "mimocode" / "mimocode.db"
    if not db_path.exists():
        return sessions
    try:
        conn = sqlite3.connect(str(db_path))
        cur  = conn.cursor()
        cur.execute("SELECT id, title, project_id FROM session ORDER BY time_updated DESC")
        all_sessions = cur.fetchall()

        for sid, title, proj_id in all_sessions:
            cur.execute(
                "SELECT id, data, time_created FROM message WHERE session_id=? ORDER BY time_created ASC",
                (sid,)
            )
            msg_rows = cur.fetchall()
            messages = []
            for mid, data_json, ts in msg_rows:
                try:
                    data = json.loads(data_json) if data_json else {}
                    role = data.get("role","")
                    if role not in ("user","assistant"):
                        continue
                    # Gather text parts
                    pcur = conn.cursor()
                    pcur.execute("SELECT data FROM part WHERE message_id=?", (mid,))
                    content = "".join(
                        json.loads(p[0]).get("text","") for p in pcur.fetchall()
                        if p[0]
                    )
                    if content.strip():
                        messages.append({"role": role, "content": content[:8000]})
                except Exception:
                    continue
            if messages:
                sessions.append({
                    "session_id": f"mimocode_{sid[:16]}",
                    "title":      f"MIMO Code: {title or sid[:20]}",
                    "messages":   messages,
                })
        conn.close()
    except Exception as e:
        print(f"  [Warn] mimocode.db: {e}")
    return sessions


def load_openclaw_agent_sessions() -> list:
    """Load Openclaw sub-agent memory dream events as sessions."""
    sessions = []
    oc_root = Path.home() / "aho" / "openclaw"
    for agent_dir in oc_root.iterdir():
        if not agent_dir.is_dir():
            continue
        dreams = agent_dir / "memory" / ".dreams" / "events.jsonl"
        if not dreams.exists():
            continue
        messages = []
        try:
            for line in open(dreams, errors="ignore"):
                try:
                    ev = json.loads(line)
                    content = ev.get("content") or ev.get("summary") or ev.get("text") or ""
                    if isinstance(content, dict):
                        content = json.dumps(content, ensure_ascii=False)
                    if content.strip():
                        messages.append({"role": "assistant", "content": content[:8000]})
                except Exception:
                    continue
        except Exception:
            continue
        if messages:
            sessions.append({
                "session_id": f"openclaw-agent_{agent_dir.name}",
                "title":      f"Openclaw Agent: {agent_dir.name}",
                "messages":   messages,
            })
    return sessions


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=== Universal Session Importer v3 ===")
    print("  Flow: create → batch_add → commit → PENDING task")
    print()

    print("[1/5] Fetching existing sessions (skip duplicates)...")
    existing = get_existing_session_ids()
    print(f"       Already in OpenViking: {len(existing)}")

    print("\n[2/5] Scanning all sources...")
    all_sessions = []

    ag_ide = load_antigravity_sessions(
        str(Path.home() / ".gemini" / "antigravity-ide"), "antigravity-ide"
    )
    print(f"  Antigravity IDE:        {len(ag_ide):>4} sessions")
    all_sessions.extend(ag_ide)

    ag_v2 = load_antigravity_sessions(
        str(Path.home() / ".gemini" / "antigravity"), "antigravity-v2"
    )
    print(f"  Antigravity V2.0:       {len(ag_v2):>4} sessions")
    all_sessions.extend(ag_v2)

    hermes = load_hermes_sessions()
    print(f"  Hermes Agent:           {len(hermes):>4} sessions")
    all_sessions.extend(hermes)

    mimo = load_mimocode_sessions()
    print(f"  MIMO Code:              {len(mimo):>4} sessions")
    all_sessions.extend(mimo)

    oc_agents = load_openclaw_agent_sessions()
    print(f"  Openclaw Agents:        {len(oc_agents):>4} sessions")
    all_sessions.extend(oc_agents)

    # Deduplicate
    pending = [s for s in all_sessions if s["session_id"] not in existing]
    skipped = len(all_sessions) - len(pending)
    print(f"\n  Total to import: {len(pending)}  (skipping {skipped} already imported)")

    if not pending:
        print("\n✅ All sessions already imported.")
        return

    print(f"\n[3/5] Importing sessions...")
    ok = err = 0
    total = len(pending)

    for i, sess in enumerate(pending, 1):
        result = import_session(sess["session_id"], sess["title"], sess["messages"])
        if result == "ok":
            ok += 1
        elif result.startswith("skip"):
            pass
        else:
            err += 1
            if err <= 5:
                print(f"  ERR [{i}/{total}] {sess['session_id']}: {result}")

        if i % 25 == 0 or i == total:
            print(f"  [{i:>4}/{total}] OK={ok} ERR={err}", flush=True)

        time.sleep(DELAY_PER_SESSION)

    print(f"\n[5/5] Done! Queued {ok} sessions as PENDING tasks. Errors: {err}")
    print(f"      Tasks will process at their own pace in the Task Center.")


if __name__ == "__main__":
    main()
