# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Multi-Role View Projector (Card-47).

Derives role-specific projections from unified code and skill facts:
1. Developer: API signatures, DTOs, AST seams, and contracts.
2. Tester: Input/output constraints, status codes, and test targets.
3. Operator: Network ports, HTTP method distributions, and health endpoints.
"""

from __future__ import annotations

from typing import Any, Dict, List

from openviking.service.code_fact_compiler import McpToolFactRecord, RouteFactRecord
from openviking.service.skill_fact_compiler import SkillFactRecord


class RoleProjector:
    """Projector for deriving tailored views without duplicating underlying facts."""

    @classmethod
    def project_dev(
        cls,
        skills: List[SkillFactRecord],
        routes: List[RouteFactRecord],
        tools: List[McpToolFactRecord],
    ) -> Dict[str, Any]:
        """Derive developer-centric projection focused on signatures and seams."""
        mcp_contracts = [
            {
                "name": t.name,
                "handler_name": t.handler_name,
                "parameters_signature": t.parameters_signature,
                "return_type": t.return_type,
                "is_async": t.is_async,
                "source_file": t.source_file,
            }
            for t in tools
        ]
        skill_interfaces = [
            {
                "name": s.name,
                "allowed_tools": s.allowed_tools,
                "l0_summary": s.l0_summary,
            }
            for s in skills
        ]
        return {
            "role": "dev",
            "mcp_contracts": mcp_contracts,
            "skill_interfaces": skill_interfaces,
            "total_mcp_contracts": len(mcp_contracts),
            "total_skills": len(skill_interfaces),
        }

    @classmethod
    def project_test(
        cls,
        routes: List[RouteFactRecord],
        tools: List[McpToolFactRecord],
    ) -> Dict[str, Any]:
        """Derive QA/tester-centric projection focused on verification targets."""
        routes_to_test = [
            {
                "method": r.method,
                "path": r.path,
                "handler_name": r.handler_name,
                "summary": r.summary,
            }
            for r in routes
        ]
        tools_to_test = [
            {
                "name": t.name,
                "parameters_signature": t.parameters_signature,
                "return_type": t.return_type,
            }
            for t in tools
        ]
        return {
            "role": "test",
            "routes_to_test": routes_to_test,
            "tools_to_test": tools_to_test,
            "total_testable_endpoints": len(routes_to_test),
            "total_testable_tools": len(tools_to_test),
        }

    @classmethod
    def project_ops(cls, routes: List[RouteFactRecord]) -> Dict[str, Any]:
        """Derive operator/fleet-centric projection focused on infrastructure and routes."""
        methods_dist: Dict[str, int] = {}
        for r in routes:
            methods_dist[r.method] = methods_dist.get(r.method, 0) + 1

        return {
            "role": "ops",
            "primary_service_port": 1933,
            "satellite_ports": [13100, 11432, 11433],
            "total_endpoints": len(routes),
            "methods_distribution": methods_dist,
        }
