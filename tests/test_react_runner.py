from __future__ import annotations

import asyncio
import unittest
from dataclasses import replace
from unittest.mock import AsyncMock, patch

from backend.agent.react_runner import stream_chat_react
from backend.config import settings


async def _collect(events_gen):
    out = []
    async for e in events_gen:
        out.append(e)
    return out


class ReactRunnerTest(unittest.TestCase):
    def test_small_talk_skips_llm_and_skill(self):
        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=4)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    with patch("backend.agent.react_runner.run_script") as mock_run:
                        events = await _collect(
                            stream_chat_react(
                                [{"role": "user", "content": "你好"}], trace_id="t0"
                            )
                        )
                        mock_llm.assert_not_awaited()
                        mock_run.assert_not_called()
                        texts = [e for e in events if e.get("type") == "text"]
                        self.assertTrue(any("您好" in str(e.get("content")) for e in texts))

        asyncio.run(run())

    def test_call_skill_then_finish_uses_two_llm_rounds_and_one_script(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-semantic-query",
            "skill_args": [],
            "thought": "需要查询",
        }
        second = {
            "action": "finish",
            "text": "根据数据，结论如下。",
            "chart_plan": None,
            "kpi_cards": [],
        }
        script_result = {
            "kind": "table",
            "text": "查询完成",
            "data": {"rows": [{"区域": "华东", "销售额": "1"}]},
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=6)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.side_effect = [first, second]
                    with patch("backend.agent.react_runner.run_script") as mock_run:
                        mock_run.return_value = script_result
                        events = await _collect(
                            stream_chat_react(
                                [{"role": "user", "content": "1-4月销售额"}],
                                trace_id="t1",
                            )
                        )
                        self.assertEqual(mock_llm.await_count, 2)
                        mock_run.assert_called_once()
                        types = [e.get("type") for e in events]
                        self.assertIn("done", types)
                        self.assertIn("text", types)

        asyncio.run(run())

    def test_finish_without_skill_emits_text_only(self):
        plan = {
            "action": "finish",
            "text": "你好，我是助手。",
            "chart_plan": None,
            "kpi_cards": [],
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=4)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.return_value = plan
                    with patch("backend.agent.react_runner.run_script") as mock_run:
                        events = await _collect(
                            stream_chat_react(
                                [{"role": "user", "content": "请总结一下"}], trace_id="t2"
                            )
                        )
                        mock_llm.assert_awaited_once()
                        mock_run.assert_not_called()
                        texts = [e for e in events if e.get("type") == "text"]
                        self.assertTrue(
                            any("助手" in str(e.get("content")) for e in texts)
                        )

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
