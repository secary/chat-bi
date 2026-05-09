from backend import memory_repo


def test_suggested_prompts_filters_upload_and_long_noise(monkeypatch):
    rows = [
        {
            "title": "请读取我上传的文件 /tmp/chatbi-uploads/2ba18c6bca22448e860e601ff757a597_chatbi_file_parse_test.csv，按数据库表结构校验"
        },
        {"title": "基于这个文件，分析各区域的销售额和毛利润"},
        {"title": "各区域销售额的占比如何？"},
        {"title": "   各区域销售额的占比如何？   "},
    ]

    monkeypatch.setattr(memory_repo, "app_fetch_all", lambda *_args, **_kwargs: rows)

    prompts = memory_repo.suggested_prompts_for_user(1)

    assert prompts == ["各区域销售额的占比如何？"]


def test_suggested_prompts_keeps_short_useful_titles(monkeypatch):
    rows = [
        {"title": "华东和华南销售额对比"},
        {"title": "客户数按区域分布"},
    ]

    monkeypatch.setattr(memory_repo, "app_fetch_all", lambda *_args, **_kwargs: rows)

    prompts = memory_repo.suggested_prompts_for_user(7)

    assert prompts == ["华东和华南销售额对比", "客户数按区域分布"]
