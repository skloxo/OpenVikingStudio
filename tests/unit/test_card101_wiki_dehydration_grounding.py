# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Card-101 单元测试：LLMLingua 全域 Wiki 知识库真实文档接入与镜像落盘闭环 (Card-101 Grounding Tests)
"""

import os
import shutil
import tempfile
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from openviking.service.wiki_dehydrate_apply import (
    ApplyDehydrationRequest,
    WikiDehydrateApplyService,
)
from openviking.server.app import create_app
from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role, UserIdentifier


@pytest.fixture
def temp_wiki_workspace():
    """沙盒环境用于测试 Wiki 真实文件读取、镜像落盘与快照备份。"""
    temp_dir = Path(tempfile.mkdtemp(prefix="test_wiki_dehydrate_"))
    wiki_root = temp_dir / "master_memory"
    backup_root = temp_dir / "quarantine"
    wiki_root.mkdir(parents=True, exist_ok=True)
    backup_root.mkdir(parents=True, exist_ok=True)

    # 建立两个子目录和测试文件
    decisions_dir = wiki_root / "decisions"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    doc1 = decisions_dir / "2026-09-04_task_unification.md"
    doc1_content = """---
title: Task Unification Architecture
version: 1.0.0
---

# 任务治理规范
众所周知，我们必须对系统任务进行全面收口统一管理。
显而易见的是，一切任务都必须具备可追踪性。

```python
def check_task(task_id: str) -> bool:
    return True
```
"""
    doc1.write_text(doc1_content, encoding="utf-8")

    lessons_dir = wiki_root / "evolution_lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)
    doc2 = lessons_dir / "lesson_01.md"
    doc2.write_text("# Lesson 1\n工程文明的底线在于真实闭环与严谨留痕。\n", encoding="utf-8")

    yield {
        "temp_dir": temp_dir,
        "wiki_root": wiki_root,
        "backup_root": backup_root,
        "doc1": doc1,
        "doc2": doc2,
        "doc1_content": doc1_content,
    }

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_list_wiki_documents(temp_wiki_workspace):
    """验证 Wiki 文档列表发现与分类过滤。"""
    ws = temp_wiki_workspace
    service = WikiDehydrateApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["wiki_root"]],
    )
    docs = service.list_documents()
    assert len(docs) == 2
    names = [d.name for d in docs]
    assert "2026-09-04_task_unification.md" in names
    assert "lesson_01.md" in names

    # 分类过滤
    decision_docs = service.list_documents(category="decisions")
    assert len(decision_docs) == 1
    assert decision_docs[0].category == "decisions"


def test_read_wiki_document(temp_wiki_workspace):
    """验证根据 URI 读取文档内容。"""
    ws = temp_wiki_workspace
    service = WikiDehydrateApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["wiki_root"]],
    )
    uri = "viking://resources/master_memory/decisions/2026-09-04_task_unification.md"
    content = service.read_document(uri)
    assert "Task Unification Architecture" in content

    with pytest.raises(FileNotFoundError):
        service.read_document("viking://resources/master_memory/non_existent.md")


def test_apply_mirror_mode(temp_wiki_workspace):
    """验证镜像模式 (.dehydrated.md) 生成与快照备份。"""
    ws = temp_wiki_workspace
    service = WikiDehydrateApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["wiki_root"]],
    )
    uri = "viking://resources/master_memory/decisions/2026-09-04_task_unification.md"
    dehydrated_text = """---
title: Task Unification Architecture
version: 1.0.0
---

# 任务治理规范
系统任务必须全面收口统一管理，具备可追踪性。

```python
def check_task(task_id: str) -> bool:
    return True
```
"""
    req = ApplyDehydrationRequest(
        uri=uri,
        dehydrated_content=dehydrated_text,
        mode="mirror",
        operator="test_agent",
    )
    res = service.apply_dehydration(req)
    assert res.success is True
    assert res.mode == "mirror"
    assert res.target_uri.endswith(".dehydrated.md")

    # 验证镜像文件已生成
    mirror_file = ws["doc1"].parent / "2026-09-04_task_unification.dehydrated.md"
    assert mirror_file.exists()
    assert mirror_file.read_text(encoding="utf-8").strip() == dehydrated_text.strip()

    # 验证原文件未被篡改
    assert ws["doc1"].read_text(encoding="utf-8") == ws["doc1_content"]

    # 验证快照文件已生成
    snapshot = Path(res.snapshot_path)
    assert snapshot.exists()
    assert snapshot.read_text(encoding="utf-8") == ws["doc1_content"]


def test_apply_in_place_mode(temp_wiki_workspace):
    """验证原地覆写模式与快照保护。"""
    ws = temp_wiki_workspace
    service = WikiDehydrateApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["wiki_root"]],
    )
    uri = "viking://resources/master_memory/evolution_lessons/lesson_01.md"
    new_content = "# Lesson 1\n工程底线在于真实闭环与严谨留痕。\n"

    req = ApplyDehydrationRequest(
        uri=uri,
        dehydrated_content=new_content,
        mode="in_place",
        operator="test_agent",
    )
    res = service.apply_dehydration(req)
    assert res.success is True
    assert res.mode == "in_place"
    assert ws["doc2"].read_text(encoding="utf-8").strip() == new_content.strip()

    # 快照保护
    snapshot = Path(res.snapshot_path)
    assert snapshot.exists()
    assert "工程文明的底线" in snapshot.read_text(encoding="utf-8")


def test_structural_gate_rejection(temp_wiki_workspace):
    """验证当 YAML 头部丢失或代码块数量不一致时触发结构门禁拦截。"""
    ws = temp_wiki_workspace
    service = WikiDehydrateApplyService(
        backup_root=ws["backup_root"],
        candidate_dirs=[ws["wiki_root"]],
    )
    uri = "viking://resources/master_memory/decisions/2026-09-04_task_unification.md"

    # 缺失 YAML 头部
    bad_content = "# 任务治理规范\n丢失了 YAML frontmatter。"
    with pytest.raises(ValueError, match="YAML frontmatter was removed"):
        service.apply_dehydration(
            ApplyDehydrationRequest(uri=uri, dehydrated_content=bad_content)
        )


def test_api_endpoints(temp_wiki_workspace):
    """验证 FastAPI 端点 /documents, /document, /apply 闭环。"""
    ws = temp_wiki_workspace
    app = create_app()

    # 注入受信任的测试 context
    dummy_ctx = RequestContext(
        user=UserIdentifier(user_id="test_user", account_id="default"),
        role=Role.ADMIN,
    )
    app.dependency_overrides[get_request_context] = lambda: dummy_ctx

    client = TestClient(app)

    # 1. GET /documents
    res_list = client.get("/api/v1/wiki/dehydrate/documents?limit=10")
    assert res_list.status_code == 200
    docs = res_list.json()
    assert isinstance(docs, list)

    # 2. GET /document
    if docs:
        first_uri = docs[0]["uri"]
        res_doc = client.get(f"/api/v1/wiki/dehydrate/document?uri={first_uri}")
        assert res_doc.status_code == 200
        assert "content" in res_doc.json()
