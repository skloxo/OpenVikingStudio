# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Configuration for the external/scheduled Compile task API."""

from typing import Literal

from pydantic import BaseModel, model_validator


class CompileApiConfig(BaseModel):
    """Configuration for the external Compile task API."""

    base_url: str = ""
    gateway_token: str = ""
    http_timeout_seconds: float = 10.0
    poll_interval_ms: int = 30000
    scheduler_enabled: bool = False
    scheduler_backend: Literal["redis"] = "redis"

    @model_validator(mode="after")
    def _validate(self) -> "CompileApiConfig":
        if self.base_url and "://" not in self.base_url:
            raise ValueError("compile_api.base_url must include scheme (e.g., https://...)")
        if self.http_timeout_seconds <= 0:
            raise ValueError("compile_api.http_timeout_seconds must be > 0")
        if self.poll_interval_ms <= 0:
            raise ValueError("compile_api.poll_interval_ms must be > 0")
        self.base_url = self.base_url.rstrip("/")
        return self
