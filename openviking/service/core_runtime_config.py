# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0
"""Runtime config, account workspace, TTL, and system-assets lifecycle helpers for OpenVikingService."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Optional

from openviking.server.config_models import UserConfigDefaults
from openviking.server.identity import RequestContext
from openviking.storage.errors import LockAcquisitionError, ResourceBusyError
from openviking.storage.pathlock_transfer import PathLockGuard
from openviking.system_assets.reconcile import AccountLister, SystemAssetReconciler
from openviking_cli.exceptions import NotInitializedError
from openviking_cli.utils.config.agent_evolution_config import AgentEvolutionConfig
from openviking_cli.utils.logger import get_logger

if TYPE_CHECKING:
    from openviking.config.vlm import VLMResolver
    from openviking.ttl.adapter import TTLAdapter

logger = get_logger(__name__)


class _CoreRuntimeConfigMixin:
    """Mixin encapsulating #183 double-layer config, TTL, and system-asset sync lifecycle."""

    @property
    def runtime_config_manager(self) -> Optional[Any]:
        return getattr(self, "_runtime_config_manager", None)

    @property
    def vector_config_resolver(self) -> Optional[Any]:
        return getattr(self, "_vector_config_resolver", None)

    @property
    def embedding_provider(self) -> Optional[Any]:
        return getattr(self, "_embedding_provider", None)

    @property
    def vlm_resolver(self) -> Optional["VLMResolver"]:
        return getattr(self, "_vlm_resolver", None)

    async def release_account_vector_resources(self, account_id: str) -> None:
        vikingdb = getattr(self, "_vikingdb_manager", None)
        if vikingdb is not None and hasattr(vikingdb, "release_account"):
            await vikingdb.release_account(account_id)
        emb = getattr(self, "_embedding_provider", None)
        if emb is not None:
            await emb.invalidate(account_id)

    async def _on_account_vector_config_change(self, event: Any) -> None:
        from openviking.config.manager import ConfigChangeReason

        if event.reason is not ConfigChangeReason.EVICT and "vectordb" not in event.changed_sections:
            return
        account_id = event.scope.key
        if account_id:
            await self.release_account_vector_resources(account_id)

    def set_agent_evolution_config(self, config: AgentEvolutionConfig) -> None:
        self._agent_evolution_base_config = config.model_copy(deep=True)
        self._session_service.set_agent_evolution_config(config)

    @property
    def user_config_defaults(self) -> UserConfigDefaults:
        return self._user_config_defaults

    @user_config_defaults.setter
    def user_config_defaults(self, config: UserConfigDefaults) -> None:
        self._user_config_defaults = config
        if getattr(self, "_directory_initializer", None) is not None:
            self._directory_initializer.user_config_defaults = config

    async def apply_agent_evolution_config(self) -> None:
        manager = getattr(self, "_runtime_config_manager", None)
        if manager is None:
            return
        base_config = self._config.model_copy(
            update={"agent_evolution": self._agent_evolution_base_config.model_copy(deep=True)}
        )
        await manager.replace_base_config(base_config)

    async def _init_runtime_config_manager(self) -> None:
        from openviking.config.binding import build_runtime_config_manager
        from openviking.config.embedding import AccountEmbeddingProvider
        from openviking.config.scope import ScopeKind
        from openviking.config.vector import AccountVectorConfigResolver
        from openviking.config.vlm import AccountVLMProvider
        from openviking.pyagfs import AsyncAGFSClient

        if self._agfs_client is None:
            raise RuntimeError("AGFS client not initialized")
        base_config = self._config.model_copy(
            update={"agent_evolution": self._agent_evolution_base_config.model_copy(deep=True)},
        )
        manager = build_runtime_config_manager(
            AsyncAGFSClient(self._agfs_client),
            settings=self._config.runtime_config,
            base_config=base_config,
        )
        await manager.initialize()
        self._runtime_config_manager = manager
        if (
            self._vikingdb_manager is not None
            and getattr(self._vikingdb_manager, "acl_manager", None) is not None
            and hasattr(self._vikingdb_manager.acl_manager, "set_runtime_config_manager")
        ):
            self._vikingdb_manager.acl_manager.set_runtime_config_manager(manager)
        self._vector_config_resolver = AccountVectorConfigResolver(manager)
        self._embedding_provider = AccountEmbeddingProvider(
            self._vector_config_resolver,
            manager,
        )
        if self._vikingdb_manager is not None and hasattr(self._vikingdb_manager, "set_vector_config_resolver"):
            self._vikingdb_manager.set_vector_config_resolver(self._vector_config_resolver)
        manager.add_update_consumer(
            scope=ScopeKind.ACCOUNT,
            sections={"vectordb", "embedding"},
            consumer=self._on_account_vector_config_change,
        )
        if hasattr(self._session_service, "set_runtime_config_manager"):
            self._session_service.set_runtime_config_manager(manager)
        self._vlm_resolver = AccountVLMProvider(manager)
        if self._queue_manager is not None:
            if hasattr(self._queue_manager, "set_runtime_config_manager"):
                self._queue_manager.set_runtime_config_manager(manager)
            if hasattr(self._queue_manager, "set_vlm_resolver"):
                self._queue_manager.set_vlm_resolver(self._vlm_resolver)

    def configure_ttl(self, adapter: "TTLAdapter") -> None:
        self._ttl_adapter = adapter

    async def _stop_expiry(self) -> None:
        ttl_adapter = getattr(self, "_ttl_adapter", None)
        if ttl_adapter is not None:
            await ttl_adapter.aclose()
        runtime = getattr(self, "_expiry_runtime", None)
        if runtime is None:
            session_service = getattr(self, "_session_service", None)
            if session_service is not None and hasattr(session_service, "set_session_expiry_adapter"):
                session_service.set_session_expiry_adapter(None)
            return
        try:
            await runtime.close()
        except Exception as exc:
            logger.exception("Expiry shutdown failed")
            if getattr(exc, "code", None) == "shard_not_stopped":
                raise
        else:
            if hasattr(self._session_service, "set_session_expiry_adapter"):
                self._session_service.set_session_expiry_adapter(None)
            self._expiry_runtime = None
            logger.info("Expiry stopped")

    @asynccontextmanager
    async def account_workspace_lock(self, ctx: RequestContext):
        self._ensure_initialized()
        if not self._viking_fs:
            raise NotInitializedError("VikingFS")
        agfs = self._viking_fs._async_agfs
        path = self._viking_fs._uri_to_path("viking://", ctx=ctx)
        guard = PathLockGuard(agfs)
        try:
            try:
                lease = await guard.acquire(
                    lambda: agfs.pathlock_acquire_tree(path, timeout_secs=10.0)
                )
            except LockAcquisitionError as exc:
                raise ResourceBusyError(
                    f"Account workspace is busy and cannot be initialized now: {ctx.account_id}",
                    uri="viking://",
                ) from exc
            yield lease
        finally:
            await guard.close()

    async def initialize_account_workspace(
        self,
        ctx: RequestContext,
        *,
        lease_ref: Any = None,
    ) -> tuple[int, int]:
        self._ensure_initialized()
        if not self._directory_initializer:
            return 0, 0
        if lease_ref is not None:
            return await self._directory_initializer.initialize_account_workspace(
                ctx, lease_ref=lease_ref
            )
        async with self.account_workspace_lock(ctx) as lease:
            return await self._directory_initializer.initialize_account_workspace(
                ctx, lease_ref=lease
            )

    async def reconcile_system_assets(self, account_lister: AccountLister) -> int:
        self._ensure_initialized()
        synchronizer = getattr(self, "_system_asset_synchronizer", None)
        if not synchronizer or not self._viking_fs:
            return 0
        return await SystemAssetReconciler(
            synchronizer,
            account_lister,
            self._viking_fs._async_agfs,
            user_id=self._config.default_user or self._user.user_id,
            skip_account_ids={self._user.account_id},
        ).sync_if_changed()
