"""Manager plan validation, LLM wiring, and subagent prompt boundaries."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.multi_agent_manager import (
    _manager_context_hints,
    call_manager_plan_llm,
    validate_and_order_tasks,
)
from backend.agent.multi_agent_messages import build_subtask_messages
from backend.agent.prompt_builder import SkillDoc
from backend.agent.prompt_subagent import build_react_system_prompt_for_subagent


class MultiAgentManagerTest(unittest.TestCase):
    def test_manager_context_hints_upload_and_adopt(self) -> None:
        msgs = [
            {"role": "user", "content": "请分析 /tmp/chatbi-uploads/session_1.csv"},
            {"role": "assistant", "content": "上传表分析建议：…"},
            {"role": "user", "content": "采纳 sales_trend_monthly"},
        ]
        h = _manager_context_hints(msgs)
        self.assertIn("upload_analyst", h)
        self.assertIn("demo_query", h)
        self.assertIn("采纳", h)

    def test_manager_context_hints_empty_without_cues(self) -> None:
        msgs = [{"role": "user", "content": "1-4 月各区域销售额排行"}]
        self.assertEqual(_manager_context_hints(msgs), "")

    def test_validate_rejects_over_cap(self) -> None:
        raw = [
            {"agent_id": "a", "handoff_instruction": "one", "depends_on": None},
            {"agent_id": "b", "handoff_instruction": "two", "depends_on": None},
        ]
        self.assertIsNone(validate_and_order_tasks(raw, 1))

    def test_validate_dependency_order(self) -> None:
        raw = [
            {"agent_id": "a", "handoff_instruction": "first", "depends_on": None},
            {"agent_id": "b", "handoff_instruction": "second", "depends_on": 0},
        ]

        def fake_docs(_aid: str):
            return [MagicMock()]

        with patch(
            "backend.agent.multi_agent_manager.list_registry_agent_ids",
            return_value=["a", "b"],
        ):
            with patch(
                "backend.agent.multi_agent_manager.skills_for_agent",
                side_effect=fake_docs,
            ):
                ordered = validate_and_order_tasks(raw, 8)
                self.assertIsNotNone(ordered)
                assert ordered is not None
                self.assertEqual([x[0] for x in ordered], [0, 1])

    def test_validate_rejects_cycle(self) -> None:
        raw = [
            {"agent_id": "a", "handoff_instruction": "x", "depends_on": 1},
            {"agent_id": "b", "handoff_instruction": "y", "depends_on": 0},
        ]

        def fake_docs(_aid: str):
            return [MagicMock()]

        with patch(
            "backend.agent.multi_agent_manager.list_registry_agent_ids",
            return_value=["a", "b"],
        ):
            with patch(
                "backend.agent.multi_agent_manager.skills_for_agent",
                side_effect=fake_docs,
            ):
                self.assertIsNone(validate_and_order_tasks(raw, 8))

    def test_call_manager_plan_llm_returns_json(self) -> None:
        payload = {
            "user_intent_summary": "问数",
            "decomposition_reason": "单任务",
            "finalize_after_this_batch": True,
            "tasks": [
                {
                    "agent_id": "demo_query",
                    "handoff_instruction": "查询演示库销售额",
                    "depends_on": None,
                }
            ],
        }

        async def run():
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
            with patch(
                "backend.agent.multi_agent_manager.chatbi_acompletion",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ):
                got = await call_manager_plan_llm(
                    [{"role": "user", "content": "1-4月销售额"}], trace_id="t1"
                )
                self.assertEqual(got.get("tasks", [{}])[0].get("agent_id"), "demo_query")

        import asyncio

        asyncio.run(run())

    def test_call_manager_plan_llm_injects_context_hints(self) -> None:
        payload = {
            "user_intent_summary": "采纳上传指标",
            "decomposition_reason": "test",
            "finalize_after_this_batch": True,
            "tasks": [
                {
                    "agent_id": "upload_analyst",
                    "handoff_instruction": "执行采纳",
                    "depends_on": None,
                }
            ],
        }
        captured: dict[str, str] = {}

        async def run():
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]

            async def _acompletion(**kwargs):
                msgs = kwargs.get("messages") or []
                captured["last_user"] = str(msgs[-1].get("content") or "")
                return mock_resp

            with patch(
                "backend.agent.multi_agent_manager.chatbi_acompletion",
                new_callable=AsyncMock,
                side_effect=_acompletion,
            ):
                await call_manager_plan_llm(
                    [
                        {"role": "user", "content": "读 /tmp/chatbi-uploads/a.csv"},
                        {"role": "assistant", "content": "上传表分析建议 …"},
                        {"role": "user", "content": "采纳 m1"},
                    ],
                    trace_id="t-hints",
                )

        import asyncio

        asyncio.run(run())
        self.assertIn("系统自动检测", captured["last_user"])
        self.assertIn("upload_analyst", captured["last_user"])

    def test_subagent_react_prompt_omits_unassigned_skills(self) -> None:
        doc = SkillDoc(
            name="chatbi-semantic-query",
            description="语义查询",
            content="## Workflow\nnoop\n",
            skill_dir=Path("skills") / "chatbi-semantic-query",
        )
        text = build_react_system_prompt_for_subagent([doc])
        self.assertIn("chatbi-semantic-query", text)
        self.assertNotIn("chatbi-file-ingestion", text)

    def test_build_subtask_messages_preserves_prior_user(self) -> None:
        msgs = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
            {"role": "user", "content": "original ask"},
        ]
        out = build_subtask_messages(msgs, "do the thing", prior_observation="prev summary")
        self.assertTrue(out[-1]["content"].startswith("【Manager 交办】"))
        self.assertIn("original ask", out[-1]["content"])
        self.assertIn("prev summary", out[-1]["content"])

    def test_validate_empty_when_allowed(self) -> None:
        self.assertEqual(validate_and_order_tasks([], 4, allow_empty=True), [])

    def test_validate_empty_when_not_allowed(self) -> None:
        self.assertIsNone(validate_and_order_tasks([], 4, allow_empty=False))


if __name__ == "__main__":
    unittest.main()
