from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch


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
            app_db_config={"database": "chatbi_app", "host": "h1", "port": "1", "user": "u1", "password": "p1"},
            admin_db_config={"database": "chatbi_admin", "host": "h2", "port": "2", "user": "u2", "password": "p2"},
        )
        with patch.object(db_mysql, "settings", fake_settings):
            self.assertEqual(db_mysql.target_db_config("app")["database"], "chatbi_app")
            self.assertEqual(db_mysql.target_db_config("admin")["database"], "chatbi_admin")


if __name__ == "__main__":
    unittest.main()
