"""Router parsing and agent selection caps."""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.multi_agent_router import call_route_llm
from backend.agent.multi_agent_runner import _pick_route_agents


class MultiAgentRouterTest(unittest.TestCase):
    def test_pick_route_agents_respects_cap_and_registry(self) -> None:
        route = {
            "agents": ["risk", "marketing", "analysis"],
            "user_intent_summary": "x",
            "routing_reason": "y",
        }

        def fake_skills(agent_id: str):
            return ["doc"] if agent_id in ("risk", "marketing", "analysis") else []

        with patch(
            "backend.agent.multi_agent_runner.max_agents_per_round",
            return_value=2,
        ):
            with patch(
                "backend.agent.multi_agent_runner.list_registry_agent_ids",
                return_value=["risk", "marketing", "analysis"],
            ):
                with patch(
                    "backend.agent.multi_agent_runner.skills_for_agent",
                    side_effect=fake_skills,
                ):
                    out = _pick_route_agents(route)
                    self.assertEqual(len(out), 2)
                    self.assertEqual(out[0], "risk")

    def test_call_route_llm_returns_json(self) -> None:
        payload = {
            "agents": ["analysis"],
            "user_intent_summary": "问数",
            "routing_reason": "默认",
        }

        async def run():
            mock_resp = MagicMock()
            mock_resp.choices = [
                MagicMock(message=MagicMock(content=json.dumps(payload)))
            ]
            with patch(
                "backend.agent.multi_agent_router.acompletion",
                new_callable=AsyncMock,
                return_value=mock_resp,
            ):
                got = await call_route_llm(
                    [{"role": "user", "content": "1-4月销售额"}], trace_id="t1"
                )
                self.assertEqual(got.get("agents"), ["analysis"])

        import asyncio

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
