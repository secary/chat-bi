from __future__ import annotations

import asyncio
import json
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

from backend.agent.react_runner import _auto_analysis_args, stream_chat_react
from backend.agent.prompt_builder import SkillDoc, scan_skills_enabled
from backend.config import settings


def _skill_docs_without_validator_requires() -> list[SkillDoc]:
    docs = scan_skills_enabled(settings.skills_dir)
    return [
        SkillDoc(
            d.name,
            d.description,
            d.content,
            d.skill_dir,
            trigger_conditions=d.trigger_conditions,
            when_not_to_use=d.when_not_to_use,
            required_context=d.required_context,
            validator_requires=[],
        )
        for d in docs
    ]


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
                                skill_docs=_skill_docs_without_validator_requires(),
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

    def test_chart_recommendation_receives_rows_from_previous_skill_result(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-file-ingestion",
            "skill_args": ["请分析上传文件并画图"],
            "thought": "先读取上传文件",
        }
        second = {
            "action": "call_skill",
            "skill": "chatbi-chart-recommendation",
            "skill_args": ["请生成图表"],
            "thought": "基于结果推荐图表",
        }
        third = {
            "action": "finish",
            "text": "图表已生成。",
            "chart_plan": None,
            "kpi_cards": [],
        }
        file_result = {
            "kind": "file_ingestion",
            "text": "文件读取完成",
            "data": {
                "rows": [
                    {"区域": "华东", "销售额": "613000"},
                    {"区域": "华南", "销售额": "402000"},
                ]
            },
        }
        chart_result = {
            "kind": "chart_recommendation",
            "text": "推荐使用bar图展示当前结果。",
            "data": {"recommendation": {"status": "ready", "recommended_chart": "bar"}},
            "charts": [
                {
                    "xAxis": {"type": "category", "data": ["华东", "华南"]},
                    "yAxis": {"type": "value"},
                    "series": [{"type": "bar", "data": [613000, 402000]}],
                }
            ],
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=6)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.side_effect = [first, second, third]
                    seen_args = []

                    def _run_script(skill_doc, args, **kwargs):
                        seen_args.append((skill_doc.name, args))
                        if skill_doc.name == "chatbi-file-ingestion":
                            return file_result
                        if skill_doc.name == "chatbi-chart-recommendation":
                            return chart_result
                        raise AssertionError(f"unexpected skill {skill_doc.name}")

                    with patch("backend.agent.react_runner.run_script", side_effect=_run_script):
                        events = await _collect(
                            stream_chat_react(
                                [
                                    {
                                        "role": "user",
                                        "content": (
                                            "请根据我上传的文件 /tmp/chatbi-uploads/sample.csv "
                                            "生成可视化图表"
                                        ),
                                    }
                                ],
                                trace_id="t6",
                            )
                        )
                        chart_call = next(
                            args
                            for name, args in seen_args
                            if name == "chatbi-chart-recommendation"
                        )
                        self.assertEqual(len(chart_call), 1)
                        self.assertIn('"rows"', chart_call[0])
                        self.assertIn('"question"', chart_call[0])
                        self.assertTrue([e for e in events if e.get("type") == "chart"])

        asyncio.run(run())

    def test_upload_context_rewrites_semantic_query_to_chart_recommendation(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-file-ingestion",
            "skill_args": ["请分析上传文件并画图"],
            "thought": "先读取上传文件",
        }
        second = {
            "action": "call_skill",
            "skill": "chatbi-semantic-query",
            "skill_args": ["生成可视化图表"],
            "thought": "继续处理",
        }
        third = {
            "action": "finish",
            "text": "图表已生成。",
            "chart_plan": None,
            "kpi_cards": [],
        }
        file_result = {
            "kind": "file_ingestion",
            "text": "文件读取完成",
            "data": {
                "rows": [
                    {"区域": "华东", "销售额": "613000"},
                    {"区域": "华南", "销售额": "402000"},
                ]
            },
        }
        chart_result = {
            "kind": "chart_recommendation",
            "text": "推荐使用bar图展示当前结果。",
            "data": {"recommendation": {"status": "ready", "recommended_chart": "bar"}},
            "charts": [
                {
                    "xAxis": {"type": "category", "data": ["华东", "华南"]},
                    "yAxis": {"type": "value"},
                    "series": [{"type": "bar", "data": [613000, 402000]}],
                }
            ],
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=6)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.side_effect = [first, second, third]
                    seen = []

                    def _run_script(skill_doc, args, **kwargs):
                        seen.append(skill_doc.name)
                        if skill_doc.name == "chatbi-file-ingestion":
                            return file_result
                        if skill_doc.name == "chatbi-chart-recommendation":
                            return chart_result
                        raise AssertionError(f"unexpected skill {skill_doc.name}")

                    with patch("backend.agent.react_runner.run_script", side_effect=_run_script):
                        events = await _collect(
                            stream_chat_react(
                                [
                                    {
                                        "role": "user",
                                        "content": "请读取我上传的文件 /tmp/chatbi-uploads/sample.csv 然后生成可视化图表",
                                    }
                                ],
                                trace_id="t7",
                            )
                        )
                        self.assertEqual(
                            seen, ["chatbi-file-ingestion", "chatbi-chart-recommendation"]
                        )
                        self.assertTrue([e for e in events if e.get("type") == "chart"])

        asyncio.run(run())

    def test_repeated_file_ingestion_is_short_circuited_after_first_result(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-file-ingestion",
            "skill_args": ["请分析上传文件"],
            "thought": "先读取文件",
        }
        second = {
            "action": "call_skill",
            "skill": "chatbi-file-ingestion",
            "skill_args": ["继续分析上传文件"],
            "thought": "再读取一次文件",
        }
        file_result = {
            "kind": "file_ingestion",
            "text": "文件读取完成",
            "data": {
                "file": "/tmp/chatbi-uploads/sample.csv",
                "analysis_mode": "profile_only",
                "preview_rows": [{"门店": "南京东路店", "城市": "上海"}],
                "rows": [{"门店": "南京东路店", "城市": "上海"}],
            },
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=6)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.side_effect = [first, second]
                    seen = []

                    def _run_script(skill_doc, args, **kwargs):
                        seen.append((skill_doc.name, args))
                        return file_result

                    with patch("backend.agent.react_runner.run_script", side_effect=_run_script):
                        events = await _collect(
                            stream_chat_react(
                                [
                                    {
                                        "role": "user",
                                        "content": "请读取我上传的文件 /tmp/chatbi-uploads/sample.csv 并分析逾期贷款分布",
                                    }
                                ],
                                trace_id="t8",
                            )
                        )
                        self.assertEqual(
                            seen,
                            [
                                (
                                    "chatbi-file-ingestion",
                                    [
                                        "/tmp/chatbi-uploads/sample.csv",
                                        "--question",
                                        "请读取我上传的文件 /tmp/chatbi-uploads/sample.csv 并分析逾期贷款分布",
                                        "--include-rows",
                                    ],
                                )
                            ],
                        )
                        thinking = " ".join(
                            event.get("content", "")
                            for event in events
                            if event.get("type") == "thinking"
                        )
                        self.assertIn("文件已解析完成，正在整理结果", thinking)
                        self.assertEqual(events[-1].get("type"), "done")

        asyncio.run(run())

    def test_auto_analysis_receives_rows_via_input_file(self):
        rows = [{"门店": "南京东路店", "销售额": "100"}]
        args = _auto_analysis_args("请推荐指标", [], {"data": {"rows": rows}})

        self.assertEqual(args[0], "--input-file")
        with open(args[1], encoding="utf-8") as handle:
            payload = json.load(handle)
        self.assertEqual(payload["rows"], rows)
        self.assertEqual(payload["question"], "请推荐指标")

    def test_auto_analysis_structured_result_stops_react_loop(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-auto-analysis",
            "skill_args": ["请推荐指标"],
            "thought": "生成可确认的指标方案",
        }
        file_result = {
            "kind": "file_ingestion",
            "text": "文件读取完成",
            "data": {
                "file": "/tmp/chatbi-uploads/sample.csv",
                "rows": [{"门店": "南京东路店", "销售额": "100"}],
            },
        }
        auto_result = {
            "kind": "auto_analysis",
            "text": "请确认是否采纳以下指标。",
            "data": {
                "status": "need_confirmation",
                "analysis_proposal": {
                    "markdown": "### 建议指标\n- 销售额趋势",
                    "proposed_metrics": [],
                },
            },
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=6)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.side_effect = [first, first]

                    def _run_script(skill_doc, args, **kwargs):
                        if skill_doc.name == "chatbi-file-ingestion":
                            return file_result
                        if skill_doc.name == "chatbi-auto-analysis":
                            return auto_result
                        raise AssertionError(skill_doc.name)

                    with patch(
                        "backend.agent.react_runner.run_script",
                        side_effect=_run_script,
                    ):
                        events = await _collect(
                            stream_chat_react(
                                [
                                    {
                                        "role": "user",
                                        "content": (
                                            "请分析上传文件 /tmp/chatbi-uploads/sample.csv "
                                            "适合哪些指标"
                                        ),
                                    }
                                ],
                                trace_id="t9",
                            )
                        )
                        self.assertEqual(mock_llm.await_count, 2)
                        self.assertTrue([e for e in events if e.get("type") == "analysis_proposal"])
                        self.assertEqual(events[-1].get("type"), "done")

        asyncio.run(run())

    def test_validation_rejects_chart_without_prior_observation(self):
        first = {
            "action": "call_skill",
            "skill": "chatbi-chart-recommendation",
            "skill_args": ["请推荐图表"],
            "thought": "直接推荐",
        }

        async def run():
            cfg = replace(settings, agent_react=True, agent_max_steps=3)
            with patch("backend.agent.react_runner.settings", cfg):
                with patch(
                    "backend.agent.react_runner.call_llm_for_react_step",
                    new_callable=AsyncMock,
                ) as mock_llm:
                    mock_llm.return_value = first
                    with patch("backend.agent.react_runner.run_script") as mock_run:
                        events = await _collect(
                            stream_chat_react(
                                [{"role": "user", "content": "请推荐图表"}],
                                trace_id="t-val",
                            )
                        )
                        mock_run.assert_not_called()
                        thinking = " ".join(
                            e.get("content", "") for e in events if e.get("type") == "thinking"
                        )
                        self.assertIn("技能校验未通过", thinking)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
