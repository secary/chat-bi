from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from backend.agent.prompt_builder import parse_frontmatter


@dataclass(frozen=True)
class SkillAuditIssue:
    code: str
    level: str
    message: str


def list_skill_audits(
    skills_dir: Path,
    *,
    tests_dir: Path,
    enabled_slugs: set[str] | None = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    enabled = enabled_slugs or set()
    for skill_dir in sorted(path for path in skills_dir.iterdir() if path.is_dir()):
        rows.append(
            audit_skill_dir(skill_dir, tests_dir=tests_dir, enabled=skill_dir.name in enabled)
        )
    return rows


def audit_skill_dir(skill_dir: Path, *, tests_dir: Path, enabled: bool) -> Dict[str, Any]:
    skill_md = skill_dir / "SKILL.md"
    scripts_dir = skill_dir / "scripts"
    issues: List[SkillAuditIssue] = []
    name = skill_dir.name
    description = ""
    trigger_conditions: List[str] = []
    required_context: List[str] = []
    has_workflow = False
    has_safety = False

    if not skill_md.is_file():
        issues.append(
            SkillAuditIssue("SKILL_MD_MISSING", "error", "缺少 SKILL.md，无法进入技能候选集。")
        )
    else:
        text = skill_md.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        name = str(meta.get("name") or skill_dir.name)
        description = str(meta.get("description") or "").strip()
        trigger_conditions = _coerce_list(meta.get("trigger_conditions"))
        required_context = _coerce_list(meta.get("required_context"))
        has_workflow = "## Workflow" in body
        has_safety = "## Safety" in body

        if not description:
            issues.append(
                SkillAuditIssue(
                    "DESCRIPTION_MISSING", "warning", "缺少 description，新增 skill 的用途不明确。"
                )
            )
        if not trigger_conditions:
            issues.append(
                SkillAuditIssue(
                    "TRIGGER_CONDITIONS_MISSING",
                    "warning",
                    "缺少 trigger_conditions，Harness 难以判断何时选用。",
                )
            )
        if not required_context:
            issues.append(
                SkillAuditIssue(
                    "REQUIRED_CONTEXT_MISSING",
                    "warning",
                    "缺少 required_context，前审计难以判断必备上下文。",
                )
            )
        if not has_workflow:
            issues.append(
                SkillAuditIssue(
                    "WORKFLOW_SECTION_MISSING", "warning", "缺少 ## Workflow，执行步骤说明不完整。"
                )
            )
        if not has_safety:
            issues.append(
                SkillAuditIssue(
                    "SAFETY_SECTION_MISSING", "warning", "缺少 ## Safety，风险边界不清晰。"
                )
            )

    script_files = (
        sorted(path for path in scripts_dir.rglob("*.py")) if scripts_dir.is_dir() else []
    )
    if not script_files:
        issues.append(
            SkillAuditIssue(
                "SCRIPT_ENTRY_MISSING",
                "warning",
                "未发现 Python 脚本入口，运行时可能只能依赖文档说明。",
            )
        )

    matched_tests = _find_matching_tests(skill_dir.name, tests_dir)
    if not matched_tests:
        issues.append(
            SkillAuditIssue(
                "TEST_MISSING", "warning", "未发现对应测试文件，建议补 smoke test 或技能单测。"
            )
        )

    status = _status_for_issues(issues)
    return {
        "slug": skill_dir.name,
        "name": name,
        "description": description,
        "enabled": enabled,
        "status": status,
        "issue_count": len(issues),
        "issues": [issue.__dict__ for issue in issues],
        "script_count": len(script_files),
        "test_count": len(matched_tests),
        "has_skill_md": skill_md.is_file(),
        "has_workflow": has_workflow,
        "has_safety": has_safety,
        "trigger_count": len(trigger_conditions),
        "required_context_count": len(required_context),
    }


def _coerce_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _find_matching_tests(skill_slug: str, tests_dir: Path) -> List[str]:
    if not tests_dir.is_dir():
        return []
    candidates = {
        skill_slug.replace("-", "_"),
        skill_slug.replace("chatbi-", "").replace("-", "_"),
        skill_slug.replace("chatbi_", "").replace("-", "_"),
    }
    out: List[str] = []
    for path in tests_dir.glob("test_*.py"):
        stem = path.stem.lower()
        if any(token and token in stem for token in candidates):
            out.append(path.name)
    return sorted(set(out))


def _status_for_issues(issues: List[SkillAuditIssue]) -> str:
    levels = {issue.level for issue in issues}
    if "error" in levels:
        return "error"
    if "warning" in levels:
        return "warning"
    return "ok"
