from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CaseStep:
    message: str
    expect_skills: list[str] = field(default_factory=list)
    no_skill_call: bool = False
    expect_text: list[str] = field(default_factory=list)
    expect_no_text: list[str] = field(default_factory=list)
    expect_chart: bool = False
    expect_analysis_proposal: bool = False
    expect_dashboard_ready: bool = False


@dataclass
class Case:
    id: str
    label: str
    message: str
    expect_skills: list[str] = field(default_factory=list)
    no_skill_call: bool = False
    expect_text: list[str] = field(default_factory=list)
    expect_no_text: list[str] = field(default_factory=list)
    expect_chart: bool = False
    multi_agents: bool = False
    upload_file: str | None = None
    steps: list[CaseStep] = field(default_factory=list)


CASES: list[Case] = [
    Case(
        "S1",
        "区域销售额排行",
        "1-4月各区域销售额排行",
        expect_skills=["chatbi-semantic-query"],
        expect_chart=True,
    ),
    Case(
        "S2",
        "按月趋势",
        "2026年销售额按月趋势",
        expect_skills=["chatbi-semantic-query"],
        expect_chart=True,
    ),
    Case("S3", "单值 KPI", "华东4月毛利率", expect_skills=["chatbi-semantic-query"]),
    Case(
        "S4", "数据库概览", "当前数据库有哪些表可以查", expect_skills=["chatbi-database-overview"]
    ),
    Case("S5", "环比对比", "销售额和上月相比怎么样", expect_skills=["chatbi-comparison"]),
    Case(
        "S6",
        "指标口径解释",
        "销售额口径是什么",
        expect_skills=["chatbi-metric-explainer"],
        expect_text=["销售额口径"],
    ),
    Case(
        "M1",
        "查询+建议（区域）",
        "1-4月各区域销售额排行，并给出经营建议",
        expect_skills=["chatbi-semantic-query", "chatbi-decision-advisor"],
        expect_text=["决策"],
    ),
    Case(
        "M2",
        "查询+建议（毛利率）",
        "各渠道毛利率经营建议",
        expect_skills=["chatbi-semantic-query", "chatbi-decision-advisor"],
        expect_text=["决策"],
    ),
    Case(
        "M3",
        "查询+建议（区域焦点）",
        "华东销售额建议",
        expect_skills=["chatbi-semantic-query", "chatbi-decision-advisor"],
        expect_text=["决策"],
    ),
    Case(
        "C1",
        "图表无原始 JSON",
        "请把下面结果用最合适的图表可视化出来："
        '{"question":"2026年1-4月销售额趋势","rows":['
        '{"月份":"2026-01","销售额":355000},'
        '{"月份":"2026-02","销售额":378000},'
        '{"月份":"2026-03","销售额":412000},'
        '{"月份":"2026-04","销售额":462000}]}',
        expect_no_text=['"series":', '"xAxis":'],
        expect_chart=True,
    ),
    Case("E1", "小聊天不调 Skill", "你好", no_skill_call=True),
    Case("E2", "不存在年份", "2024年销售额", expect_skills=["chatbi-semantic-query"]),
    Case(
        "U1",
        "上传表解析-指标采纳-画图",
        "上传数据自动分析",
        upload_file="data/chatbi_sales.csv",
        steps=[
            CaseStep(
                "分析这份数据适合哪些指标，先给我可采纳的指标建议",
                expect_skills=["chatbi-file-ingestion", "chatbi-auto-analysis"],
                expect_analysis_proposal=True,
            ),
            CaseStep(
                "采纳全部指标并画图",
                expect_skills=["chatbi-auto-analysis"],
                expect_dashboard_ready=True,
            ),
        ],
    ),
]


CASE_GROUPS: dict[str, list[str]] = {
    "smoke": ["S1", "S4", "E1"],
    "query": ["S1", "S2", "S3"],
    "metadata": ["S4", "S6"],
    "comparison": ["S5"],
    "advisor": ["M1", "M2", "M3"],
    "chart": ["S1", "S2", "C1"],
    "upload": ["U1"],
    "edge": ["E1", "E2"],
    "all": [case.id for case in CASES],
}
