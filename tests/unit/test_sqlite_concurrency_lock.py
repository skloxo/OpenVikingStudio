# -*- coding: utf-8 -*-
"""
Concurrency stress test verifying SQLite lock resilience with timeout=30.0 and WAL mode.
Validates that multiple threads writing simultaneously do not raise `database is locked`.
"""

import os
import tempfile
import threading
import pytest
from openviking.service.active_notes_history import ActiveNotesHistoryManager


def test_sqlite_concurrent_writes():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "concurrency_test.db")
        manager = ActiveNotesHistoryManager(db_path=db_path)

        num_threads = 20
        writes_per_thread = 10
        errors = []

        def worker(thread_id: int):
            try:
                for i in range(writes_per_thread):
                    session_id = f"session_thread_{thread_id}"
                    manager.update_notes(
                        session_id=session_id,
                        active_goal=f"Goal from thread {thread_id} iteration {i}",
                        working_constraints=["NO LOCK TIMEOUT", "WAL MODE ACTIVE"],
                        current_state=f"State {i}",
                        discovered_facts=[f"Fact {thread_id}_{i}"],
                    )
            except Exception as e:
                errors.append((thread_id, e))

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Assert zero lock errors occurred across all 200 concurrent write operations
        assert len(errors) == 0, f"Encountered SQLite concurrency errors: {errors}"

        # Verify all sessions were created and persisted
        for thread_id in range(num_threads):
            session_id = f"session_thread_{thread_id}"
            notes = manager.get_or_create_notes(session_id)
            assert notes.session_id == session_id
            assert notes.version == writes_per_thread
