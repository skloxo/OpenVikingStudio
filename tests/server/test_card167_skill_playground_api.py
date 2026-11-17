# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""API tests for Skill Playground (Card-167 / Tududi #155)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers import skill_playground
from openviking_cli.session.user_id import UserIdentifier


def _make_client(skills_dir: Path, monkeypatch) -> TestClient:
    app = FastAPI()
    app.include_router(skill_playground.router)
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="acct-1", user_id="tester"),
        role=Role.ADMIN,
    )
    monkeypatch.setattr(skill_playground, "resolve_skills_root", lambda: skills_dir)
    return TestClient(app)


def _seed_skills(root: Path) -> None:
    s1 = root / "web-harvest-pro"
    s1.mkdir(parents=True)
    (s1 / "SKILL.md").write_text(
        "---\n"
        "name: web-harvest-pro\n"
        "domain: crawl\n"
        "description: Web scraping and article extraction\n"
        "triggers:\n"
        "  - 抓取网页正文\n"
        "  - extract webpage article\n"
        "---\n\n# Web Harvest\n",
        encoding="utf-8",
    )
    s2 = root / "credential-vault"
    s2.mkdir(parents=True)
    (s2 / "SKILL.md").write_text(
        "---\n"
        "name: credential-vault\n"
        "domain: security\n"
        "description: KeePass local secrets search and rotation\n"
        "triggers:\n"
        "  - 查询密码库凭据\n"
        "  - keepass password lookup\n"
        "---\n\n# Vault\n",
        encoding="utf-8",
    )


def test_playground_hit_test_returns_scores_margin_collision_and_alias(tmp_path: Path, monkeypatch):
    _seed_skills(tmp_path)
    client = _make_client(tmp_path, monkeypatch)

    res = client.post(
        "/api/v1/skills/playground/hit-test",
        json={
            "query": "帮我抓取网页正文内容",
            "candidate_name": "wechat-article-reader",
            "candidate_triggers": ["抓取网页正文"],
            "candidate_content": "---\ndomain: crawl\n---\n抓取网页正文",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["catalog_size"] == 2
    assert body["matches"][0]["skill_name"] == "web-harvest-pro"
    assert body["top1_score"] >= 0.85
    assert body["margin"] >= 0.0
    assert body["collisions"]["has_collision"] is True
    assert body["collisions"]["collisions"][0]["conflicting_skill"] == "web-harvest-pro"
    assert body["alias_resolution"]["bundle_name"] == "web-harvest-pro"
    assert body["routing_decision"]["action"] in {"MERGE", "PACKAGE_ADD", "NEW_PACKAGE"}


def test_playground_compress_simulate_returns_six_tuple_metrics(tmp_path: Path, monkeypatch):
    _seed_skills(tmp_path)
    client = _make_client(tmp_path, monkeypatch)
    sample = (
        "---\nname: sample-ops\ndescription: Ops test skill\n---\n"
        "## Interface\nInputs and outputs\n\n"
        "## Workflow\n1. Read status\n2. Verify output\n\n"
        "## Protocol\n- Timeout after 5s\n\n"
        "## Rules\n- NO GREEN EVER in console UI\n\n"
        "## Contracts\n- Keep files under 500 lines\n\n"
        "## Evidence\n- Run pytest before handover\n"
    )
    res = client.post(
        "/api/v1/skills/playground/compress-simulate",
        json={"skill_content": sample, "seed_length": 200},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["compression"]["original_length"] == len(sample)
    assert body["compression"]["compressed_length"] > 0
    assert body["compression"]["contract_fidelity"] >= 0.0
    assert "workflow" in body["compression"]["six_tuple"]
    assert "passed" in body["gate"]


def test_playground_scaffold_generates_valid_six_section_skill(tmp_path: Path, monkeypatch):
    _seed_skills(tmp_path)
    client = _make_client(tmp_path, monkeypatch)
    res = client.post(
        "/api/v1/skills/playground/scaffold",
        json={
            "name": "incident-triage",
            "description": "Diagnose production alerts quickly",
            "domain": "observability",
            "triggers": ["排查告警", "incident triage"],
            "role": "SRE On-Call Agent",
            "constraints": ["所有外网探针强制设定 5s 超时"],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["sections"] == [
        "Interface",
        "Workflow",
        "Protocol",
        "Rules",
        "Contracts",
        "Evidence",
    ]
    assert body["validation"]["valid"] is True
    assert "## 1. Interface" in body["content"]
    assert "## 6. Evidence" in body["content"]
    assert "所有外网探针强制设定 5s 超时" in body["content"]
