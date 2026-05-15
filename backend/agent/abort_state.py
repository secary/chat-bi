"""Global abort state management for cancelling in-progress chat requests."""

from __future__ import annotations

import threading
from typing import Dict

_abort_flags: Dict[str, threading.Event] = {}
_lock = threading.Lock()


def get_abort_event(trace_id: str) -> threading.Event:
    """Get or create an abort event for a trace_id."""
    with _lock:
        return _abort_flags.setdefault(trace_id, threading.Event())


def set_abort(trace_id: str) -> None:
    """Signal abort for a trace_id."""
    with _lock:
        if trace_id in _abort_flags:
            _abort_flags[trace_id].set()


def is_aborted(trace_id: str) -> bool:
    """Check if abort has been signalled for a trace_id."""
    with _lock:
        event = _abort_flags.get(trace_id)
        return event.is_set() if event else False


def clear_abort(trace_id: str) -> None:
    """Clear the abort event for a trace_id (cleanup after request ends)."""
    with _lock:
        if trace_id in _abort_flags:
            _abort_flags[trace_id].clear()
            del _abort_flags[trace_id]
