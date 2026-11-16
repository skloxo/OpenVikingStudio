# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Compile API models and external task provider."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Mapping

import httpx
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, ValidationError, model_validator

from openviking.core.namespace import classify_uri, uri_parts
from openviking.core.path_variables import resolve_path_variables
from openviking.core.uri_validation import validate_request_viking_uri
from openviking.server.identity import RequestContext
from openviking.service.compile_targets import CompileLifecycle, UpdateSchedule, split_control_args
from openviking.service.external_task_service import (
    ExternalTaskCancellation,
    ExternalTaskError,
    ExternalTaskRetryExhaustedError,
    ExternalTaskService,
    ExternalTaskSnapshot,
)
from openviking.service.fs_service import FSService
from openviking.service.memory_compile import MemoryCompileRunner
from openviking.service.task_tracker import SENSITIVE_TASK_KEYS, TaskRecord
from openviking.session.memory.utils.memory_fields import strip_memory_fields_trailer
from openviking.storage.acl import AclAction
from openviking_cli.exceptions import (
    ConflictError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
    UnavailableError,
)
from openviking_cli.utils.config.open_viking_config import CompileApiConfig
from openviking_cli.utils.logger import get_logger

logger = get_logger(__name__)

_ACTIVE_STATUSES = frozenset({"accepted", "pending", "running", "committing"})
_TERMINAL_STATUSES = frozenset({"completed", "failed", "cancelled"})

# Sentinel --skill value that routes a Compile request to in-process memory
# consolidation instead of the VikingBot agent path. It is not a real Skill URI.
MEMORY_COMPILE_SKILL = "memory"
from openviking.service.compile_api_client import (
    CompileAPIClient, CompileConfigUpdate, CompileErrorInfo, CompileRequest,
    CompileSessionAccepted, CompileSessionStatus, _CompileEndpoint,
)


