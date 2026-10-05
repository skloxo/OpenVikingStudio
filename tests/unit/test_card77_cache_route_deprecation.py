"""
tests/unit/test_card77_cache_route_deprecation.py - Card-77 悬空缓存路由下线与端点物理注销验真单测

第一性原理与奥卡姆剃刀：
验证 /api/v1/cache/stats, /clear, /benchmark 路由已被物理注销，
routers 模块彻底切除 cache_tier2_router 导出，杜绝一切悬空伪端点。
"""

import pytest
from fastapi.routing import APIRoute

import openviking.server.routers as routers
from openviking.server.app import create_app


def test_routers_all_excludes_cache_tier2():
    """验证 routers.__all__ 彻底移除 cache_tier2_router"""
    assert "cache_tier2_router" not in routers.__all__, (
        "cache_tier2_router 仍残留在 openviking.server.routers.__all__ 中"
    )
    assert not hasattr(routers, "cache_tier2_router"), (
        "routers 命名空间仍可访问 cache_tier2_router 属性"
    )


def test_cache_tier2_module_physically_deleted():
    """验证 openviking.server.routers.cache_tier2 物理模块已被删除"""
    with pytest.raises(ModuleNotFoundError):
        import openviking.server.routers.cache_tier2  # noqa: F401


def test_fastapi_app_has_zero_cache_routes():
    """验证 FastAPI 应用程序已无任何 /api/v1/cache 前缀路由"""
    app = create_app()
    cache_routes = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.path.startswith("/api/v1/cache") or "/cache/" in route.path:
                cache_routes.append(route.path)

    assert len(cache_routes) == 0, (
        f"FastAPI app 仍注册了悬空缓存路由: {cache_routes}"
    )


def test_app_router_mount_purity():
    """验证 app 中不存在任何指向 Tier2LRUCacheEngine 的端点绑定"""
    app = create_app()
    route_endpoints = [
        getattr(endpoint, "__name__", "")
        for r in app.routes
        if isinstance(r, APIRoute) and (endpoint := getattr(r, "endpoint", None)) is not None
    ]
    assert "get_cache_stats" not in route_endpoints
    assert "clear_cache" not in route_endpoints
    assert "benchmark_cache" not in route_endpoints
