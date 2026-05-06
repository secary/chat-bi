"""Unit tests for HTTP helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from backend.http_utils import request_trace_id


def test_request_trace_id_uses_header_when_valid() -> None:
    req = MagicMock()
    req.headers.get.return_value = "a" * 8
    assert request_trace_id(req) == "a" * 8


def test_request_trace_id_generates_when_header_invalid() -> None:
    req = MagicMock()
    req.headers.get.return_value = "short"
    out = request_trace_id(req)
    assert len(out) == 32
