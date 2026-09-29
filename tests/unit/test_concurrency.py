# Copyright (c) 2026 Beijing Volcano Engine Technology Co., Ltd.
# SPDX-License-Identifier: AGPL-3.0

"""Unit tests for AsyncSemaphore cross-loop concurrency primitive."""

import asyncio
import threading
import pytest

from openviking.concurrency import AsyncSemaphore


@pytest.mark.asyncio
async def test_async_semaphore_basic():
    sem = AsyncSemaphore(2)
    assert sem._value == 2

    async with sem:
        assert sem._value == 1
        async with sem:
            assert sem._value == 0

    assert sem._value == 2


@pytest.mark.asyncio
async def test_async_semaphore_concurrency_limit():
    sem = AsyncSemaphore(2)
    current_concurrent = 0
    max_concurrent = 0

    async def worker():
        nonlocal current_concurrent, max_concurrent
        async with sem:
            current_concurrent += 1
            max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.01)
            current_concurrent -= 1

    await asyncio.gather(*[worker() for _ in range(6)])
    assert max_concurrent == 2
    assert current_concurrent == 0


def test_async_semaphore_cross_thread_loops():
    """Verify AsyncSemaphore works seamlessly across distinct threads with their own event loops."""
    sem = AsyncSemaphore(1)
    results = []

    def run_worker(worker_id: int):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def task():
            async with sem:
                results.append(f"enter_{worker_id}")
                await asyncio.sleep(0.02)
                results.append(f"exit_{worker_id}")

        try:
            loop.run_until_complete(task())
        finally:
            loop.close()

    t1 = threading.Thread(target=run_worker, args=(1,))
    t2 = threading.Thread(target=run_worker, args=(2,))

    t1.start()
    t2.start()
    t1.join(timeout=5)
    t2.join(timeout=5)

    assert len(results) == 4
    # Mutually exclusive execution: enter_X must be followed by exit_X before enter_Y
    assert (results[0].startswith("enter_") and results[1].startswith("exit_"))


@pytest.mark.asyncio
async def test_async_semaphore_cancellation():
    sem = AsyncSemaphore(1)
    await sem.acquire()

    waiter_started = asyncio.Event()

    async def waiting_task():
        waiter_started.set()
        await sem.acquire()

    task = asyncio.create_task(waiting_task())
    await waiter_started.wait()
    await asyncio.sleep(0.01)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Slot should still be available after initial acquire releases
    sem.release()
    assert sem._value == 1
