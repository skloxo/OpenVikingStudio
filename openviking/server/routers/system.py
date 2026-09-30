# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""System endpoints for OpenViking HTTP Server."""

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from openviking.core.defensive import get_defensive_telemetry
from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.server.auth import get_request_context, require_role
from openviking.server.dependencies import get_service
from openviking.server.identity import AuthMode, RequestContext, Role
from openviking.server.models import Response
from openviking.server.routers.system_harness import (
    agent_loop_simulation_probe,
    bisection_heal_simulation_probe,
    get_agent_loop_telemetry,
    get_bisection_heal_telemetry,
    get_harness_metrics,
    harness_router,
    test_anti_lazy_guard,
    verify_harness_probe,
)
from openviking.server.routers.system_intent import (
    intent_router,
    match_intent,
    write_disambiguation,
)
from openviking.service.harness_catalog import (
    CORE_SKILLS_CATALOG,
    _get_active_skills_catalog,
    _load_all_evolution_lessons,
)
from openviking.server.routers.system_models import (
    AgentLoopProbeRequest,
    BackendSyncRequest,
    BisectionHealProbeRequest,
    ConsistencyRequest,
    MatchIntentRequest,
    TestGuardRequest,
    VerifyProbeRequest,
    WaitRequest,
    WriteDisambiguationRequest,
)
from openviking.server.routers.system_probes import (
    _embedding_probe,
    _is_ready_check_ok,
    _probe_agfs_readiness,
    _read_host_cpu,
    _read_host_mem,
    probe_gpu_telemetry,
    probe_system_host_resources,
)
from openviking.storage.viking_fs import get_viking_fs
from openviking_cli.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()
router.include_router(harness_router)
router.include_router(intent_router)

__all__ = [
    "router",
    "get_viking_fs",
    "_read_host_mem",
    "_read_host_cpu",
    "_is_ready_check_ok",
    "_probe_agfs_readiness",
    "_embedding_probe",
    "probe_gpu_telemetry",
    "probe_system_host_resources",
    "_load_all_evolution_lessons",
    "_get_active_skills_catalog",
    "CORE_SKILLS_CATALOG",
    "MatchIntentRequest",
    "WriteDisambiguationRequest",
    "VerifyProbeRequest",
    "TestGuardRequest",
    "AgentLoopProbeRequest",
    "BisectionHealProbeRequest",
    "WaitRequest",
    "ConsistencyRequest",
    "BackendSyncRequest",
    "match_intent",
    "write_disambiguation",
    "get_bisection_heal_telemetry",
    "bisection_heal_simulation_probe",
    "get_harness_metrics",
    "verify_harness_probe",
    "test_anti_lazy_guard",
    "get_agent_loop_telemetry",
    "agent_loop_simulation_probe",
]


@router.get("/health", tags=["system"])
async def health_check(request: Request):
    try:
        from openviking._version import version as __version__
    except Exception:
        try:
            import openviking

            __version__ = getattr(openviking, "__version__", "1.4.0")
        except Exception:
            __version__ = "1.4.0"

    result = {"status": "ok", "healthy": True, "version": __version__}

    try:
        config = getattr(request.app.state, "config", None)
        effective_auth_mode = AuthMode.API_KEY.value
        if config is not None and hasattr(config, "get_effective_auth_mode"):
            effective_auth_mode = config.get_effective_auth_mode()
        result["auth_mode"] = effective_auth_mode

        x_api_key = request.headers.get("X-API-Key")
        authorization = request.headers.get("Authorization")

        if x_api_key or authorization:
            try:
                from openviking.server.auth import resolve_identity

                identity = await resolve_identity(
                    request,
                    x_api_key=x_api_key,
                    authorization=authorization,
                    x_openviking_account=request.headers.get("X-OpenViking-Account"),
                    x_openviking_user=request.headers.get("X-OpenViking-User"),
                )
                result["account_id"] = str(identity.account_id)
                result["user_id"] = str(identity.user_id)
                result["role"] = str(identity.role)
            except Exception as e:
                logger.warning(f"Failed to resolve identity: {e}")
    except Exception as e:
        logger.error(f"Failed to get health check: {e}")

    return result


@router.get("/ready", tags=["system"])
async def readiness_check(request: Request):
    """Readiness probe — checks AGFS, VectorDB, and APIKeyManager."""
    try:
        service = get_service()
        if not service._initialized:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "reason": "initializing"},
            )
    except RuntimeError:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "initializing"},
        )

    checks: dict[str, Any] = {}

    try:
        checks["agfs"] = await _probe_agfs_readiness()
    except Exception as e:
        checks["agfs"] = {"status": "error", "checks": {"filesystem": f"error: {e}"}}

    try:
        viking_fs = get_viking_fs()
        storage = viking_fs._get_vector_store()
        if storage:
            healthy = await storage.health_check()
            checks["vectordb"] = "ok" if healthy else "unhealthy"
        else:
            checks["vectordb"] = "not_configured"
    except Exception as e:
        checks["vectordb"] = f"error: {e}"

    try:
        manager = getattr(request.app.state, "api_key_manager", None)
        if manager is not None:
            checks["api_key_manager"] = "ok"
        else:
            checks["api_key_manager"] = "not_configured"
    except Exception as e:
        checks["api_key_manager"] = f"error: {e}"

    try:
        from openviking_cli.utils.config.open_viking_config import OpenVikingConfigSingleton

        ov_config = OpenVikingConfigSingleton.get_instance()
        embedder = ov_config.embedding.get_embedder()
        if embedder is not None:
            probe_result = await asyncio.wait_for(_embedding_probe(embedder), timeout=10.0)
            checks["embedding"] = probe_result
        else:
            checks["embedding"] = "not_configured"
    except asyncio.TimeoutError:
        checks["embedding"] = "error: probe timed out (provider unreachable)"
    except Exception as e:
        checks["embedding"] = f"error: {e}"

    try:
        from openviking_cli.utils.config.open_viking_config import OpenVikingConfigSingleton
        from openviking_cli.utils.ollama import check_ollama_running, detect_ollama_in_config

        ov_config = OpenVikingConfigSingleton.get_instance()
        uses_ollama, ollama_host, ollama_port = detect_ollama_in_config(ov_config)
        if uses_ollama:
            if check_ollama_running(ollama_host, ollama_port):
                checks["ollama"] = "ok"
            else:
                checks["ollama"] = f"unreachable at {ollama_host}:{ollama_port}"
        else:
            checks["ollama"] = "not_configured"
    except Exception as e:
        checks["ollama"] = f"error: {e}"

    all_ok = all(_is_ready_check_ok(v) for v in checks.values())
    status_code = 200 if all_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
    )


