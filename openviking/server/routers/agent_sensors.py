# -*- coding: utf-8 -*-
"""REST API router for Agent 3D Performance Sensors.

Card-Metrics-AgentSensors (v1.5.44)
Exposes endpoints for querying Token SNR, P@5 Precision, and Human Intervention Rate.
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel, Field

from openviking.core.agent_sensors import (
    AgentSensorsAggregator,
)

router = APIRouter(prefix="/api/v1/metrics/agent-sensors", tags=["agent-sensors"])


class RecordSampleRequest(BaseModel):
    session_id: str = Field(..., description="Unique ID of the agent session")
    effective_tokens: int = Field(..., ge=0, description="Tokens used in valid code/instructions")
    total_tokens: int = Field(..., gt=0, description="Total tokens in context window")
    top5_hits: int = Field(..., ge=0, le=5, description="Count of top-5 retrieved items adopted (0-5)")
    interventions_count: int = Field(0, ge=0, description="Number of human interrupts or corrections")


@router.get("")
def get_agent_sensors_summary() -> Dict[str, Any]:
    """Retrieve aggregated Token SNR, P@5, and Intervention Rate metrics."""
    aggregator = AgentSensorsAggregator.get_instance()
    metrics = aggregator.get_aggregated_metrics()
    return {"status": "success", "data": metrics}


@router.post("/sample")
def record_agent_sensor_sample(req: RecordSampleRequest) -> Dict[str, Any]:
    """Ingest a new session telemetry point and recalculate windowed sensors."""
    aggregator = AgentSensorsAggregator.get_instance()
    point = aggregator.record_telemetry(
        session_id=req.session_id,
        effective_tokens=req.effective_tokens,
        total_tokens=req.total_tokens,
        top5_hits=req.top5_hits,
        interventions_count=req.interventions_count,
    )
    return {
        "status": "success",
        "point": {
            "session_id": point.session_id,
            "token_snr": point.token_snr,
            "p5_precision": point.p5_precision,
            "human_intervention_flag": point.human_intervention_flag,
            "effective_tokens": point.effective_tokens,
            "total_tokens": point.total_tokens,
            "top5_hits": point.top5_hits,
            "interventions_count": point.interventions_count,
            "timestamp": point.timestamp,
        },
    }
