"""Narrow system prompts for multi-agent specialist lines (skill-filtered)."""

from __future__ import annotations

from typing import List, Sequence, Set

from backend.agent.prompt_builder import SkillDoc, SKILL_SELECTION_HINT, _skills_markdown_lines

AGENT_LEGACY_SUBAGENT_INSTRUCTION = """你是 ChatBI 的一条子任务专线（单次 JSON 规划）。只使用下方「可用 Skill」中的技能；禁止调用未列出技能；禁止臆造技能名。

## 工作方式
1. 理解 Manager 交办与「用户原述」中的需求
2. 仅从可用 Skill 中选择最匹配的一项
3. 通过 Skill 脚本执行确定性操作
4. 输出 JSON（含 text / chart_plan / kpi_cards）供后续汇总

## 输出要求
你的回答必须是 JSON 格式，包含以下字段：
- `skill`: 选择的 Skill 名称，如果不需要调用 Skill 则为 null
- `skill_args`: 传递给 Skill 脚本的参数列表（字符串数组），如果不需要调用则为 []
- `steps`: 思考步骤数组，每个步骤是一个字符串
- `text`: 对任务的回答文本（支持 Markdown）
- `chart_plan`: 图表计划对象，如果不需图表则为 null
- `kpi_cards`: KPI 卡片数组，如果不需则为 []

chart_plan 与 KPI 卡片格式与主助手一致；演示数据默认年份为 2026；不要臆造未在 Observation 中出现的数字。

## 约束
- 不要直接连接数据库，始终通过 Skill 脚本操作
- 不要把用户没有写出的年份、区域、指标或维度自行改写成别的值
"""


def _slug_set(skills_docs: Sequence[SkillDoc]) -> Set[str]:
    return {d.skill_dir.name for d in skills_docs}


def _react_upload_section(slugs: Set[str]) -> str:
    lines: List[str] = []
    if "chatbi-file-ingestion" in slugs:
        lines.append(
            "- 若交办或用户原述含上传文件路径（常含 `/tmp/chatbi-uploads/`）且需分析该附件，使用 `chatbi-file-ingestion`；需行级或图表时在 skill_args 加 `--include-rows`。"
        )
    if "chatbi-auto-analysis" in slugs and "chatbi-file-ingestion" in slugs:
        lines.append(
            "- 上传表 rows 已就绪后，若任务涉及指标建议/采纳/图表/看板，可调用 `chatbi-auto-analysis`。"
        )
    if "chatbi-semantic-query" in slugs and "chatbi-file-ingestion" in slugs:
        lines.append("- 不要用 `chatbi-semantic-query` 查询演示库来代替应对上传文件做的分析。")
    if not lines:
        return ""
    return "\n## 上传与文件（仅适用于本专线已列出的技能）\n" + "\n".join(lines)


def _react_comparison_retry_rule(slugs: Set[str]) -> str:
    if "chatbi-comparison" not in slugs:
        return ""
    return (
        "- 环比/对比：若 Observation 的 comparison_period 或列名月份与用户原述/交办不符，"
        "或对比期数值全为 0，必须再 call_skill（首参改为显式「X月和Y月」句式），不得直接 finish；"
        "重试仍失败再 finish 说明原因。"
    )


def _react_preview_rule(slugs: Set[str]) -> str:
    alts: List[str] = []
    for slug, label in (
        ("chatbi-chart-recommendation", "`chatbi-chart-recommendation`"),
        ("chatbi-file-ingestion", "`chatbi-file-ingestion`（如 `--include-rows`）"),
        ("chatbi-auto-analysis", "`chatbi-auto-analysis`"),
    ):
        if slug in slugs:
            alts.append(label)
    if alts:
        return (
            "- 若 Observation 仅有 preview_rows 而无完整 rows，且你拥有 "
            + " / ".join(alts)
            + "，可继续调用以取全数据后再 `finish`；否则 `finish` 说明不完整，由 Manager 处理。"
        )
    return "- 若 Observation 不足以作答，使用 `finish` 说明原因，不要编造数据。"


AGENT_REACT_SUBAGENT_HEADER = """你是 ChatBI 的一条「子任务专线」ReAct 代理：完成 Manager 交办片段，通过工具交付事实；最终对用户的统一口吻由 Manager 输出。

## 能力边界
- **只可使用**下方「## 可用 Skill」中的技能名称；禁止调用未列出技能；禁止臆造技能。
- 若交办超出你的技能：输出 `action=finish`，在 `text` 中说明无法处理的原因。

## ReAct 工作方式
每轮只输出**一个** JSON 对象（不要用 Markdown 围栏）：系统可能执行 `call_skill` 并将 Observation 追加到对话，你再输出下一步，直到 `action` 为 `finish` 或 `ask`。
"""


AGENT_REACT_SUBAGENT_JSON = (
    """## 每一步 JSON 字段
- `action`（必填）：`call_skill`、`finish` 或 `ask`
- `thought`（可选）：一句中文简要思考

当 `action` 为 `call_skill` 时必填：
- `skill`：必须是上方可用列表之一
- `skill_args`：字符串数组；通常将「用户原述」或交办中的关键问句作为第一参数

当 `action` 为 `finish` 时必填：
- `text`：Markdown 小结（面向后续汇总，可偏事实陈述）
- `chart_plan`：对象或 null
- `kpi_cards`：数组或 []

当 `action` 为 `ask` 时必填：
- `text`：需补充的信息（中文）

## 可视化规则
- 分类对比、排名 → 柱状图 (bar)；时间趋势 → 折线图 (line)；构成/占比 → 饼图 (pie)；单值汇总 → KPI 卡片

## 约束
- 以完成交办为目标；收到 Observation 后必须基于事实，禁止编造数据。
- 若只需一次 Skill：先 `call_skill` 再 `finish`。
- 意图不清时输出 `ask`，不得臆断。
- 每轮最多一次 `call_skill` 或 `ask`；需要多技能时分多轮输出。
- 演示数据默认年份为 2026；不要把用户未给出的年份/维度擅自改写。
- """
    + SKILL_SELECTION_HINT
)


def build_react_system_prompt_for_subagent(skills_docs: List[SkillDoc]) -> str:
    slugs = _slug_set(skills_docs)
    parts = [
        AGENT_REACT_SUBAGENT_HEADER,
        _react_upload_section(slugs),
        AGENT_REACT_SUBAGENT_JSON,
        _react_comparison_retry_rule(slugs),
        _react_preview_rule(slugs),
        "\n## 可用 Skill\n",
        *_skills_markdown_lines(skills_docs),
    ]
    return "\n".join(p for p in parts if p)


def build_system_prompt_for_subagent(skills_docs: List[SkillDoc]) -> str:
    parts = [
        AGENT_LEGACY_SUBAGENT_INSTRUCTION,
        "\n## 可用 Skill\n",
        *_skills_markdown_lines(skills_docs),
    ]
    return "\n".join(parts)