class _CompileServiceOpsMixin:

    def _require_lifecycle(self) -> CompileLifecycle:
        if self._lifecycle is None:
            raise UnavailableError("compile settings", "Compile target registry is not configured")
        return self._lifecycle

    async def _target(
        self,
        to: str,
        ctx: RequestContext,
        *,
        include_deleted: bool = False,
        action: AclAction = AclAction.READ,
    ) -> dict[str, Any]:
        """Resolve an account's registered target after checking the requested ACL action."""
        lifecycle = self._require_lifecycle()
        target = validate_request_viking_uri(resolve_path_variables(to), ctx, field_name="to")
        await lifecycle._fs._ensure_access(target.rstrip("/"), ctx, action=action)
        record = await lifecycle.store.get_by_to(
            ctx.account_id, target.rstrip("/"), include_deleted=include_deleted
        )
        if record is None:
            raise NotFoundError(to, "compile target")
        return record

    @staticmethod
    def _config_view(record: Mapping[str, Any]) -> dict[str, Any]:
        from openviking.service.compile_scheduler import next_run_at

        return {
            "status": record["status"],
            "to": record["to"],
            "initialized": record["initialized"],
            "initial_actor": record.get("initial_actor"),
            "from": record["from"],
            "skill": record["skill"],
            "instruction": record["instruction"],
            "auto_update": record["auto_update"],
            "update_schedule": record["update_schedule"],
            "next_run_at": next_run_at(dict(record)),
            "last_run": record["last_run"],
            "last_error": record["last_error"],
            "content_updated_at": record.get("content_updated_at"),
            "first_compile_created_at": record.get("first_compile_created_at"),
            "compile_type": record.get("compile_type", "compile"),
            "conflicts_num": record.get("conflicts_num", 0),
        }

    async def get_config(self, to: str, ctx: RequestContext) -> dict[str, Any]:
        return self._config_view(await self._target(to, ctx))

    async def update_config(self, body: "CompileConfigUpdate", ctx: RequestContext) -> dict:
        lifecycle = self._require_lifecycle()
        record = await self._target(body.to, ctx, action=AclAction.WRITE)
        identity = (record["to"], record["deleted_at"])
        request = await self._normalize_request(
            self._normalize_request_uris(
                CompileRequest.model_validate(
                    {"from": body.from_, "to": record["to"], "skill": body.skill}
                ),
                ctx,
            ),
            ctx,
        )
        lifecycle.validate_layout(record["to"], request.from_)
        async with lifecycle.store.edit(ctx.account_id, record["to"]) as record:
            if record["status"] != "active" or (record["to"], record["deleted_at"]) != identity:
                raise ConflictError(
                    "Compile target changed during configuration", resource="COMPILE_TARGET"
                )
            lifecycle.apply_sources(record, request.from_, request.skill)
            if body.instruction_sent:
                record["instruction"] = (body.instruction or "").strip() or None
            await lifecycle.apply_schedule(
                record,
                ctx,
                body.auto_update,
                body.update_schedule.model_dump() if body.update_schedule is not None else None,
            )
            if lifecycle.reschedule is not None:
                await lifecycle.reschedule(ctx.account_id, record, raise_on_error=True)
        return self._config_view(record)

    async def list_configs(
        self, ctx: RequestContext, *, limit: int, cursor: str | None
    ) -> dict[str, Any]:
        """Read active target states lazily in SHA256(to) order, with one readable lookahead."""
        from openviking.service.compile_scheduler import next_run_at

        lifecycle = self._require_lifecycle()
        items = []
        async for item in lifecycle.store.iter_summaries(ctx.account_id, cursor=cursor):
            if item["status"] == "deleted":
                continue
            try:
                await lifecycle._fs._ensure_access(item["to"], ctx)
            except PermissionDeniedError:
                continue
            items.append(
                {
                    "status": item["status"],
                    "to": item["to"],
                    "initialized": item["initialized"],
                    "running": item["running"],
                    "auto_update": item["auto_update"],
                    "update_schedule": item["update_schedule"],
                    "next_run_at": next_run_at(item),
                    "content_updated_at": item.get("content_updated_at"),
                    "first_compile_created_at": item.get("first_compile_created_at"),
                    "compile_type": item.get("compile_type", "compile"),
                    "conflicts_num": item.get("conflicts_num", 0),
                }
            )
            if len(items) > limit:
                break
        page = items[:limit]
        return {
            "targets": page,
            "next_cursor": page[-1]["to"] if len(items) > limit else None,
        }

    async def list_operations(
        self, to: str, ctx: RequestContext, *, limit: int, cursor: str | None
    ) -> dict[str, Any]:
        """Page authorized target operations with public Compile metadata only.

        Common operation fields retain their stored structure. Compile checkpoints
        remain private even when they share the persisted metadata dictionary.
        """
        record = await self._target(to, ctx, include_deleted=True)
        operations = await self._require_lifecycle().store.list_operations(
            ctx.account_id, record["to"], limit=limit + 1, cursor=cursor
        )
        page = operations[:limit]
        public = [self._operation_view(operation) for operation in page]
        next_cursor = page[-1]["operation_id"] if len(operations) > limit else None
        return {"operations": public, "next_cursor": next_cursor}

    @staticmethod
    def _operation_view(operation: Mapping[str, Any]) -> dict[str, Any]:
        """Expose operation fields and public metadata while excluding private checkpoints."""
        return {
            key: operation[key]
            for key in (
                "operation_id",
                "operation_type",
                "actor",
                "created_at",
                "status",
                "started_at",
                "finished_at",
                "params",
                "result",
                "error",
            )
        } | {
            "meta": {
                key: operation["meta"][key]
                for key in (
                    "task_id",
                    "trigger",
                    "execution",
                    "skill_snapshot",
                    "base",
                    "head",
                    "changes",
                )
                if key in operation["meta"]
            },
        }

    async def get_operation(
        self,
        to: str,
        operation_id: str,
        ctx: RequestContext,
    ) -> dict[str, Any]:
        """Read one authorized operation, including deleted targets and public metadata only."""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._-]{0,127}", operation_id):
            raise InvalidArgumentError("Invalid operation_id")
        record = await self._target(to, ctx, include_deleted=True)
        operation = await self._require_lifecycle().store.get_operation(
            ctx.account_id, record["to"], operation_id
        )
        if operation is None:
            raise NotFoundError(operation_id, "operation")
        return self._operation_view(operation)

    async def operation_outputs(
        self,
        to: str,
        operation_id: str,
        ctx: RequestContext,
        *,
        limit: int,
        cursor: str | None,
    ) -> dict[str, Any]:
        """Read one authorized operation's immutable-path version references, ordered by URI."""
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9:._-]{0,127}", operation_id):
            raise InvalidArgumentError("Invalid operation_id")
        record = await self._target(to, ctx)
        store = self._require_lifecycle().store
        if await store.get_operation(ctx.account_id, record["to"], operation_id) is None:
            raise NotFoundError(operation_id, "operation")
        manifest = await store.get_outputs(ctx.account_id, record["to"], operation_id)
        if manifest is None:
            raise NotFoundError(operation_id, "operation outputs not recorded")
        outputs = sorted(manifest["outputs"], key=lambda item: item["uri"])
        if cursor:
            outputs = [item for item in outputs if item["uri"] > cursor]
        page = outputs[:limit]
        return {"outputs": page, "next_cursor": page[-1]["uri"] if len(outputs) > limit else None}

    async def file_versions(
        self, uri: str, ctx: RequestContext, *, limit: int, before: str | None
    ) -> dict[str, Any]:
        return await self._require_lifecycle().versions.versions(
            uri, ctx, limit=limit, before=before
        )

    async def restore_file_version(
        self, uri: str, restore_commit_id: str, current_commit_id: str, ctx: RequestContext
    ) -> dict[str, Any]:
        """Return restored version metadata; stale file commits or active Compile raise ConflictError."""

        async def write(content: bytes, commit_content: Any) -> None:
            # Use normal refresh while recording a restore version.
            try:
                body: str | bytes = content.decode("utf-8")
            except UnicodeDecodeError:
                body = content
            if isinstance(body, str) and classify_uri(uri).is_memory:
                body = strip_memory_fields_trailer(body)
            await self._fs.write(
                uri,
                body,
                ctx,
                edit_source="compile",
                commit_content=commit_content,
            )

        return await self._require_lifecycle().versions.restore(
            uri=uri,
            restore_commit_id=restore_commit_id,
            current_commit_id=current_commit_id,
            ctx=ctx,
            write=write,
        )

    @staticmethod
    def _merge_args(
        payload: Mapping[str, Any] | None,
        private_payload: Mapping[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Recombine saved args without mutation, or return None when absent.

        Private values take precedence. The result can contain credentials and
        is only for Runtime request bodies, never logs or public task metadata.
        """
        public_args = (payload or {}).get("args")
        private_args = (private_payload or {}).get("args")
        if not isinstance(public_args, dict) and not isinstance(private_args, dict):
            return None
        return {
            **(public_args if isinstance(public_args, dict) else {}),
            **(private_args if isinstance(private_args, dict) else {}),
        }

    def _normalize_request_uris(
        self, request: CompileRequest, ctx: RequestContext
    ) -> CompileRequest:
        """Normalize identity-bound names without requiring live resources."""
        sources = list(
            dict.fromkeys(
                validate_request_viking_uri(
                    resolve_path_variables(source), ctx, field_name=f"from[{index}]"
                ).rstrip("/")
                for index, source in enumerate(request.from_)
            )
        )
        for source in sources:
            if classify_uri(source).is_system:
                raise InvalidArgumentError("Compile source must not be in the system namespace")
        skill = request.skill.removesuffix("/SKILL.md")
        skill = validate_request_viking_uri(
            resolve_path_variables(skill), ctx, field_name="skill"
        ).rstrip("/")
        if not classify_uri(skill).is_skill_root:
            raise InvalidArgumentError("skill must resolve to a Skill directory or SKILL.md")
        target = validate_request_viking_uri(
            resolve_path_variables(request.to), ctx, field_name="to"
        ).rstrip("/")
        self._validate_target(target)
        return request.model_copy(update={"from_": sources, "to": target, "skill": skill})

    async def _normalize_request(
        self, request: CompileRequest, ctx: RequestContext
    ) -> CompileRequest:
        request = self._normalize_request_uris(request, ctx)
        for uri in request.from_:
            stat = await self._fs.stat(uri, ctx, skip_count=True)
            if not stat.get("isDir"):
                raise InvalidArgumentError(f"Compile source must be a directory: {uri}")
        skill_stat = await self._fs.stat(request.skill, ctx, skip_count=True)
        if not skill_stat.get("isDir"):
            raise InvalidArgumentError("skill must resolve to a Skill directory or SKILL.md")
        skill_file = await self._fs.stat(f"{request.skill}/SKILL.md", ctx, skip_count=True)
        if skill_file.get("isDir"):
            raise InvalidArgumentError("Skill directory must contain a SKILL.md file")
        await self._fs.ensure_write_access(request.to, ctx)
        try:
            target_stat = await self._fs.stat(request.to, ctx, skip_count=True)
        except NotFoundError:
            pass
        else:
            if not target_stat.get("isDir"):
                raise InvalidArgumentError("Compile target must be a directory")
        return request

    @staticmethod
    def _validate_target(target: str) -> None:
        classification = classify_uri(target)
        parts = uri_parts(target)
        if classification.is_system:
            raise InvalidArgumentError("Compile target must not be in the system namespace")
        if classification.context_type == "skill":
            if (
                not classification.is_skill_namespace
                or classification.scope not in {"user", "agent"}
                or (classification.scope == "agent" and parts != ["agent", "skills"])
            ):
                raise InvalidArgumentError(
                    "Compile Skill target must be a supported skills namespace"
                )
            return
        if classification.context_type not in {"resource", "memory"}:
            raise InvalidArgumentError(
                "Compile target must be a resource, memory, or skills directory"
            )
        if classification.context_type == "memory":
            if (
                classification.content_index is None
                or len(parts) <= classification.content_index + 1
            ):
                raise InvalidArgumentError("Compile target must be inside a memory type directory")
        elif parts == ["resources"] or (
            classification.content_index is not None
            and len(parts) <= classification.content_index + 1
        ):
            raise InvalidArgumentError("Compile target must be inside a resource directory")

    @staticmethod
    def _split_payload(request: CompileRequest) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        args = payload.get("args")
        if not isinstance(args, dict):
            return payload, {}
        private_args = {key: args.pop(key) for key in SENSITIVE_TASK_KEYS if key in args}
        if not private_args:
            return payload, {}
        if not args:
            payload.pop("args", None)
        return payload, {"args": private_args}

    @staticmethod
    def _snapshot(task: CompileSessionStatus) -> ExternalTaskSnapshot:
        status = (task.status or "").strip().lower()
        if not status:
            normalized_stage = task.stage.strip().lower().replace(" ", "")
            if "cancelled" in normalized_stage or "canceled" in normalized_stage:
                status = "cancelled"
            elif task.error is not None or any(
                marker in normalized_stage for marker in ("failed", "error")
            ):
                status = "failed"
            elif any(
                marker in normalized_stage
                for marker in ("completed", "succeeded", "success", "finished")
            ):
                status = "completed"
            else:
                status = "running"
        if status in _ACTIVE_STATUSES:
            status = "running"
        elif status == "cancelling":
            pass
        elif status not in _TERMINAL_STATUSES:
            raise ExternalTaskError(
                "INVALID_RESPONSE",
                f"Unknown Compile task status: {status}",
                transient=False,
            )

        if isinstance(task.error, CompileErrorInfo):
            error_code = task.error.code
            error_message = task.error.message
        elif task.error:
            error_code = "UNKNOWN"
            error_message = str(task.error)
        else:
            error_code = None
            error_message = None
        return ExternalTaskSnapshot(
            status=status,
            stage=task.stage,
            result=task.result,
            meta=task.meta,
            error_code=error_code,
            error_message=error_message,
        )
