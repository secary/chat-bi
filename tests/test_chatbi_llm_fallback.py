"""chatbi_acompletion retries on transient failures."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class ChatbiLlmFallbackTest(unittest.TestCase):
    def test_fallback_on_connection_error(self) -> None:
        from backend.llm_runtime import chatbi_acompletion

        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock(message=MagicMock(content="{}"))]

        async def run() -> None:
            with patch(
                "backend.llm_runtime._attempt_param_dicts",
                return_value=[{"model": "m1"}, {"model": "m2"}],
            ):
                with patch("litellm.acompletion", new_callable=AsyncMock) as ac:
                    ac.side_effect = [ConnectionError("network"), mock_resp]
                    out = await chatbi_acompletion(messages=[], temperature=0)
                    self.assertEqual(out, mock_resp)
                    self.assertEqual(ac.await_count, 2)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
