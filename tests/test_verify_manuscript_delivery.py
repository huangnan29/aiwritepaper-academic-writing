#!/usr/bin/env python3
"""verify_manuscript_delivery.py的隔离测试。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_manuscript_delivery.py"
SPEC = importlib.util.spec_from_file_location("verify_manuscript_delivery", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class DeliveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        body = "正文论证。" * 20
        self.markdown = self.root / "07-paper-full.md"
        self.markdown.write_text(
            "# 摘要\n摘要不计数。\n\n# 第1章 绪论\n" + body
            + "\n\n## 1.1 问题\n" + body
            + "\n\n### 1.1.1 边界\n" + body
            + "\n\n# 参考文献\n[1] 测试文献。\n",
            encoding="utf-8",
        )
        (self.root / "03-evidence-matrix.csv").write_text(
            "source_id,title,status\nS1,测试文献,VERIFIED_FULLTEXT\n", encoding="utf-8"
        )
        (self.root / "references.bib").write_text("@article{s1, title={测试文献}}\n", encoding="utf-8")
        docx_name = "测试论文_20260824-120000.docx"
        pdf_name = "测试论文_20260824-120000.pdf"
        document_xml = '''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>第1章</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t>1.1</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="Heading3"/></w:pPr><w:r><w:t>1.1.1</w:t></w:r></w:p>
<w:p><w:r><w:instrText>TOC \\o "1-3"</w:instrText></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p/></w:tc></w:tr></w:tbl>
</w:body></w:document>'''
        with zipfile.ZipFile(self.root / docx_name, "w") as archive:
            archive.writestr("word/document.xml", document_xml)
        try:
            from pypdf import PdfWriter
            writer = PdfWriter()
            writer.add_blank_page(width=595, height=842)
            with (self.root / pdf_name).open("wb") as handle:
                writer.write(handle)
        except ImportError:
            (self.root / pdf_name).write_bytes(b"%PDF-1.4\n%%EOF")
        manifest = {
            "docx": docx_name, "pdf": pdf_name,
            "docx_sha256": hashlib.sha256((self.root / docx_name).read_bytes()).hexdigest(),
            "pdf_sha256": hashlib.sha256((self.root / pdf_name).read_bytes()).hexdigest(),
            "tables": 1, "research_status": "PARTIAL", "delivery_status": "PASS",
        }
        (self.root / "run-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def verifier(self, minimum: int = 100, maximum: int = 1000) -> MODULE.DeliveryVerifier:
        verifier = MODULE.DeliveryVerifier(self.root, minimum, maximum, 300)
        verifier.verify_body_length(self.markdown)
        verifier.verify_evidence_matrix(
            self.root / "03-evidence-matrix.csv", self.markdown, self.root / "references.bib"
        )
        verifier.verify_run_manifest(self.root / "run-manifest.json", self.markdown)
        return verifier

    def test_valid_delivery(self) -> None:
        self.assertEqual(self.verifier().errors, [])

    def test_body_length_low(self) -> None:
        self.assertTrue(any("BODY_LENGTH_LOW" in item for item in self.verifier(minimum=1000).errors))

    def test_filename_without_timestamp_fails(self) -> None:
        manifest_path = self.root / "run-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        old = self.root / manifest["docx"]
        new = self.root / "测试论文.docx"
        old.rename(new)
        manifest["docx"] = new.name
        manifest["docx_sha256"] = hashlib.sha256(new.read_bytes()).hexdigest()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(any("FINAL_FILENAME_INVALID" in item for item in self.verifier().errors))

    def test_malformed_evidence_row_fails(self) -> None:
        (self.root / "03-evidence-matrix.csv").write_text(
            "source_id,title,status\nS1,标题,作者,VERIFIED_FULLTEXT\n", encoding="utf-8"
        )
        self.assertTrue(any("EVIDENCE_MATRIX_ROW" in item for item in self.verifier().errors))

    def test_docx_table_loss_fails(self) -> None:
        manifest_path = self.root / "run-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tables"] = 2
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
        self.assertTrue(any("DOCX_TABLE_COUNT_LOW" in item for item in self.verifier().errors))


if __name__ == "__main__":
    unittest.main()
