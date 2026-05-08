"""Tests for upload path injection on CSV follow-up turns."""

from backend.agent.upload_context import augment_messages_for_upload_followup


def test_no_paths_unchanged():
    msgs = [{"role": "user", "content": "帮我分析CSV并画图"}]
    assert augment_messages_for_upload_followup(msgs) == msgs


def test_prepends_hint_when_path_in_prior_turn():
    path = "/tmp/chatbi-uploads/a93eb5ae568d416c98c6e5f5db0d1edf_chatbi_file_parse_test.csv"
    msgs = [
        {"role": "user", "content": f"请读取 {path}，按数据库表结构校验"},
        {"role": "assistant", "content": "校验通过。"},
        {"role": "user", "content": "帮我分析CSV文件中都有什么数据，并画图展示。"},
    ]
    out = augment_messages_for_upload_followup(msgs)
    assert len(out) == 3
    last = out[-1]["content"]
    assert path in last
    assert last.startswith("[ChatBI 上下文")
    assert "chatbi-file-ingestion" in last
    assert "chatbi-semantic-query" in last


def test_skips_when_last_message_already_has_path():
    path = "/tmp/chatbi-uploads/abc_test.csv"
    msgs = [
        {"role": "user", "content": "校验"},
        {"role": "user", "content": f"分析 {path}"},
    ]
    out = augment_messages_for_upload_followup(msgs)
    assert out[-1]["content"] == f"分析 {path}"


def test_skips_pure_db_question_without_file_markers():
    path = "/tmp/chatbi-uploads/abc_test.csv"
    msgs = [
        {"role": "user", "content": f"文件 {path}"},
        {"role": "user", "content": "2026年1-4月各区域销售额排行"},
    ]
    out = augment_messages_for_upload_followup(msgs)
    assert out[-1]["content"] == "2026年1-4月各区域销售额排行"
