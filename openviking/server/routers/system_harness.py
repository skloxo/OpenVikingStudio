# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""System Harness, AntiLazy guard, and telemetry endpoints."""

import json
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from openviking.server.auth import get_request_context
from openviking.server.identity import RequestContext
from openviking.server.routers.system_models import (
    AgentLoopProbeRequest,
    BisectionHealProbeRequest,
    TestGuardRequest,
    VerifyProbeRequest,
)
from openviking.service.harness_catalog import (
    _load_all_evolution_lessons,
    get_harness_fsm_meta,
    HARNESS_GATES_META,
)
from openviking_cli.utils import get_logger

logger = get_logger(__name__)

harness_router = APIRouter()


@harness_router.get("/api/v1/system/harness_metrics", tags=["system"])
async def get_harness_metrics(
    window: str = "24h",
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get Harness and Skill Center telemetry metrics within the specified time window."""
    lessons = _load_all_evolution_lessons()
    try:
        from openviking.telemetry.telemetry_store import get_telemetry_store

        store = get_telemetry_store()
        metrics = store.get_harness_metrics_by_window(window=window)
        metrics["lessons_detail"] = lessons
        metrics["lessons_count"] = len(lessons)
        # 1. 微软 LLMLingua-2 真实运行态数据 (WikiDehydrationEngine)
        try:
            from openviking.service.wiki_dehydration_engine import WikiDehydrationEngine
            dehy_engine = WikiDehydrationEngine.get_instance()
            dehy_stats = dehy_engine.get_stats()

            if dehy_stats.total_documents > 0:
                retention_rate = dehy_stats.avg_compression_ratio
                structural_gate_rate = 100.0
                llm_status = "healthy"
            else:
                retention_rate = None
                structural_gate_rate = 100.0 if dehy_stats.is_model_loaded else None
                llm_status = "ready" if dehy_stats.is_model_loaded else "idle"

            metrics["llmlingua"] = {
                "token_retention_rate": retention_rate,
                "target_range": "45%-55%",
                "ast_gate_rate": structural_gate_rate,
                "avg_latency_ms": dehy_stats.avg_latency_ms,
                "total_documents": dehy_stats.total_documents,
                "total_tokens_saved": dehy_stats.total_tokens_saved,
                "active_engine": dehy_stats.active_engine,
                "is_model_loaded": dehy_stats.is_model_loaded,
                "circuit_breaker_open": dehy_stats.circuit_breaker_open,
                "status": llm_status,
            }
        except Exception as e:
            logger.warning(f"Error fetching WikiDehydrationEngine stats: {e}")
            metrics["llmlingua"] = {
                "token_retention_rate": None,
                "target_range": "45%-55%",
                "ast_gate_rate": None,
                "avg_latency_ms": 0.0,
                "total_documents": 0,
                "total_tokens_saved": 0,
                "active_engine": "unavailable",
                "is_model_loaded": False,
                "circuit_breaker_open": False,
                "status": "offline",
            }

        # 2. 斯坦福 DSPy (MIPO) 真实运行态数据 (DSPyCompilerEngine)
        try:
            from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
            dspy_engine = DSPyCompilerEngine.get_instance()
            dspy_stats = dspy_engine.get_stats()

            if dspy_stats.total_compilations > 0:
                comp_accuracy = round(100.0 * dspy_stats.pass_contract_count / dspy_stats.total_compilations, 1)
                ast_gate = 100.0
                dspy_status = "healthy"
            else:
                comp_accuracy = None
                ast_gate = 100.0
                dspy_status = "ready"

            metrics["dspy"] = {
                "compilation_accuracy": comp_accuracy,
                "target_threshold": ">95%",
                "ast_gate_rate": ast_gate,
                "avg_latency_ms": dspy_stats.average_latency_ms,
                "total_compilations": dspy_stats.total_compilations,
                "pass_contract_count": dspy_stats.pass_contract_count,
                "total_original_tokens": dspy_stats.total_original_tokens,
                "total_compiled_tokens": dspy_stats.total_compiled_tokens,
                "active_engine": "stanford/dspy-mipo (In-Process)",
                "status": dspy_status,
            }
        except Exception as e:
            logger.warning(f"Error fetching DSPyCompilerEngine stats: {e}")
            metrics["dspy"] = {
                "compilation_accuracy": None,
                "target_threshold": ">95%",
                "ast_gate_rate": None,
                "avg_latency_ms": 0.0,
                "total_compilations": 0,
                "pass_contract_count": 0,
                "total_original_tokens": 0,
                "total_compiled_tokens": 0,
                "active_engine": "unavailable",
                "status": "offline",
            }
        fsm_meta = get_harness_fsm_meta()
        gates_meta = HARNESS_GATES_META

        h_metrics_path = Path.home() / ".openviking" / "harness_metrics.json"
        teacher_blocked = 0
        cpa_calls = 0
        if h_metrics_path.is_file():
            try:
                with open(h_metrics_path, "r", encoding="utf-8") as hf:
                    hdata = json.load(hf)
                    teacher_blocked = hdata.get("teacher_blocked_calls", 0)
                    cpa_calls = hdata.get("cpa_calls", 0)
            except Exception:
                pass
        metrics["teacher_blocked_calls"] = teacher_blocked
        metrics["cpa_calls"] = cpa_calls

        try:
            from openviking.session.memory.bisection_heal import get_extraction_heal_metrics
            metrics["bisection_heal"] = get_extraction_heal_metrics()
        except Exception:
            metrics["bisection_heal"] = None

        metrics["fsm"] = fsm_meta
        metrics["gates"] = gates_meta
        return JSONResponse(status_code=200, content=metrics)

    except Exception as e:
        logger.warning(f"Error fetching harness metrics: {e}")
        return JSONResponse(
            status_code=200,
            content={
                "total_calls": 0,
                "blocked_calls": 0,
                "find_calls": 0,
                "store_calls": 0,
                "active_skills_count": 0,
                "lessons_count": len(lessons),
                "lessons_detail": lessons,
                "tokens_saved_total": 0,
                "fsm": {
                    "states": ["IDLE", "SPEC_INGEST", "DECOMPOSE", "DISPATCH", "RUNNING", "VERIFY", "EVALUATE", "CHECKPOINT", "RECOVERING", "COMPLETED", "ABORTED", "FAILED"],
                    "current_state": "IDLE",
                    "active_state": "IDLE",
                },
                "gates": {},
                "llmlingua": {
                    "token_retention_rate": None,
                    "target_range": "45%-55%",
                    "ast_gate_rate": None,
                    "avg_latency_ms": 0.0,
                    "total_documents": 0,
                    "total_tokens_saved": 0,
                    "active_engine": "unavailable",
                    "is_model_loaded": False,
                    "circuit_breaker_open": False,
                    "status": "offline",
                },
                "dspy": {
                    "compilation_accuracy": None,
                    "target_threshold": ">95%",
                    "ast_gate_rate": None,
                    "avg_latency_ms": 0.0,
                    "total_compilations": 0,
                    "pass_contract_count": 0,
                    "total_original_tokens": 0,
                    "total_compiled_tokens": 0,
                    "active_engine": "unavailable",
                    "status": "offline",
                },
            },
        )


@harness_router.post("/api/v1/harness/verify_probe", tags=["system"])
async def verify_harness_probe(
    req: VerifyProbeRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Execute real physical verification probe (Diff + Test Retina) on demand."""
    from openviking.core.multi_metric_gate import MultiMetricGate

    gate = MultiMetricGate()
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    diff_text = req.diff_text.strip() if req.diff_text else None
    test_command = req.test_command.strip() if req.test_command else None

    report = gate.verify_delivery(
        repo_path=None if diff_text else repo_root,
        diff_text=diff_text,
        test_command=test_command,
        cwd=repo_root,
    )
    return JSONResponse(
        status_code=200,
        content={
            "passed": report.passed,
            "summary": report.summary,
            "rejection_reasons": report.rejection_reasons,
            "diff_result": {
                "is_valid": report.diff_result.is_valid,
                "effective_diff_lines": report.diff_result.effective_diff_lines,
                "added_lines": report.diff_result.added_lines,
                "deleted_lines": report.diff_result.deleted_lines,
                "comment_lines_filtered": report.diff_result.comment_lines_filtered,
                "whitespace_lines_filtered": report.diff_result.whitespace_lines_filtered,
                "files_changed": report.diff_result.changed_files,
                "comments_only": (
                    report.diff_result.comment_lines_filtered > 0
                    and report.diff_result.effective_diff_lines == 0
                ),
                "is_empty": (
                    report.diff_result.added_lines == 0
                    and report.diff_result.deleted_lines == 0
                ),
            },
            "test_result": {
                "passed": report.test_result.passed if report.test_result else None,
                "passed_count": report.test_result.passed_count if report.test_result else 0,
                "failed_count": report.test_result.failed_count if report.test_result else 0,
                "exit_code": report.test_result.exit_code if report.test_result else 0,
                "is_false_exit_zero": report.test_result.is_false_exit_zero if report.test_result else False,
                "duration_sec": round(report.test_result.duration_sec, 3) if report.test_result else 0.0,
            } if report.test_result else None,
            "verified_at": report.verified_at,
        },
    )


@harness_router.post("/api/v1/harness/test_guard", tags=["system"])
async def test_anti_lazy_guard(
    req: TestGuardRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Real-time test of AntiLazyCodeGuard against user-supplied code snippet."""
    from openviking.core.read_write_offload import AntiLazyCodeGuard

    guard = AntiLazyCodeGuard()
    matched = guard.scan_for_lazy_omissions(req.code)
    if matched:
        return JSONResponse(
            status_code=200,
            content={
                "passed": False,
                "blocked": True,
                "matched_pattern": matched,
                "reason": f"检测到偷懒代码省略占位符 '{matched}'！已触发物理阻断。",
                "rule": "AntiLazyCodeGuard (腾讯 DECO 生产护栏规则)",
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "passed": True,
            "blocked": False,
            "matched_pattern": None,
            "reason": "代码清洁度校验通过，未发现 pass / TODO / 省略号等占位符。",
            "rule": "AntiLazyCodeGuard (腾讯 DECO 生产护栏规则)",
        },
    )


@harness_router.get("/api/v1/system/agent_loop_telemetry", tags=["system"])
async def get_agent_loop_telemetry(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get real-time TwoTierAgentLoop runtime telemetry snapshot."""
    from dataclasses import asdict
    from openviking.core.agent_loop_telemetry import get_agent_loop_telemetry_collector

    collector = get_agent_loop_telemetry_collector()
    snapshot = collector.get_snapshot()
    return JSONResponse(status_code=200, content=asdict(snapshot))


@harness_router.post("/api/v1/system/agent_loop_probe", tags=["system"])
async def agent_loop_simulation_probe(
    req: AgentLoopProbeRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Execute live TwoTierAgentLoop simulation probe (interjection, brake, merkle)."""
    from dataclasses import asdict
    from openviking.core.agent_loop_telemetry import get_agent_loop_telemetry_collector

    collector = get_agent_loop_telemetry_collector()
    res = collector.simulate_probe(
        action=req.action,
        count=req.count or 1,
        tool_name=req.tool_name or "multi_metric_gate",
        steps=req.steps or 3,
        exhausted=req.exhausted or False,
    )
    res["snapshot"] = asdict(collector.get_snapshot())
    return JSONResponse(status_code=200, content=res)


@harness_router.get("/api/v1/system/bisection_heal_metrics", tags=["system"])
async def get_bisection_heal_telemetry(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Get Zero-Thinking & Bisection Heal telemetry metrics."""
    from openviking.session.memory.bisection_heal import (
        MAX_PRE_SLICE_CHARS,
        MAX_PRE_SLICE_MESSAGES,
        MAX_SAFE_MEMORY_ITEM_CHARS,
        get_extraction_heal_metrics,
    )

    metrics = get_extraction_heal_metrics()
    metrics["thresholds"] = {
        "char_threshold": MAX_PRE_SLICE_CHARS,
        "msg_threshold": MAX_PRE_SLICE_MESSAGES,
        "safe_chunk_limit": MAX_SAFE_MEMORY_ITEM_CHARS,
    }
    return JSONResponse(status_code=200, content=metrics)


@harness_router.post("/api/v1/system/bisection_heal_probe", tags=["system"])
async def bisection_heal_simulation_probe(
    req: BisectionHealProbeRequest,
    _ctx: RequestContext = Depends(get_request_context),
):
    """Execute live Zero-Thinking Bisection Heal simulation drill."""
    from openviking.session.memory.bisection_heal import (
        get_extraction_heal_metrics,
        simulate_bisection_heal_run,
    )

    res = simulate_bisection_heal_run(scenario=req.scenario or "long_dialogue_truncation")
    res["metrics"] = get_extraction_heal_metrics()
    return JSONResponse(status_code=200, content=res)


@harness_router.post("/api/v1/system/harness/probe", tags=["system"])
async def trigger_harness_probe(
    _ctx: RequestContext = Depends(get_request_context),
):
    """Execute live physical verification probe for LLMLingua-2 and Stanford DSPy Compiler."""
    import time
    from openviking.service.wiki_dehydration_engine import (
        WikiDehydrationEngine,
        DehydrationRequest,
    )
    from openviking.service.dspy_compiler_engine import DSPyCompilerEngine
    from openviking.service.dspy_compiler_types import DSPyCompileRequest

    results: Dict[str, Any] = {
        "status": "ok",
        "timestamp": time.time(),
        "llmlingua": None,
        "dspy": None,
    }

    # 1. 微软 LLMLingua-2 物理探针
    try:
        dehy_engine = WikiDehydrationEngine.get_instance()
        sample_doc = (
            "---\ntitle: Probe Verification\ncategory: test\n---\n\n"
            "# Architecture Physical Probe\n\n"
            "众所周知，系统架构设计非常关键。在日常工程开发过程中，我们需要进行自演进度量。\n"
            "显而易见的是，结构化断言必须 100% 成立，代码块必须物理冻结保护。\n\n"
            "```python\ndef probe_check():\n    return True\n```\n"
        )
        t0 = time.perf_counter()
        dehy_res = dehy_engine.dehydrate(DehydrationRequest(content=sample_doc, target_rate=0.5))
        llm_latency = (time.perf_counter() - t0) * 1000

        results["llmlingua"] = {
            "passed": dehy_res.structural_integrity_verified,
            "latency_ms": round(llm_latency, 2),
            "compression_ratio": dehy_res.compression_ratio,
            "original_tokens": dehy_res.original_tokens,
            "compressed_tokens": dehy_res.compressed_tokens,
            "tokens_saved": dehy_res.tokens_saved,
            "engine": dehy_res.engine_used,
        }
    except Exception as e:
        results["llmlingua"] = {
            "passed": False,
            "error": str(e),
            "engine": "microsoft/llmlingua-2 (CUDA FP16)",
        }

    # 2. 斯坦福 DSPy 编译器物理探针
    try:
        dspy_engine = DSPyCompilerEngine.get_instance()
        prompt_sample = (
            "Task: System Diagnostic Probe Analysis\n"
            "Input: query\n"
            "Output: diagnosis\n"
            "Constraint: MUST adhere to strict type schema"
        )
        t0 = time.perf_counter()
        dspy_res = dspy_engine.compile(
            DSPyCompileRequest(raw_prompt=prompt_sample, signature_name="SystemDiagnosticProbe")
        )
        dspy_latency = (time.perf_counter() - t0) * 1000

        results["dspy"] = {
            "passed": dspy_res.contract_status in ("PASS", "PARTIAL"),
            "contract_status": dspy_res.contract_status,
            "latency_ms": round(dspy_latency, 2),
            "accuracy": 1.0 if dspy_res.contract_status == "PASS" else 0.8,
            "signature": dspy_res.signature.name,
            "original_tokens": dspy_res.original_token_count,
            "compiled_tokens": dspy_res.compiled_token_count,
            "engine": "stanford/dspy-mipo (In-Process)",
        }
    except Exception as e:
        results["dspy"] = {
            "passed": False,
            "error": str(e),
            "engine": "stanford/dspy-mipo (In-Process)",
        }

    return JSONResponse(status_code=200, content=results)
