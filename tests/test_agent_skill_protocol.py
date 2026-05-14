from __future__ import annotations

import asyncio
import unittest

from backend.agent.formatter import stream_result_events
from backend.agent.protocol import normalize_skill_result


class SkillProtocolTest(unittest.TestCase):
    def test_normalizes_legacy_table_rows(self):
        result = normalize_skill_result([{"区域": "华东", "销售额": "100"}], "demo")

        self.assertEqual(result["kind"], "table")
        self.assertEqual(result["data"]["rows"][0]["区域"], "华东")
        self.assertIn("查询完成", result["text"])

    def test_streams_structured_decision_result(self):
        result = {
            "kind": "decision",
            "text": "## 决策建议",
            "data": {},
            "kpis": [{"label": "销售额", "value": "100", "unit": "元", "status": "neutral"}],
        }

        async def collect():
            return [
                event async for event in stream_result_events("chatbi-decision-advisor", {}, result)
            ]

        events = asyncio.run(collect())
        self.assertEqual(events[0], {"type": "text", "content": "## 决策建议"})
        self.assertEqual(events[1]["type"], "kpi_cards")

    def test_prefers_skill_chart_plan_over_llm_plan(self):
        result = {
            "kind": "table",
            "text": "查询完成",
            "data": {"rows": [{"区域": "华东", "销售额": "100"}]},
            "chart_plan": {
                "chart_type": "bar",
                "dimension": "区域",
                "metrics": ["销售额"],
            },
        }
        llm_plan = {
            "chart_plan": {"chart_type": "line", "dimension": "月份", "metrics": ["销售额"]}
        }

        async def collect():
            return [
                event
                async for event in stream_result_events("chatbi-semantic-query", llm_plan, result)
            ]

        events = asyncio.run(collect())
        chart_events = [event for event in events if event.get("type") == "chart"]
        self.assertEqual(len(chart_events), 1)
        self.assertEqual(chart_events[0]["content"]["series"][0]["type"], "bar")

    def test_streams_plan_summary_when_result_provides_it(self):
        result = {
            "kind": "table",
            "text": "查询完成",
            "data": {
                "rows": [{"区域": "华东", "销售额": "100"}],
                "plan_trace": [
                    "收到问数请求：1-4月各区域销售额排行",
                    "识别时间范围：`order_date` >= '2026-01-01' AND `order_date` < '2026-05-01'",
                ],
                "plan_summary": {
                    "metric": "销售额",
                    "dimensions": ["区域"],
                    "filters": [],
                    "time_filter": "`order_date` >= '2026-01-01' AND `order_date` < '2026-05-01'",
                    "order_by_metric_desc": True,
                    "limit": None,
                },
            },
        }

        async def collect():
            return [
                event async for event in stream_result_events("chatbi-semantic-query", {}, result)
            ]

        events = asyncio.run(collect())
        plan_events = [event for event in events if event.get("type") == "plan_summary"]
        self.assertEqual(len(plan_events), 1)
        self.assertEqual(plan_events[0]["content"]["metric"], "销售额")
        self.assertEqual(events[0]["type"], "thinking")
        self.assertEqual(events[0]["content"], "收到问数请求：1-4月各区域销售额排行")
        self.assertEqual(
            events[1]["content"],
            "识别时间范围：`order_date` >= '2026-01-01' AND `order_date` < '2026-05-01'",
        )

    def test_streams_auto_analysis_middleware_events(self):
        result = {
            "kind": "auto_analysis",
            "text": "## 上传表分析建议",
            "data": {
                "analysis_proposal": {"markdown": "建议采纳", "proposed_metrics": []},
                "dashboard_middleware": {"markdown": "看板已生成", "widgets": []},
            },
        }

        async def collect():
            return [
                event async for event in stream_result_events("chatbi-auto-analysis", {}, result)
            ]

        events = asyncio.run(collect())
        self.assertEqual(events[0]["type"], "text")
        self.assertTrue(any(event["type"] == "analysis_proposal" for event in events))
        self.assertTrue(any(event["type"] == "dashboard_ready" for event in events))

    def test_does_not_build_finish_kpis_for_multi_row_table(self):
        result = {
            "kind": "table",
            "text": "查询完成，共返回 2 条结果。",
            "data": {
                "rows": [
                    {"区域": "华东", "毛利率": "0.3650"},
                    {"区域": "华南", "毛利率": "0.3620"},
                ]
            },
        }
        llm_plan = {
            "kpi_cards": [
                {"label": "最高区域", "field": "区域", "unit": "", "status": "neutral"},
                {"label": "毛利率", "field": "毛利率", "unit": "%", "status": "neutral"},
            ]
        }

        async def collect():
            return [
                event
                async for event in stream_result_events("chatbi-semantic-query", llm_plan, result)
            ]

        events = asyncio.run(collect())
        kpi_events = [event for event in events if event.get("type") == "kpi_cards"]
        self.assertEqual(kpi_events, [])


if __name__ == "__main__":
    unittest.main()
