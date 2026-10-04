# -*- coding: utf-8 -*-
"""Agent 3D Performance Sensors Telemetry Engine.

Card-Metrics-AgentSensors (v1.5.44)
Computes and aggregates the three physical gauges:
1. Token SNR (Effective Payload Ratio: valid instructions & code / total context)
2. P@5 Precision (Top-5 retrieval hit & adoption rate in generation)
3. Human Intervention Rate (Ratio of sessions requiring human steering/interrupts)
"""

from __future__ import annotations

import json
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentSensorTelemetry:
    """Telemetry data point for a single session or batch execution."""
    session_id: str
    token_snr: float              # 0.0 ~ 1.0 (Target >= 0.65)
    p5_precision: float           # 0.0 ~ 1.0 (Target >= 0.80)
    human_intervention_flag: bool # True if human steering occurred
    effective_tokens: int = 0
    total_tokens: int = 0
    top5_hits: int = 0
    interventions_count: int = 0
    timestamp: float = field(default_factory=time.time)


class AgentSensorsAggregator:
    """Aggregates telemetry, computes windowed averages, and appends to JSONL."""

    _instance: Optional[AgentSensorsAggregator] = None
    _lock = threading.Lock()

    def __init__(self, log_dir: Optional[str] = None) -> None:
        base_dir = log_dir or os.path.expanduser("~/.openviking/data")
        self.metrics_file = os.path.join(base_dir, "agent_metrics.jsonl")
        self._history: List[AgentSensorTelemetry] = []
        self._max_history = 200
        self._ensure_storage()

    @classmethod
    def get_instance(cls) -> AgentSensorsAggregator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_storage(self) -> None:
        """Safely ensure storage directory exists and preload existing telemetry."""
        try:
            os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    for line in lines[-self._max_history:]:
                        if line.strip():
                            data = json.loads(line)
                            self._history.append(AgentSensorTelemetry(**data))
        except Exception:
            # Fallback to pure in-memory operation if filesystem restricted
            pass

    def record_telemetry(
        self,
        session_id: str,
        effective_tokens: int,
        total_tokens: int,
        top5_hits: int,
        interventions_count: int,
    ) -> AgentSensorTelemetry:
        """Calculate and persist a single telemetry event."""
        snr = min(1.0, max(0.0, effective_tokens / total_tokens)) if total_tokens > 0 else 0.0
        p5 = min(1.0, max(0.0, top5_hits / 5.0))
        intervention_flag = interventions_count > 0

        point = AgentSensorTelemetry(
            session_id=session_id,
            token_snr=round(snr, 4),
            p5_precision=round(p5, 4),
            human_intervention_flag=intervention_flag,
            effective_tokens=effective_tokens,
            total_tokens=total_tokens,
            top5_hits=top5_hits,
            interventions_count=interventions_count,
            timestamp=time.time(),
        )

        with self._lock:
            self._history.append(point)
            if len(self._history) > self._max_history:
                self._history.pop(0)

        # Append to JSONL file
        try:
            with open(self.metrics_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(point), ensure_ascii=False) + "\n")
        except Exception:
            pass

        return point

    def get_aggregated_metrics(self) -> Dict[str, Any]:
        """Compute windowed averages and baseline deviation."""
        with self._lock:
            points = list(self._history)

        if not points:
            # Cold baseline state
            return {
                "sample_count": 0,
                "avg_token_snr": 0.0,
                "avg_p5_precision": 0.0,
                "human_intervention_rate": 0.0,
                "snr_status": "insufficient_data",
                "p5_status": "insufficient_data",
                "intervention_status": "insufficient_data",
                "recent_timeline": [],
            }

        total_snr = sum(p.token_snr for p in points)
        total_p5 = sum(p.p5_precision for p in points)
        total_interventions = sum(1 for p in points if p.human_intervention_flag)
        count = len(points)

        avg_snr = round(total_snr / count, 4)
        avg_p5 = round(total_p5 / count, 4)
        intervention_rate = round(total_interventions / count, 4)

        return {
            "sample_count": count,
            "avg_token_snr": avg_snr,
            "avg_p5_precision": avg_p5,
            "human_intervention_rate": intervention_rate,
            "snr_status": "optimal" if avg_snr >= 0.65 else "degraded",
            "p5_status": "optimal" if avg_p5 >= 0.80 else "suboptimal",
            "intervention_status": "optimal" if intervention_rate <= 0.15 else "elevated",
            "recent_timeline": [
                {
                    "session_id": p.session_id,
                    "token_snr": p.token_snr,
                    "p5_precision": p.p5_precision,
                    "interventions": p.interventions_count,
                    "timestamp": p.timestamp,
                }
                for p in points[-20:]
            ],
        }


