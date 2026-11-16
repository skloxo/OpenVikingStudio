# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Compatibility methods aligning New/LegacyAPIKeyManager with #183 Admin/BotStudio routes."""

from __future__ import annotations

import fnmatch
from typing import Optional

from openviking.server.account_stores.models import AccountSummary, UsersPage, UserSummary


class _APIKeyAdminCompatMixin:
    """Async/paginated management views backed by the existing APIKeyManager store."""

    def require_writable(self) -> None:
        return None

    async def get_account(self, account_id: str) -> Optional[AccountSummary]:
        for item in self.get_accounts():
            if item.get("account_id") == account_id:
                row = dict(item)
                row.setdefault("status", "active")
                return row  # type: ignore[return-value]
        return None

    async def list_accounts(
        self,
        *,
        name_filter: Optional[str] = None,
        limit: Optional[int] = None,
        page: int = 1,
        query_filter: Optional[str] = None,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        **filters,
    ) -> list[AccountSummary]:
        del filters
        rows = [dict(r) for r in self.get_accounts()]
        for row in rows:
            row.setdefault("status", "active")
        if status is not None:
            rows = [r for r in rows if r.get("status", "active") == status]
        if name_filter:
            rows = [r for r in rows if fnmatch.fnmatch(str(r.get("account_id", "")), name_filter)]
        if query_filter:
            needle = query_filter.lower()
            rows = [r for r in rows if needle in str(r.get("account_id", "")).lower()]
        if cursor:
            rows = sorted(rows, key=lambda x: str(x.get("account_id", "")))
            rows = [r for r in rows if str(r.get("account_id", "")) > cursor]
        if limit is not None and limit > 0:
            start = max(0, (max(1, page) - 1) * limit)
            rows = rows[start : start + limit]
        return rows  # type: ignore[return-value]

    async def list_users_page(
        self,
        account_id: str,
        *,
        limit: Optional[int] = 100,
        cursor: Optional[str] = None,
        name_filter: Optional[str] = None,
        role_filter: Optional[str] = None,
        expose_key: bool = True,
        mask_keys: bool = False,
        hide_other_keys: bool = False,
        viewer_account_id: Optional[str] = None,
        viewer_user_id: Optional[str] = None,
        page: int = 1,
        query_filter: Optional[str] = None,
        fresh: bool = False,
    ) -> UsersPage:
        del fresh
        all_rows = self.get_users(
            account_id,
            limit=100_000,
            name_filter=None,
            role_filter=None,
            expose_key=expose_key,
        )
        account_total = len(all_rows)
        manager_count = sum(1 for r in all_rows if r.get("role") in {"admin", "root"})
        key_count = sum(1 for r in all_rows if r.get("api_key") or r.get("key_prefix"))

        filtered = self.get_users(
            account_id,
            limit=100_000,
            name_filter=name_filter,
            role_filter=role_filter,
            expose_key=expose_key,
        )
        if query_filter:
            needle = query_filter.lower()
            filtered = [r for r in filtered if needle in str(r.get("user_id", "")).lower()]
        total = len(filtered)
        if cursor:
            filtered = sorted(filtered, key=lambda r: str(r.get("user_id", "")))
            filtered = [r for r in filtered if str(r.get("user_id", "")) > cursor]
        if limit is not None and limit > 0:
            start = max(0, (max(1, page) - 1) * limit)
            filtered = filtered[start : start + limit]

        users: list[UserSummary] = []
        for raw in filtered:
            u = dict(raw)
            is_self = viewer_account_id == account_id and viewer_user_id == u.get("user_id")
            if hide_other_keys and not is_self:
                u.pop("api_key", None)
                u.pop("key_prefix", None)
            elif mask_keys and not is_self:
                raw_key = u.pop("api_key", None)
                if raw_key and not u.get("key_prefix"):
                    u["key_prefix"] = str(raw_key)[:12] + "..."
            users.append(u)  # type: ignore[arg-type]

        return {
            "users": users,
            "total": total,
            "account_total": account_total,
            "manager_count": manager_count,
            "key_count": key_count,
        }

    async def get_user_membership(self, account_id: str, user_id: str) -> Optional[UserSummary]:
        if not self.has_user(account_id, user_id):
            return None
        role = self.get_user_role(account_id, user_id)
        return {"user_id": user_id, "role": str(getattr(role, "value", role))}

    async def get_user_for_management(self, account_id: str, user_id: str) -> Optional[UserSummary]:
        return await self.get_user_membership(account_id, user_id)

    async def add_group_members(
        self, account_id: str, group_id: str, user_ids: list[str]
    ) -> list[str]:
        added: list[str] = []
        for uid in user_ids:
            if await self.add_group_member(account_id, group_id, uid):
                added.append(uid)
        return added

    async def remove_group_members(
        self, account_id: str, group_id: str, user_ids: list[str]
    ) -> list[str]:
        removed: list[str] = []
        for uid in user_ids:
            if await self.remove_group_member(account_id, group_id, uid):
                removed.append(uid)
        return removed
