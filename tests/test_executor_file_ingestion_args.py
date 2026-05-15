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


def test_file_ingestion_includes_rows_after_metric_confirmation():
    path = "/tmp/chatbi-uploads/auto_analysis_ready.csv"
    messages = [
        {"role": "user", "content": f"我上传了文件 {path}"},
        {"role": "user", "content": "采纳全部指标并生成看板"},
    ]
    out = skill_args_for_execution("chatbi-file-ingestion", ["继续"], messages)
    assert out == [path, "--question", "采纳全部指标并生成看板", "--include-rows"]


def test_semantic_query_prefers_user_original_block_in_composed_message():
    composed = (
        "【Manager 交办】\n华东华北华南西南\n\n【用户原述】\n各个区域的销售额可以做成柱状图来划分。"
    )
    messages = [{"role": "user", "content": composed}]
    out = skill_args_for_execution("chatbi-semantic-query", [], messages)
    assert out == ["各个区域的销售额可以做成柱状图来划分。"]


def test_semantic_query_falls_back_to_full_user_when_no_original_marker():
    messages = [{"role": "user", "content": "1-4月各区域销售额排行"}]
    out = skill_args_for_execution("chatbi-semantic-query", [], messages)
    assert out == ["1-4月各区域销售额排行"]
