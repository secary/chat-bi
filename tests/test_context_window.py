from backend.agent import context_window
from backend.agent.context_window import build_manager_context, build_react_context


def test_react_context_uses_current_user_session_summary(monkeypatch):
    calls = []

    def fake_summaries(user_id: int, limit: int = 5):
        calls.append((user_id, limit))
        return [
            {
                "source_session_id": 11,
                "content": "用户经常追问华东区域销售额。",
            }
        ]

    monkeypatch.setattr(context_window, "list_recent_session_summaries", fake_summaries)

    body = build_react_context(
        11,
        "继续分析",
        [{"role": "user", "content": "继续分析"}],
        user_id=7,
    )

    assert calls == [(7, 10)]
    assert "用户经常追问华东区域销售额" in body


def test_manager_context_does_not_query_summary_without_user(monkeypatch):
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("summary lookup requires a real user_id")

    monkeypatch.setattr(context_window, "list_recent_session_summaries", fail_if_called)

    body = build_manager_context(
        11,
        "继续分析",
        [{"role": "user", "content": "继续分析"}],
    )

    assert "## 会话摘要" not in body
    assert "继续分析" in body
