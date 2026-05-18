from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional, Sequence


@contextmanager
def _temp_sys_path(path: Path) -> Iterator[None]:
    path_str = str(path)
    sys.path.insert(0, path_str)
    try:
        yield
    finally:
        try:
            sys.path.remove(path_str)
        except ValueError:
            pass


def load_local_module(owner_file: str | Path, relative_path: str) -> Any:
    owner = Path(owner_file).resolve()
    target = (owner.parent / relative_path).resolve()
    module_name = f"_chatbi_skill_local_{abs(hash((str(owner), str(target))))}"
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载本地模块：{target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    with _temp_sys_path(target.parent):
        spec.loader.exec_module(module)
    return module


def call_local_runner(
    owner_file: str | Path,
    relative_path: str,
    runner_name: str,
    argv: Optional[Sequence[str]] = None,
    context: Any = None,
) -> Any:
    module = load_local_module(owner_file, relative_path)
    runner = getattr(module, runner_name, None)
    if not callable(runner):
        raise RuntimeError(f"模块未暴露 {runner_name}：{relative_path}")
    return runner(argv, context)


def resolve_db_config(context: Any, fallback: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    if context is not None:
        merged = getattr(context, "merged_db_config", None)
        if callable(merged):
            return dict(merged())
        raw = getattr(context, "db_config", None)
        if isinstance(raw, dict) and raw:
            return dict(raw)
    return dict(fallback or {})


def ensure_active(context: Any) -> None:
    if context is None:
        return
    checker = getattr(context, "check_active", None)
    if callable(checker):
        checker()


def context_cancelled(context: Any):
    if context is None:
        return lambda: False
    callback = getattr(context, "cancelled", None)
    if callable(callback):
        return callback
    return lambda: False


def context_timeout(context: Any, default: float = 30.0) -> float:
    if context is None:
        return default
    try:
        return float(getattr(context, "timeout_seconds", default))
    except (TypeError, ValueError):
        return default
