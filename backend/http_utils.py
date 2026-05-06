"""HTTP helpers shared by routes."""

from __future__ import annotations

import re
import uuid

from fastapi import Request


def request_trace_id(request: Request) -> str:
    incoming = request.headers.get("x-trace-id", "").strip()
    if incoming and re.fullmatch(r"[0-9A-Za-z._:-]{8,64}", incoming):
        return incoming
    return uuid.uuid4().hex
