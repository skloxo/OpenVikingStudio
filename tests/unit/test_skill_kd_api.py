"""
Unit tests for SKILL-KD REST API router.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.skill_kd import router as skill_kd_router
from openviking_cli.session.user_id import UserIdentifier


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(skill_kd_router, prefix="/api/v1")

    async def _mock_ctx() -> RequestContext:
        return RequestContext(
            user_id=UserIdentifier("test-user"),
            role=Role.ADMIN,
            auth_mode="dev",
        )

    app.dependency_overrides[get_request_context] = _mock_ctx
    return TestClient(app)


def test_list_rules_api(client: TestClient) -> None:
    res = client.get("/api/v1/skill-kd/rules")
    assert res.status_code == 200
    rules = res.json()
    assert isinstance(rules, list)
    assert len(rules) >= 1


def test_metrics_api(client: TestClient) -> None:
    res = client.get("/api/v1/skill-kd/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert "total_candidate_rules" in metrics
    assert "reexecution_pass_rate_pct" in metrics
    assert "sweet_spot_compliant" in metrics


def test_extract_bifurcation_api(client: TestClient) -> None:
    payload = {
        "student_trajectory": {
            "agent_id": "student_test",
            "task_id": "task_api_01",
            "task_description": "Fix bug",
            "turns": [
                {
                    "turn_idx": 0,
                    "action_type": "command",
                    "action_content": "bad_command",
                    "observation": "Error: command not found",
                    "is_success": False,
                }
            ],
            "final_success": False,
        },
        "teacher_trajectory": {
            "agent_id": "teacher_test",
            "task_id": "task_api_01",
            "task_description": "Fix bug",
            "turns": [
                {
                    "turn_idx": 0,
                    "action_type": "command",
                    "action_content": "good_command",
                    "observation": "Success",
                    "is_success": True,
                }
            ],
            "final_success": True,
        },
        "task_scenario": "shell_execution",
    }

    res = client.post("/api/v1/skill-kd/bifurcation/extract", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["bifurcation_count"] == 1
    assert len(data["candidate_rules"]) == 1
    patch_id = data["candidate_rules"][0]["patch_id"]

    # Now re-execute this rule in sandbox
    reexec_res = client.post(
        "/api/v1/skill-kd/reexecute",
        json={
            "patch_id": patch_id,
            "task_id": "task_api_01",
            "student_model_id": "student_test",
            "force_mock_outcome": True,
        },
    )
    assert reexec_res.status_code == 200
    reexec_data = reexec_res.json()
    assert reexec_data["turned_green"] is True
    assert reexec_data["gate_verdict"] == "ACCEPTED"


def test_consolidate_api(client: TestClient) -> None:
    res = client.post("/api/v1/skill-kd/rules/consolidate", json={"max_lines_limit": 300})
    assert res.status_code == 200
    data = res.json()
    assert "consolidated_rule_count" in data
    assert "within_sweet_spot" in data