@router.get("/api/v1/system/status", tags=["system"])
async def system_status(
    ctx: RequestContext = Depends(get_request_context),
):
    """Get system status."""
    service = get_service()
    return Response(
        status="ok",
        result={
            "initialized": service._initialized,
            "user": ctx.user.user_id,
        },
    )


@router.post("/api/v1/system/wait", tags=["system"])
async def wait_processed(
    request: WaitRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Wait for all processing to complete."""
    service = get_service()
    result = await service.resources.wait_processed(timeout=request.timeout)
    return Response(status="ok", result=result)


@router.post("/api/v1/system/consistency", tags=["system"])
async def check_consistency(
    request: ConsistencyRequest,
    ctx: RequestContext = Depends(get_request_context),
):
    """Check filesystem/vector-index consistency for a URI subtree with optional orphan pruning."""
    service = get_service()
    uri = validate_request_viking_uri(resolve_path_variables(request.uri), ctx)
    result = await service.check_consistency(
        uri=uri,
        ctx=ctx,
        prune=request.prune,
    )
    return Response(status="ok", result=result)


@router.post("/api/v1/system/backend/sync-status", tags=["system"])
async def backend_sync_status(
    request: BackendSyncRequest,
    ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN),
):
    """Return multi-write backend sync status for a Viking URI subtree."""
    service = get_service()
    uri = validate_request_viking_uri(resolve_path_variables(request.uri), ctx)
    result = await service.fs.system_sync_status(uri, ctx=ctx)
    return Response(status="ok", result=result)


@router.post("/api/v1/system/backend/sync-retry", tags=["system"])
async def backend_sync_retry(
    request: BackendSyncRequest,
    ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN),
):
    """Retry pending multi-write backend sync work for a Viking URI subtree."""
    service = get_service()
    uri = validate_request_viking_uri(resolve_path_variables(request.uri), ctx)
    result = await service.fs.system_sync_retry(uri, ctx=ctx)
    return Response(status="ok", result=result)


@router.get("/api/v1/system/sync/{sync_path:path}", tags=["system"])
async def admin_sync_status(
    sync_path: str,
    ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN),
):
    """Return multi-write backend sync status for one URI subtree through the admin API."""
    service = get_service()
    uri = validate_request_viking_uri(resolve_path_variables(sync_path), ctx)
    result = await service.fs.system_sync_status(uri, ctx=ctx)
    return Response(status="ok", result=result)


@router.post("/api/v1/system/sync/{sync_path:path}/retry", tags=["system"])
async def admin_sync_retry(
    sync_path: str,
    ctx: RequestContext = require_role(Role.ROOT, Role.ADMIN),
):
    """Retry pending multi-write backend sync work for one URI subtree through the admin API."""
    service = get_service()
    uri = validate_request_viking_uri(resolve_path_variables(sync_path), ctx)
    result = await service.fs.system_sync_retry(uri, ctx=ctx)
    return Response(status="ok", result=result)


@router.get("/api/v1/system/telemetry/trends", tags=["system"])
async def get_telemetry_trends(
    metric: str = "sla",
    window: str = "7d",
    ctx: RequestContext = Depends(get_request_context),
):
    """Return timeseries trend data points from SQLite TelemetryStore."""
    del ctx
    try:
        from openviking.telemetry.telemetry_store import TelemetryStore

        ts = TelemetryStore.get_instance()
        points = ts.get_trends(metric=metric, window=window)
        return {"status": "ok", "metric": metric, "window": window, "points": points}
    except Exception as e:
        logger.warning(f"Error getting telemetry trends: {e}")
        return {"status": "ok", "metric": metric, "window": window, "points": []}


@router.get("/api/v1/system/gpu", tags=["system"])
async def get_gpu_telemetry(
    ctx: RequestContext = Depends(get_request_context),
):
    """Return real GPU VRAM usage and compute utilization via nvidia-smi probe."""
    del ctx
    return await probe_gpu_telemetry()


@router.get("/api/v1/system/resources", tags=["system"])
async def get_system_host_resources(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Return real host CPU, memory, and system resource metrics."""
    return probe_system_host_resources()


@router.get("/api/v1/system/entropy/gatekeeper", tags=["system"])
async def get_entropy_gatekeeper_stats(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Retrieve real-time telemetry stats and recent decisions from EntropyGatekeeper."""
    from openviking.service.entropy_gatekeeper import EntropyGatekeeper

    stats = EntropyGatekeeper.get_instance().get_stats()
    return Response(
        status="ok",
        result=stats,
    ).model_dump(exclude_none=True)


@router.get("/api/v1/system/defensive", tags=["system"])
async def get_defensive_telemetry_endpoint(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Retrieve defensive registry telemetry and recent fallback trigger events."""
    return Response(
        status="ok",
        result=get_defensive_telemetry(),
    ).model_dump(exclude_none=True)
