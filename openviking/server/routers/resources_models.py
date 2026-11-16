# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Request schemas for resources router."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from openviking.resource.processing_mode import DEFAULT_PROCESSING_MODE, ProcessingMode
from openviking.telemetry import TelemetryRequest


class AddResourceRequest(BaseModel):
    """Request model for add_resource."""

    model_config = ConfigDict(extra="forbid")

    path: Optional[str] = None
    temp_file_id: Optional[str] = None
    add_type: Optional[str] = None
    to: Optional[str] = None
    parent: Optional[str] = None
    create_parent: bool = False
    reason: str = ""
    instruction: str = ""
    wait: bool = False
    timeout: Optional[float] = None
    strict: bool = False
    source_name: Optional[str] = None
    ignore_dirs: Optional[str] = None
    include: Optional[str] = None
    exclude: Optional[str] = None
    directly_upload_media: bool = True
    preserve_structure: Optional[bool] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    telemetry: TelemetryRequest = False
    watch_interval: float = 0
    processing_mode: ProcessingMode = DEFAULT_PROCESSING_MODE
    tags: Optional[list[str]] = None
    tag_mode: str = "replace"

    @model_validator(mode="after")
    def check_path_or_temp_file_id(self):
        if not self.path and not self.temp_file_id:
            raise ValueError("Either 'path' or 'temp_file_id' must be provided")
        return self

    @model_validator(mode="after")
    def check_add_type(self):
        if self.add_type is not None:
            self.add_type = self.add_type.strip() or None
        if self.add_type and self.temp_file_id:
            raise ValueError("'add_type' cannot be combined with 'temp_file_id'")
        if self.add_type and not self.path:
            raise ValueError("'add_type' requires 'path'")
        if self.add_type and self.parent:
            raise ValueError("'add_type' cannot be combined with 'parent'")
        if self.add_type and not self.to:
            raise ValueError("'add_type' requires an exact 'to' target")
        return self


class AddSkillRequest(BaseModel):
    """Request model for add_skill."""

    model_config = ConfigDict(extra="forbid")

    data: Any = None
    temp_file_id: Optional[str] = None
    wait: bool = False
    timeout: Optional[float] = None
    source_metadata: Optional[Dict[str, Any]] = None
    target_uri: Optional[str] = None
    telemetry: TelemetryRequest = False

    @model_validator(mode="after")
    def check_data_or_temp_file_id(self):
        if self.data is None and not self.temp_file_id:
            raise ValueError("Either 'data' or 'temp_file_id' must be provided")
        return self
