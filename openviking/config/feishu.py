# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Account/cluster Feishu config resolution with legacy cluster fallback."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from openviking_cli.utils.config import get_openviking_config
from openviking_cli.utils.config.parser_config import FeishuConfig

_ACCOUNT_FEISHU_FIELDS = (
    "app_id",
    "app_secret",
    "max_rows_per_sheet",
    "max_records_per_table",
    "download_images",
    "request_timeout",
)


def resolve_feishu_config(view: Any) -> FeishuConfig:
    """Resolve one account's Feishu configuration from an account/cluster view."""
    cluster_config = view.cluster.feishu
    account_config = getattr(view.account, "feishu", None)
    if account_config is None:
        return cluster_config

    account_defaults = FeishuConfig(domain=cluster_config.domain)
    updates = {
        field: value
        for field in _ACCOUNT_FEISHU_FIELDS
        if (value := getattr(account_config, field, None)) is not None
    }
    return replace(account_defaults, **updates)


async def get_effective_feishu_config(manager: Any, account_id: str) -> FeishuConfig:
    """Resolve Feishu config from manager when present, else cluster config."""
    if manager is not None and hasattr(manager, "resolve_account"):
        return await manager.resolve_account(account_id, resolve_feishu_config)
    return get_openviking_config().feishu
