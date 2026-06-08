import importlib


def test_format_memory_empty_when_disabled(monkeypatch):
    monkeypatch.setenv("CHATBI_MEMORY_DISABLED", "1")
    import backend.memory_service as ms

    importlib.reload(ms)
    assert ms.format_memory_for_prompt(1) == ""
    monkeypatch.delenv("CHATBI_MEMORY_DISABLED", raising=False)
    importlib.reload(ms)


def test_format_memory_excludes_current_session_summary(monkeypatch):
    import backend.memory_service as ms

    monkeypatch.setattr(ms, "_MEMORY_OFF", False)
    monkeypatch.setattr(
        ms,
        "get_long_term_row",
        lambda user_id: {"content": "偏好：先给结论。"},
    )
    monkeypatch.setattr(
        ms,
        "list_recent_session_summaries",
        lambda user_id, limit: [
            {"title": "当前会话", "content": "当前摘要", "source_session_id": 11},
            {"title": "历史会话", "content": "历史摘要", "source_session_id": 10},
        ],
    )

    block = ms.format_memory_for_prompt(7, exclude_session_id=11)

    assert "偏好：先给结论" in block
    assert "历史摘要" in block
    assert "当前摘要" not in block
