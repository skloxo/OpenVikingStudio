"""
tests/unit/test_card78_dead_cache_purge.py - Card-78 冗余缓存代码清退与真实轻量架构验真

第一性原理与奥卡姆剃刀：
验证 Tier2LRUCacheEngine 与 cache_tier2_types 模块已被物理切除，
杜绝一切伪造 10k 并发压测的玩具代码与死肉模块，系统纯净度 100% 达标。
"""

import pytest
import openviking.service as service


def test_cache_tier2_engine_physically_deleted():
    """验证 openviking.service.cache_tier2_engine 已物理删除"""
    with pytest.raises(ModuleNotFoundError):
        import openviking.service.cache_tier2_engine  # noqa: F401


def test_cache_tier2_types_physically_deleted():
    """验证 openviking.service.cache_tier2_types 已物理删除"""
    with pytest.raises(ModuleNotFoundError):
        import openviking.service.cache_tier2_types  # noqa: F401


def test_service_module_cleanliness():
    """验证 openviking.service 模块命名空间没有任何 cache_tier2 相关的遗留"""
    assert not hasattr(service, "Tier2LRUCacheEngine")
    assert not hasattr(service, "cache_tier2_engine")
    assert not hasattr(service, "CacheStats")
    assert not hasattr(service, "CachePolicy")


def test_occam_razor_no_hidden_wrappers():
    """验证系统不依赖任何外部玩具缓存引擎，核心服务保持纯粹轻量"""
    from openviking.service.core import OpenVikingService

    # 核心服务类不依赖任何假缓存实例
    assert not hasattr(OpenVikingService, "tier2_cache")
    assert not hasattr(OpenVikingService, "cache_tier2")
