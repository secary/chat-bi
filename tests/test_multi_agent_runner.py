from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.multi_agent_runner import stream_chat_multi_agent


class MultiAgentRunnerHarnessTest(unittest.TestCase):
    def test_multi_agent_logs_harness_events_for_specialist_round(self) -> None:
        async def _run() -> None:
            async def fake_specialist(*args, **kwargs):
                sink = kwargs["result_sink"]
                sink["last_result"] = {
                    "kind": "table",
                    "text": "sales ok",
                    "data": {
                        "rows": [{"区域": "华东", "销售额": 100}],
                        "sql": "SELECT SUM(sales_amount) FROM sales_order",
                        "plan_trace": [
                            "识别指标：销售额",
                            "生成 SQL：SELECT SUM(sales_amount) FROM sales_order",
                        ],
                    },
                }
                sink["last_skill_name"] = "chatbi-semantic-query"
                sink["skill_executions"] = [
                    {
                        "skill": "chatbi-semantic-query",
                        "result": sink["last_result"],
                        "observation": "查到 1 行结果。",
                        "step": 1,
                    }
                ]
                yield {"type": "thinking", "content": "开始查询"}

            async def fake_stream_result_events(*args, **kwargs):
                yield {"type": "text", "content": "最终结果"}

            events = []
            with (
                patch(
                    "backend.agent.multi_agent_runner.validate_and_order_tasks",
                    return_value=[
                        (
                            0,
                            {
                                "agent_id": "demo_query",
                                "handoff_instruction": "查询 1-4 月各区域销售额",
                                "depends_on": None,
                            },
                        )
                    ],
                ),
                patch(
                    "backend.agent.multi_agent_runner.skills_for_agent",
                    return_value=[MagicMock()],
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_label",
                    return_value="问数专线",
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_role_prompt",
                    return_value="你是问数专线",
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_specialist",
                    side_effect=fake_specialist,
                ),
                patch(
                    "backend.agent.multi_agent_runner.call_summarize_llm",
                    new_callable=AsyncMock,
                    return_value={"text": "最终结果"},
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_result_events",
                    side_effect=fake_stream_result_events,
                ),
                patch(
                    "backend.agent.abort_state.is_aborted",
                    return_value=False,
                ),
                patch(
                    "backend.agent.harness_events.log_event",
                    side_effect=lambda trace_id, span_name, event_name, **kwargs: events.append(
                        {
                            "trace_id": trace_id,
                            "span_name": span_name,
                            "event_name": event_name,
                            "payload": kwargs.get("payload") or {},
                        }
                    ),
                ),
            ):
                got = []
                async for event in stream_chat_multi_agent(
                    [{"role": "user", "content": "1-4 月各区域销售额排行"}],
                    trace_id="t-multi",
                ):
                    got.append(event)

            self.assertEqual(got[-1]["type"], "done")
            harness_events = [
                (item["event_name"], item["payload"].get("action"))
                for item in events
                if item["span_name"] == "agent.harness"
            ]
            self.assertIn(("action_validated", "delegate_tasks"), harness_events)
            self.assertIn(("action_authorized", "delegate_tasks"), harness_events)
            self.assertIn(("action_executing", "run_specialist"), harness_events)
            self.assertIn(("observation_built", "run_specialist"), harness_events)
            self.assertIn(("finish_emitted", "finish"), harness_events)
            thinking = [item.get("content") for item in got if item.get("type") == "thinking"]
            messages = [
                item.get("message") if isinstance(item, dict) else str(item) for item in thinking
            ]
            self.assertFalse(any("开始查询" in item for item in messages))
            self.assertFalse(any("问数专线" in item for item in messages))
            self.assertIn("正在理解问题...", messages)
            self.assertIn("正在处理信息...", messages)
            self.assertIn("已完成一步处理...", messages)
            self.assertIn("正在整理答案...", messages)
            detail_steps = [
                item for item in thinking if isinstance(item, dict) and item.get("details")
            ]
            self.assertEqual(len(detail_steps), 1)
            self.assertEqual(detail_steps[0]["details"][0]["title"], "SQL")
            self.assertEqual(detail_steps[0]["details"][0]["language"], "sql")
            self.assertIn("SELECT SUM", detail_steps[0]["details"][0]["content"])

        import asyncio

        asyncio.run(_run())

    def test_multi_agent_invalid_tasks_log_rejection_and_fallback(self) -> None:
        async def _run() -> None:
            async def fake_single(*args, **kwargs):
                yield {"type": "text", "content": "fallback"}
                yield {"type": "done", "content": None}

            events = []
            with (
                patch(
                    "backend.agent.multi_agent_runner.validate_and_order_tasks",
                    return_value=None,
                ),
                patch(
                    "backend.agent.abort_state.is_aborted",
                    return_value=False,
                ),
                patch(
                    "backend.agent.runner.stream_chat",
                    side_effect=fake_single,
                ),
                patch(
                    "backend.agent.harness_events.log_event",
                    side_effect=lambda trace_id, span_name, event_name, **kwargs: events.append(
                        {
                            "trace_id": trace_id,
                            "span_name": span_name,
                            "event_name": event_name,
                            "payload": kwargs.get("payload") or {},
                        }
                    ),
                ),
            ):
                got = []
                async for event in stream_chat_multi_agent(
                    [{"role": "user", "content": "查销售额"}],
                    trace_id="t-invalid",
                ):
                    got.append(event)

            self.assertEqual(got[-2]["type"], "text")
            self.assertEqual(got[-2]["content"], "fallback")
            self.assertEqual(got[-1]["type"], "done")
            rejected = [
                item
                for item in events
                if item["span_name"] == "agent.harness" and item["event_name"] == "policy_rejected"
            ]
            self.assertEqual(len(rejected), 1)
            self.assertIn("未通过 Harness 校验", rejected[0]["payload"].get("reason", ""))

        import asyncio

        asyncio.run(_run())

    def test_multi_agent_logs_summary_dependency_unmet_before_synthesis(self) -> None:
        async def _run() -> None:
            async def fake_specialist(*args, **kwargs):
                yield {"type": "text", "content": "缺少已采纳指标的具体数值，无法生成建议"}

            async def fake_stream_result_events(*args, **kwargs):
                yield {"type": "text", "content": "最终结果"}

            events = []
            with (
                patch(
                    "backend.agent.multi_agent_runner.validate_and_order_tasks",
                    return_value=[
                        (
                            0,
                            {
                                "agent_id": "business_advisor",
                                "handoff_instruction": "基于已采纳指标给经营建议",
                                "depends_on": None,
                            },
                        )
                    ],
                ),
                patch(
                    "backend.agent.multi_agent_runner.skills_for_agent",
                    return_value=[MagicMock()],
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_label",
                    return_value="经营决策建议",
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_role_prompt",
                    return_value="你是经营建议专线",
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_specialist",
                    side_effect=fake_specialist,
                ),
                patch(
                    "backend.agent.multi_agent_runner.call_summarize_llm",
                    new_callable=AsyncMock,
                    return_value={"text": "最终结果"},
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_result_events",
                    side_effect=fake_stream_result_events,
                ),
                patch(
                    "backend.agent.abort_state.is_aborted",
                    return_value=False,
                ),
                patch(
                    "backend.agent.harness_events.log_event",
                    side_effect=lambda trace_id, span_name, event_name, **kwargs: events.append(
                        {
                            "trace_id": trace_id,
                            "span_name": span_name,
                            "event_name": event_name,
                            "payload": kwargs.get("payload") or {},
                        }
                    ),
                ),
            ):
                got = []
                async for event in stream_chat_multi_agent(
                    [{"role": "user", "content": "给出经营建议"}],
                    trace_id="t-summary-warning",
                ):
                    got.append(event)

            self.assertEqual(got[-1]["type"], "done")
            warnings = [
                item
                for item in events
                if item["span_name"] == "agent.harness"
                and item["event_name"] == "summary_dependency_unmet"
            ]
            self.assertEqual(len(warnings), 1)
            self.assertEqual(warnings[0]["payload"].get("warning_count"), 1)

        import asyncio

        asyncio.run(_run())

    def test_multi_agent_blocks_summary_when_decision_has_no_facts(self) -> None:
        async def _run() -> None:
            async def fake_specialist(*args, **kwargs):
                sink = kwargs["result_sink"]
                sink["last_result"] = {
                    "kind": "text",
                    "text": "可以加强管理并持续跟进。",
                    "data": {},
                }
                sink["last_skill_name"] = "chatbi-decision-advisor"
                yield {"type": "text", "content": "可以加强管理并持续跟进。"}

            events = []
            summarize = AsyncMock(return_value={"text": "不应汇总"})
            with (
                patch(
                    "backend.agent.multi_agent_runner.validate_and_order_tasks",
                    return_value=[
                        (
                            0,
                            {
                                "agent_id": "business_advisor",
                                "handoff_instruction": "直接给经营建议",
                                "depends_on": None,
                            },
                        )
                    ],
                ),
                patch(
                    "backend.agent.multi_agent_runner.skills_for_agent", return_value=[MagicMock()]
                ),
                patch("backend.agent.multi_agent_runner.agent_label", return_value="经营决策建议"),
                patch(
                    "backend.agent.multi_agent_runner.agent_role_prompt",
                    return_value="你是经营建议专线",
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_specialist",
                    side_effect=fake_specialist,
                ),
                patch("backend.agent.multi_agent_runner.call_summarize_llm", summarize),
                patch("backend.agent.abort_state.is_aborted", return_value=False),
                patch(
                    "backend.agent.multi_agent_runner.log_event",
                    side_effect=lambda trace_id, span_name, event_name, **kwargs: events.append(
                        {
                            "trace_id": trace_id,
                            "span_name": span_name,
                            "event_name": event_name,
                            "payload": kwargs.get("payload") or {},
                        }
                    ),
                ),
            ):
                got = []
                async for event in stream_chat_multi_agent(
                    [{"role": "user", "content": "给出经营建议"}],
                    trace_id="t-final-audit-block",
                ):
                    got.append(event)

            summarize.assert_not_awaited()
            texts = [
                str(event.get("content") or "") for event in got if event.get("type") == "text"
            ]
            self.assertTrue(any("未通过最终事实审计" in text for text in texts))
            final_audits = [
                item
                for item in events
                if item["span_name"] == "agent.harness"
                and item["event_name"] == "multi_final_audit"
            ]
            self.assertEqual(final_audits[0]["payload"].get("status"), "error")

        import asyncio

        asyncio.run(_run())

    def test_multi_agent_blocks_summary_with_unsupported_number_claim(self) -> None:
        async def _run() -> None:
            async def fake_specialist(*args, **kwargs):
                sink = kwargs["result_sink"]
                sink["last_result"] = {
                    "kind": "table",
                    "text": "query ok",
                    "data": {"rows": [{"区域": "华东", "销售额": "100"}]},
                }
                sink["last_skill_name"] = "chatbi-semantic-query"
                sink["skill_executions"] = [
                    {
                        "skill": "chatbi-semantic-query",
                        "result": sink["last_result"],
                        "observation": "华东销售额为 100 元。",
                        "step": 1,
                    }
                ]
                yield {"type": "thinking", "content": "处理中"}

            summarize = AsyncMock(return_value={"text": "华东销售额为 999 元。"})
            events = []
            with (
                patch(
                    "backend.agent.multi_agent_runner.validate_and_order_tasks",
                    return_value=[
                        (
                            0,
                            {
                                "agent_id": "demo_query",
                                "handoff_instruction": "查询华东销售额",
                                "depends_on": None,
                            },
                        )
                    ],
                ),
                patch(
                    "backend.agent.multi_agent_runner.skills_for_agent", return_value=[MagicMock()]
                ),
                patch("backend.agent.multi_agent_runner.agent_label", return_value="问数专线"),
                patch(
                    "backend.agent.multi_agent_runner.agent_role_prompt",
                    return_value="你是问数专线",
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_specialist",
                    side_effect=fake_specialist,
                ),
                patch("backend.agent.multi_agent_runner.call_summarize_llm", summarize),
                patch("backend.agent.abort_state.is_aborted", return_value=False),
                patch(
                    "backend.agent.multi_agent_runner.log_event",
                    side_effect=lambda trace_id, span_name, event_name, **kwargs: events.append(
                        {
                            "trace_id": trace_id,
                            "span_name": span_name,
                            "event_name": event_name,
                            "payload": kwargs.get("payload") or {},
                        }
                    ),
                ),
            ):
                got = []
                async for event in stream_chat_multi_agent(
                    [{"role": "user", "content": "查华东销售额"}],
                    trace_id="t-claim-audit-block",
                ):
                    got.append(event)

            summarize.assert_awaited_once()
            texts = [
                str(event.get("content") or "") for event in got if event.get("type") == "text"
            ]
            self.assertTrue(any("未通过最终事实审计" in text for text in texts))
            claim_audits = [
                item
                for item in events
                if item["span_name"] == "agent.harness"
                and item["event_name"] == "multi_summary_claim_audit"
            ]
            self.assertEqual(claim_audits[0]["payload"].get("status"), "error")
            self.assertIn("999", str(claim_audits[0]["payload"].get("issues")))

        import asyncio

        asyncio.run(_run())

    def test_multi_agent_passes_dependency_result_into_business_advisor(self) -> None:
        async def _run() -> None:
            captured = {}

            async def fake_specialist(*args, **kwargs):
                sink = kwargs["result_sink"]
                agent_id = kwargs["specialist_agent_id"]
                if agent_id == "demo_query":
                    sink["last_result"] = {
                        "kind": "table",
                        "text": "query ok",
                        "data": {"rows": [{"区域": "华东", "毛利率": "21%"}]},
                    }
                    sink["last_skill_name"] = "chatbi-semantic-query"
                    sink["skill_executions"] = [
                        {
                            "skill": "chatbi-semantic-query",
                            "result": sink["last_result"],
                            "observation": "查到 1 行结果。",
                            "step": 1,
                        }
                    ]
                else:
                    captured["initial_last_result"] = kwargs.get("initial_last_result")
                    captured["initial_last_skill_name"] = kwargs.get("initial_last_skill_name")
                    sink["last_result"] = {
                        "kind": "decision",
                        "text": "建议深耕华东。",
                        "data": {"advices": [{"title": "深耕华东"}]},
                    }
                    sink["last_skill_name"] = "chatbi-decision-advisor"
                    sink["skill_executions"] = [
                        {
                            "skill": "chatbi-decision-advisor",
                            "result": sink["last_result"],
                            "observation": "已生成经营建议。",
                            "step": 1,
                        }
                    ]
                yield {"type": "thinking", "content": "处理中"}

            async def fake_stream_result_events(*args, **kwargs):
                yield {"type": "text", "content": "最终结果"}

            with (
                patch(
                    "backend.agent.multi_agent_runner.validate_and_order_tasks",
                    side_effect=[
                        [
                            (
                                0,
                                {
                                    "agent_id": "demo_query",
                                    "handoff_instruction": "查询 1-4 月各区域毛利率",
                                    "depends_on": None,
                                },
                            )
                        ],
                        [
                            (
                                0,
                                {
                                    "agent_id": "business_advisor",
                                    "handoff_instruction": "基于前置问数结果给经营建议",
                                    "depends_on": 0,
                                },
                            )
                        ],
                    ],
                ),
                patch(
                    "backend.agent.multi_agent_runner.skills_for_agent",
                    return_value=[MagicMock()],
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_label",
                    side_effect=lambda agent_id: agent_id,
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_role_prompt",
                    side_effect=lambda agent_id: f"你是 {agent_id}",
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_specialist",
                    side_effect=fake_specialist,
                ),
                patch(
                    "backend.agent.multi_agent_runner.call_summarize_llm",
                    new_callable=AsyncMock,
                    return_value={"text": "最终结果"},
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_result_events",
                    side_effect=fake_stream_result_events,
                ),
                patch(
                    "backend.agent.abort_state.is_aborted",
                    return_value=False,
                ),
            ):
                got = []
                async for event in stream_chat_multi_agent(
                    [{"role": "user", "content": "先查毛利率，再给经营建议"}],
                    trace_id="t-dependency-seed",
                ):
                    got.append(event)

            self.assertEqual(got[-1]["type"], "done")
            self.assertEqual(captured["initial_last_skill_name"], "chatbi-semantic-query")
            self.assertEqual(
                captured["initial_last_result"]["data"]["rows"][0]["区域"],
                "华东",
            )

        import asyncio

        asyncio.run(_run())

    def test_multi_agent_harness_routes_query_result_to_business_advisor(self) -> None:
        async def _run() -> None:
            captured = {"agents": []}
            events = []

            async def fake_specialist(*args, **kwargs):
                sink = kwargs["result_sink"]
                agent_id = kwargs["specialist_agent_id"]
                captured["agents"].append(agent_id)
                if agent_id == "demo_query":
                    sink["last_result"] = {
                        "kind": "table",
                        "text": "query ok",
                        "data": {"rows": [{"区域": "华东", "销售额": "100", "毛利": "22"}]},
                    }
                    sink["last_skill_name"] = "chatbi-semantic-query"
                    sink["skill_executions"] = [
                        {
                            "skill": "chatbi-semantic-query",
                            "result": sink["last_result"],
                            "observation": "查到 1 行结果。",
                            "step": 1,
                        }
                    ]
                else:
                    captured["seed_result"] = kwargs.get("initial_last_result")
                    captured["seed_skill_name"] = kwargs.get("initial_last_skill_name")
                    sink["last_result"] = {
                        "kind": "decision",
                        "text": "建议聚焦华东。",
                        "data": {
                            "facts": {
                                "overview": {
                                    "sales": "100",
                                    "target_achievement_rate": "88%",
                                    "gross_margin_rate": "22%",
                                }
                            },
                            "advices": [
                                {
                                    "decision": "聚焦华东",
                                    "reason": "华东销售额100，毛利率22%。",
                                    "actions": ["继续推进重点客户"],
                                }
                            ],
                        },
                    }
                    sink["last_skill_name"] = "chatbi-decision-advisor"
                    sink["skill_executions"] = [
                        {
                            "skill": "chatbi-decision-advisor",
                            "result": sink["last_result"],
                            "observation": "已生成经营建议。",
                            "step": 1,
                        }
                    ]
                yield {"type": "thinking", "content": "处理中"}

            async def fake_stream_result_events(*args, **kwargs):
                yield {"type": "text", "content": "最终结果"}

            with (
                patch(
                    "backend.agent.multi_agent_runner.validate_and_order_tasks",
                    side_effect=[
                        [
                            (
                                0,
                                {
                                    "agent_id": "demo_query",
                                    "handoff_instruction": "先查询华东近3个月销售和毛利",
                                    "depends_on": None,
                                },
                            )
                        ],
                        [
                            (
                                0,
                                {
                                    "agent_id": "business_advisor",
                                    "handoff_instruction": "基于前置问数结果直接生成经营建议，优先引用已有 rows 与结构化事实，不要重复问数；若事实不足，请明确指出缺口。",
                                    "depends_on": None,
                                },
                            )
                        ],
                    ],
                ),
                patch(
                    "backend.agent.multi_agent_runner.skills_for_agent",
                    return_value=[MagicMock()],
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_label",
                    side_effect=lambda agent_id: agent_id,
                ),
                patch(
                    "backend.agent.multi_agent_runner.agent_role_prompt",
                    side_effect=lambda agent_id: f"你是 {agent_id}",
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_specialist",
                    side_effect=fake_specialist,
                ),
                patch(
                    "backend.agent.multi_agent_runner.call_summarize_llm",
                    new_callable=AsyncMock,
                    return_value={"text": "最终结果"},
                ),
                patch(
                    "backend.agent.multi_agent_runner.stream_result_events",
                    side_effect=fake_stream_result_events,
                ),
                patch(
                    "backend.agent.abort_state.is_aborted",
                    return_value=False,
                ),
                patch(
                    "backend.agent.harness_events.log_event",
                    side_effect=lambda trace_id, span_name, event_name, **kwargs: events.append(
                        {
                            "trace_id": trace_id,
                            "span_name": span_name,
                            "event_name": event_name,
                            "payload": kwargs.get("payload") or {},
                        }
                    ),
                ),
                patch(
                    "backend.agent.multi_agent_runner.log_event",
                    side_effect=lambda trace_id, span_name, event_name, **kwargs: events.append(
                        {
                            "trace_id": trace_id,
                            "span_name": span_name,
                            "event_name": event_name,
                            "payload": kwargs.get("payload") or {},
                        }
                    ),
                ),
            ):
                got = []
                async for event in stream_chat_multi_agent(
                    [{"role": "user", "content": "基于华东近3个月销售和毛利给经营建议"}],
                    trace_id="t-route-handoff",
                ):
                    got.append(event)

            self.assertEqual(got[-1]["type"], "done")
            self.assertEqual(captured["agents"], ["demo_query", "business_advisor"])
            self.assertEqual(captured["seed_skill_name"], "chatbi-semantic-query")
            self.assertEqual(
                captured["seed_result"]["data"]["rows"][0]["区域"],
                "华东",
            )
            transitions = [
                item
                for item in events
                if item["span_name"] == "agent.harness"
                and item["event_name"] == "route_transition_selected"
            ]
            self.assertEqual(len(transitions), 1)
            self.assertEqual(transitions[0]["payload"].get("to_agent"), "business_advisor")
            completed = [
                item
                for item in events
                if item["span_name"] == "agent.harness"
                and item["event_name"] == "route_objective_completed"
            ]
            self.assertEqual(len(completed), 1)

        import asyncio

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
