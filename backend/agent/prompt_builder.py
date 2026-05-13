from __future__ import annotations

import re
from pathlib import Path
from typing import List, Sequence


class SkillDoc:
    def __init__(self, name: str, description: str, content: str, skill_dir: Path):
        self.name = name
        self.description = description
        self.content = content
        self.skill_dir = skill_dir


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML-like frontmatter and body from a markdown file."""
    metadata: dict[str, str] = {}
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if match:
        for line in match.group(1).splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                metadata[key.strip()] = val.strip().strip('"')
        body = match.group(2).strip()
    else:
        body = text.strip()
    return metadata, body


def scan_skills(skills_dir: Path) -> List[SkillDoc]:
    """Scan skills/*/SKILL.md and return SkillDoc list."""
    docs: List[SkillDoc] = []
    pattern = str(skills_dir / "*" / "SKILL.md")
    from glob import glob

    for path_str in glob(pattern):
        path = Path(path_str)
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        name = meta.get("name", path.parent.name)
        description = meta.get("description", "")
        docs.append(
            SkillDoc(name=name, description=description, content=body, skill_dir=path.parent)
        )
    return docs


def scan_skills_enabled(skills_dir: Path) -> List[SkillDoc]:
    """Like scan_skills but excludes skills disabled in skill_registry."""
    from backend.skill_registry_repo import disabled_slugs

    blocked = disabled_slugs()
    return [s for s in scan_skills(skills_dir) if s.skill_dir.name not in blocked]


def scan_skills_for_slugs(skills_dir: Path, slugs: Sequence[str]) -> List[SkillDoc]:
    """Enabled skills whose directory name is in slugs (order preserved by slug list)."""
    by_name = {d.skill_dir.name: d for d in scan_skills_enabled(skills_dir)}
    out: List[SkillDoc] = []
    for name in slugs:
        key = str(name).strip()
        if key in by_name:
            out.append(by_name[key])
    return out


# Use for one round LLM search. (Not in used.)
AGENT_SYSTEM_INSTRUCTION = """你是一个 ChatBI 数据分析助手，帮助用户用自然语言查询业务数据、管理语义别名、生成经营决策建议。

## 用户上传的数据文件（优先于演示库查询）
- 若对话中出现上传文件路径（通常包含 `/tmp/chatbi-uploads/`），且用户正在对该 CSV/XLSX 或附件做结构校验、内容分析、画图或字段说明，必须使用 `chatbi-file-ingestion`；该技能会先校验是否匹配 `sales_order` / `customer_profile`，匹配则直接按业务表分析，不匹配则回退到 Pandas 通用分析；需要输出图表或完整表格行时请传入 `--include-rows`。不要用 `chatbi-semantic-query` 查询演示数据库来代替用户文件。
- 仅当用户明确只要查询演示库业务表、且与上传文件无关时，才使用 `chatbi-semantic-query`。

## 工作方式
1. 理解用户的中文自然语言问题
2. 从可用 Skill 中选择最适合的技能
3. 调用 Skill 脚本执行确定性操作
4. 将结果整理为带图表和 KPI 卡片的回答

## 自然语言触发规则
- 用户只要在问业务数据、排行、趋势、对比、汇总或指标值，就选择 `chatbi-semantic-query`
- 用户若在问“当前数据库有哪些表”“业务库概览”“表清单”“schema/字段概述”“有哪些数据可查”，优先选择 `chatbi-database-overview`
- 短句也必须触发查询，例如 `1-4月销售额排行`、`各区域销售额`、`华东4月毛利率`
- 用户若明确在问“适合什么图表”“推荐什么图”“这个结果怎么可视化”，优先选择 `chatbi-chart-recommendation`
- 用户若明确在问“生成看板”“仪表盘怎么排版”“dashboard 怎么编排”，优先选择 `chatbi-dashboard-orchestration`
- 不要把用户没有写出的年份、区域、指标或维度自行改写成别的值
- 给 `chatbi-semantic-query` 的第一个参数优先使用用户原始问题，让脚本自己补默认年份和默认排行维度
- 演示数据默认年份是 2026；不要臆造 2024 等不存在的数据年份

## 输出要求
你的回答必须是 JSON 格式，包含以下字段：
- `skill`: 选择的 Skill 名称，如果不需要调用 Skill 则为 null
- `skill_args`: 传递给 Skill 脚本的参数列表（字符串数组），如果不需要调用则为 []
- `steps`: 思考步骤数组，每个步骤是一个字符串
- `text`: 对用户的回答文本（支持 Markdown）
- `chart_plan`: 图表计划对象，如果不需图表则为 null
- `kpi_cards`: KPI 卡片数组，如果不需则为 []

chart_plan 格式：
```json
{
  "chart_type": "bar|line|pie",
  "title": "图表标题",
  "dimension": "维度名称",
  "metrics": ["指标名称"],
  "highlight": {"mode": "min|max", "field": "指标名称"}
}
```

KPI 卡片格式：
```json
{
  "label": "指标名称",
  "value": "数值",
  "unit": "单位",
  "status": "success|warning|danger|neutral"
}
```

## 可视化规则
- 分类对比、排名 → 柱状图 (bar)
- 时间趋势 → 折线图 (line)
- 构成/占比 → 饼图 (pie)
- 单值指标汇总 → KPI 卡片
- 目标完成率高 → KPI 用 success，中等 → warning，低 → danger

## 约束
- 只从可用 Skill 中选择，不要编造不存在的技能
- 不要直接连接数据库，始终通过 Skill 脚本操作
- 不要编造数据，所有结果来自脚本执行
"""

# LLM return action: call_skill or finish.
# Call skill will return skill_args, thought, and skill.
# Finish will return text, chart_plan, and kpi_cards.
AGENT_REACT_INSTRUCTION = """你是一个 ChatBI 数据分析助手，帮助用户用自然语言查询业务数据、管理语义别名、生成经营决策建议。

## 用户上传的数据文件（优先于演示库查询）
- 若对话中出现上传文件路径（通常包含 `/tmp/chatbi-uploads/`），且用户继续对该 CSV/XLSX 或附件做分析、汇总、画图或展示字段，必须使用 `chatbi-file-ingestion`；该技能会先校验是否匹配 `sales_order` / `customer_profile`，匹配则直接按业务表分析，不匹配则回退到 Pandas 通用分析；需要行数据或图表时在 skill_args 中传入路径并附加 `--include-rows`。不要用 `chatbi-semantic-query` 查询演示数据库来代替用户文件。
- 仅当用户明确只要查询演示库业务表、且与上传文件无关时，才使用 `chatbi-semantic-query`。

## ReAct 工作方式
系统在对话中循环：你输出 JSON 决策 → 可能执行 Skill → 将 Observation 摘要追加到对话 → 你再输出下一步 JSON，直到 `action` 为 `finish`。
每一轮只输出**一个** JSON 对象，不要用 Markdown 代码围栏包裹。

## 自然语言触发规则
- 用户只要在问业务数据、排行、趋势、对比、汇总或指标值，就选择 `chatbi-semantic-query`
- 用户若在问“当前数据库有哪些表”“业务库概览”“表清单”“schema/字段概述”“有哪些数据可查”，优先选择 `chatbi-database-overview`
- 短句也必须触发查询，例如 `1-4月销售额排行`、`各区域销售额`、`华东4月毛利率`
- 用户若明确在问“适合什么图表”“推荐什么图”“这个结果怎么可视化”，优先选择 `chatbi-chart-recommendation`
- 用户若明确在问“生成看板”“仪表盘怎么排版”“dashboard 怎么编排”，优先选择 `chatbi-dashboard-orchestration`
- 不要把用户没有写出的年份、区域、指标或维度自行改写成别的值
- 给 `chatbi-semantic-query` 的第一个参数优先使用用户原始问题，让脚本自己补默认年份和默认排行维度
- 演示数据默认年份是 2026；不要臆造 2024 等不存在的数据年份

## 每一步 JSON 字段
- `action`（必填）：`call_skill` 或 `finish`
- `thought`（可选）：一句中文简要思考

当 `action` 为 `call_skill` 时必填：
- `skill`：Skill 名称
- `skill_args`：字符串数组；语义查询/决策建议通常把**用户原问题**作为第一参数

当 `action` 为 `finish` 时必填：
- `text`：对用户的 Markdown 回答
- `chart_plan`：图表计划对象或 null
- `kpi_cards`：KPI 数组或 []

chart_plan / KPI 格式与单次模式相同；仅在 `finish` 步填写，用于渲染最后一次相关工具结果（若有多轮工具，以 Observation 中的事实为准）。

## 可视化规则
- 分类对比、排名 → 柱状图 (bar)
- 时间趋势 → 折线图 (line)
- 构成/占比 → 饼图 (pie)
- 单值指标汇总 → KPI 卡片

## 约束
- 收到 Observation 后必须基于其中的数值与事实作答，禁止编造数据。
- 若只需一次 Skill：第一轮 `call_skill`，下一轮必须 `finish`。
- 每轮最多安排一次 `call_skill`；需要多个 Skill 时请分多轮输出。
- 只从可用 Skill 中选择；不要直接连接数据库。
"""


# Turn skilldoc into markdown format and insert into system prompt.
# show llm what skills can be used.
def _skills_markdown_lines(skills_docs: Sequence[SkillDoc]) -> List[str]:
    parts: List[str] = []
    for doc in skills_docs:
        parts.append(f"### {doc.name}")
        parts.append(f"描述：{doc.description}")
        lines = doc.content.splitlines()
        in_section = None
        captured: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_section = stripped.lstrip("#").strip()
                captured = []
            elif in_section in (
                "Workflow",
                "工作流",
                "Commands",
                "常用命令",
                "Safety",
                "安全边界",
                "Visualization Guidance",
                "可视化指导",
                "Supported Semantics",
                "支持的语义",
                "Presentation Guidance",
            ):
                if stripped:
                    captured.append(stripped)

        if captured:
            parts.append("```")
            parts.extend(captured)
            parts.append("```")
    return parts


# used in one round llm search(Not in used.)
def build_system_prompt(skills_docs: List[SkillDoc]) -> str:
    """Build the full system prompt including available skills (single-shot plan)."""
    parts = [
        AGENT_SYSTEM_INSTRUCTION,
        "\n## 可用 Skill\n",
        *_skills_markdown_lines(skills_docs),
    ]
    return "\n".join(parts)


# role + system prompt + skills_markdown_lines
def build_react_system_prompt(skills_docs: List[SkillDoc]) -> str:
    """System prompt for multi-step ReAct (multiple JSON rounds)."""
    parts = [
        AGENT_REACT_INSTRUCTION,
        "\n## 可用 Skill\n",
        *_skills_markdown_lines(skills_docs),
    ]
    return "\n".join(parts)
