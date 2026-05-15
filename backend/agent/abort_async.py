"""Async helpers to honour /abort while awaiting slow LLM calls."""

from __future__ import annotations

import asyncio
from typing import Awaitable, TypeVar

T = TypeVar("T")


class ChatAbortedError(Exception):
    """Raised when the user requested /abort for this trace during an LLM wait."""


async def await_with_abort(
    awaitable: Awaitable[T], trace_id: str, *, poll_interval: float = 0.25
) -> T:
    """Await *awaitable* but cancel it once ``is_aborted(trace_id)`` becomes true."""
    from backend.agent.abort_state import is_aborted

    tid = (trace_id or "").strip()
    if not tid:
        return await awaitable

    task = asyncio.ensure_future(awaitable)
    try:
        while not task.done():
            if is_aborted(tid):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                raise ChatAbortedError() from None
            await asyncio.wait({task}, timeout=poll_interval, return_when=asyncio.FIRST_COMPLETED)
        exc = task.exception()
        if exc is not None:
            raise exc
        return task.result()
    except asyncio.CancelledError:
        if is_aborted(tid):
            raise ChatAbortedError() from None
        raise
