# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Search Key Rotator, Credit Extraction, and Key Fingerprinting.
"""

import json
from pathlib import Path
import pytest
import tempfile

from openviking.service.search_accounting_store import SearchAccountingStore
from openviking.service.search_key_rotator import SearchKeyRotator, SearchKeyItem


@pytest.fixture
def temp_rotator():
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "search_keys.json"
        db_path = Path(tmpdir) / "test_accounting.db"

        sample_keys = {
            "keenable": [
                {"alias": "acc1", "key": "keen_test_key_11111111111111111111", "monthly_quota": 100000},
                {"alias": "acc2", "key": "keen_test_key_22222222222222222222", "monthly_quota": 100000},
            ],
            "exa": [
                {"alias": "acc1", "key": "exa-test-key-11111111111111111111", "monthly_quota": 10.0},
            ],
            "tavily": [
                {"alias": "acc1", "key": "tvly-dev-test-11111111111111111111", "monthly_quota": 1000},
            ],
        }
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(sample_keys, f)

        SearchAccountingStore.reset_instance()
        SearchAccountingStore.get_instance(db_path=db_path)

        SearchKeyRotator.reset_instance()
        rotator = SearchKeyRotator.get_instance(config_path=cfg_path)
        yield rotator

        SearchKeyRotator.reset_instance()
        SearchAccountingStore.reset_instance()


def test_key_fingerprint_and_round_robin(temp_rotator: SearchKeyRotator):
    # 指纹格式：kb_前8位哈希
    key1 = temp_rotator.get_next_key("keenable")
    assert key1 is not None
    assert key1.fingerprint.startswith("kb_")
    assert len(key1.fingerprint) == 11  # "kb_" + 8 hex chars

    # 轮询到下一个 key
    key2 = temp_rotator.get_next_key("keenable")
    assert key2 is not None
    assert key2.key_id != key1.key_id

    # 再次获取回到 key1
    key3 = temp_rotator.get_next_key("keenable")
    assert key3.key_id == key1.key_id


def test_429_rate_limit_failover(temp_rotator: SearchKeyRotator):
    key1 = temp_rotator.get_next_key("keenable")
    assert key1 is not None

    # 标记 key1 429 冷却
    key1.mark_rate_limited(cooldown_sec=60.0)
    assert not key1.is_available()

    # 下一次调用应自动轮换到 key2，而不是返回处于冷却中的 key1
    key2 = temp_rotator.get_next_key("keenable")
    assert key2 is not None
    assert key2.key_id != key1.key_id
    assert key2.is_available()


def test_authoritative_credits_extraction():
    # 1. Tavily 响应体显式返回 credits
    body_tv = {"credits": 2.5, "results": []}
    c1 = SearchKeyRotator.extract_authoritative_credits("tavily", "search_deep", 200, {}, body_tv)
    assert c1 == 2.5

    # 2. Tavily 响应头返回 x-tavily-credits-used
    headers_tv = {"X-Tavily-Credits-Used": "1.8"}
    c2 = SearchKeyRotator.extract_authoritative_credits("tavily", "search_deep", 200, headers_tv, {})
    assert c2 == 1.8

    # 3. Keenable 响应头返回 x-credit-cost
    headers_kb = {"x-credit-cost": "1.0"}
    c3 = SearchKeyRotator.extract_authoritative_credits("keenable", "web_search", 200, headers_kb, {})
    assert c3 == 1.0

    # 4. Exa 响应体返回 cost
    body_exa = {"cost": 0.008}
    c4 = SearchKeyRotator.extract_authoritative_credits("exa", "search_neural", 200, {}, body_exa)
    assert c4 == 0.008

    # 5. 状态码非 200 消耗记为 0.0
    c_err = SearchKeyRotator.extract_authoritative_credits("tavily", "search_deep", 429, {}, None)
    assert c_err == 0.0


def test_get_key_health_overview(temp_rotator: SearchKeyRotator):
    overview = temp_rotator.get_key_health_overview()
    assert overview["total_keys"] == 4
    assert len(overview["keys"]) == 4
    assert "watermarks" in overview
    assert overview["watermarks"]["keenable"]["total_quota"] == 800000
    assert overview["watermarks"]["exa"]["total_quota"] == 90.0
    assert overview["watermarks"]["tavily"]["total_quota"] == 9000
