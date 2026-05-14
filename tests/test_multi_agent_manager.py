"""Manager plan validation, LLM wiring, and subagent prompt boundaries."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.multi_agent_manager import call_manager_plan_llm, validate_and_order_tasks
from backend.agent.multi_agent_messages import build_subtask_messages
from backend.agent.prompt_builder import SkillDoc
from backend.agent.prompt_subagent import build_react_system_prompt_for_subagent


class MultiAgentManagerTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
