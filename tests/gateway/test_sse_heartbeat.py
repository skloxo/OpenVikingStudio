"""SSE heartbeats preserve framing, deadlines and cancellation."""

import asyncio

import pytest

from openviking_gateway import protocols, proxy
from openviking_gateway.protocols import HEARTBEAT_SECONDS, heartbeat

KEEP_ALIVE = b": keep-alive\n\n"


async def test_busy_source_preserves_bytes():
    data = [b'data: {"text":"', b'hello"}\n\n', b"data: [DONE]\n\n"]

    async def source():
        for chunk in data:
            yield chunk

    assert [chunk async for chunk in heartbeat(source(), 1)] == data


async def test_idle_source_keeps_one_task_and_propagates_timeout():
    tasks, output = [], []

    async def source():
        async with asyncio.timeout(0.06):
            for chunk in (b"first", b"second"):
                tasks.append(asyncio.current_task())
                yield chunk
                await asyncio.sleep(0.02)
            await asyncio.Event().wait()

    with pytest.raises(asyncio.TimeoutError):
        async with asyncio.timeout(1):
            async for chunk in heartbeat(source(), 0.005):
                output.append(chunk)
    assert [chunk for chunk in output if chunk is not None] == [b"first", b"second"]
    assert None in output
    assert tasks[0] is tasks[1] and tasks[0].done()


@pytest.mark.parametrize("error", [ValueError("upstream failed"), asyncio.CancelledError()])
async def test_source_failure_wakes_consumer_without_waiting_for_heartbeat(error):
    async def source():
        yield b"first"
        await asyncio.sleep(0.01)
        raise error

    async with asyncio.timeout(1):
        with pytest.raises(type(error)):
            async for _ in heartbeat(source(), 15):
                pass


async def test_deadline_during_backpressure_reaches_source_timeout_context():
    async def source():
        async with asyncio.timeout(0.03):
            for _ in range(10):
                yield b"chunk"

    stream = heartbeat(source(), 15)
    assert await anext(stream) == b"chunk"
    await asyncio.sleep(0.06)
    async with asyncio.timeout(1):
        with pytest.raises(asyncio.TimeoutError):
            async for _ in stream:
                pass


@pytest.mark.parametrize("backpressure", [False, True])
async def test_closing_consumer_cancels_and_closes_source(backpressure):
    advanced, closed, tasks = [], [], []

    async def source():
        tasks.append(asyncio.current_task())
        try:
            async with asyncio.timeout(1):
                for number in range(100):
                    advanced.append(number)
                    yield b"chunk"
                    if not backpressure:
                        await asyncio.Event().wait()
        finally:
            closed.append(asyncio.current_task())

    stream = heartbeat(source(), 0.005)
    assert await anext(stream) == b"chunk"
    await asyncio.sleep(0.02)
    assert len(advanced) <= 3
    async with asyncio.timeout(1):
        await stream.aclose()
    assert closed == tasks and tasks[0].done()


async def test_proxy_sse_with_heartbeat_emits_keepalive_on_idle(monkeypatch):
    assert HEARTBEAT_SECONDS == 15
    assert protocols.HEARTBEAT_SECONDS == 15
    monkeypatch.setattr(proxy, "HEARTBEAT_SECONDS", 0.005)

    async def source():
        yield b'data: {"step":1}\n\n'
        await asyncio.sleep(0.03)
        yield b"data: [DONE]\n\n"

    chunks = [chunk async for chunk in proxy._sse_with_heartbeat(source())]
    assert chunks[0] == b'data: {"step":1}\n\n'
    assert KEEP_ALIVE in chunks
    assert chunks[-1] == b"data: [DONE]\n\n"
