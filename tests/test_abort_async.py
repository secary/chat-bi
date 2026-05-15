from __future__ import annotations

import asyncio

import pytest

from backend.agent.abort_async import ChatAbortedError, await_with_abort
from backend.agent.abort_state import clear_abort, get_abort_event


def test_await_with_abort_completes_when_not_aborted() -> None:
    tid = "abort-async-ok-traceid-01"
    clear_abort(tid)
    get_abort_event(tid)
    try:

        async def quick() -> int:
            return 7

        async def body() -> None:
            assert await await_with_abort(quick(), tid, poll_interval=0.05) == 7

        asyncio.run(body())
    finally:
        clear_abort(tid)


def test_await_with_abort_raises_when_aborted_mid_wait() -> None:
    tid = "abort-async-stop-traceid-02"
    clear_abort(tid)
    get_abort_event(tid)
    try:

        async def slow() -> None:
            await asyncio.sleep(10)

        async def arm_abort() -> None:
            await asyncio.sleep(0.08)
            get_abort_event(tid).set()

        async def body() -> None:
            with pytest.raises(ChatAbortedError):
                await asyncio.gather(
                    arm_abort(),
                    await_with_abort(slow(), tid, poll_interval=0.05),
                )

        asyncio.run(body())
    finally:
        clear_abort(tid)
