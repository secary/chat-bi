from __future__ import annotations

import unittest

from backend.routes.chat_route import (
    _next_disconnect_state,
    _session_title_from_message,
    _should_auto_update_session_title,
)


class ChatRouteDisconnectTest(unittest.TestCase):
    def test_disconnect_state_sticks_after_first_disconnect(self):
        self.assertFalse(_next_disconnect_state(False, False))
        self.assertTrue(_next_disconnect_state(False, True))
        self.assertTrue(_next_disconnect_state(True, False))

    def test_auto_title_only_for_default_empty_session(self):
        self.assertTrue(_should_auto_update_session_title("新聊天", []))
        self.assertTrue(_should_auto_update_session_title("  新聊天  ", []))
        self.assertTrue(_should_auto_update_session_title("新对话", []))
        self.assertFalse(
            _should_auto_update_session_title("新聊天", [{"role": "user", "content": "旧问题"}])
        )
        self.assertFalse(_should_auto_update_session_title("手动标题", []))

    def test_session_title_compacts_user_question(self):
        self.assertEqual(
            _session_title_from_message("请帮我分析一下华东 5 月销售额和毛利率，可以吗？"),
            "华东 5 月销售额和毛利率",
        )
        self.assertEqual(
            _session_title_from_message("看看客户数按区域分布，并给出经营建议"),
            "客户数按区域分布",
        )
        self.assertEqual(_session_title_from_message("   "), "新聊天")

    def test_session_title_compacts_upload_noise(self):
        self.assertEqual(
            _session_title_from_message(
                "请读取我上传的文件 /tmp/chatbi-uploads/abc_sales.csv，按数据库表结构校验"
            ),
            "上传文件结构校验",
        )


if __name__ == "__main__":
    unittest.main()
