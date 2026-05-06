from __future__ import annotations

import sys
import types
import unittest

litellm_stub = types.ModuleType("litellm")
litellm_stub.acompletion = None
sys.modules.setdefault("litellm", litellm_stub)

from backend.agent.runner import infer_primary_dimension


class QueryAdviceDimensionFlowTest(unittest.TestCase):
    def test_infers_primary_dimension_from_query_rows(self):
        result = {
            "data": {
                "rows": [
                    {"区域": "华东", "销售额": "610000"},
                    {"区域": "华南", "销售额": "400000"},
                ]
            }
        }

        self.assertEqual(infer_primary_dimension(result), "区域")


if __name__ == "__main__":
    unittest.main()
