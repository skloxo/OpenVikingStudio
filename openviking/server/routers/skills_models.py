# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Request and response models for skills router."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, model_validator
from openviking.telemetry import TelemetryRequest


class UpdateSkillRequest(BaseModel):
    """Replace an existing agent skill with new skill content."""

    model_config = ConfigDict(extra="forbid")

    data: Any = None
    temp_file_id: Optional[str] = None
    wait: bool = False
    timeout: Optional[float] = None
    source_metadata: Optional[Dict[str, Any]] = None
    telemetry: TelemetryRequest = False
    target_uri: Optional[str] = None

    @model_validator(mode="after")
    def check_data_or_temp_file_id(self):
        if self.data is None and not self.temp_file_id:
            raise ValueError("Either 'data' or 'temp_file_id' must be provided")
        return self


class FindSkillsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    limit: int = 10
    score_threshold: Optional[float] = None
    level: Optional[list[int]] = None
    telemetry: TelemetryRequest = False
    target_uri: Optional[str] = None


class ValidateSkillRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: Any
    strict: bool = False
    source_path: Optional[str] = None
    skill_dir_name: Optional[str] = None
    target_uri: Optional[str] = None
