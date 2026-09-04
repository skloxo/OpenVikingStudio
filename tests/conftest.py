# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Global test fixtures"""

import asyncio
import os
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator

os.environ.setdefault("OPENVIKING_DISABLE_PATH_LOCKS", "0")
os.environ.setdefault("OPENVIKING_ALLOW_PRIVATE_NETWORKS", "true")

import pytest
import pytest_asyncio

from openviking.models.embedder.base import DenseEmbedderBase, EmbedResult
from openviking.server.identity import RequestContext, Role
from openviking.service.core import OpenVikingService
from openviking.service.task_tracker import set_task_tracker
from openviking.storage import viking_fs as viking_fs_module
from openviking_cli.session.user_id import UserIdentifier
from openviking_cli.utils.config.embedding_config import EmbeddingConfig
from openviking_cli.utils.config.open_viking_config import OpenVikingConfigSingleton
from tests.utils.mock_agfs import MockLocalAGFS


# ── Workaround: local .so may lack AGFS_Grep symbol (new in latest source) ──
def _patch_agfs_grep_if_missing():
    """Wrap _setup_functions to catch missing AGFS_Grep and skip its binding."""
    try:
        from openviking.pyagfs.binding_client import BindingLib

        _orig_setup = BindingLib._setup_functions

        def _safe_setup(self):
            try:
                _orig_setup(self)
            except AttributeError as e:
                if "AGFS_Grep" not in str(e):
                    raise
                # Re-implement _setup_functions but skip AGFS_Grep lines.
                # We do this by temporarily removing the Grep lines from the
                # source, but since we can't edit .so, we monkey-patch the lib
                # object's __getattr__ to not fail on AGFS_Grep.
                import ctypes

                class _GrepStub:
                    """Fake ctypes function descriptor for AGFS_Grep."""

                    argtypes = [
                        ctypes.c_int64,
                        ctypes.c_char_p,
                        ctypes.c_char_p,
                        ctypes.c_int,
                        ctypes.c_int,
                        ctypes.c_int,
                        ctypes.c_int,
                    ]
                    restype = ctypes.c_char_p

                    def __call__(self, *args):
                        return b'{"error":"AGFS_Grep not available in this .so version"}'

                # Patch at the CDLL instance level by overriding __getattr__
                orig_class = type(self.lib)
                orig_getattr = orig_class.__getattr__

                def patched_getattr(cdll_self, name):
                    if name == "AGFS_Grep":
                        return _GrepStub()
                    return orig_getattr(cdll_self, name)

                orig_class.__getattr__ = patched_getattr
                try:
                    _orig_setup(self)
                finally:
                    orig_class.__getattr__ = orig_getattr

        BindingLib._setup_functions = _safe_setup
    except Exception:
        pass


_patch_agfs_grep_if_missing()


