# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Union
from uuid import uuid4


@dataclass
class EmbeddingMsg:
    message: Union[str, List[Dict[str, Any]]]
    context_data: Dict[str, Any]
    id: str = field(default_factory=lambda: str(uuid4()))
    telemetry_id: str = ""

    def __init__(
        self,
        message: Union[str, List[Dict[str, Any]]],
        context_data: Dict[str, Any],
        telemetry_id: str = "",
    ):
        self.id = str(uuid4())
        self.message = message
        self.context_data = context_data
        self.telemetry_id = telemetry_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert embedding message to dictionary format."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert embedding message to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EmbeddingMsg":
        """Create an embedding message object from dictionary."""
        obj = EmbeddingMsg(
            message=data["message"],
            context_data=data["context_data"],
            telemetry_id=data.get("telemetry_id", ""),
        )
        obj.id = data.get("id", obj.id)
        return obj

    @classmethod
    def for_delete(
        cls,
        record_ids: List[str],
        context_data: Dict[str, Any],
        telemetry_id: str = "",
    ) -> "EmbeddingMsg":
        ctx_data = dict(context_data)
        ctx_data["action"] = "delete"
        ctx_data["record_ids"] = list(record_ids)
        return cls(
            message="",
            context_data=ctx_data,
            telemetry_id=telemetry_id,
        )

    @classmethod
    def for_update_fields(
        cls,
        record_id: str,
        field_patch: Any,
        context_data: Dict[str, Any],
        telemetry_id: str = "",
    ) -> "EmbeddingMsg":
        ctx_data = dict(context_data)
        ctx_data["action"] = "update_fields"
        ctx_data["record_id"] = record_id
        if hasattr(field_patch, "to_dict"):
            ctx_data["field_patch"] = field_patch.to_dict()
        elif hasattr(field_patch, "values"):
            ctx_data["field_patch"] = dict(field_patch.values)
        else:
            ctx_data["field_patch"] = field_patch
        return cls(
            message="",
            context_data=ctx_data,
            telemetry_id=telemetry_id,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "EmbeddingMsg":
        """Safely create object from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string: {e}")

