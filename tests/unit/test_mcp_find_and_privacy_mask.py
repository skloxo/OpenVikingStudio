# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
tests/unit/test_mcp_find_and_privacy_mask.py
Card-219 针对性单测：
1. 验证 OpenVikingService.find 委托机制与防御性契约；
2. 验证 openviking_privacy_mask 对短 Key 与自然语言密码的高精度脱敏；
3. 验证芒格逆向对抗用例 (if password is None、CSS sk-cube、文档 required) 零误伤。
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from openviking.privacy.privacy_masker import (
    PrivacyMasker,
    get_privacy_masker,
    mask_text,
)
from openviking.service.privacy_masker import (
    PrivacyMasker as ServicePrivacyMasker,
    mask_sensitive_text,
)


def test_privacy_mask_positive_cases():
    """正向测试：3070 DSH 端历史真实 Case 必须 100% 正确脱敏"""
    # 1. 3070 真实测试输入
    raw_dsh = 'My API key is sk-1234567890abcdef and password is hunter2'
    masked = mask_text(raw_dsh)
    assert 'sk-1234567890abcdef' not in masked
    assert 'hunter2' not in masked
    assert 'sk-***[REDACTED_API_KEY]' in masked
    assert 'password is ***[REDACTED]***' in masked

    # 2. 键值赋值与引号语法
    raw_assign = 'api_key: "sk-proj-998877665544332211" password="super_secret_pwd"'
    masked_assign = mask_text(raw_assign)
    assert '998877665544332211' not in masked_assign
    assert 'super_secret_pwd' not in masked_assign

    # 3. 数据库 URI
    raw_uri = 'DATABASE_URL=postgres://dbuser:mypassword123@localhost:5432/main'
    masked_uri = mask_text(raw_uri)
    assert 'mypassword123' not in masked_uri
    assert '***[PASSWORD_MASKED]***' in masked_uri

    # 4. 私网端点可选脱敏
    raw_endpoint = 'Connecting to 192.168.1.100:8080 internal API'
    assert '192.168.1.100:8080' in mask_text(raw_endpoint, mask_private_endpoints=False)
    masked_ep = mask_text(raw_endpoint, mask_private_endpoints=True)
    assert '192.168.1.100:8080' not in masked_ep
    assert '***.***.***.***:***' in masked_ep


def test_privacy_mask_munger_negative_cases():
    """芒格逆向对抗测试：代码语法与技术文档绝对禁止发生破坏性误伤"""
    # 1. Python 逻辑判断：if password is None / null / not
    code_snippet = 'if password is None:\n    raise ValueError("password is required")'
    masked_code = mask_text(code_snippet)
    assert masked_code == code_snippet, f"Python code was mutated! {masked_code}"

    # 2. 技术文档说明
    doc_text = "The password is empty by default, but password is valid once set."
    masked_doc = mask_text(doc_text)
    assert masked_doc == doc_text, f"Doc was mutated! {masked_doc}"

    # 3. 前端 CSS / 外部类名
    css_class = '<div class="sk-folding-cube"><span class="sk-cube"></span></div>'
    masked_css = mask_text(css_class)
    assert masked_css == css_class, f"CSS classes mutated! {masked_css}"


def test_privacy_masker_facade_ssot_alignment():
    """测试 service.privacy_masker 与 privacy.privacy_masker 的单一真相源一致性"""
    raw = 'sk-1234567890abcdef and password="secret"'
    res1 = ServicePrivacyMasker.mask_text(raw)
    res2 = mask_text(raw)
    assert res1 == res2
    assert 'sk-1234567890abcdef' not in res1


@pytest.mark.asyncio
async def test_openviking_service_find_delegation():
    """验证 OpenVikingService.find 顶层快捷委托正常转接且无 AttributeError"""
    from openviking.service.core import OpenVikingService

    # 构造 mock service 实例
    service = OpenVikingService.__new__(OpenVikingService)
    service._initialized = True
    service._user = MagicMock(user_id="test_user")

    mock_search = MagicMock()
    mock_search.find = AsyncMock(return_value={"status": "ok", "memories": [], "resources": []})
    service._search_service = mock_search

    # 调用顶层 find
    res = await service.find(query="search test", limit=5)
    assert res["status"] == "ok"
    mock_search.find.assert_awaited_once()
