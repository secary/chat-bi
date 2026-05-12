from __future__ import annotations

import asyncio
import sys
import types
import unittest
from dataclasses import replace
from unittest.mock import AsyncMock, patch

litellm_stub = types.ModuleType("litellm")
litellm_stub.acompletion = None
sys.modules.setdefault("litellm", litellm_stub)
pymysql_stub = types.ModuleType("pymysql")
pymysql_stub.connect = None
sys.modules.setdefault("pymysql", pymysql_stub)
cursors_stub = types.ModuleType("pymysql.cursors")
cursors_stub.DictCursor = object
sys.modules.setdefault("pymysql.cursors", cursors_stub)

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
                            stream_chat_react([{"role": "user", "content": "你好"}], trace_id="t0")
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
                        self.assertTrue(any("助手" in str(e.get("content")) for e in texts))

        asyncio.run(run())

    def test_visual_first_skill_suppresses_finish_text_and_keeps_chart(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-chart-recommendation",
            "skill_args": [],
            "thought": "先做图表推荐",
        }
        second = {
            "action": "finish",
            "text": "下面是图表推荐说明文字。",
            "chart_plan": None,
            "kpi_cards": [],
        }
        script_result = {
            "kind": "chart_recommendation",
            "text": "推荐使用line图展示当前结果。",
            "data": {"rows": [{"月份": "2026-01", "销售额": "100"}]},
            "charts": [
                {
                    "xAxis": {"type": "category", "data": ["2026-01"]},
                    "yAxis": {"type": "value"},
                    "series": [{"type": "line", "data": [100]}],
                }
            ],
            "kpis": [],
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
                                [{"role": "user", "content": "请推荐图表"}],
                                trace_id="t3",
                            )
                        )
                        chart_events = [e for e in events if e.get("type") == "chart"]
                        text_events = [e for e in events if e.get("type") == "text"]
                        self.assertEqual(len(chart_events), 1)
                        self.assertEqual(chart_events[0]["content"]["series"][0]["type"], "line")
                        self.assertEqual(text_events, [])

        asyncio.run(run())

    def test_query_plus_decision_auto_runs_followup_advice(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-semantic-query",
            "skill_args": [],
            "thought": "先查询数据",
        }
        second = {
            "action": "finish",
            "text": "整理完成。",
            "chart_plan": None,
            "kpi_cards": [],
        }
        query_result = {
            "kind": "table",
            "text": "查询完成",
            "data": {"rows": [{"区域": "华东", "销售额": "1"}]},
        }
        advice_result = {
            "kind": "decision",
            "text": "建议继续深耕华东。",
            "data": {"advices": [{"title": "深耕华东"}]},
            "charts": [],
            "kpis": [],
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
                        with patch("backend.agent.react_followup.run_script") as mock_followup:
                            mock_run.return_value = query_result
                            mock_followup.return_value = advice_result
                            events = await _collect(
                                stream_chat_react(
                                    [
                                        {
                                            "role": "user",
                                            "content": "1-4月各区域销售额排行，并给出经营建议",
                                        }
                                    ],
                                    trace_id="t4",
                                )
                            )
                            self.assertEqual(mock_run.call_count, 1)
                            self.assertEqual(mock_followup.call_count, 1)
                            thinking = "\n".join(
                                str(e.get("content")) for e in events if e.get("type") == "thinking"
                            )
                            self.assertIn("Skill「chatbi-decision-advisor」", thinking)
                            self.assertTrue(
                                any("深耕华东" in str(e.get("content")) for e in events)
                            )

        asyncio.run(run())

    def test_invalid_finish_json_falls_back_to_last_skill_result(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-semantic-query",
            "skill_args": [],
            "thought": "需要查询",
        }
        script_result = {
            "kind": "table",
            "text": "查询完成",
            "chart_plan": {"chart_type": "line", "dimension": "月份", "metrics": ["销售额"]},
            "data": {"rows": [{"月份": "2026-01", "销售额": "100"}]},
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=6)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.side_effect = [first, ValueError("bad json")]
                    with patch("backend.agent.react_runner.run_script") as mock_run:
                        mock_run.return_value = script_result
                        events = await _collect(
                            stream_chat_react(
                                [{"role": "user", "content": "2026年销售额按月趋势"}],
                                trace_id="t5",
                            )
                        )
                        self.assertFalse([e for e in events if e.get("type") == "error"])
                        self.assertTrue([e for e in events if e.get("type") == "chart"])
                        self.assertEqual(events[-1].get("type"), "done")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
