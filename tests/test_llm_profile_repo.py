"""llm_profile_repo helpers."""

from __future__ import annotations

import unittest

from backend.llm_profile_repo import public_row


class LlmProfileRepoTest(unittest.TestCase):
    def test_public_row_masks_api_key(self) -> None:
        view = public_row(
            {
                "id": 3,
                "display_name": "Dev",
                "model": "openai/x",
                "api_base": "https://x/v1",
                "api_key": "secret",
                "sort_order": 1,
                "health_status": "ok",
                "health_detail": None,
                "health_checked_at": None,
                "supports_vision": 0,
                "created_at": None,
                "updated_at": None,
            }
        )
        self.assertEqual(view["id"], 3)
        self.assertTrue(view["api_key_set"])
        self.assertFalse(view["supports_vision"])
        self.assertNotIn("api_key", view)


if __name__ == "__main__":
    unittest.main()
