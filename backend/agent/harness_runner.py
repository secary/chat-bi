from __future__ import annotations

import json
from typing import Any, Dict

from backend.agent.harness_policy import HarnessPolicyDecision
from backend.agent.harness_schema import HarnessValidation


def rejection_observation(
    validation: HarnessValidation | None, policy: HarnessPolicyDecision | None
) -> str:
    if validation and not validation.ok:
        return _obs("schema_rejected", validation.reason)
    if policy and not policy.ok:
        return _obs("policy_rejected", policy.reason)
    return _obs("unknown_rejected", "未知 Harness 拒绝。")


def _obs(category: str, reason: str, extra: Dict[str, Any] | None = None) -> str:
    payload: Dict[str, Any] = {"ok": False, "category": category, "reason": reason}
    if extra:
        payload.update(extra)
    return json.dumps(payload, ensure_ascii=False)
