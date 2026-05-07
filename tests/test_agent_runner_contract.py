from __future__ import annotations

import asyncio
import unittest
from dataclasses import replace
from unittest.mock import AsyncMock, patch

from backend.agent.runner import stream_chat
from backend.config import settings


async def _collect_events(messages: list) -> list:
    events = []
    async for event in stream_chat(messages, trace_id="test-contract"):
        events.append(event)
    return events


class AgentRunnerContractTest(unittest.TestCase):
    """Encodes acceptance: one LLM plan call and at most one skill run per user turn."""

    def test_single_plan_call_and_single_run_script_when_skill_selected(self):
        plan = {
            "skill": "chatbi-semantic-query",
            "skill_args": [],
            "chart_plan": None,
            "kpi_cards": None,
        }
        script_result = {"kind": "table", "text": "查询完成", "data": {"rows": []}}

        async def run():
            legacy = replace(settings, agent_react=False)
            with patch("backend.agent.runner.settings", legacy):
                with patch(
                    "backend.agent.runner.call_llm_for_plan", new_callable=AsyncMock
                ) as mock_llm:
                    mock_llm.return_value = plan
                    with patch("backend.agent.runner.run_script") as mock_run:
                        mock_run.return_value = script_result
                        events = await _collect_events(
                            [{"role": "user", "content": "1-4月销售额排行"}]
                        )
                        mock_llm.assert_awaited_once()
                        mock_run.assert_called_once()
                        types = [e.get("type") for e in events]
                        self.assertIn("done", types)

        asyncio.run(run())

    def test_small_talk_in_legacy_mode_skips_planner_and_skill(self):
        async def run():
            legacy = replace(settings, agent_react=False)
            with patch("backend.agent.runner.settings", legacy):
                with patch(
                    "backend.agent.runner.call_llm_for_plan", new_callable=AsyncMock
                ) as mock_llm:
                    with patch("backend.agent.runner.run_script") as mock_run:
                        events = await _collect_events(
                            [{"role": "user", "content": "谢谢"}]
                        )
                        mock_llm.assert_not_awaited()
                        mock_run.assert_not_called()
                        texts = [e for e in events if e.get("type") == "text"]
                        self.assertTrue(any("不客气" in str(e.get("content")) for e in texts))

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
