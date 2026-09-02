"""交付校验回归：目录、媒体题注和正文计数边界。"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_manuscript_delivery.py"
SPEC = importlib.util.spec_from_file_location("delivery_regressions", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class DeliveryPruningRegressionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.markdown = self.root / "paper.md"
        self.markdown.write_text("# 第1章 绪论\n正文 English prose here。\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_empty_toc_fails(self) -> None:
        path = self.root / "empty.pdf"
        self._pdf(path, ["封面", "目录\n更新目录"])
        verifier = MODULE.DeliveryVerifier(self.root, 1, 1000, 10)
        verifier.verify_pdf(path, True, self.markdown)
        self.assertTrue(any("PDF_TOC_ENTRIES_MISSING" in item for item in verifier.errors))

    def test_real_toc_entries_with_page_numbers_pass(self) -> None:
        path = self.root / "toc.pdf"
        self._pdf(path, ["封面", "目录\n第1章 绪论 ........ 3\n", "第1章 绪论"])
        verifier = MODULE.DeliveryVerifier(self.root, 1, 1000, 10)
        verifier.verify_pdf(path, True, self.markdown)
        self.assertFalse(any(item.startswith("PDF_TOC_") for item in verifier.errors))

    def test_metadata_alt_with_unique_caption_passes(self) -> None:
        path = self.root / "media.docx"
        xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:body>
        <w:p><w:r><w:drawing><wp:inline><wp:docPr id="1" descr="趋势图"/></wp:inline></w:drawing></w:r></w:p>
        <w:p><w:pPr><w:pStyle w:val="Caption"/></w:pPr><w:r><w:t>图1 趋势图</w:t></w:r></w:p>
        <w:p><w:r><w:t>正文参见图1即可。</w:t></w:r></w:p>
        </w:body></w:document>'''
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", xml)
        verifier = MODULE.DeliveryVerifier(self.root, 1, 1000, 10)
        verifier.verify_docx(path, None, self.markdown, False, False, 11.5)
        self.assertFalse(any("DOCX_DUPLICATE_MEDIA_CAPTION" in item for item in verifier.errors))

    def test_visible_alt_then_caption_fails_but_body_reference_is_legal(self) -> None:
        path = self.root / "media-visible-alt.docx"
        xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"><w:body>
        <w:p><w:r><w:drawing><wp:inline><wp:docPr id="1" descr="渡船意象照片"/></wp:inline></w:drawing></w:r></w:p>
        <w:p><w:r><w:t>渡船意象照片</w:t></w:r></w:p>
        <w:p><w:pPr><w:pStyle w:val="Caption"/></w:pPr><w:r><w:t>图1 边城渡船意象</w:t></w:r></w:p>
        <w:p><w:r><w:t>正文参见图1即可。</w:t></w:r></w:p>
        </w:body></w:document>'''
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("word/document.xml", xml)
        verifier = MODULE.DeliveryVerifier(self.root, 1, 1000, 10)
        verifier.verify_docx(path, None, self.markdown, False, False, 11.5)
        self.assertTrue(any("DOCX_DUPLICATE_MEDIA_CAPTION" in item for item in verifier.errors))

    def test_multiline_tex_table_and_commands_are_excluded_from_count(self) -> None:
        body = "# 第1章 绪论\nAlpha beta.\n\\begin{longtable}{ll}\n\\toprule\nTable cell words\n\\end{longtable}\n\\textbf{Gamma} delta."
        cleaned = MODULE.DeliveryVerifier.manuscript_body(body)
        self.assertEqual(len(__import__("re").findall(r"\b[A-Za-z]+(?:[-'][A-Za-z]+)*\b", cleaned)), 4)

    def test_pandoc_multiline_table_with_blank_records(self) -> None:
        source = "# 第1章 绪论\n保留正文 Alpha beta\n\n  --------------------------------\n  表头一     表头二\n  -------- --------\n  表格甲     表格乙\n\n  表格丙     表格丁\n  --------------------------------\n\n后续正文 Gamma\n"
        clean = MODULE.DeliveryVerifier.manuscript_body(source)
        self.assertNotIn("表头", clean)
        self.assertNotIn("表格", clean)
        self.assertIn("保留正文 Alpha beta", clean)
        self.assertIn("后续正文 Gamma", clean)

    def test_indented_horizontal_rule_does_not_remove_prose(self) -> None:
        source = "# 第1章 绪论\n  ------------\n正文没有列分隔线。\n  ------------\n末尾正文。"
        clean = MODULE.DeliveryVerifier.manuscript_body(source)
        self.assertIn("正文没有列分隔线", clean)
        self.assertIn("末尾正文", clean)

    def _pdf(self, path: Path, pages: list[str]) -> None:
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        document = canvas.Canvas(str(path))
        for page in pages:
            text = document.beginText(72, 760)
            text.setFont("STSong-Light", 12)
            for line in page.splitlines():
                text.textLine(line)
            document.drawText(text)
            document.showPage()
        document.save()


if __name__ == "__main__":
    unittest.main()
