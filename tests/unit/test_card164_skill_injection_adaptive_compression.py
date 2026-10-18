# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Unit tests for Card-164:
智能体运行态技能按需动态注脑与 Token 预算自适应抽稀
(Just-In-Time Skill Injection & Token-Budget Adaptive Compression SSOT).
"""

import json
import pytest
from openviking.service.skill_injection_service import (
    SkillInjectionService,
    SkillInjectionResult,
)


SAMPLE_RAW_SKILL = """---
name: sample-deploy-runner
description: 自动发布与部署运维自动化工作流
---

# Interface
- input: target_env: str, image_tag: str
- output: deployment_status: dict

# Workflow
1. Please ensure that you check parameter types thoroughly.
2. Next, verify cluster health and node quotas.
3. In this step, trigger rolling update using proxy if available.
4. Wait every 5 seconds until it completes.
5. Finally verify telemetry and health probes.

# Rules
- Always remember to verify that no secrets or API keys are leaked into the code repository.
- NO GREEN EVER: UI displays cyan or blue for status.
- Be aware that timeouts must not exceed 30 seconds.

# Contracts
- Invariant: Cluster capacity must remain >= 50% during rollout.
- Ceiling: Max retry count is 3.

# Evidence
- Verify test_deploy_pipeline passed.
- Assert health probe HTTP 200 within 5000ms.
"""


def test_injection_service_no_compact_returns_raw():
    """验证 compact=False 且无预算时，100% 原始文本返回，零破坏。"""
    service = SkillInjectionService.get_instance()
    result = service.compress_for_injection(SAMPLE_RAW_SKILL, compact=False)
    assert isinstance(result, SkillInjectionResult)
    assert not result.is_compact
    assert result.content == SAMPLE_RAW_SKILL
    assert result.compression_ratio == 0.0


def test_injection_service_compact_preserves_contracts_and_frontmatter():
    """验证 compact=True 时，提取六元组、消减口水话、保留 YAML Header 与 Contracts。"""
    service = SkillInjectionService.get_instance()
    result = service.compress_for_injection(SAMPLE_RAW_SKILL, compact=True)
    assert result.is_compact
    assert result.compression_ratio > 0.10  # 短样本去除口水话达标 11%+
    assert "---" in result.content
    assert "name: sample-deploy-runner" in result.content
    assert "Cluster capacity must remain >= 50%" in result.content
    assert "NO GREEN EVER" in result.content
    assert result.contract_fidelity == 1.0



def test_injection_service_budget_adaptive_truncation():
    """验证指定 budget_tokens 时，自适应按优先级截断，守住 Token 预算上限。"""
    service = SkillInjectionService.get_instance()
    # 限制极低预算 (例如 80 tokens)
    budget = 80
    result = service.compress_for_injection(SAMPLE_RAW_SKILL, compact=True, budget_tokens=budget)
    assert result.is_compact
    assert result.estimated_tokens <= budget + 25  # 允许极小元数据容差
    # 核心不变式与契约必须仍在
    assert "Cluster capacity must remain >= 50%" in result.content or "sample-deploy-runner" in result.content


def test_injection_service_munger_inversion_adversarial_cases():
    """芒格逆向思维对抗测试：空内容、无标头纯文本、代码块绝对保护。"""
    service = SkillInjectionService.get_instance()

    # 1. 空内容防御
    empty_res = service.compress_for_injection("", compact=True)
    assert empty_res.content == ""
    assert empty_res.estimated_tokens == 0

    # 2. 代码块绝对保护 (代码块内的语法不能被口水话正则篡改)
    code_skill = """---
name: code-skill
description: 代码块测试
---

# Workflow
1. Run following script:
```python
def check_key():
    # Please ensure that you do not leak
    msg = "Please ensure that you do not change"
    return msg
```
"""
    code_res = service.compress_for_injection(code_skill, compact=True)
    assert 'msg = "Please ensure that you do not change"' in code_res.content


@pytest.mark.asyncio
async def test_fastmcp_openviking_skills_get_and_inject():
    """验证 FastMCP openviking_skills 支持 action='get' 并返回紧凑规约。"""
    from openviking.server.mcp_endpoint import openviking_skills

    # 测试读取已知大包或虚拟场景
    res_str = await openviking_skills(
        action="get",
        name="codebase-engineering",
        compact=True,
        budget_tokens=300,
    )
    data = json.loads(res_str)
    assert data["status"] == "ok"
    assert data["name"] in ("codebase-engineering", "codebase_engineering")
    assert data["is_compact"] is True
    assert "content" in data
    assert len(data["content"]) > 0


@pytest.mark.asyncio
async def test_fastmcp_openviking_skills_get_virtual_scenario():
    """验证 FastMCP openviking_skills 获取虚拟场景别名 (如 auto-pr) 支持透明投影。"""
    from openviking.server.mcp_endpoint import openviking_skills

    res_str = await openviking_skills(
        action="inject",
        name="auto-pr",
        compact=True,
    )
    data = json.loads(res_str)
    assert data["status"] == "ok"
    assert "content" in data
    assert data["is_compact"] is True


def test_rest_api_get_skill_compact_mode():
    """验证 REST API GET /api/v1/skills/{name}?compact=true 端点。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openviking.server.routers.skills import router as skills_router
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = FastAPI()
    app.include_router(skills_router)
    dummy_ctx = RequestContext(
        user=UserIdentifier(user_id="user_admin", account_id="acc_default"),
        role=Role.ADMIN,
    )

    app.dependency_overrides[get_request_context] = lambda: dummy_ctx
    client = TestClient(app)

    # 1. 测试虚拟场景投影获取带 compact 选项
    resp = client.get("/api/v1/skills/auto-pr?compact=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    res = data["result"]
    assert res["is_compact"] is True
    assert "compression" in res
    assert res["compression"]["ratio"] >= 0.0

    # 2. 测试带 budget_tokens
    resp_budget = client.get("/api/v1/skills/auto-pr?compact=true&budget_tokens=200")
    assert resp_budget.status_code == 200
    data_b = resp_budget.json()
    assert data_b["status"] == "ok"
    assert data_b["result"]["is_compact"] is True