_INTERVENTION_KEYWORDS_RE = re.compile(
    r"(不对|错误|报错|重写|重做|重试|改成|修改|不是这样|有问题|停一下|弄错|fix|retry|error|wrong|incorrect|undo|redo|bug)",
    re.IGNORECASE,
)
_CODE_BLOCK_RE = re.compile(r"```[a-zA-Z0-9_-]*\n([\s\S]*?)```")


def extract_session_telemetry_metrics(
    messages: List[Any],
    usage_uris: Optional[List[str]] = None,
    session_id: str = "",
) -> Dict[str, Any]:
    """Calculate 3D performance sensor metrics from a session message sequence.

    1. Token SNR: Effective payload (code blocks + valid instructions + tool outputs) / total tokens
    2. P@5 Precision: Hits on context (usage_uris & ContextParts) capped at 5
    3. Human Intervention: User corrective steering steps detected
    """
    from openviking.utils.token_estimation import estimate_text_tokens

    total_tokens = 0
    effective_tokens = 0
    context_hits = len(usage_uris or [])
    interventions_count = 0

    user_turn_index = 0
    for msg in messages:
        role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else "")
        parts = getattr(msg, "parts", None) or (msg.get("parts") if isinstance(msg, dict) else [])
        content = getattr(msg, "content", "") or ""

        msg_tokens = getattr(msg, "estimated_tokens", 0)
        if not msg_tokens:
            if parts:
                msg_tokens = sum(
                    estimate_text_tokens(getattr(p, "text", "") or getattr(p, "abstract", "") or str(getattr(p, "tool_output", "")))
                    for p in parts
                )
            else:
                msg_tokens = estimate_text_tokens(content)

        total_tokens += max(1, msg_tokens) if content or parts else 0

        if parts:
            for p in parts:
                p_cls = p.__class__.__name__ if p is not None else ""
                if p_cls == "ContextPart" or (isinstance(p, dict) and p.get("type") == "context"):
                    context_hits += 1
                elif p_cls == "ToolPart" or (isinstance(p, dict) and p.get("type") == "tool"):
                    tool_out = getattr(p, "tool_output", "") or (p.get("output") if isinstance(p, dict) else "")
                    effective_tokens += estimate_text_tokens(str(tool_out))

        if role == "user":
            user_text = content
            if not user_text and parts:
                user_text = "".join(str(getattr(p, "text", "")) for p in parts)
            if user_turn_index > 0 and user_text:
                if _INTERVENTION_KEYWORDS_RE.search(user_text):
                    interventions_count += 1
            user_turn_index += 1
            effective_tokens += estimate_text_tokens(user_text)
        elif role == "assistant":
            asst_text = content
            if not asst_text and parts:
                asst_text = "".join(str(getattr(p, "text", "")) for p in parts)
            code_blocks = _CODE_BLOCK_RE.findall(asst_text)
            for code in code_blocks:
                effective_tokens += estimate_text_tokens(code)
            if not code_blocks and asst_text:
                effective_tokens += int(estimate_text_tokens(asst_text) * 0.7)

    if total_tokens > 0:
        effective_tokens = min(total_tokens, effective_tokens)
    else:
        effective_tokens = 0

    top5_hits = min(5, max(0, context_hits))

    return {
        "session_id": session_id or f"sess_{int(time.time()*1000)}",
        "effective_tokens": effective_tokens,
        "total_tokens": total_tokens,
        "top5_hits": top5_hits,
        "interventions_count": interventions_count,
    }

