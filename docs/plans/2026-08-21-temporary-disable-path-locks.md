# Temporary Path Lock Bypass Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Disable Path Lock operations process-wide by default, with an explicit environment-variable escape hatch to restore them during troubleshooting.

**Architecture:** `AsyncAGFSClient` is the single Python boundary before the Rust Path Lock manager. By default it makes acquire calls return a compatible synthetic owned lease and lifecycle/query calls return no-op results without reaching the binding. Set `OPENVIKING_DISABLE_PATH_LOCKS=false` to restore the original binding calls.

**Tech Stack:** Python 3, asyncio, pytest, AsyncAGFSClient.

---

### Task 1: Specify the bypass in async-client tests

**Files:**
- Modify: `tests/agfs/test_async_client.py`

**Step 1: Write the failing test**

Add a recording fake with all Path Lock methods. Under `OPENVIKING_DISABLE_PATH_LOCKS=1`, assert every acquire returns a synthetic owned lease, lifecycle methods accept it, queries return unlocked/empty values, and no backend Path Lock method runs.

**Step 2: Run test to verify it fails**

Run: `uv run --active pytest tests/agfs/test_async_client.py -q`
Expected: FAIL because the adapter currently forwards Path Lock calls to the binding.

### Task 2: Implement the minimum adapter bypass

**Files:**
- Modify: `openviking/pyagfs/async_client.py`

**Step 1: Add an environment flag helper and synthetic lease constants**

Treat only `1`, `true`, `yes`, and `on` (case-insensitive) as enabled. Keep the check per invocation so test changes and process configuration changes are observed without recreating the client.

**Step 2: Bypass every Path Lock method consistently**

Return a compatible owned lease for all acquire/adopt methods; return a compatible handoff ref for `to_handoff`; do nothing for release/handoff; return `refreshed`, `False`, and zero-count observability values for refresh, lock checks, and observe. Preserve validation of malformed batch requests before bypassing.

**Step 3: Run focused tests**

Run: `uv run --active pytest tests/agfs/test_async_client.py tests/pyagfs/test_async_client_fs_ctx.py -q`
Expected: PASS.

### Task 3: Verify the default behavior and quality gates

**Files:**
- Modify: `tests/agfs/test_async_client.py`

**Step 1: Add an unset-variable regression assertion**

Assert a normal Path Lock call still reaches the backend with the existing context and arguments when the environment variable is absent.

**Step 2: Run checks**

Run: `uv run --active pytest tests/agfs/test_async_client.py tests/pyagfs/test_async_client_fs_ctx.py -q`
Run: `uv run --active ruff check openviking/pyagfs/async_client.py tests/agfs/test_async_client.py`

**Step 3: Review the diff**

Run: `git diff --check && git diff -- openviking/pyagfs/async_client.py tests/agfs/test_async_client.py docs/plans/2026-08-21-temporary-disable-path-locks.md`
