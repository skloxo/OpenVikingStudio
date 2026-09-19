# -*- coding: utf-8 -*-
"""Unit tests for Card-Skill-ZipOnWrite-ContractualCompression (SkillZip 0-Rollout Engine).

Validates:
1. Six-Tuple Contractual Schema extraction (Interface, Workflow, Protocol, Rules, Contracts, Evidence).
2. Explain Once, Reference Everywhere (EORE) rule hoisting and deduplication.
3. 0-Rollout deterministic restructuring & knapsack compression (>= 30% reduction on bloated skills).
4. Zip-on-Write Gate enforcement (1.6~1.9x seed length ceiling & 100% contract fidelity).
5. FastAPI REST endpoints (/api/v1/skills/zip/compress, /gate-check, /stats).
"""

import pytest
from fastapi.testclient import TestClient


SAMPLE_VERBOSE_SKILL = """---
name: git-pr-flow
description: Automated Git PR submitter and reviewer
---
# Interface
- Input: branch_name: str, commit_message: str, reviewers: list[str]
- Output: pr_url: str, merge_status: bool
- Tools: git_push(), gh_api_create_pr(), gh_api_check_status()

# Workflow
1. Please ensure that you check the git status first before doing anything.
2. In this step, the user will expect that you run the test suite using pytest.
3. Always verify that no secrets or API keys are leaked into the code repository.
4. Next, push the branch to remote origin using the proxy if available.
5. Create the PR using gh_api_create_pr() with the commit message.
6. Poll the CI check status every 5 seconds until it completes.
7. Always verify that no secrets or API keys are leaked into the code repository.

# Protocol
- State FSM: INIT -> TESTING -> PUSHING -> PR_OPENED -> MERGED
- Timeout: 600s
- Retry: 3 times with exponential backoff

# Rules
- Always verify that no secrets or API keys are leaked into the code repository.
- NO GREEN EVER: Use cyan-500 for good and rose-500 for errors.
- Never propose a cd command directly to the shell.
- Please make sure that you do not add unnecessary external dependencies.
- NO GREEN EVER: Use cyan-500 for good and rose-500 for errors.

# Contracts
- Invariant: Single file size must not exceed 500 lines.
- Invariant: Zero plaintext credentials in source code.
- Invariant: Contract fidelity must remain 100%.

# Evidence
- Test: pytest tests/unit/test_pr_flow.py must pass 100%.
- Assertion: PR URL must match regex https://github.com/.+/pull/\\d+.
"""

SAMPLE_SEED_SKILL = """# Interface: git_push, gh_create_pr
# Workflow: 1. check status, 2. test, 3. push, 4. create pr
# Rules: 1. No secrets, 2. NO GREEN EVER
# Contracts: Invariant <= 500 lines
"""


def test_six_tuple_extraction():
    from openviking.service.skill_zip_engine import SkillZipEngine

    engine = SkillZipEngine()
    six_tuple = engine.parse_six_tuple(SAMPLE_VERBOSE_SKILL)

    assert "branch_name: str" in six_tuple.interface
    assert len(six_tuple.workflow) >= 5
    assert any("FSM" in p for p in six_tuple.protocol)
    assert len(six_tuple.rules) >= 3
    assert any("500 lines" in c for c in six_tuple.contracts)
    assert any("test_pr_flow.py" in e for e in six_tuple.evidence)


def test_eore_rule_hoisting_and_deduplication():
    from openviking.service.skill_zip_engine import SkillZipEngine

    engine = SkillZipEngine()
    six_tuple = engine.parse_six_tuple(SAMPLE_VERBOSE_SKILL)
    
    # Before deduplication, rules have duplicates (e.g. NO GREEN EVER, no secrets)
    deduped_tuple = engine.hoist_and_deduplicate(six_tuple)

    # Check that identical or near-identical rules are consolidated
    rule_texts = [r.lower() for r in deduped_tuple.rules]
    no_green_count = sum(1 for r in rule_texts if "no green ever" in r)
    assert no_green_count == 1, f"NO GREEN EVER should be deduplicated to 1, got {no_green_count}"
    
    no_secret_count = sum(1 for r in rule_texts if "no secrets or api keys" in r)
    assert no_secret_count == 1, f"No secrets rule should be deduplicated to 1, got {no_secret_count}"


def test_zero_rollout_deterministic_compression():
    from openviking.service.skill_zip_engine import SkillZipEngine

    engine = SkillZipEngine()
    result = engine.compress(SAMPLE_VERBOSE_SKILL)

    assert result.original_length == len(SAMPLE_VERBOSE_SKILL)
    assert result.compressed_length < result.original_length
    # Compression ratio should be >= 30% on verbose repetitive skills
    assert result.compression_ratio >= 0.30, f"Expected >= 0.30, got {result.compression_ratio}"
    # Invariant contracts must be 100% preserved
    assert result.contract_fidelity == 1.0
    assert "500 lines" in result.compressed_content
    assert "Zero plaintext credentials" in result.compressed_content
    assert result.latency_ms < 50.0  # 0-Rollout deterministic execution in <50ms


def test_zip_on_write_gate():
    from openviking.service.skill_zip_engine import SkillZipEngine

    engine = SkillZipEngine()
    seed_len = len(SAMPLE_SEED_SKILL)

    # 1. Normal short skill within 1.6x seed passes
    short_skill = SAMPLE_SEED_SKILL + "\n# Extra: minor comment"
    gate_short = engine.check_gate(short_skill, seed_length=seed_len)
    assert gate_short.passed is True
    assert gate_short.multiplier <= 1.9

    # 2. Bloated skill exceeding 1.9x seed length is flagged
    gate_bloated = engine.check_gate(SAMPLE_VERBOSE_SKILL, seed_length=seed_len)
    assert gate_bloated.multiplier > 1.9
    assert gate_bloated.passed is False
    assert gate_bloated.recommended_action in ("TRIGGER_ZIP", "REJECT_BLOATED")

    # 3. After zip, candidate passes gate
    zip_res = engine.compress(SAMPLE_VERBOSE_SKILL)
    gate_after_zip = engine.check_gate(zip_res.compressed_content, seed_length=seed_len)
    assert gate_after_zip.multiplier < gate_bloated.multiplier


def test_fastapi_skill_zip_endpoints():
    from openviking.server.app import create_app
    from openviking.server.auth import get_request_context
    from openviking.server.identity import RequestContext, Role, UserIdentifier

    app = create_app()
    app.dependency_overrides[get_request_context] = lambda: RequestContext(
        user=UserIdentifier(account_id="test-account", user_id="commander@antigravity"),
        role=Role.ADMIN,
    )
    client = TestClient(app)

    # 1. Compress endpoint
    comp_resp = client.post(
        "/api/v1/skills/zip/compress",
        json={"skill_content": SAMPLE_VERBOSE_SKILL},
    )
    assert comp_resp.status_code == 200
    data = comp_resp.json()
    assert data["compression_ratio"] >= 0.30
    assert data["contract_fidelity"] == 1.0
    assert len(data["compressed_content"]) > 0

    # 2. Gate check endpoint
    gate_resp = client.post(
        "/api/v1/skills/zip/gate-check",
        json={"skill_content": SAMPLE_VERBOSE_SKILL, "seed_length": len(SAMPLE_SEED_SKILL)},
    )
    assert gate_resp.status_code == 200
    gate_data = gate_resp.json()
    assert gate_data["multiplier"] > 1.9
    assert gate_data["passed"] is False

    # 3. Stats endpoint
    stats_resp = client.get("/api/v1/skills/zip/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_compressed"] >= 1
    assert stats["avg_compression_ratio"] >= 0.30
