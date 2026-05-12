"""saved_settings_apply visibility for admin UI."""

from __future__ import annotations

import unittest
from unittest.mock import patch


class AppLlmSavedTest(unittest.TestCase):
    def test_saved_true_when_active_profile_exists(self) -> None:
        from backend.app_llm import saved_settings_apply

        with patch(
            "backend.app_llm.llm_profile_repo.get_by_id",
            return_value={"model": "openai/x"},
        ):
            self.assertTrue(saved_settings_apply({"active_profile_id": 9}))

    def test_saved_false_when_empty_row(self) -> None:
        from backend.app_llm import saved_settings_apply

        self.assertFalse(saved_settings_apply(None))


if __name__ == "__main__":
    unittest.main()
