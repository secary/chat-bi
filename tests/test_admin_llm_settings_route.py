"""Admin LLM settings default profile view and activation."""

from __future__ import annotations

import types
import unittest
from unittest.mock import AsyncMock, patch


class AdminLlmSettingsRouteTest(unittest.TestCase):
    def test_settings_view_prepends_default_config_profile(self) -> None:
        from backend.routes import admin_llm_route

        saved_row = {"active_profile_id": 7}
        profile_row = {
            "id": 7,
            "display_name": "备用模型",
            "model": "openai/backup",
            "api_base": "https://backup.example/v1",
            "api_key": "saved-key",
            "sort_order": 0,
            "health_status": "unknown",
            "health_detail": None,
            "health_checked_at": None,
            "created_at": None,
            "updated_at": None,
        }
        with (
            patch(
                "backend.routes.admin_llm_route.settings",
                types.SimpleNamespace(
                    llm_params={
                        "model": "openai/default",
                        "api_base": "https://default.example/v1",
                        "api_key": "env-key",
                    }
                ),
            ),
            patch(
                "backend.routes.admin_llm_route.llm_profile_repo.list_ordered",
                return_value=[profile_row],
            ),
            patch(
                "backend.routes.admin_llm_route.effective_llm_params",
                return_value={"model": "openai/backup"},
            ),
            patch("backend.routes.admin_llm_route.saved_settings_apply", return_value=True),
        ):
            view = admin_llm_route._settings_view(saved_row)

        self.assertEqual(view["profiles"][0]["id"], 0)
        self.assertEqual(view["profiles"][0]["display_name"], "默认配置")
        self.assertTrue(view["profiles"][0]["is_env_default"])
        self.assertEqual(view["profiles"][0]["model"], "openai/default")
        self.assertEqual(view["profiles"][1]["id"], 7)

    def test_set_active_default_clears_saved_overrides(self) -> None:
        from backend.routes.admin_llm_profiles_route import ActiveBody, set_active_llm_profile

        request = types.SimpleNamespace(headers={})
        with (
            patch(
                "backend.routes.admin_llm_profiles_route.llm_settings_repo.activate_env_defaults"
            ) as activate_default,
            patch(
                "backend.routes.admin_llm_profiles_route.llm_profile_repo.set_active_profile"
            ) as set_active,
            patch("backend.routes.admin_llm_profiles_route.log_event"),
        ):
            result = set_active_llm_profile(ActiveBody(profile_id=0), request)  # type: ignore[arg-type]

        self.assertEqual(result, {"ok": True})
        activate_default.assert_called_once_with()
        set_active.assert_not_called()


class AdminLlmSettingsRouteAsyncTest(unittest.IsolatedAsyncioTestCase):
    async def test_default_profile_test_uses_env_params(self) -> None:
        from backend.routes import admin_llm_profiles_route

        with (
            patch(
                "backend.routes.admin_llm_profiles_route.settings",
                types.SimpleNamespace(llm_params={"model": "openai/default", "api_key": "env-key"}),
            ),
            patch(
                "backend.routes.admin_llm_profiles_route._probe_litellm_params",
                new_callable=AsyncMock,
                return_value=(True, "ok"),
            ) as probe,
        ):
            result = await admin_llm_profiles_route._probe_profile(0)

        self.assertEqual(result, (True, "ok"))
        probe.assert_awaited_once_with({"model": "openai/default", "api_key": "env-key"})


if __name__ == "__main__":
    unittest.main()