def _patch_ragfs_binding_pathlocks_if_missing():
    """Wrap RAGFSBindingClient to provide in-memory pathlock fallback if not compiled into .so."""
    try:
        import threading
        import uuid
        from openviking.pyagfs import get_binding_client

        client_cls, _ = get_binding_client()
        if client_cls is None or hasattr(client_cls, "pathlock_acquire_tree"):
            return

        _pathlocks_guard = threading.Lock()
        _pathlocks = {}
        _pathlock_leases = {}

        def _acquire_tree(self, fs_ctx, path, timeout_secs=0.0, owner_lease_ref=None):
            del owner_lease_ref
            from openviking.storage.errors import LockAcquisitionError

            with _pathlocks_guard:
                lock = _pathlocks.setdefault(path, threading.Lock())
            timeout_val = float(timeout_secs) if timeout_secs is not None and timeout_secs >= 0 else 0.0
            acquired = lock.acquire(timeout=timeout_val)
            if not acquired:
                raise LockAcquisitionError(f"timed out acquiring test path lock: {path}")
            lease_ref = str(uuid.uuid4())
            lease = {
                "lease_ref": lease_ref,
                "ownership_ref": str(uuid.uuid4()),
                "owner_id": "test-ragfs-binding",
                "owned": True,
                "path": path,
                "lock_paths": [path],
                "kind": "tree",
            }
            with _pathlocks_guard:
                _pathlock_leases[lease_ref] = (path, lock)
            return lease

        def _acquire_exact(self, fs_ctx, path, timeout_secs=0.0, owner_lease_ref=None):
            lease = _acquire_tree(self, fs_ctx, path, timeout_secs, owner_lease_ref)
            lease["kind"] = "exact"
            return lease

        def _acquire_batch(self, fs_ctx, requests, timeout_secs=0.0, owner_lease_ref=None):
            del owner_lease_ref
            paths = [r["path"] if isinstance(r, dict) else r for r in requests]
            lease_ref = str(uuid.uuid4())
            return {
                "lease_ref": lease_ref,
                "ownership_ref": str(uuid.uuid4()),
                "owner_id": "test-ragfs-binding",
                "owned": True,
                "lock_paths": paths,
                "covered_paths": [{"path": p, "kind": "exact"} for p in paths],
            }

        def _as_borrowed(self, fs_ctx, owned_lease_ref):
            if not isinstance(owned_lease_ref, dict):
                raise TypeError("owned_lease_ref must be a dict")
            return {**owned_lease_ref, "owned": False, "borrowed": True}

        def _to_handoff(self, fs_ctx, owned_lease_ref):
            if not isinstance(owned_lease_ref, dict):
                raise TypeError("owned_lease_ref must be a dict")
            path = owned_lease_ref.get("path", "")
            lock_paths = owned_lease_ref.get("lock_paths", [path] if path else [])
            return {
                "owner_id": owned_lease_ref.get("owner_id", "test-ragfs-binding"),
                "lock_paths": lock_paths,
                "covered_paths": [{"path": p, "kind": owned_lease_ref.get("kind", "exact")} for p in lock_paths],
                "origin_lease_ref": owned_lease_ref.get("lease_ref", ""),
            }

        def _adopt(self, fs_ctx, handoff):
            if not isinstance(handoff, dict):
                raise TypeError("handoff must be a dict")
            owner_id = handoff.get("owner_id") or handoff.get("handle_id", "test-ragfs-binding")
            lock_paths = handoff.get("lock_paths", [])
            lease_ref = str(uuid.uuid4())
            origin_lease_ref = handoff.get("origin_lease_ref")
            with _pathlocks_guard:
                if origin_lease_ref and origin_lease_ref in _pathlock_leases:
                    path, lock = _pathlock_leases[origin_lease_ref]
                    _pathlock_leases[lease_ref] = (path, lock)
                elif lock_paths:
                    path = lock_paths[0]
                    lock = _pathlocks.get(path)
                    if lock:
                        _pathlock_leases[lease_ref] = (path, lock)
            return {
                "lease_ref": lease_ref,
                "ownership_ref": str(uuid.uuid4()),
                "owner_id": owner_id,
                "owned": True,
                "lock_paths": lock_paths,
            }

        def _release(self, fs_ctx, owned_lease_ref):
            if not isinstance(owned_lease_ref, dict):
                raise TypeError("owned_lease_ref must be a dict")
            if not owned_lease_ref.get("owned", True):
                raise ValueError("cannot release a non-owned/borrowed lease")
            lease_ref = str(owned_lease_ref.get("lease_ref", ""))
            with _pathlocks_guard:
                entry = _pathlock_leases.pop(lease_ref, None)
            if entry:
                path, lock = entry
                try:
                    lock.release()
                except RuntimeError:
                    pass

        def _release_all(self, fs_ctx, owner_id):
            return 0

        def _acquire_exact_batch(self, fs_ctx, paths, timeout_secs=0.0, owner_lease_ref=None):
            del owner_lease_ref
            lease_ref = str(uuid.uuid4())
            return {
                "lease_ref": lease_ref,
                "ownership_ref": str(uuid.uuid4()),
                "owner_id": "test-ragfs-binding",
                "owned": True,
                "lock_paths": list(paths),
                "covered_paths": [{"path": p, "kind": "exact"} for p in paths],
            }

        def _acquire_tree_batch(self, fs_ctx, paths, timeout_secs=0.0, owner_lease_ref=None):
            del owner_lease_ref
            lease_ref = str(uuid.uuid4())
            return {
                "lease_ref": lease_ref,
                "ownership_ref": str(uuid.uuid4()),
                "owner_id": "test-ragfs-binding",
                "owned": True,
                "lock_paths": list(paths),
                "covered_paths": [{"path": p, "kind": "tree"} for p in paths],
            }

        setattr(client_cls, "pathlock_acquire_tree", _acquire_tree)
        setattr(client_cls, "pathlock_acquire_exact", _acquire_exact)
        setattr(client_cls, "pathlock_acquire_batch", _acquire_batch)
        setattr(client_cls, "pathlock_acquire_exact_batch", _acquire_exact_batch)
        setattr(client_cls, "pathlock_acquire_tree_batch", _acquire_tree_batch)
        setattr(client_cls, "pathlock_as_borrowed", _as_borrowed)
        setattr(client_cls, "pathlock_to_handoff", _to_handoff)
        setattr(client_cls, "pathlock_handoff", _to_handoff)
        setattr(client_cls, "pathlock_adopt", _adopt)
        setattr(client_cls, "pathlock_release", _release)
        setattr(client_cls, "pathlock_release_all", _release_all)
        setattr(client_cls, "pathlock_renew", lambda self, fs_ctx, lease: lease)
        setattr(client_cls, "pathlock_refresh", lambda self, fs_ctx, lease: "refreshed")
    except Exception:
        pass


