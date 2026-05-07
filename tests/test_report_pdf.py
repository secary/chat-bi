"""PDF report generation."""

from __future__ import annotations

import io
import unittest

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[misc, assignment]


class ReportPdfTest(unittest.TestCase):
    def test_messages_to_html_document(self) -> None:
        from backend.report.pdf_report import messages_to_html_document

        html_doc = messages_to_html_document(
            [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "答复示例"},
            ],
            "测试会话",
        )
        self.assertIn("测试会话", html_doc)
        self.assertIn("你好", html_doc)

    def test_render_session_pdf_bytes_when_weasyprint_works(self) -> None:
        from backend.report.pdf_report import render_session_pdf_bytes

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
        self.assertIn("你好", text)


if __name__ == "__main__":
    unittest.main()
