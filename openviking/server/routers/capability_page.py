"""
REST API router for Tencent Capability Pages and Negative Boundary Router.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from openviking.core.capability_page import (
    CapabilityPage,
    DiscriminativeBody,
    capability_store,
)
from openviking.core.negative_boundary_router import (
    NeighborContrastEngine,
    NeighborContrastResult,
    RouteDecision,
    boundary_router,
)

router = APIRouter(prefix="/capability-pages", tags=["CapabilityPages"])


class CreateCapabilityPageRequest(BaseModel):
    skill_id: str
    skill_name: str
    cluster_id: str = "ops"
    positive_triggers: List[str] = Field(default_factory=list)
    negative_boundaries: List[str] = Field(default_factory=list)
    summary: str
    prerequisites: List[str] = Field(default_factory=list)
    inputs: Dict[str, str] = Field(default_factory=dict)
    outputs: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContrastNeighborsRequest(BaseModel):
    target_skill_id: str


class RouteRequest(BaseModel):
    query: str
    cluster_id: Optional[str] = None
    top_k: int = 5
    penalty_factor: float = 0.8


def _seed_initial_pages_if_empty() -> None:
    """Pre-seeds canonical skills if store is empty."""
    if capability_store.count() > 0:
        return

    # Skill 1: docker_inspect_logs
    capability_store.upsert_page(CapabilityPage(
        skill_id="docker_inspect_logs",
        skill_name="Docker 容器日志查看",
        cluster_id="container_ops",
        positive_triggers=[
            "查看 Docker 容器运行日志",
            "检查容器 stdout 输出与报错",
            "获取容器日志尾部 100 行",
        ],
        negative_boundaries=[
            "DO NOT use for '重启容器' -> Redirect to Docker 容器重启运维",
            "DO NOT use for '清理 Docker 磁盘或删除容器镜像' -> Redirect to Docker 存储清理",
        ],
        discriminative_body=DiscriminativeBody(
            summary="只读检查指定 Docker 容器的标准输出与错误日志流，无副作用。",
            prerequisites=["docker cli installed", "container running or stopped"],
            inputs={"container_id": "string", "tail_lines": "integer"},
            outputs={"logs": "string", "exit_code": "integer"},
        ),
    ))

    # Skill 2: docker_restart_service
    capability_store.upsert_page(CapabilityPage(
        skill_id="docker_restart_service",
        skill_name="Docker 容器重启运维",
        cluster_id="container_ops",
        positive_triggers=[
            "重启容器",
            "重新启动挂掉的 Docker 实例",
            "重启应用服务容器",
        ],
        negative_boundaries=[
            "DO NOT use for '查看 Docker 容器运行日志' -> Redirect to Docker 容器日志查看",
            "DO NOT use for '完全销毁删除容器' -> Redirect to Docker 存储清理",
        ],
        discriminative_body=DiscriminativeBody(
            summary="向 Docker 守护进程发送重启信号，优雅停机并重新拉起容器实例。",
            prerequisites=["docker privileges", "container exists"],
            inputs={"container_id": "string", "timeout_sec": "integer"},
            outputs={"success": "boolean", "restart_time": "float"},
        ),
    ))

    # Skill 3: python_performance_profiler
    capability_store.upsert_page(CapabilityPage(
        skill_id="python_performance_profiler",
        skill_name="Python 性能分析与火焰图",
        cluster_id="code_quality",
        positive_triggers=[
            "分析 Python 代码性能瓶颈",
            "生成 CPU/内存火焰图",
            "排查 Python 函数耗时与热点",
        ],
        negative_boundaries=[
            "DO NOT use for 'Python 代码格式化与 Ruff 检查' -> Redirect to Python 语法规范检查",
            "DO NOT use for '执行 pytest 单元测试' -> Redirect to Python 单元测试执行",
        ],
        discriminative_body=DiscriminativeBody(
            summary="利用 cProfile / py-spy 对 Python 脚本或运行中服务进行无侵入性能采样。",
            prerequisites=["python3", "cProfile / py-spy"],
            inputs={"target_script": "string", "duration_sec": "integer"},
            outputs={"flamegraph_path": "string", "top_bottlenecks": "list"},
        ),
    ))

    # Skill 4: python_linter_fixer
    capability_store.upsert_page(CapabilityPage(
        skill_id="python_linter_fixer",
        skill_name="Python 语法规范检查",
        cluster_id="code_quality",
        positive_triggers=[
            "Python 代码格式化与 Ruff 检查",
            "执行 flake8 / black 静态代码扫描",
            "自动修复代码缩进与未引用导入",
        ],
        negative_boundaries=[
            "DO NOT use for '分析 Python 代码性能瓶颈' -> Redirect to Python 性能分析与火焰图",
        ],
        discriminative_body=DiscriminativeBody(
            summary="静态检查代码风格与语法错误，并执行安全的自动格式化与修复。",
            prerequisites=["ruff / black installed"],
            inputs={"path": "string", "auto_fix": "boolean"},
            outputs={"issues_found": "integer", "fixed_count": "integer"},
        ),
    ))


_seed_initial_pages_if_empty()


@router.get("", response_model=List[CapabilityPage])
def list_capability_pages(cluster_id: Optional[str] = None) -> List[CapabilityPage]:
    """List all capability pages with optional cluster filter."""
    return capability_store.list_pages(cluster_id=cluster_id)


@router.get("/{skill_id}", response_model=CapabilityPage)
def get_capability_page(skill_id: str) -> CapabilityPage:
    """Get single capability page by skill_id."""
    page = capability_store.get_page(skill_id)
    if not page:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    return page


@router.post("", response_model=CapabilityPage)
def create_or_update_capability_page(req: CreateCapabilityPageRequest) -> CapabilityPage:
    """Create or update a three-segment capability page."""
    page = CapabilityPage(
        skill_id=req.skill_id,
        skill_name=req.skill_name,
        cluster_id=req.cluster_id,
        positive_triggers=req.positive_triggers,
        negative_boundaries=req.negative_boundaries,
        discriminative_body=DiscriminativeBody(
            summary=req.summary,
            prerequisites=req.prerequisites,
            inputs=req.inputs,
            outputs=req.outputs,
        ),
        metadata=req.metadata,
    )
    return capability_store.upsert_page(page)


@router.delete("/{skill_id}")
def delete_capability_page(skill_id: str) -> Dict[str, Any]:
    """Delete a capability page."""
    success = capability_store.delete_page(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    return {"success": True, "deleted_skill_id": skill_id}


@router.post("/contrast-neighbors", response_model=NeighborContrastResult)
def contrast_neighbors(req: ContrastNeighborsRequest) -> NeighborContrastResult:
    """Analyze cluster siblings to derive T- negative boundaries."""
    return NeighborContrastEngine.contrast_neighbors(req.target_skill_id, capability_store)


@router.post("/route", response_model=RouteDecision)
def route_query(req: RouteRequest) -> RouteDecision:
    """Execute two-stage negative boundary routing."""
    return boundary_router.route(
        query=req.query,
        cluster_id=req.cluster_id,
        top_k=req.top_k,
        penalty_factor=req.penalty_factor,
    )


@router.get("/metrics/summary")
def get_router_metrics() -> Dict[str, Any]:
    """Get boundary router operational metrics."""
    return boundary_router.get_metrics()
