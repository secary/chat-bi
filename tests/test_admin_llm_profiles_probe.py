"""LLM profile probe tests unsaved config before persistence."""

from __future__ import annotations

import types
import unittest
from unittest.mock import AsyncMock, patch


class AdminLlmProfilesProbeTest(unittest.IsolatedAsyncioTestCase):
    async def test_probe_uses_payload_without_setting_saved_health(self) -> None:
        from backend.routes.admin_llm_profiles_route import LlmProfileProbe, probe_llm_profile

        request = types.SimpleNamespace(headers={})
        with (
            patch(
                "backend.routes.admin_llm_profiles_route.profile_row_to_litellm_params",
                return_value={"model": "openai/x", "api_base": "https://x/v1", "api_key": "key"},
            ) as params_mock,
            patch(
                "backend.routes.admin_llm_profiles_route.log_event",
            ) as log_mock,
            patch("litellm.acompletion", new_callable=AsyncMock) as completion_mock,
            patch(
                "backend.routes.admin_llm_profiles_route.llm_profile_repo.set_health"
            ) as health_mock,
        ):
            result = await probe_llm_profile(
                LlmProfileProbe(model=" openai/x ", api_base="https://x/v1", api_key="key"),
                request,  # type: ignore[arg-type]
            )

        self.assertEqual(result, {"ok": True, "message": "ok"})
        params_mock.assert_called_once_with(
            {"model": "openai/x", "api_base": "https://x/v1", "api_key": "key"}
        )
        completion_mock.assert_awaited_once()
        health_mock.assert_not_called()
        log_mock.assert_called_once()

    async def test_probe_can_reuse_saved_profile_key_for_edit(self) -> None:
        from backend.routes.admin_llm_profiles_route import LlmProfileProbe, probe_llm_profile

        request = types.SimpleNamespace(headers={})
        with (
            patch(
                "backend.routes.admin_llm_profiles_route.llm_profile_repo.get_by_id",
                return_value={"id": 7, "api_key": "saved-key"},
            ) as get_mock,
            patch(
                "backend.routes.admin_llm_profiles_route.profile_row_to_litellm_params",
                return_value={
                    "model": "openai/y",
                    "api_base": "https://y/v1",
                    "api_key": "saved-key",
                },
            ) as params_mock,
            patch("backend.routes.admin_llm_profiles_route.log_event"),
            patch("litellm.acompletion", new_callable=AsyncMock),
        ):
            result = await probe_llm_profile(
                LlmProfileProbe(
                    model="openai/y",
                    api_base="https://y/v1",
                    api_key=None,
                    source_profile_id=7,
                ),
                request,  # type: ignore[arg-type]
            )

        self.assertEqual(result, {"ok": True, "message": "ok"})
        get_mock.assert_called_once_with(7)
        params_mock.assert_called_once_with(
            {"model": "openai/y", "api_base": "https://y/v1", "api_key": "saved-key"}
        )


if __name__ == "__main__":
    unittest.main()
