#!/usr/bin/env python3
"""
sync_mimocode_sessions.py
Export MIMO code sessions from mimocode.db and upload to OpenViking.
One resource per session, single commit at end.
"""

import sqlite3
import json
import requests
import os
import time
import io

DB_PATH = os.path.expanduser("~/.local/share/mimocode/mimocode.db")
OV_BASE = "http://127.0.0.1:1933/api/v1"
NAMESPACE = "mimocode"

def get_sessions(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.title, s.time_created, s.time_updated,
               p.name as project_name
        FROM session s
        LEFT JOIN project p ON s.project_id = p.id
        ORDER BY s.time_updated DESC
    """)
    return cur.fetchall()

def get_session_messages(conn, session_id):
    cur = conn.cursor()
    cur.execute("""
        SELECT m.id, m.data, m.time_created
        FROM message m
        WHERE m.session_id = ?
        ORDER BY m.time_created ASC
    """, (session_id,))
    
    rows = cur.fetchall()
    processed_messages = []
    
    for row in rows:
        m_id, data_json, ts = row
        data = json.loads(data_json)
        role = data.get("role")
        
        # Get content parts
        part_cur = conn.cursor()
        part_cur.execute("SELECT data FROM part WHERE message_id = ?", (m_id,))
        parts = part_cur.fetchall()
        content = "".join([json.loads(p[0]).get("text", "") for p in parts])
        
        processed_messages.append((m_id, role, ts, content))
        
    return processed_messages

def format_session_text(session_row, messages):
    sid, title, created_at, updated_at, project_name = session_row
    lines = []
    lines.append(f"# MIMO Code Session: {title or sid}")
    lines.append(f"- Project: {project_name or 'N/A'}")
    lines.append(f"- Created: {created_at}")
    lines.append(f"- Updated: {updated_at}")
    lines.append(f"- Session ID: {sid}")
    lines.append("")

    for msg in messages:
        msg_id, role, ts, content = msg
        if not content:
            continue
        role_label = {"user": "👤 User", "assistant": "🤖 MIMO", "system": "⚙️ System"}.get(role, role)
        lines.append(f"### [{ts}] {role_label}")
        lines.append(content.strip())
        lines.append("")

    return "\n".join(lines)

def upload_text_as_resource(name, text):
    # Step 1: temp_upload as multipart
    file_obj = io.BytesIO(text.encode("utf-8"))
    resp = requests.post(
        f"{OV_BASE}/resources/temp_upload",
        files={"file": (f"{name}.md", file_obj, "text/markdown")}
    )
    if resp.status_code != 200:
        raise Exception(f"temp_upload failed: {resp.status_code} {resp.text[:200]}")
    temp_file_id = resp.json().get("temp_file_id") or resp.json().get("id")
    if not temp_file_id:
        raise Exception(f"No temp_file_id in response: {resp.text[:200]}")

    # Step 2: add_resource
    payload = {
        "name": name,
        "namespace": NAMESPACE,
        "temp_file_id": temp_file_id,
        "metadata": {"source": "mimocode", "type": "session"}
    }
    resp2 = requests.post(f"{OV_BASE}/resources/add_resource", json=payload)
    if resp2.status_code not in (200, 201):
        raise Exception(f"add_resource failed: {resp2.status_code} {resp2.text[:200]}")
    return resp2.json()

def commit_namespace():
    resp = requests.post(f"{OV_BASE}/resources/commit", json={"namespace": NAMESPACE})
    if resp.status_code not in (200, 202):
        print(f"  [WARN] commit returned {resp.status_code}: {resp.text[:100]}")
    else:
        print(f"  [OK] committed namespace '{NAMESPACE}'")

def main():
    print(f"[*] Connecting to {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    sessions = get_sessions(conn)
    print(f"[*] Found {len(sessions)} sessions to export")

    ok = 0
    err = 0
    for i, session_row in enumerate(sessions):
        sid, title, created_at, updated_at, project_name = session_row
        name = f"mimocode-session-{sid[:8] if len(str(sid))>=8 else sid}"

        messages = get_session_messages(conn, sid)
        if not messages:
            print(f"  [{i+1}/{len(sessions)}] SKIP {name}: no messages")
            continue

        text = format_session_text(session_row, messages)
        if len(text.strip()) < 50:
            print(f"  [{i+1}/{len(sessions)}] SKIP {name}: content too short")
            continue

        try:
            upload_text_as_resource(name, text)
            print(f"  [{i+1}/{len(sessions)}] OK   {name} ({len(messages)} msgs, {len(text)} chars)")
            ok += 1
        except Exception as e:
            print(f"  [{i+1}/{len(sessions)}] ERR  {name}: {e}")
            err += 1

        # Small rate-limit pause every 5 uploads
        if (i + 1) % 5 == 0:
            time.sleep(0.5)

    conn.close()

    print()
    print(f"[*] Done. OK={ok}, ERR={err}")
    print("[*] Committing namespace once...")
    commit_namespace()
    print("[*] All MIMO code sessions queued successfully.")

if __name__ == "__main__":
    main()
