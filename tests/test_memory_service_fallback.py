import asyncio

from backend import memory_service


def test_refresh_memory_persists_fallback_summary_when_summary_llm_fails(monkeypatch):
    inserted = []
    long_terms = []
    events = []

    async def fail_llm(*_args, **_kwargs):
        raise RuntimeError("llm unavailable")

    monkeypatch.setattr(memory_service, "_MEMORY_OFF", False)
    monkeypatch.setattr(memory_service, "_llm_text", fail_llm)
    monkeypatch.setattr(
        memory_service,
        "insert_session_summary",
        lambda user_id, session_id, title, content: inserted.append(
            {
                "user_id": user_id,
                "session_id": session_id,
                "title": title,
                "content": content,
            }
        ),
    )
    monkeypatch.setattr(memory_service, "trim_session_summaries", lambda *_args: None)
    monkeypatch.setattr(memory_service, "list_recent_session_summaries", lambda *_args: [])
    monkeypatch.setattr(memory_service, "get_long_term_row", lambda *_args: None)
    monkeypatch.setattr(
        memory_service,
        "upsert_long_term",
        lambda user_id, content: long_terms.append({"user_id": user_id, "content": content}),
    )
    monkeypatch.setattr(
        memory_service,
        "log_event",
        lambda *args, **kwargs: events.append((args, kwargs)),
    )

    asyncio.run(
        memory_service.refresh_memory_after_turn(
            "trace-1",
            7,
            42,
            "看看华东 5 月销售额和毛利率",
            "华东 5 月销售额为 100 万，毛利率为 32%。",
        )
    )

    assert inserted
    assert inserted[0]["user_id"] == 7
    assert inserted[0]["session_id"] == 42
    assert inserted[0]["title"] == "看看华东 5 月销售额和毛利率"
    assert "规则摘要保存" in inserted[0]["content"]
    assert "看看华东 5 月销售额和毛利率" in inserted[0]["content"]
    assert long_terms
    assert "近期会话补充" in long_terms[0]["content"]
    assert any(args[2] == "session_summary_fallback_used" for args, _kwargs in events)
    assert any(args[2] == "long_term_fallback_used" for args, _kwargs in events)


def test_refresh_memory_keeps_session_summary_when_long_term_llm_fails(monkeypatch):
    inserted = []
    long_terms = []
    calls = {"count": 0}

    async def mixed_llm(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return "用户关注区域销售额对比，并希望保留毛利率口径。"
        raise RuntimeError("merge failed")

    monkeypatch.setattr(memory_service, "_MEMORY_OFF", False)
    monkeypatch.setattr(memory_service, "_llm_text", mixed_llm)
    monkeypatch.setattr(
        memory_service,
        "insert_session_summary",
        lambda user_id, session_id, title, content: inserted.append(content),
    )
    monkeypatch.setattr(memory_service, "trim_session_summaries", lambda *_args: None)
    monkeypatch.setattr(
        memory_service,
        "list_recent_session_summaries",
        lambda *_args: [
            {
                "title": "区域销售额对比",
                "content": "用户关注区域销售额对比，并希望保留毛利率口径。",
            }
        ],
    )
    monkeypatch.setattr(
        memory_service,
        "get_long_term_row",
        lambda *_args: {"id": 1, "content": "旧偏好：回答要先给结论。"},
    )
    monkeypatch.setattr(
        memory_service,
        "upsert_long_term",
        lambda user_id, content: long_terms.append({"user_id": user_id, "content": content}),
    )
    monkeypatch.setattr(memory_service, "log_event", lambda *_args, **_kwargs: None)

    asyncio.run(
        memory_service.refresh_memory_after_turn(
            "trace-2",
            8,
            43,
            "区域销售额对比",
            "华东高于华南。",
        )
    )

    assert inserted == ["用户关注区域销售额对比，并希望保留毛利率口径。"]
    assert long_terms
    assert "旧偏好：回答要先给结论。" in long_terms[0]["content"]
    assert "用户关注区域销售额对比" in long_terms[0]["content"]
