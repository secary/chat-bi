from backend.agent.executor import skill_args_for_execution


def test_file_ingestion_extracts_upload_path_from_natural_language_arg():
    path = "/tmp/chatbi-uploads/a93eb5ae568d416c98c6e5f5db0d1edf_chatbi_file_parse_test.csv"
    args = [f"请读取我上传的文件 {path}，按数据库表结构校验", "--include-rows"]
    out = skill_args_for_execution("chatbi-file-ingestion", args, [])
    assert out == [path, "--include-rows"]


def test_file_ingestion_falls_back_to_latest_user_upload_path():
    old_path = "/tmp/chatbi-uploads/old_chatbi_file_parse_test.csv"
    new_path = "/tmp/chatbi-uploads/new_chatbi_file_parse_test.csv"
    messages = [
        {"role": "user", "content": f"之前文件：{old_path}"},
        {"role": "assistant", "content": f"文件读取失败：{old_path}"},
        {"role": "user", "content": f"请改用这个：{new_path}"},
    ]
    out = skill_args_for_execution("chatbi-file-ingestion", ["请读取附件并校验"], messages)
    assert out == [new_path]


def test_file_ingestion_auto_adds_include_rows_for_visual_followup():
    path = "/tmp/chatbi-uploads/chart_ready.csv"
    messages = [
        {"role": "user", "content": f"我上传了文件 {path}"},
        {"role": "user", "content": "请基于这个文件生成可视化图表"},
    ]
    out = skill_args_for_execution("chatbi-file-ingestion", ["请继续画图"], messages)
    assert out == [path, "--include-rows"]


def test_file_ingestion_filters_unsupported_llm_options():
    path = "/tmp/chatbi-uploads/chart_ready.csv"
    messages = [{"role": "user", "content": f"我上传了文件 {path}，请生成图表"}]
    out = skill_args_for_execution(
        "chatbi-file-ingestion",
        ["请继续分析", "--dimensions", "region", "--metrics", "sales_amount", "--include-rows"],
        messages,
    )
    assert out == [path, "--include-rows"]


def test_file_ingestion_passes_latest_user_question_for_followup_analysis():
    path = "/tmp/chatbi-uploads/deposit_ready.csv"
    messages = [
        {"role": "user", "content": f"我上传了文件 {path}"},
        {"role": "user", "content": "请按账户状态做统计"},
    ]
    out = skill_args_for_execution("chatbi-file-ingestion", ["请继续分析"], messages)
    assert out == [path, "--question", "请按账户状态做统计", "--include-rows"]
