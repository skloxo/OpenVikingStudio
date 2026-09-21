"""
Unit tests for 404 root cause elimination & Postel's Law error rate cure.
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

from openviking.server.auth import get_request_context, get_session_request_context
from openviking.server.identity import RequestContext, Role
from openviking.server.routers.capability_page import router as capability_page_router
from openviking.server.routers.skill_kd import router as skill_kd_router
from openviking.server.routers.sessions import router as sessions_router
from openviking.observability.usage_audit.projection import should_skip_audit_route
from openviking_cli.session.user_id import UserIdentifier
from fastapi.responses import Response as RawResponse


from typing import Generator
from unittest.mock import AsyncMock, MagicMock
from openviking_cli.exceptions import NotFoundError
from openviking.server.dependencies import set_service


@pytest.fixture
def cure_app() -> Generator[FastAPI, None, None]:
    app = FastAPI()

    # Mount service-worker routes as in app.py
    @app.api_route("/service-worker.js", methods=["GET", "HEAD"], include_in_schema=False)
    @app.api_route("/studio/service-worker.js", methods=["GET", "HEAD"], include_in_schema=False)
    async def _service_worker_handler():
        return RawResponse(
            content="// OpenViking Studio no-op service worker\n",
            media_type="application/javascript",
            headers={"Cache-Control": "no-cache"},
        )

    # Mount the production routers directly (without manual prefix override)
    app.include_router(capability_page_router)
    app.include_router(skill_kd_router)
    app.include_router(sessions_router)

    # Setup mock service for sessions
    mock_service = MagicMock()
    mock_sessions = MagicMock()
    mock_sessions.get = AsyncMock(side_effect=NotFoundError("nonexistent-session-for-cure-test", "session"))
    mock_service.sessions = mock_sessions
    set_service(mock_service)

    async def _mock_ctx() -> RequestContext:
        return RequestContext(
            user=UserIdentifier("test_account", "test_user"),
            role=Role.ADMIN,
        )

    app.dependency_overrides[get_request_context] = _mock_ctx
    app.dependency_overrides[get_session_request_context] = _mock_ctx
    yield app
    set_service(None)


@pytest.fixture
def client(cure_app: FastAPI) -> TestClient:
    return TestClient(cure_app)


def test_service_worker_routes_return_200(client: TestClient) -> None:
    res_root = client.get("/service-worker.js")
    assert res_root.status_code == 200
    assert "javascript" in res_root.headers.get("content-type", "")

    res_studio = client.get("/studio/service-worker.js")
    assert res_studio.status_code == 200
    assert "javascript" in res_studio.headers.get("content-type", "")


def test_audit_skips_service_worker() -> None:
    assert should_skip_audit_route("/service-worker.js") is True
    assert should_skip_audit_route("/studio/service-worker.js") is True


def test_capability_page_router_prefix_aligned(client: TestClient) -> None:
    res = client.get("/api/v1/capability-pages")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    res_metrics = client.get("/api/v1/capability-pages/metrics/summary")
    assert res_metrics.status_code == 200
    data = res_metrics.json()
    assert "total_routes" in data


def test_skill_kd_router_prefix_aligned(client: TestClient) -> None:
    res = client.get("/api/v1/skill-kd/rules")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_session_context_postels_law_fallback(client: TestClient) -> None:
    # Non-existent session must return 200 with empty working memory instead of 404
    res = client.get("/api/v1/sessions/nonexistent-session-for-cure-test/context")
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") == "ok"
    result = body.get("result", {})
    assert result.get("messages") == []
    assert result.get("estimatedTokens") == 0
    assert "stats" in result
