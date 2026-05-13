"""PDF report generation."""

from __future__ import annotations

import importlib
import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[misc, assignment]


class ReportPdfTest(unittest.TestCase):
    def test_pdf_report_import_is_lazy_about_matplotlib(self) -> None:
        module_name = "backend.report.pdf_report"
        original = sys.modules.pop(module_name, None)
        try:
            real_import = __import__

            def fake_import(name, *args, **kwargs):
                if name.startswith("matplotlib"):
                    raise AssertionError("pdf_report import should not load matplotlib eagerly")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                module = importlib.import_module(module_name)
            self.assertTrue(hasattr(module, "messages_to_html_document"))
        finally:
            sys.modules.pop(module_name, None)
            if original is not None:
                sys.modules[module_name] = original

    def test_sessions_route_import_is_lazy_about_pdf_stack(self) -> None:
        module_name = "backend.routes.sessions_route"
        original = sys.modules.pop(module_name, None)
        try:
            real_import = __import__

            def fake_import(name, *args, **kwargs):
                if name.startswith("matplotlib"):
                    raise AssertionError("sessions_route import should not load matplotlib eagerly")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                module = importlib.import_module(module_name)
            self.assertTrue(hasattr(module, "get_session_report_pdf"))
        finally:
            sys.modules.pop(module_name, None)
            if original is not None:
                sys.modules[module_name] = original

    def test_select_sans_fonts_prefers_cjk(self) -> None:
        from backend.report.pdf_chart_png import _select_sans_fonts

        fonts = _select_sans_fonts({"DejaVu Sans", "Noto Sans CJK SC"})
        self.assertEqual(fonts[0], "Noto Sans CJK SC")
        self.assertIn("DejaVu Sans", fonts)

    def test_messages_to_html_document(self) -> None:
        from backend.report.pdf_report import messages_to_html_document

        with patch.dict(os.environ, {"CHATBI_PDF_SUMMARY_DISABLED": "1"}):
            html_doc = messages_to_html_document(
                [
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "答复示例"},
                ],
                "测试会话",
            )
        self.assertIn("测试会话", html_doc)
        self.assertIn("摘要", html_doc)
        self.assertIn("你好", html_doc)

    def test_messages_to_html_contains_chart_base64(self) -> None:
        from backend.report.pdf_report import messages_to_html_document

        chart_opt = {
            "xAxis": {"type": "category", "data": ["华东", "华北"]},
            "yAxis": {"type": "value"},
            "series": [{"type": "bar", "name": "销售额", "data": [100.0, 200.0]}],
        }
        with patch.dict(os.environ, {"CHATBI_PDF_SUMMARY_DISABLED": "1"}):
            html_doc = messages_to_html_document(
                [
                    {"role": "user", "content": "各区销售"},
                    {"role": "assistant", "content": "如下。", "chart": chart_opt},
                ],
                "测试",
            )
        self.assertIn('class="chart-img"', html_doc)
        self.assertIn("data:image/png;base64,", html_doc)

    def test_summarize_with_chatbi_completion_mock(self) -> None:
        from backend.report.pdf_report import messages_to_html_document

        mock_resp = MagicMock()
        mock_resp.choices = [
            MagicMock(message=MagicMock(content="【精炼】要点一行：销售额同比上升。"))
        ]
        with patch.dict(os.environ, {"CHATBI_PDF_SUMMARY_DISABLED": "0"}):
            with patch("backend.report.pdf_summary.chatbi_completion", return_value=mock_resp):
                html_doc = messages_to_html_document(
                    [
                        {"role": "user", "content": "很长的问题" * 20},
                        {"role": "assistant", "content": "很长的回答" * 40},
                    ],
                    "Mocked",
                )
        self.assertIn("销售额同比上升", html_doc)
        self.assertNotIn("很长的问题" * 20, html_doc)

    def test_render_session_pdf_bytes_when_weasyprint_works(self) -> None:
        from backend.report.pdf_report import render_session_pdf_bytes

        with patch.dict(os.environ, {"CHATBI_PDF_SUMMARY_DISABLED": "1"}):
            messages = [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "答复示例"},
            ]
            try:
                pdf = render_session_pdf_bytes(messages, "测试会话")
            except RuntimeError as exc:
                self.skipTest(str(exc))
        self.assertGreater(len(pdf), 500)
        if PdfReader is None:
            return
        reader = PdfReader(io.BytesIO(pdf))
        text = "".join((page.extract_text() or "") for page in reader.pages)
        self.assertIn("测试会话", text)

    def test_render_session_pdf_bytes_fallback_to_reportlab(self) -> None:
        from backend.report.pdf_report import render_session_pdf_bytes

        real_import = __import__

        def fake_import(name, *args, **kwargs):
            if name == "weasyprint":
                raise OSError("missing cairo")
            return real_import(name, *args, **kwargs)

        with patch.dict(os.environ, {"CHATBI_PDF_SUMMARY_DISABLED": "1"}):
            with patch("builtins.__import__", side_effect=fake_import):
                pdf = render_session_pdf_bytes([{"role": "user", "content": "你好"}], "降级测试")
        self.assertTrue(pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
