#!/usr/bin/env python3
"""
Openclaw Documentation, Wiki & Archive Vectorizer for OpenViking.
Uploads and registers all Wiki, Docs, Markdown, Roles, and Archives into OpenViking Memory Hub.
"""

import os
import glob
import time
import requests

OPENVIKING_API = os.getenv("OV_BASE_URL", "http://127.0.0.1:1933")
DELAY_BETWEEN_RESOURCES = 0.05

OPENCLAW_SEARCH_ROOTS = [
    "/home/skloxo/aho/openclaw",
    "/home/skloxo/.openclaw",
]

KEY_SUBDIRS = [
    "wiki",
    "docs",
    "documentation",
    "references",
    "archive",
    "archives",
    "migrated-backup",
    "backup",
    "roles",
    "planner",
    "designer",
    "evaluator",
    "skills",
    "knowledge",
]

def fetch_existing_resources() -> set:
    """Fetch root URIs of resources already in OpenViking."""
    try:
        resp = requests.get(f"{OPENVIKING_API}/api/v1/resources", timeout=5)
        if resp.status_code == 200:
            result = resp.json().get("result", [])
            if isinstance(result, list):
                return {r.get("root_uri") or r.get("uri") for r in result if isinstance(r, dict)}
    except Exception as e:
        print(f"[Warning] Failed to fetch existing resources: {e}")
    return set()

def upload_and_register_doc(abs_path: str) -> bool:
    """Upload document via multipart temp_upload and register into OpenViking memory."""
    filename = os.path.basename(abs_path)
    upload_url = f"{OPENVIKING_API}/api/v1/resources/temp_upload"
    add_url = f"{OPENVIKING_API}/api/v1/resources"

    try:
        with open(abs_path, 'rb') as f:
            files = {'file': (filename, f, 'text/markdown')}
            resp = requests.post(upload_url, files=files, timeout=10)
            if resp.status_code != 200:
                print(f"[Upload Error {resp.status_code}] {filename}: {resp.text}")
                return False

            temp_file_id = resp.json().get("result", {}).get("temp_file_id")

        if temp_file_id:
            payload = {
                "temp_file_id": temp_file_id,
                "reason": f"Openclaw Doc Ingestion: {filename}"
            }
            add_resp = requests.post(add_url, json=payload, timeout=10)
            if add_resp.status_code in (200, 201):
                return True
            else:
                print(f"[Register Error {add_resp.status_code}] {filename}: {add_resp.text}")
                return False
    except Exception as e:
        print(f"[Error] Failed to process {abs_path}: {e}")
        return False

def discover_openclaw_docs() -> list:
    """Discover high-value markdown and text documents across Openclaw Wiki, Docs, and Archives."""
    valid_paths = set()

    for base_root in OPENCLAW_SEARCH_ROOTS:
        if not os.path.exists(base_root):
            continue

        for root, dirs, files in os.walk(base_root):
            rel = os.path.relpath(root, base_root).lower()
            if any(ignored in rel for ignored in ['node_modules', '.git', 'venv', 'dist', 'build', '.next']):
                continue

            # Check if directory matches key doc/wiki/archive subdirs or root
            is_target_dir = any(k in rel for k in KEY_SUBDIRS) or root == base_root
            for f in files:
                if f.endswith('.md') or f.endswith('.txt'):
                    if is_target_dir:
                        abs_p = os.path.abspath(os.path.join(root, f))
                        # Ignore auto-generated or small dummy files
                        try:
                            if os.path.getsize(abs_p) > 20: # Must have content
                                valid_paths.add(abs_p)
                        except Exception:
                            pass

    return sorted(list(valid_paths))

def main():
    print("=== Openclaw Universal Documentation, Wiki & Archive Vectorizer ===")
    existing_resources = fetch_existing_resources()
    print(f"Existing resources registered in OpenViking: {len(existing_resources)}")

    print("\nScanning Openclaw for Wiki, Docs, References, Roles, and Archives...")
    discovered_docs = discover_openclaw_docs()
    print(f"Discovered {len(discovered_docs)} documentation/archive files.")

    print(f"\n🚀 Starting orderly multipart upload & vectorization (1 Task per Resource)...")
    start_time = time.time()
    added_count = 0

    for idx, doc_path in enumerate(discovered_docs, 1):
        if upload_and_register_doc(doc_path):
            added_count += 1
        time.sleep(DELAY_BETWEEN_RESOURCES)

        if idx % 10 == 0 or idx == len(discovered_docs):
            elapsed = time.time() - start_time
            rate = added_count / elapsed if elapsed > 0 else 0
            print(f"[Progress] {idx}/{len(discovered_docs)} docs uploaded & queued for vectorization ({rate:.1f} docs/s)", flush=True)

    print(f"\n✅ Complete! Successfully registered {added_count} files for vectorization in {time.time()-start_time:.2f}s.")

if __name__ == "__main__":
    main()