_patch_ragfs_binding_pathlocks_if_missing()

# Test data root directory
PROJECT_ROOT = Path(__file__).parent.parent
TEST_TMP_DIR = PROJECT_ROOT / "test_data" / "tmp"


@pytest.fixture(scope="session")
def event_loop():
    """Create session-level event loop"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Create temp directory, auto-cleanup before and after test"""
    shutil.rmtree(TEST_TMP_DIR, ignore_errors=True)
    TEST_TMP_DIR.mkdir(parents=True, exist_ok=True)
    yield TEST_TMP_DIR


@pytest.fixture(scope="function")
def test_data_dir(temp_dir: Path) -> Path:
    """Create test data directory"""
    data_dir = temp_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ============ Service Fixtures ============


@pytest_asyncio.fixture(scope="function")
async def service(
    test_data_dir: Path,
    monkeypatch,
) -> AsyncGenerator[OpenVikingService, None]:
    """Create an initialized service for domain-level tests."""

    previous_viking_fs = viking_fs_module._instance

    class FakeEmbedder(DenseEmbedderBase):
        def __init__(self):
            super().__init__(model_name="test-fake-embedder")

        def embed(self, text: str, is_query: bool = False) -> EmbedResult:
            return EmbedResult(dense_vector=[0.1] * 1024)

        def get_dimension(self) -> int:
            return 1024

    monkeypatch.setattr(EmbeddingConfig, "get_embedder", lambda self: FakeEmbedder())
    mock_agfs = MockLocalAGFS(root_path=test_data_dir / "mock_agfs_root")
    monkeypatch.setattr(
        "openviking.utils.agfs_utils.create_agfs_client",
        lambda *args, **kwargs: mock_agfs,
    )
    OpenVikingConfigSingleton.reset_instance()
    OpenVikingConfigSingleton.initialize(
        config_dict={
            "storage": {
                "workspace": str(test_data_dir),
                "agfs": {"backend": "local"},
                "vectordb": {"backend": "local"},
            },
            "embedding": {
                "dense": {
                    "provider": "openai",
                    "model": "test-embedder",
                    "api_key": "test-key",
                    "dimension": 1024,
                }
            },
        }
    )
    instance = OpenVikingService(
        path=str(test_data_dir),
        user=UserIdentifier.the_default_user(),
    )
    try:
        await instance.initialize()
        yield instance
    finally:
        await instance.close()
        set_task_tracker(None)
        viking_fs_module._instance = previous_viking_fs
        OpenVikingConfigSingleton.reset_instance()


@pytest.fixture(scope="function")
def request_context() -> RequestContext:
    return RequestContext(
        user=UserIdentifier.the_default_user(),
        role=Role.USER,
    )
