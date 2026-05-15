"""Shared upload-file path detection for skill routing and validation."""

from __future__ import annotations


def has_upload_file_reference(text: str) -> bool:
    """True when dialogue text suggests a local uploaded CSV/XLSX path."""
    if not text:
        return False
    low = text.lower()
    if "chatbi-uploads" in low:
        return True
    if "/tmp/" in low and any(ext in low for ext in (".csv", ".xlsx", ".xls")):
        return True
    return False
