from __future__ import annotations

import importlib.util
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, Optional, Sequence

from backend.config import settings


class SkillRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillContext:
    trace_id: str = ""
    db_config: Optional[Dict[str, str]] = None
    db_overrides: Optional[Dict[str, str]] = None
    cancelled: Callable[[], bool] = field(default=lambda: False, repr=False)
    timeout_seconds: float = 60.0
    max_result_rows: int = 2000
    started_at: float = field(default_factory=time.monotonic, repr=False)

    def base_db_config(self) -> Dict[str, str]:
        return {
            "host": settings.db_host,
            "port": settings.db_port,
            "user": settings.db_user,
            "password": settings.db_password,
            "database": settings.db_name,
        }

    def merged_db_config(self) -> Dict[str, str]:
        base = dict(self.db_config or self.base_db_config())
        if self.db_overrides:
            base.update(self.db_overrides)
        return base

    def env(self) -> Dict[str, str]:
        db = self.merged_db_config()
        base = {
            "CHATBI_DB_HOST": str(db["host"]),
            "CHATBI_DB_PORT": str(db["port"]),
            "CHATBI_DB_USER": str(db["user"]),
            "CHATBI_DB_PASSWORD": str(db["password"]),
            "CHATBI_DB_NAME": str(db["database"]),
            "CHATBI_TRACE_ID": self.trace_id,
        }
        return base

    def check_active(self) -> None:
        if self.cancelled():
            raise SkillRuntimeError("用户中止了查询")
        if self.timeout_seconds > 0 and time.monotonic() - self.started_at > self.timeout_seconds:
            raise SkillRuntimeError("技能执行超时")


@contextmanager
def activated_skill_env(context: SkillContext) -> Iterator[None]:
    updates = context.env()
    previous = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            os.environ[key] = value
        yield
    finally:
        for key, old_value in previous.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


def load_skill_module(module_path: Path, context: SkillContext) -> Any:
    context.check_active()
    module_name = f"_chatbi_skill_{abs(hash((str(module_path), id(context))))}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载技能模块：{module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    with activated_skill_env(context):
        spec.loader.exec_module(module)
    return module


def _limit_skill_result_rows(result: Dict[str, Any], max_rows: int) -> Dict[str, Any]:
    if max_rows <= 0:
        return result
    data = result.get("data")
    if not isinstance(data, dict):
        return result
    rows = data.get("rows")
    if not isinstance(rows, list) or len(rows) <= max_rows:
        return result
    limited = dict(result)
    limited_data = dict(data)
    limited_data["rows"] = rows[:max_rows]
    limited_data["result_truncated"] = True
    limited_data["original_row_count"] = len(rows)
    limited["data"] = limited_data
    return limited


def run_skill_api(skill_dir: Path, args: Sequence[str], context: SkillContext) -> Dict[str, Any]:
    context.check_active()
    api_path = skill_dir / "api.py"
    if not api_path.is_file():
        raise SkillRuntimeError(f"技能未提供 api.py：{skill_dir}")
    try:
        module = load_skill_module(api_path, context)
        runner = getattr(module, "run", None)
        if not callable(runner):
            raise SkillRuntimeError(f"技能 API 未暴露 run：{api_path}")
        with activated_skill_env(context):
            result = runner(list(args), context)
        context.check_active()
    except SkillRuntimeError:
        raise
    except Exception as exc:
        raise SkillRuntimeError(f"技能执行失败：{type(exc).__name__}: {exc}") from exc
    if not isinstance(result, dict):
        raise SkillRuntimeError(f"技能返回值必须是 dict：{api_path}")
    return _limit_skill_result_rows(result, context.max_result_rows)
