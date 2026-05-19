"""Router parsing and agent selection caps."""

from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agent.multi_agent_router import call_route_llm


class MultiAgentRouterTest(unittest.TestCase):
    def test_call_route_llm_returns_json(self) -> None:
        payload = {
            "agents": ["analysis"],
            "user_intent_summary": "问数",
            "routing_reason": "默认",
        }

        async def run():
            mock_resp = MagicMock()
            mock_resp.choices = [MagicMock(message=MagicMock(content=json.dumps(payload)))]
            with patch(
                "backend.agent.multi_agent_router.chatbi_acompletion",
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
