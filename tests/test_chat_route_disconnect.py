from __future__ import annotations

import unittest

from backend.routes.chat_route import _next_disconnect_state


class ChatRouteDisconnectTest(unittest.TestCase):
    def test_disconnect_state_sticks_after_first_disconnect(self):
        self.assertFalse(_next_disconnect_state(False, False))
        self.assertTrue(_next_disconnect_state(False, True))
        self.assertTrue(_next_disconnect_state(True, False))


if __name__ == "__main__":
    unittest.main()
