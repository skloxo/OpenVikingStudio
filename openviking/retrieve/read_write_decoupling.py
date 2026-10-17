# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""
Read/Write Decoupling Knowledge Engineering Desk (WeKnora & Karpathy Architecture).
Separates heavy graph compilation (Editorial Desk) from ultra-low latency reads (Serving Desk).
(Card-Knowledge-HG-RAG-HierarchicalCompass / v1.5.19 / OPT-02)

Architectural Boundary & SSOT Delegation:
- In-Memory Serving Layer: Serves as an immutable read-only memory snapshot with atomic
  pointer swaps for zero-contention reads during graph recompilation.
- Persistence & Concurrency SSOT: Persistent storage, ACID transactions, and multi-process
  concurrency remain strictly delegated to SQLite in WAL mode (Single Source of Truth via
  VikingFS). This desk does NOT replace database-level concurrency, strictly following
  Occam's Razor to avoid overengineering.
"""

import threading
import time
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from openviking.retrieve.compass_topology import (
    CompassNode,
    HierarchicalCompassNavigator,
    NavigationResult,
    CompassDirection,
)


class KnowledgeDeskStats(BaseModel):
    """Statistics for the read-write decoupled knowledge desk."""
    active_version: int = 1
    total_nodes: int = 0
    total_roots: int = 0
    max_depth: int = 0
    last_swap_ts: float = 0.0
    serving_desk_ready: bool = True


class KnowledgeDeskManager:
    """
    Read/Write Decoupled Knowledge Desk Manager.
    - Editorial Desk: Draft/Staging environment for tree assembly & batch updates.
    - Serving Desk: Immutable read-only snapshot for lock-free, zero-contention reads.
    - SSOT Delegation: Durability & persistence are strictly anchored in SQLite WAL mode.
    """

    _instance: Optional["KnowledgeDeskManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._version = 1
        self._last_swap_ts = time.time()
        # Active Serving Desk Navigator
        self._serving_navigator = HierarchicalCompassNavigator()
        # Staging Editorial Desk Navigator
        self._editorial_navigator = HierarchicalCompassNavigator()
        self._init_seed_compass_topology()

    @classmethod
    def get_instance(cls) -> "KnowledgeDeskManager":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def _init_seed_compass_topology(self) -> None:
        """Seed the knowledge desk with OpenViking core hierarchical architecture."""
        nodes = [
            # Root Level (depth=0)
            CompassNode(
                node_id="root_openviking",
                title="OpenViking 核心架构与知识中枢",
                content_snippet="OpenViking 是基于第一性原理打造的分布式智能体体外大脑与记忆中枢，对外统一服务端口 1933。",
                depth=0,
                breadcrumbs=["OpenViking 核心架构与知识中枢"],
                parent_id=None,
                children_ids=["ch_invariants", "ch_retrieval", "ch_storage"],
            ),
            # Chapter 1: Invariants (depth=1)
            CompassNode(
                node_id="ch_invariants",
                title="企业级四大不可变式 (Enterprise Invariants)",
                content_snippet="包含可终止 (Terminability)、可隔离 (Isolatability)、可恢复 (Recoverability)、可观测 (Observability)。",
                depth=1,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "企业级四大不可变式"],
                parent_id="root_openviking",
                children_ids=["sec_budget", "sec_spec_fs"],
                sibling_next_id="ch_retrieval",
            ),
            # Section 1.1: Budget (depth=2)
            CompassNode(
                node_id="sec_budget",
                title="ExecutionBudget 耗时与 Token 熔断器",
                content_snippet="支持总耗时、Token 量、成本 USD 与工具调用次数硬上限限制，超时自动熔断防死循环。",
                depth=2,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "企业级四大不可变式", "ExecutionBudget 熔断器"],
                parent_id="ch_invariants",
                sibling_next_id="sec_spec_fs",
            ),
            # Section 1.2: SpecWorkspace (depth=2)
            CompassNode(
                node_id="sec_spec_fs",
                title="SpecWorkspace 静态资产只读挂载沙箱",
                content_snippet="严格只读挂载 AGENTS.md 与 skills/，会话沙箱独立隔离读写，物理阻断路径穿越。",
                depth=2,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "企业级四大不可变式", "SpecWorkspace 沙箱"],
                parent_id="ch_invariants",
                sibling_prev_id="sec_budget",
            ),
            # Chapter 2: Retrieval Engines (depth=1)
            CompassNode(
                node_id="ch_retrieval",
                title="双轨多引擎检索体系 (Retrieval Engines)",
                content_snippet="融合 BM25 词法倒排索引、稠密向量检索、zg 本地 AST 语义搜索与 RAG 主动弃答门禁。",
                depth=1,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "双轨多引擎检索体系"],
                parent_id="root_openviking",
                children_ids=["sec_bm25", "sec_zg", "sec_abstention"],
                sibling_prev_id="ch_invariants",
                sibling_next_id="ch_storage",
            ),
            # Section 2.1: BM25 (depth=2)
            CompassNode(
                node_id="sec_bm25",
                title="BM25 SQLite FTS5 与无参 RRF 融合",
                content_snippet="消除纯 Dense 向量在精确代码符号、类名与错误栈的检索盲区，实现 100% 精确符号提权。",
                depth=2,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "双轨多引擎检索体系", "BM25 FTS5 混合检索"],
                parent_id="ch_retrieval",
                sibling_next_id="sec_zg",
            ),
            # Section 2.2: zg (depth=2)
            CompassNode(
                node_id="sec_zg",
                title="zg 本地命令行代码语义搜索 (TieredLazyFetch)",
                content_snippet="纯本地 0 显存，AST 符号级切片，depth=1 紧凑指纹相比完整代码块节约 78% Token。",
                depth=2,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "双轨多引擎检索体系", "zg 本地代码语义搜索"],
                parent_id="ch_retrieval",
                sibling_prev_id="sec_bm25",
                sibling_next_id="sec_abstention",
            ),
            # Section 2.3: RAG Abstention (depth=2)
            CompassNode(
                node_id="sec_abstention",
                title="RAG 证据约束验证与零幻觉主动弃答门禁",
                content_snippet="MinHash LSH 毫秒级近去重，RARG 证据覆盖率判官，出域查询 100% 触发主动弃答。",
                depth=2,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "双轨多引擎检索体系", "RAG 主动弃答门禁"],
                parent_id="ch_retrieval",
                sibling_prev_id="sec_zg",
            ),
            # Chapter 3: Storage (depth=1)
            CompassNode(
                node_id="ch_storage",
                title="VikingFS 统一存储与多模态适配",
                content_snippet="底层收口 SQLite 物理数据库与分层嵌入存储，统一拦截 WebDAV、REST 与 MCP 写入路径。",
                depth=1,
                breadcrumbs=["OpenViking 核心架构与知识中枢", "VikingFS 统一存储"],
                parent_id="root_openviking",
                children_ids=[],
                sibling_prev_id="ch_retrieval",
            ),
        ]

        for n in nodes:
            self._serving_navigator.add_node(n)
            self._editorial_navigator.add_node(n)

    def get_serving_navigator(self) -> HierarchicalCompassNavigator:
        """Get the active read-only serving desk navigator."""
        return self._serving_navigator

    def swap_editorial_to_serving(self) -> KnowledgeDeskStats:
        """
        Atomic swap: Publish editorial staging graph to the serving desk.
        Zero downtime, lock-free swap.
        """
        with self._lock:
            # Atomic pointer swap
            self._serving_navigator = self._editorial_navigator
            self._version += 1
            self._last_swap_ts = time.time()
            # Clone new editorial desk for subsequent edits
            self._editorial_navigator = HierarchicalCompassNavigator(
                dict(self._serving_navigator._nodes)
            )
            return self.get_stats()

    def get_stats(self) -> KnowledgeDeskStats:
        """Get current knowledge desk operational statistics."""
        nav = self._serving_navigator
        nodes = nav._nodes.values()
        roots = sum(1 for n in nodes if n.parent_id is None)
        max_d = max((n.depth for n in nodes), default=0)

        return KnowledgeDeskStats(
            active_version=self._version,
            total_nodes=nav.total_nodes,
            total_roots=roots,
            max_depth=max_d,
            last_swap_ts=self._last_swap_ts,
            serving_desk_ready=True,
        )
