# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Sync skills and codebase symbols into SQLite FTS5 BM25 index.
"""

import json
from pathlib import Path
from openviking.storage.bm25_fts_index import BM25FTSIndex


def sync_bm25():
    bm25 = BM25FTSIndex.get_instance()
    skills_file = Path("/home/skloxo/.openviking/all_skills.json")
    docs = []

    if skills_file.exists():
        try:
            skills = json.loads(skills_file.read_text())
            for s in skills:
                name = s.get("name") or s.get("title") or ""
                path = s.get("path") or s.get("uri") or ""
                desc = s.get("description") or ""
                content = f"{name} {desc} {path}"

                p = Path(path)
                if p.is_file():
                    try:
                        content += " " + p.read_text(errors="ignore")[:4000]
                    except Exception:
                        pass
                elif (p / "SKILL.md").is_file():
                    try:
                        content += " " + (p / "SKILL.md").read_text(errors="ignore")[:4000]
                    except Exception:
                        pass

                docs.append({
                    "uri": f"skill://{name}",
                    "title": name,
                    "content": content,
                    "level": 2,
                    "context_type": "skill",
                })
        except Exception as e:
            print(f"Error loading skills: {e}")

    src_dir = Path(__file__).resolve().parent.parent / "openviking"
    for py_file in src_dir.rglob("*.py"):
        rel = py_file.relative_to(src_dir.parent)
        try:
            txt = py_file.read_text(errors="ignore")
            docs.append({
                "uri": f"code://{rel}",
                "title": py_file.stem,
                "content": txt[:8000],
                "level": 2,
                "context_type": "code",
            })
        except Exception:
            pass

    count = bm25.index_batch(docs)
    print(f"Successfully indexed {count} documents into BM25 FTS5 index!")
    stats = bm25.get_stats()
    print(f"Total in DB: {stats.total_documents}, DB size: {stats.db_size_bytes} bytes")


if __name__ == "__main__":
    sync_bm25()
