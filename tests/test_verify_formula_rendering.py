#!/usr/bin/env python3
"""公式渲染机械检查器的隔离回归测试。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_formula_rendering.py"
SPEC = importlib.util.spec_from_file_location("verify_formula_rendering", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def make_docx(path: Path, visible_text: str, omml_count: int) -> None:
    math_nodes = "".join(
        '<m:oMath><m:r><m:t>x</m:t></m:r></m:oMath>' for _ in range(omml_count)
    )
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><w:body>'
        f'<w:p><w:r><w:t>{visible_text}</w:t></w:r>{math_nodes}</w:p>'
        '</w:body></w:document>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


class FormulaRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "equations").mkdir()
        self.markdown = self.root / "07-paper-full.md"
        self.audit = self.root / "equations/formula-audit.md"
        self.audit.write_text("# 公式审计\n符号：x；单位：无量纲；量纲：一致；视觉：已抽查。\n", encoding="utf-8")
        self.docx = self.root / "测试_20260828-120000.docx"
        self.pdf = self.root / "测试_20260828-120000.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nformula-test")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_manifest(self) -> None:
        (self.root / "run-manifest.json").write_text(json.dumps({
            "docx": self.docx.name,
            "pdf": self.pdf.name,
            "docx_sha256": hashlib.sha256(self.docx.read_bytes()).hexdigest(),
            "pdf_sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
        }), encoding="utf-8")

    def verifier(self) -> MODULE.FormulaVerifier:
        verifier = MODULE.FormulaVerifier(self.root)
        with mock.patch.object(MODULE, "pdf_metrics", return_value=(
            {"extractor": "test", "pages": 1, "raw_tex_hits": [], "visible_text_length": 10}, []
        )):
            verifier.verify(self.markdown, self.root / "run-manifest.json", self.audit)
        return verifier

    def test_valid_dollar_formulas_and_omml_pass(self) -> None:
        self.markdown.write_text("正文中有 $x+y$。\n\n$$z=\\frac{x}{y}$$\n", encoding="utf-8")
        make_docx(self.docx, "正文公式已经转换", 2)
        self.write_manifest()
        self.assertEqual(self.verifier().errors, [])

    def test_antigravity_raw_latex_in_docx_fails(self) -> None:
        self.markdown.write_text("$$\\frac{\\partial C}{\\partial t}=0$$\n", encoding="utf-8")
        make_docx(self.docx, r"$$\frac{\partial C}{\partial t}=0$$", 0)
        self.write_manifest()
        errors = self.verifier().errors
        self.assertTrue(any("DOCX_RAW_LATEX" in item for item in errors))
        self.assertTrue(any("DOCX_OMML_COUNT_LOW" in item for item in errors))

    def test_hy4_backslash_delimiters_are_rejected_before_export(self) -> None:
        self.markdown.write_text(r"行内 \(C_{\text{in}}\)，独立式 \[f_c=\frac{1}{2\pi R_f C_f}\]", encoding="utf-8")
        make_docx(self.docx, r"\(C_{\text{in}}\) \[f_c=\frac{1}{2\pi R_f C_f}\]", 0)
        self.write_manifest()
        errors = self.verifier().errors
        self.assertTrue(any("SOURCE_DELIMITER_NOT_NORMALIZED" in item for item in errors))
        self.assertTrue(any("DOCX_RAW_LATEX" in item for item in errors))

    def test_unbalanced_braces_fail(self) -> None:
        formulas, errors = MODULE.extract_formulas(r"$\frac{x}{y$")
        self.assertEqual(len(formulas), 1)
        self.assertTrue(any("SOURCE_BRACE_UNBALANCED" in item for item in errors))

    def test_python_escape_corruption_in_formula_fails(self) -> None:
        formulas, errors = MODULE.extract_formulas("$C_\text{in}=\frac{x}{y}$")
        self.assertEqual(len(formulas), 1)
        self.assertTrue(any("SOURCE_CONTROL_CHARACTER" in item for item in errors))

    def test_pdf_visible_raw_latex_fails(self) -> None:
        with mock.patch.object(MODULE, "extract_pdf_text", return_value=(r"结果为 \frac{x}{y}", "test", 1)):
            metrics, errors = MODULE.pdf_metrics(self.pdf)
        self.assertIn(r"\frac", metrics["raw_tex_hits"])
        self.assertTrue(any("PDF_RAW_LATEX" in item for item in errors))

    def test_single_dollar_delimiter_in_docx_fails(self) -> None:
        metrics, errors = MODULE.docx_metrics(self.docx)
        self.assertEqual(errors, [f"DOCX_MISSING: {self.docx}"])
        make_docx(self.docx, "$C_f=10$", 0)
        metrics, errors = MODULE.docx_metrics(self.docx)
        self.assertIn("$", metrics["raw_tex_hits"])
        self.assertTrue(any("DOCX_RAW_LATEX" in item for item in errors))

    def test_audit_file_required(self) -> None:
        self.markdown.write_text("$x=1$\n", encoding="utf-8")
        make_docx(self.docx, "公式", 1)
        self.write_manifest()
        self.audit.unlink()
        self.assertTrue(any("FORMULA_AUDIT_MISSING" in item for item in self.verifier().errors))


if __name__ == "__main__":
    unittest.main()
