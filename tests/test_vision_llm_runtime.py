"""Vision LLM routing: capability gate and dedicated profile resolution."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend.vision.chart_table_extract import enrich_last_user_message_with_vision
from backend.vision.vision_llm_runtime import (
    compute_vision_extract_enabled,
    resolve_vision_litellm_base_params,
)


class VisionResolveTest(unittest.TestCase):
    def test_disabled_by_env_returns_none(self) -> None:
        with patch.dict(os.environ, {"CHATBI_VISION_DISABLED": "1"}, clear=False):
            self.assertIsNone(resolve_vision_litellm_base_params())
            self.assertFalse(compute_vision_extract_enabled())

    def test_env_main_flag_uses_effective_params(self) -> None:
        env = {
            "CHATBI_VISION_DISABLED": "",
            "CHATBI_VISION_ALLOW_ENV_MAIN": "1",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch("backend.vision.vision_llm_runtime.get_row", return_value=None):
                with patch(
                    "backend.vision.vision_llm_runtime.effective_llm_params",
                    return_value={"model": "openai/gpt-4o-mini", "api_key": "k"},
                ):
                    p = resolve_vision_litellm_base_params()
                    self.assertIsNotNone(p)
                    self.assertEqual(p.get("model"), "openai/gpt-4o-mini")
                    self.assertTrue(compute_vision_extract_enabled())


class VisionEnrichAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_enrich_skips_when_no_capability(self) -> None:
        with patch.dict(os.environ, {"CHATBI_VISION_DISABLED": ""}, clear=False):
            with patch(
                "backend.vision.chart_table_extract.resolve_vision_litellm_base_params",
                return_value=None,
            ):
                msgs = [{"role": "user", "content": "/tmp/x.png"}]
                out = await enrich_last_user_message_with_vision(msgs, "t1")
                self.assertEqual(out, msgs)


if __name__ == "__main__":
    unittest.main()
