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
                    "data": {"rows": [{"区域": "华东", "销售额": 100}]},
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
                    "backend.agent.multi_agent_runner.call_manager_plan_llm",
                    new_callable=AsyncMock,
                    return_value={
                        "user_intent_summary": "问数",
                        "decomposition_reason": "单专线处理即可",
                        "finalize_after_this_batch": True,
                        "tasks": [
                            {
                                "agent_id": "demo_query",
                                "handoff_instruction": "查询 1-4 月各区域销售额",
                                "depends_on": None,
                            }
                        ],
                    },
                ),
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
                    "backend.agent.multi_agent_runner.call_manager_plan_llm",
                    new_callable=AsyncMock,
                    return_value={
                        "user_intent_summary": "问数",
                        "decomposition_reason": "invalid",
                        "tasks": [{"agent_id": "demo_query"}],
                    },
                ),
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
                    "backend.agent.multi_agent_runner.call_manager_plan_llm",
                    new_callable=AsyncMock,
                    return_value={
                        "user_intent_summary": "建议",
                        "decomposition_reason": "先走经营建议专线",
                        "finalize_after_this_batch": True,
                        "tasks": [
                            {
                                "agent_id": "business_advisor",
                                "handoff_instruction": "基于已采纳指标给经营建议",
                                "depends_on": None,
                            }
                        ],
                    },
                ),
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
                    [{"role": "user", "content": "采纳全部指标然后给出经营建议"}],
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
                    "backend.agent.multi_agent_runner.call_manager_plan_llm",
                    new_callable=AsyncMock,
                    side_effect=[
                        {
                            "user_intent_summary": "问数+建议",
                            "decomposition_reason": "先查数再给建议",
                            "finalize_after_this_batch": False,
                            "tasks": [
                                {
                                    "agent_id": "demo_query",
                                    "handoff_instruction": "查询 1-4 月各区域毛利率",
                                    "depends_on": None,
                                }
                            ],
                        },
                        {
                            "user_intent_summary": "给建议",
                            "decomposition_reason": "基于前置结果给建议",
                            "finalize_after_this_batch": True,
                            "tasks": [
                                {
                                    "agent_id": "business_advisor",
                                    "handoff_instruction": "基于前置问数结果给经营建议",
                                    "depends_on": 0,
                                }
                            ],
                        },
                    ],
                ),
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


if __name__ == "__main__":
    unittest.main()
