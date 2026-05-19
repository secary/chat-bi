from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HarnessState:
    trace_id: str
    user_text: str
    max_steps: int
    session_id: Optional[int] = None
    mode: str = "single"
    step_index: int = 0
    completed_skills: List[str] = field(default_factory=list)
    last_skill_name: Optional[str] = None
    last_result: Optional[Dict[str, Any]] = None
    rejections: List[str] = field(default_factory=list)
    consecutive_rejections: int = 0
    max_consecutive_rejections: int = 2

    def begin_step(self, step_index: int) -> None:
        self.step_index = step_index

    def record_skill(self, skill_name: str, result: Dict[str, Any]) -> None:
        self.completed_skills.append(skill_name)
        self.last_skill_name = skill_name
        self.last_result = result
        self.consecutive_rejections = 0

    def record_accept(self) -> None:
        self.consecutive_rejections = 0

    def record_rejection(self, reason: str) -> None:
        self.rejections.append(reason)
        self.consecutive_rejections += 1

    def should_stop_after_rejection(self) -> bool:
        return self.consecutive_rejections >= self.max_consecutive_rejections
