from __future__ import annotations

import re
from pathlib import Path
from typing import List

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
        docs.append(SkillDoc(name=name, description=description, content=body, skill_dir=path.parent))
    return docs


AGENT_SYSTEM_INSTRUCTION = """你是一个 ChatBI 数据分析助手，帮助用户用自然语言查询业务数据、管理语义别名、生成经营决策建议。

## 工作方式
1. 理解用户的中文自然语言问题
2. 从可用 Skill 中选择最适合的技能
3. 调用 Skill 脚本执行确定性操作
4. 将结果整理为带图表和 KPI 卡片的回答

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


def build_system_prompt(skills_docs: List[SkillDoc]) -> str:
    """Build the full system prompt including available skills."""
    parts = [AGENT_SYSTEM_INSTRUCTION, "\n## 可用 Skill\n"]

    for doc in skills_docs:
        parts.append(f"### {doc.name}")
        parts.append(f"描述：{doc.description}")
        # Extract key sections from the skill content
        lines = doc.content.splitlines()
        in_section = None
        captured: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_section = stripped.lstrip("#").strip()
                captured = []
            elif in_section in ("Workflow", "工作流", "Commands", "常用命令", "Safety", "安全边界",
                                "Visualization Guidance", "可视化指导", "Supported Semantics", "支持的语义",
                                "Presentation Guidance"):
                if stripped:
                    captured.append(stripped)

        if captured:
            parts.append("```")
            parts.extend(captured)
            parts.append("```")

    return "\n".join(parts)
