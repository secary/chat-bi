from __future__ import annotations

import sys
import types
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

pymysql_stub = types.ModuleType("pymysql")
pymysql_stub.connect = None
sys.modules.setdefault("pymysql", pymysql_stub)
cursors_stub = types.ModuleType("pymysql.cursors")
cursors_stub.DictCursor = object
sys.modules.setdefault("pymysql.cursors", cursors_stub)

from backend import db_mysql


class DbMysqlTargetsTest(unittest.TestCase):
    def test_target_db_config_routes_admin_and_app(self):
        fake_settings = types.SimpleNamespace(
            app_db_config={
                "database": "chatbi_app",
                "host": "h1",
                "port": "1",
                "user": "u1",
                "password": "p1",
            },
            admin_db_config={
                "database": "chatbi_admin",
                "host": "h2",
                "port": "2",
                "user": "u2",
                "password": "p2",
            },
        )
        with patch.object(db_mysql, "settings", fake_settings):
            self.assertEqual(db_mysql.target_db_config("app")["database"], "chatbi_app")
            self.assertEqual(db_mysql.target_db_config("admin")["database"], "chatbi_admin")

    def test_admin_execute_lastrowid_uses_insert_cursor_lastrowid(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.lastrowid = 99

        @contextmanager
        def fake_admin_connection():
            conn = MagicMock()
            cursor_cm = MagicMock()
            cursor_cm.__enter__.return_value = mock_cursor
            cursor_cm.__exit__.return_value = None
            conn.cursor.return_value = cursor_cm
            yield conn

        with patch.object(db_mysql, "admin_connection", fake_admin_connection):
            rid = db_mysql.admin_execute_lastrowid("INSERT INTO t (a) VALUES (%s)", (1,))
        self.assertEqual(rid, 99)
        mock_cursor.execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
